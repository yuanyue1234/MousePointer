from __future__ import annotations

import ctypes
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
import winreg
import zipfile
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, VERTICAL, Canvas, IntVar, StringVar, Tk, Toplevel, filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None

try:
    import pystray
except Exception:
    pystray = None


IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
WORK_ROOT = APP_DIR / "_build" if IS_FROZEN else APP_DIR / "build"
OUTPUT_DIR = APP_DIR if IS_FROZEN else APP_DIR / "dist"
APP_DATA = Path(os.environ.get("APPDATA", str(Path.home()))) / "MouseCursorThemeBuilder"
SETTINGS_FILE = APP_DATA / "settings.json"
DEFAULT_STORAGE_ROOT = APP_DATA / "mouse_files"
DEFAULT_OUTPUT_ROOT = APP_DATA / "installers"
SCHEME_LIBRARY = DEFAULT_STORAGE_ROOT / "schemes"
RESOURCE_LIBRARY = DEFAULT_STORAGE_ROOT / "resources"
INSTALLED_LIBRARY = DEFAULT_STORAGE_ROOT / "installed"
SCHEDULE_FILE = APP_DATA / "schedule.json"
WEEK_SCHEDULE_FILE = APP_DATA / "week_schedule.json"
ERROR_LOG = APP_DIR / "错误记录.md"
DEFAULT_CURSOR_SIZE = 64
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RESOURCE_URL = "https://yvtgt-my.sharepoint.com/:f:/g/personal/asunny_yvtgt_onmicrosoft_com/IgAikChiblmJQqSfaLGiF-ZEAXMNYeBJLh_IlV2F8M-GVhs?e=OKbO42"


@dataclass(frozen=True)
class CursorRole:
    label: str
    reg_name: str
    file_stem: str
    hotspot_ratio: tuple[float, float]
    tip: str


CURSOR_ROLES: list[CursorRole] = [
    CursorRole("正常选择", "Arrow", "arrow", (0.02, 0.02), "普通箭头"),
    CursorRole("帮助选择", "Help", "help", (0.02, 0.02), "帮助提示"),
    CursorRole("后台运行", "AppStarting", "app_starting", (0.02, 0.02), "后台运行"),
    CursorRole("忙", "Wait", "wait", (0.50, 0.50), "系统忙碌"),
    CursorRole("精确选择", "Crosshair", "crosshair", (0.50, 0.50), "准星"),
    CursorRole("文本选择", "IBeam", "ibeam", (0.50, 0.50), "文本输入"),
    CursorRole("手写", "NWPen", "nw_pen", (0.05, 0.95), "手写笔"),
    CursorRole("不可用", "No", "no", (0.50, 0.50), "禁止"),
    CursorRole("垂直调整大小", "SizeNS", "size_ns", (0.50, 0.50), "上下拖动"),
    CursorRole("水平调整大小", "SizeWE", "size_we", (0.50, 0.50), "左右拖动"),
    CursorRole("沿对角线调整大小 1", "SizeNWSE", "size_nwse", (0.50, 0.50), "左上右下"),
    CursorRole("沿对角线调整大小 2", "SizeNESW", "size_nesw", (0.50, 0.50), "右上左下"),
    CursorRole("移动", "SizeAll", "size_all", (0.50, 0.50), "四向移动"),
    CursorRole("候选", "UpArrow", "up_arrow", (0.50, 0.02), "候选选择"),
    CursorRole("链接选择", "Hand", "hand", (0.25, 0.02), "链接"),
    CursorRole("位置选择", "Pin", "pin", (0.50, 0.50), "位置"),
    CursorRole("个人选择", "Person", "person", (0.50, 0.50), "个人"),
]

ROLE_BY_REG = {role.reg_name: role for role in CURSOR_ROLES}
DEFAULT_SCHEME_NAMES = ["01方案", "02方案"]
DEFAULT_ARCHIVE_KEYWORDS = ["小垚", "鼠鼠"]
SUPPORTED_TYPES = (
    ("图片和光标", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico *.cur *.ani"),
    ("图片", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico"),
    ("Windows 光标", "*.cur *.ani"),
    ("所有文件", "*.*"),
)


def log_error(title: str, exc: BaseException | str) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(exc, BaseException):
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        detail = str(exc)
    with ERROR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {datetime.now():%Y-%m-%d %H:%M:%S} {title}\n\n```text\n{detail}\n```\n")


def resource_path(relative: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return APP_DIR / relative


def bundled_archives() -> list[Path]:
    archives = list(APP_DIR.glob("*.zip"))
    base = getattr(sys, "_MEIPASS", None)
    if base:
        archives.extend(Path(base).glob("*.zip"))
    return list(dict.fromkeys(archives))


def load_settings() -> dict[str, str]:
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        log_error("读取设置失败", exc)
    return {}


def save_settings(data: dict[str, str]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_storage_root(path: Path) -> None:
    global SCHEME_LIBRARY, RESOURCE_LIBRARY, INSTALLED_LIBRARY
    root = path.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    SCHEME_LIBRARY = root / "schemes"
    RESOURCE_LIBRARY = root / "resources"
    INSTALLED_LIBRARY = root / "installed"
    SCHEME_LIBRARY.mkdir(parents=True, exist_ok=True)
    RESOURCE_LIBRARY.mkdir(parents=True, exist_ok=True)
    INSTALLED_LIBRARY.mkdir(parents=True, exist_ok=True)


def configured_storage_root() -> Path:
    value = load_settings().get("storage_root", "")
    return Path(value) if value else DEFAULT_STORAGE_ROOT


def configured_output_root() -> Path:
    value = load_settings().get("output_root", "")
    return Path(value) if value else DEFAULT_OUTPUT_ROOT


apply_storage_root(configured_storage_root())


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip(" ._")
    return cleaned or "我的鼠标样式"


def image_from_path(path: Path) -> Image.Image:
    if path.suffix.lower() == ".svg":
        raise RuntimeError("SVG 只作为参考图使用。请先导出 PNG 后再作为鼠标素材。")
    return Image.open(path).convert("RGBA")


def centered_rgba(image: Image.Image, size: int) -> Image.Image:
    image = ImageOps.contain(image, (size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
    return canvas


def hotspot_for(role: CursorRole, size: int) -> tuple[int, int]:
    x = int(round(role.hotspot_ratio[0] * (size - 1)))
    y = int(round(role.hotspot_ratio[1] * (size - 1)))
    return max(0, min(size - 1, x)), max(0, min(size - 1, y))


def write_png_cursor(image: Image.Image, output_path: Path, role: CursorRole, size: int) -> None:
    cursor = centered_rgba(image, size)
    png = io.BytesIO()
    cursor.save(png, format="PNG")
    data = png.getvalue()
    hot_x, hot_y = hotspot_for(role, size)
    header = struct.pack("<HHH", 0, 2, 1)
    width_byte = size if size < 256 else 0
    directory = struct.pack("<BBBBHHII", width_byte, width_byte, 0, 0, hot_x, hot_y, len(data), 22)
    output_path.write_bytes(header + directory + data)


def convert_to_cursor(source: Path, output_path: Path, role: CursorRole, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in {".cur", ".ani"}:
        shutil.copy2(source, output_path.with_suffix(source.suffix.lower()))
        return
    write_png_cursor(image_from_path(source), output_path, role, size)


def apply_cursor_scheme(theme_name: str, cursor_files: dict[str, str]) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, theme_name)
        winreg.SetValueEx(key, "Scheme Source", 0, winreg.REG_DWORD, 2)
        for reg_name, file_path in cursor_files.items():
            winreg.SetValueEx(key, reg_name, 0, winreg.REG_EXPAND_SZ, file_path)
    ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Control Panel\\Cursors", 0, 1000, None)


def installer_source(theme_name: str, files: dict[str, str]) -> str:
    return f'''import ctypes
import os
import shutil
import sys
import traceback
import winreg
from datetime import datetime
from pathlib import Path
from tkinter import Tk, messagebox

THEME_NAME = {json.dumps(theme_name, ensure_ascii=False)}
CURSOR_FILES = {json.dumps(files, ensure_ascii=False, indent=4)}


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return Path(__file__).resolve().parent / relative


def log_error(exc):
    log = Path(__file__).resolve().with_name("错误记录.md")
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"\\n## {{datetime.now():%Y-%m-%d %H:%M:%S}} 安装失败\\n\\n```text\\n{{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))}}\\n```\\n")


def install():
    target_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "MouseCursorThemes" / THEME_NAME
    target_dir.mkdir(parents=True, exist_ok=True)
    installed = {{}}
    for reg_name, file_name in CURSOR_FILES.items():
        src = resource_path("assets") / file_name
        dst = target_dir / file_name
        shutil.copy2(src, dst)
        installed[reg_name] = str(dst)

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, THEME_NAME)
        winreg.SetValueEx(key, "Scheme Source", 0, winreg.REG_DWORD, 2)
        for reg_name, file_path in installed.items():
            winreg.SetValueEx(key, reg_name, 0, winreg.REG_EXPAND_SZ, file_path)

    ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Control Panel\\\\Cursors", 0, 1000, None)
    return target_dir


def main():
    root = Tk()
    root.withdraw()
    try:
        target = install()
    except Exception as exc:
        log_error(exc)
        messagebox.showerror("鼠标样式安装失败", str(exc))
        raise
    else:
        messagebox.showinfo("鼠标样式安装完成", f"已安装：{{THEME_NAME}}\\n文件位置：{{target}}")


if __name__ == "__main__":
    main()
'''


def find_python_with_pyinstaller() -> str:
    if not IS_FROZEN:
        return sys.executable
    candidates = [
        APP_DIR.parent / ".venv" / "Scripts" / "python.exe",
        APP_DIR / ".venv" / "Scripts" / "python.exe",
        shutil.which("python"),
        shutil.which("python3"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        result = subprocess.run([str(path), "-c", "import PyInstaller"], text=True, capture_output=True, check=False)
        if result.returncode == 0:
            return str(path)
    raise RuntimeError("找不到包含 PyInstaller 的 Python。请先运行 requirements.txt 安装依赖。")


def find_winrar() -> Path | None:
    for command in ("WinRAR.exe", "Rar.exe", "rar.exe"):
        found = shutil.which(command)
        if found:
            return Path(found)
    for path in (
        Path(os.environ.get("ProgramFiles", "")) / "WinRAR" / "WinRAR.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "WinRAR" / "WinRAR.exe",
    ):
        if path.exists():
            return path
    return None


def parse_drop_paths(data: str, tk_root: Tk) -> list[Path]:
    return [Path(item) for item in tk_root.tk.splitlist(data)]


def cursor_preview_image(path: Path, box: tuple[int, int] = (180, 140)) -> Image.Image:
    margin = 8
    if path.suffix.lower() in {".cur", ".ani"}:
        size = max(24, min(box) - margin * 2)
        rendered = render_cursor_with_windows(path, size)
        if rendered:
            bg = Image.new("RGBA", box, (248, 250, 252, 255))
            bg.alpha_composite(rendered, ((box[0] - rendered.width) // 2, (box[1] - rendered.height) // 2))
            return bg
    image = centered_rgba(image_from_path(path), max(16, min(box) - margin * 2))
    bg = Image.new("RGBA", box, (248, 250, 252, 255))
    bg.alpha_composite(image, ((box[0] - image.width) // 2, (box[1] - image.height) // 2))
    return bg


def render_cursor_with_windows(path: Path, size: int) -> Image.Image | None:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    IMAGE_CURSOR = 2
    LR_LOADFROMFILE = 0x10
    DI_NORMAL = 0x3
    hcursor = user32.LoadImageW(None, str(path), IMAGE_CURSOR, size, size, LR_LOADFROMFILE)
    if not hcursor:
        return None
    hdc_screen = user32.GetDC(None)
    hdc = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, size, size)
    old = gdi32.SelectObject(hdc, hbmp)
    brush = gdi32.CreateSolidBrush(0x00FAF8F8)
    rect = (ctypes.c_long * 4)(0, 0, size, size)
    user32.FillRect(hdc, ctypes.byref(rect), brush)
    user32.DrawIconEx(hdc, 0, 0, hcursor, size, size, 0, None, DI_NORMAL)
    raw = ctypes.create_string_buffer(size * size * 4)
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32),
        ]
    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = size
    bmi.bmiHeader.biHeight = -size
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    gdi32.GetDIBits(hdc, hbmp, 0, size, raw, ctypes.byref(bmi), 0)
    gdi32.SelectObject(hdc, old)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteObject(brush)
    gdi32.DeleteDC(hdc)
    user32.ReleaseDC(None, hdc_screen)
    user32.DestroyCursor(hcursor)
    return Image.frombuffer("RGBA", (size, size), raw, "raw", "BGRA", 0, 1)


def map_files_to_roles(files: list[Path]) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    names = [(p, p.name.lower()) for p in files if p.suffix.lower() in {".cur", ".ani"}]
    rules = [
        ("Arrow", ["normal", "arrow", "select", "选中", "选择", "鼠鼠0"]),
        ("Help", ["help", "question", "问号", "疑问"]),
        ("AppStarting", ["working", "app", "后台", "等不及"]),
        ("Wait", ["busy", "wait", "等待"]),
        ("Crosshair", ["cross", "十字"]),
        ("IBeam", ["beam", "text", "打字"]),
        ("NWPen", ["pen", "铅笔"]),
        ("No", ["no", "unavailable", "禁止"]),
        ("SizeNS", ["sizens", "vert", "上下"]),
        ("SizeWE", ["sizewe", "horiz", "左右"]),
        ("SizeNWSE", ["nwse", "斜1"]),
        ("SizeNESW", ["nesw", "斜2"]),
        ("SizeAll", ["all", "move", "移动"]),
        ("UpArrow", ["up", "向上", "alternate"]),
        ("Hand", ["hand", "link", "手指"]),
    ]
    for reg, keys in rules:
        for path, name in names:
            if path in mapping.values():
                continue
            if any(key in name for key in keys):
                mapping[reg] = path
                break
    numbered = {p.stem: p for p, name in names if p.stem.isdigit()}
    number_roles = [
        "Arrow", "Help", "AppStarting", "Wait", "Crosshair", "IBeam", "NWPen", "No",
        "SizeNS", "SizeWE", "SizeNWSE", "SizeNESW", "SizeAll", "UpArrow", "Hand",
    ]
    for index, reg in enumerate(number_roles, start=1):
        key = f"{index:02d}"
        if reg not in mapping and key in numbered:
            mapping[reg] = numbered[key]
    return mapping


def parse_inf_mapping(root: Path) -> dict[str, Path]:
    infs = list(root.rglob("*.inf"))
    files = [p for p in root.rglob("*") if p.suffix.lower() in {".cur", ".ani"}]
    if not infs:
        return map_files_to_roles(files)
    raw = infs[0].read_bytes()
    text = ""
    for encoding in ("utf-16", "utf-8-sig", "gbk", "cp936", "latin1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "Cursors" in text or "Control Panel" in text:
            break
    mapping: dict[str, Path] = {}
    by_name = {p.name.lower(): p for p in files}
    for reg in ROLE_BY_REG:
        match = re.search(rf"HKCU,\s*\"Control Panel\\Cursors\",\s*{reg}\s*,[^,]*,\s*\"?([^\"\\r\\n]+)\"?", text, re.I)
        if match:
            raw_name = match.group(1).strip()
            var_match = re.fullmatch(r".*%([^%]+)%", raw_name)
            if var_match:
                variable = var_match.group(1)
                string_match = re.search(rf"^\s*{re.escape(variable)}\s*=\s*\"?([^\"\\r\\n]+)\"?", text, re.I | re.M)
                raw_name = string_match.group(1).strip() if string_match else raw_name
            name = Path(raw_name).name.lower()
            if name in by_name:
                mapping[reg] = by_name[name]
    mapping.update({k: v for k, v in map_files_to_roles(files).items() if k not in mapping})
    return mapping


def extract_import_package(source: Path) -> Path:
    target = WORK_ROOT / "imports" / sanitize_name(source.stem)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            archive.extractall(target)
        return target
    if source.suffix.lower() == ".7z":
        import py7zr
        with py7zr.SevenZipFile(source, mode="r") as archive:
            archive.extractall(target)
        return target
    if source.suffix.lower() == ".rar":
        try:
            import rarfile
            with rarfile.RarFile(source) as archive:
                archive.extractall(target)
            return target
        except Exception:
            pass
    if source.suffix.lower() == ".exe":
        if extract_pyinstaller_assets(source, target):
            return target
    result = subprocess.run(["tar", "-xf", str(source), "-C", str(target)], text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return target
    raise RuntimeError(f"无法解压 {source.name}。该文件可能不是可读取的压缩包，或 EXE 不是自解压格式。")


def set_auto_start(enabled: bool) -> None:
    command = subprocess.list2cmdline(background_command())
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "MouseCursorThemeBuilder", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "MouseCursorThemeBuilder")
            except FileNotFoundError:
                pass


def background_command() -> list[str]:
    if IS_FROZEN:
        return [str(Path(sys.executable).resolve()), "--background"]
    return [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), "--background"]


def start_background_process() -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS
    subprocess.Popen(
        background_command(),
        cwd=str(APP_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def acquire_background_lock():
    pid_file = APP_DATA / "background.pid"
    APP_DATA.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(pid_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            return fd
        except FileExistsError:
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip() or "0")
            except Exception:
                pid = 0
            if not pid:
                time.sleep(0.1)
                continue
            if pid and process_exists(pid):
                return None
            try:
                pid_file.unlink()
            except FileNotFoundError:
                pass
        except Exception:
            return None


def process_exists(pid: int) -> bool:
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def extract_pyinstaller_assets(source: Path, target: Path) -> bool:
    data = source.read_bytes()
    magic = b"MEI\014\013\012\013\016"
    cookie_offset = data.rfind(magic)
    if cookie_offset < 0:
        return False
    cookie_format = "!8sIIII64s"
    cookie_size = struct.calcsize(cookie_format)
    if cookie_offset + cookie_size > len(data):
        return False
    _, archive_length, toc_offset, toc_length, _pyvers, _pylib = struct.unpack(cookie_format, data[cookie_offset:cookie_offset + cookie_size])
    archive_start = cookie_offset + cookie_size - archive_length
    toc_start = archive_start + toc_offset
    toc_end = toc_start + toc_length
    if archive_start < 0 or toc_start < 0 or toc_end > len(data):
        return False
    entry_format = "!IIIIBc"
    entry_size = struct.calcsize(entry_format)
    pos = toc_start
    extracted = 0
    while pos < toc_end:
        entry_length, entry_offset, data_length, _uncompressed_length, compression_flag, _typecode = struct.unpack(entry_format, data[pos:pos + entry_size])
        pos += entry_size
        name_length = entry_length - entry_size
        name = data[pos:pos + name_length].rstrip(b"\0").decode("utf-8", errors="replace")
        pos += name_length
        normalized = name.replace("\\", "/")
        if normalized.startswith("assets/") and Path(normalized).suffix.lower() in {".cur", ".ani", ".png", ".ico"}:
            payload = data[archive_start + entry_offset:archive_start + entry_offset + data_length]
            if compression_flag:
                payload = zlib.decompress(payload)
            output = target / normalized
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(payload)
            extracted += 1
    return extracted > 0


class CursorThemeBuilder:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("鼠标指针配置生成器")
        self.root.geometry("1180x780")
        self.root.minsize(980, 680)

        self.theme_name = StringVar(value=DEFAULT_SCHEME_NAMES[0])
        self.selected: dict[str, Path] = {}
        self.path_vars: dict[str, StringVar] = {}
        self.ref_images: dict[str, ImageTk.PhotoImage] = {}
        self.preview_images: dict[str, ImageTk.PhotoImage] = {}
        self.preview_labels: dict[str, ttk.Label] = {}
        self.schedule_items: list[dict[str, str]] = []
        self.week_items: dict[str, str] = {}
        self.scheduler_running = False
        self.scheduler_thread: threading.Thread | None = None
        self.last_schedule_key = ""

        self.configure_style()
        self.ensure_default_schemes()
        self.load_schedule()
        self.load_week_schedule()
        self.build_ui()
        self.refresh_scheme_names()
        self.refresh_schedule_list()

    def configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self.root.configure(bg="#f5f7fb")
        style.configure("TFrame", background="#f5f7fb")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Row.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f5f7fb", foreground="#172033", font=("Microsoft YaHei UI", 10))
        style.configure("Panel.TLabel", background="#ffffff")
        style.configure("Title.TLabel", background="#f5f7fb", foreground="#111827", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Subtle.TLabel", background="#f5f7fb", foreground="#64748b", font=("Microsoft YaHei UI", 9))
        style.configure("Small.Panel.TLabel", background="#ffffff", foreground="#64748b", font=("Microsoft YaHei UI", 8))
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=(12, 8))
        style.configure("TButton", padding=(10, 6))

    def build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="鼠标指针配置生成器", style="Title.TLabel").pack(side=LEFT)
        ttk.Label(header, text="拖入文件，生成可安装的鼠标方案", style="Subtle.TLabel").pack(side=LEFT, padx=(14, 0), pady=(8, 0))
        ttk.Button(header, text="定时切换", command=self.open_time_schedule).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(header, text="星期切换", command=self.open_week_schedule).pack(side=RIGHT)

        controls = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        controls.pack(fill="x", pady=(12, 10))
        ttk.Label(controls, text="方案名称", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.scheme_combo = ttk.Combobox(controls, textvariable=self.theme_name, values=DEFAULT_SCHEME_NAMES, width=24)
        self.scheme_combo.grid(row=0, column=1, sticky="w", padx=(8, 16))
        ttk.Button(controls, text="系统鼠标大小设置", command=self.open_pointer_settings).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(controls, text="Tips：建议调整大小后再应用。", style="Panel.TLabel").grid(row=0, column=3, sticky="w", padx=(12, 0))
        ttk.Button(controls, text="导入安装包/压缩包", command=self.import_package).grid(row=0, column=4, padx=(12, 0))
        ttk.Button(controls, text="保存到方案库", command=self.save_current_scheme).grid(row=0, column=5, padx=(8, 0))
        controls.columnconfigure(3, weight=1)

        body = ttk.Frame(outer)
        body.pack(fill=BOTH, expand=True)

        list_panel = ttk.Frame(body, style="Panel.TFrame", padding=(10, 8))
        list_panel.pack(side=LEFT, fill=BOTH, expand=True)
        head = ttk.Frame(list_panel, style="Panel.TFrame")
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text="参考", style="Panel.TLabel", width=8).grid(row=0, column=0, sticky="w")
        ttk.Label(head, text="鼠标状态", style="Panel.TLabel", width=18).grid(row=0, column=1, sticky="w")
        ttk.Label(head, text="拖入或选择文件", style="Panel.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Label(head, text="预览", style="Panel.TLabel", width=10).grid(row=0, column=3, sticky="e")

        canvas = Canvas(list_panel, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_panel, orient=VERTICAL, command=canvas.yview)
        self.rows = ttk.Frame(canvas, style="Panel.TFrame")
        self.rows.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rows, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")

        for index, role in enumerate(CURSOR_ROLES):
            self.add_row(index, role)

        side = ttk.Frame(body, style="Panel.TFrame", padding=12)
        side.pack(side=RIGHT, fill="y", padx=(12, 0))
        ttk.Label(side, text="实时预览", style="Panel.TLabel", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor="w")
        ttk.Label(side, text="支持 PNG/JPG/ICO/CUR/ANI。选择左侧文件后这里会显示大预览。", style="Small.Panel.TLabel", wraplength=260).pack(anchor="w", pady=(2, 10))
        self.large_preview = ttk.Label(side, text="未选择", style="Panel.TLabel", anchor="center")
        self.large_preview.pack(fill="both", expand=True, pady=(0, 10))
        self.large_preview_name = ttk.Label(side, text="", style="Small.Panel.TLabel", wraplength=260)
        self.large_preview_name.pack(anchor="w")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="应用到当前电脑", style="Primary.TButton", command=self.apply_now).pack(side=LEFT)
        ttk.Button(actions, text="生成安装包", style="Primary.TButton", command=self.build_installer).pack(side=LEFT, padx=10)
        ttk.Button(actions, text="打开输出文件夹", command=lambda: os.startfile(OUTPUT_DIR)).pack(side=LEFT)
        ttk.Button(actions, text="清空选择", command=self.clear_all).pack(side=LEFT, padx=10)
        self.status = StringVar(value="选择或拖入图片。未选择的状态不会被修改。")
        ttk.Label(actions, textvariable=self.status, style="Subtle.TLabel").pack(side=RIGHT)

    def add_row(self, index: int, role: CursorRole) -> None:
        row = ttk.Frame(self.rows, style="Row.TFrame", padding=(8, 5))
        row.grid(row=index, column=0, sticky="ew", pady=2)
        row.columnconfigure(2, weight=1)

        ref = ttk.Label(row, style="Panel.TLabel", width=7, anchor="center")
        ref.grid(row=0, column=0, sticky="w")
        ref_image = self.load_reference_icon(role)
        if ref_image:
            ref.configure(image=ref_image)
            self.ref_images[role.reg_name] = ref_image

        ttk.Label(row, text=role.label, style="Panel.TLabel", width=18).grid(row=0, column=1, sticky="w", padx=(8, 6))
        var = StringVar(value="拖入文件，或点击选择")
        self.path_vars[role.reg_name] = var
        path_label = ttk.Label(row, textvariable=var, style="Small.Panel.TLabel", width=48)
        path_label.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        ttk.Button(row, text="选择", command=lambda r=role: self.pick_file(r)).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(row, text="清除", command=lambda r=role: self.clear_file(r)).grid(row=0, column=4, padx=(0, 8))
        preview = ttk.Label(row, text="未选", style="Panel.TLabel", width=10, anchor="center")
        preview.grid(row=0, column=5)
        self.preview_labels[role.reg_name] = preview

        if DND_FILES:
            for widget in (row, path_label, preview, ref):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", lambda event, r=role: self.drop_file(event, r))

    def load_reference_icon(self, role: CursorRole) -> ImageTk.PhotoImage | None:
        icon_path = resource_path(f"assets/role_icons/{role.file_stem}.png")
        if not icon_path.exists():
            return None
        image = Image.open(icon_path).convert("RGBA")
        image = centered_rgba(image, 44)
        return ImageTk.PhotoImage(image)

    def pick_file(self, role: CursorRole) -> None:
        file_name = filedialog.askopenfilename(title=f"选择 {role.label}", filetypes=SUPPORTED_TYPES)
        if file_name:
            self.assign_file(role, Path(file_name))

    def drop_file(self, event, role: CursorRole) -> None:
        paths = parse_drop_paths(event.data, self.root)
        if paths:
            self.assign_file(role, paths[0])

    def assign_file(self, role: CursorRole, path: Path) -> None:
        try:
            self.update_preview(role, path)
        except Exception as exc:
            log_error("读取素材失败", exc)
            messagebox.showerror("无法读取素材", str(exc))
            return
        self.selected[role.reg_name] = path
        self.path_vars[role.reg_name].set(path.name)
        self.update_large_preview(path)
        self.status.set(f"已选择：{role.label} -> {path.name}")

    def update_preview(self, role: CursorRole, path: Path) -> None:
        label = self.preview_labels[role.reg_name]
        preview_size = 56
        if path.suffix.lower() in {".cur", ".ani"}:
            image = cursor_preview_image(path, (104, 72))
            photo = ImageTk.PhotoImage(image)
            self.preview_images[role.reg_name] = photo
            label.configure(image=photo, text="")
            return
        image = centered_rgba(image_from_path(path), preview_size)
        bg = Image.new("RGBA", (104, 72), (248, 250, 252, 255))
        draw = ImageDraw.Draw(bg)
        draw.rectangle((0, 0, 103, 71), outline=(203, 213, 225, 255))
        bg.alpha_composite(image, ((104 - image.width) // 2, (72 - image.height) // 2))
        photo = ImageTk.PhotoImage(bg)
        self.preview_images[role.reg_name] = photo
        label.configure(image=photo, text="")

    def update_large_preview(self, path: Path) -> None:
        image = cursor_preview_image(path, (260, 220))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 259, 219), outline=(203, 213, 225, 255))
        photo = ImageTk.PhotoImage(image)
        self.preview_images["_large"] = photo
        self.large_preview.configure(image=photo, text="")
        self.large_preview_name.configure(text=str(path))

    def on_size_change(self) -> None:
        return

    def clear_file(self, role: CursorRole) -> None:
        self.selected.pop(role.reg_name, None)
        self.path_vars[role.reg_name].set("拖入文件，或点击选择")
        self.preview_labels[role.reg_name].configure(text="未选", image="")
        self.preview_images.pop(role.reg_name, None)

    def clear_all(self) -> None:
        for role in CURSOR_ROLES:
            self.clear_file(role)
        self.status.set("已清空选择。")

    def open_pointer_settings(self) -> None:
        try:
            os.startfile("ms-settings:easeofaccess-mousepointer")
        except Exception:
            os.startfile("control.exe")

    def refresh_scheme_names(self) -> None:
        names = list(DEFAULT_SCHEME_NAMES)
        if SCHEME_LIBRARY.exists():
            names.extend(path.name for path in SCHEME_LIBRARY.iterdir() if path.is_dir())
        names = sorted(dict.fromkeys(names))
        self.scheme_combo.configure(values=names)
        if hasattr(self, "schedule_combo"):
            self.schedule_combo.configure(values=names)

    def ensure_default_schemes(self) -> None:
        for archive in bundled_archives():
            name = sanitize_name(archive.stem)
            scheme_dir = SCHEME_LIBRARY / name
            if (scheme_dir / "scheme.json").exists():
                continue
            try:
                extracted = extract_import_package(archive)
                mapping = parse_inf_mapping(extracted)
                if not mapping:
                    continue
                scheme_dir.mkdir(parents=True, exist_ok=True)
                files: dict[str, str] = {}
                for reg_name, source in mapping.items():
                    role = ROLE_BY_REG.get(reg_name)
                    if not role:
                        continue
                    output_name = f"{role.file_stem}{source.suffix.lower()}"
                    shutil.copy2(source, scheme_dir / output_name)
                    files[reg_name] = output_name
                self.save_library_manifest(name, files, scheme_dir)
            except Exception as exc:
                log_error(f"导入默认方案失败：{archive.name}", exc)

    def import_package(self) -> None:
        file_name = filedialog.askopenfilename(
            title="导入鼠标安装包或压缩包",
            filetypes=(("安装包和压缩包", "*.zip *.rar *.7z *.exe"), ("所有文件", "*.*")),
        )
        if not file_name:
            return
        source = Path(file_name)
        try:
            extracted = extract_import_package(source)
            mapping = parse_inf_mapping(extracted)
            if not mapping:
                raise RuntimeError("没有找到可识别的 .inf/.cur/.ani 鼠标方案文件。")
            for reg_name, path in mapping.items():
                role = ROLE_BY_REG.get(reg_name)
                if role:
                    self.assign_file(role, path)
            self.theme_name.set(sanitize_name(source.stem))
            self.status.set(f"已导入：{source.name}")
        except Exception as exc:
            log_error("导入安装包失败", exc)
            messagebox.showerror("导入失败", str(exc))

    def selected_roles(self) -> list[CursorRole]:
        return [role for role in CURSOR_ROLES if role.reg_name in self.selected]

    def validate(self) -> str | None:
        if not self.selected:
            return "请至少选择一个鼠标状态图片。"
        for path in self.selected.values():
            if not path.exists():
                return f"文件不存在：{path}"
        return None

    def prepare_assets(self, package_dir: Path) -> dict[str, str]:
        assets_dir = package_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
        assets_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        size = DEFAULT_CURSOR_SIZE
        for role in self.selected_roles():
            source = self.selected[role.reg_name]
            suffix = source.suffix.lower()
            output_name = f"{role.file_stem}{suffix if suffix in {'.cur', '.ani'} else '.cur'}"
            output = assets_dir / output_name
            convert_to_cursor(source, output.with_suffix(".cur") if suffix not in {".cur", ".ani"} else output, role, size)
            files[role.reg_name] = output_name
        return files

    def install_assets_to_scheme(self, theme: str, files: dict[str, str], assets_dir: Path) -> Path:
        target_dir = INSTALLED_LIBRARY / theme
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in files.values():
            shutil.copy2(assets_dir / name, target_dir / name)
        return target_dir

    def apply_now(self) -> None:
        error = self.validate()
        if error:
            messagebox.showwarning("还不能应用", error)
            return
        theme = sanitize_name(self.theme_name.get())
        try:
            package_dir = WORK_ROOT / "current_theme"
            files = self.prepare_assets(package_dir)
            target_dir = self.install_assets_to_scheme(theme, files, package_dir / "assets")
            apply_cursor_scheme(theme, {reg_name: str(target_dir / name) for reg_name, name in files.items()})
            self.save_library_manifest(theme, files, target_dir)
        except Exception as exc:
            log_error("应用失败", exc)
            messagebox.showerror("应用失败", str(exc))
            return
        self.status.set(f"已应用：{theme}")

    def save_current_scheme(self) -> None:
        error = self.validate()
        if error:
            messagebox.showwarning("还不能保存", error)
            return
        theme = sanitize_name(self.theme_name.get())
        try:
            package_dir = WORK_ROOT / "library_save"
            files = self.prepare_assets(package_dir)
            scheme_dir = SCHEME_LIBRARY / theme
            if scheme_dir.exists():
                shutil.rmtree(scheme_dir)
            shutil.copytree(package_dir / "assets", scheme_dir)
            self.save_library_manifest(theme, files, scheme_dir)
            self.refresh_scheme_names()
        except Exception as exc:
            log_error("保存方案失败", exc)
            messagebox.showerror("保存方案失败", str(exc))
            return
        self.status.set(f"已保存到方案库：{theme}")

    def save_library_manifest(self, theme: str, files: dict[str, str], folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {"name": theme, "files": files, "size": DEFAULT_CURSOR_SIZE, "saved_at": datetime.now().isoformat()}
        (folder / "scheme.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def apply_saved_scheme(self, theme: str) -> None:
        scheme_dir = SCHEME_LIBRARY / theme
        manifest_path = scheme_dir / "scheme.json"
        if not manifest_path.exists():
            raise RuntimeError(f"方案库中没有找到：{theme}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest.get("files", {})
        apply_cursor_scheme(theme, {reg_name: str(scheme_dir / name) for reg_name, name in files.items()})

    def build_installer(self) -> None:
        error = self.validate()
        if error:
            messagebox.showwarning("还不能生成", error)
            return
        theme = sanitize_name(self.theme_name.get())
        try:
            package_dir = WORK_ROOT / "installer_package"
            package_dir.mkdir(parents=True, exist_ok=True)
            files = self.prepare_assets(package_dir)
            installer_py = package_dir / "install_cursor_theme.py"
            installer_py.write_text(installer_source(theme, files), encoding="utf-8")
            exe_name = f"{theme}_鼠标样式安装器"
            installer_exe = self.build_pyinstaller_exe(installer_py, package_dir / "assets", exe_name)
            winrar = find_winrar()
            if winrar:
                packaged = self.build_winrar_sfx(winrar, installer_exe, exe_name)
                self.status.set(f"已生成 WinRAR 自解压包：{packaged}")
                messagebox.showinfo("生成完成", f"已生成 WinRAR 自解压包：\n{packaged}")
            else:
                self.status.set(f"未发现 WinRAR，已生成独立 EXE：{installer_exe}")
                messagebox.showinfo("生成完成", f"未发现 WinRAR，已生成独立 EXE：\n{installer_exe}")
        except Exception as exc:
            log_error("生成安装包失败", exc)
            messagebox.showerror("生成失败", str(exc))

    def build_pyinstaller_exe(self, installer_py: Path, assets_dir: Path, exe_name: str) -> Path:
        python = find_python_with_pyinstaller()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        command = [
            python,
            "-m",
            "PyInstaller",
            "--noconsole",
            "--onefile",
            "--clean",
            "--name",
            exe_name,
            "--distpath",
            str(OUTPUT_DIR),
            "--workpath",
            str(WORK_ROOT / "pyinstaller"),
            "--specpath",
            str(WORK_ROOT / "spec"),
            "--add-data",
            f"{assets_dir};assets",
            str(installer_py),
        ]
        self.status.set("正在生成独立安装器...")
        self.root.update_idletasks()
        result = subprocess.run(command, cwd=APP_DIR, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            log_path = WORK_ROOT / "pyinstaller_error.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8", errors="replace")
            raise RuntimeError(f"PyInstaller 打包失败，日志：{log_path}")
        return OUTPUT_DIR / f"{exe_name}.exe"

    def build_winrar_sfx(self, winrar: Path, installer_exe: Path, exe_name: str) -> Path:
        comment = WORK_ROOT / "winrar_sfx.txt"
        comment.parent.mkdir(parents=True, exist_ok=True)
        comment.write_text(
            f";The comment below contains SFX script commands\nSetup={installer_exe.name}\nTempMode\nOverwrite=1\nTitle={exe_name}\n",
            encoding="utf-8",
        )
        output = OUTPUT_DIR / f"{exe_name}_WinRAR自解压.exe"
        command = [str(winrar), "a", "-sfx", f"-z{comment}", str(output), str(installer_exe)]
        result = subprocess.run(command, cwd=OUTPUT_DIR, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            log_path = WORK_ROOT / "winrar_error.log"
            log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8", errors="replace")
            raise RuntimeError(f"WinRAR 封装失败，已保留独立 EXE：{installer_exe}，日志：{log_path}")
        return output

    def load_schedule(self) -> None:
        try:
            if SCHEDULE_FILE.exists():
                data = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
                self.schedule_items = data if isinstance(data, list) else []
        except Exception as exc:
            log_error("读取定时配置失败", exc)
            self.schedule_items = []

    def save_schedule(self) -> None:
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_FILE.write_text(json.dumps(self.schedule_items, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_week_schedule(self) -> None:
        try:
            if WEEK_SCHEDULE_FILE.exists():
                data = json.loads(WEEK_SCHEDULE_FILE.read_text(encoding="utf-8"))
                self.week_items = data if isinstance(data, dict) else {}
        except Exception as exc:
            log_error("读取星期配置失败", exc)
            self.week_items = {}

    def save_week_schedule(self) -> None:
        WEEK_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        WEEK_SCHEDULE_FILE.write_text(json.dumps(self.week_items, ensure_ascii=False, indent=2), encoding="utf-8")

    def open_time_schedule(self) -> None:
        dialog = self.create_dialog("定时切换", 430, 240)
        values = list(self.scheme_combo.cget("values"))
        current = {item.get("mode"): item for item in self.schedule_items}
        rows = [("light", "亮色模式"), ("dark", "暗色模式")]
        vars_by_mode: dict[str, tuple[StringVar, StringVar]] = {}
        for row, (mode, label) in enumerate(rows):
            ttk.Label(dialog, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=14, pady=12)
            time_var = StringVar(value=current.get(mode, {}).get("time", "09:00" if mode == "light" else "18:00"))
            scheme_var = StringVar(value=current.get(mode, {}).get("scheme", values[0] if values else ""))
            ttk.Combobox(dialog, textvariable=time_var, values=[f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)], width=8).grid(row=row, column=1)
            ttk.Combobox(dialog, textvariable=scheme_var, values=values, width=22).grid(row=row, column=2, padx=8)
            ttk.Button(dialog, text="×", width=3, command=lambda m=mode: self.clear_schedule_mode(m, dialog)).grid(row=row, column=3)
            vars_by_mode[mode] = (time_var, scheme_var)

        def save() -> None:
            try:
                items = [item for item in self.schedule_items if item.get("mode") not in {"light", "dark"}]
                for mode, (time_var, scheme_var) in vars_by_mode.items():
                    at = time_var.get().strip()
                    scheme = scheme_var.get().strip()
                    if scheme:
                        self.validate_time(at)
                        items.append({"mode": mode, "time": at, "scheme": scheme})
                self.schedule_items = items
                self.save_schedule()
                set_auto_start(True)
                self.start_scheduler()
                dialog.winfo_toplevel().destroy()
                self.status.set("定时切换已保存，已开启自启动后台。")
            except Exception as exc:
                log_error("保存定时切换失败", exc)
                messagebox.showerror("保存失败", str(exc))

        ttk.Button(dialog, text="保存并开启自启动", command=save).grid(row=3, column=0, columnspan=4, sticky="ew", padx=14, pady=(18, 6))

    def clear_schedule_mode(self, mode: str, dialog=None) -> None:
        self.schedule_items = [item for item in self.schedule_items if item.get("mode") != mode]
        self.save_schedule()
        self.status.set(f"已清除 {mode} 定时。")
        if dialog:
            dialog.winfo_toplevel().destroy()

    def open_week_schedule(self) -> None:
        dialog = self.create_dialog("星期切换", 450, 420)
        values = [""] + list(self.scheme_combo.cget("values"))
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        vars_by_day: dict[str, StringVar] = {}
        for row, day in enumerate(weekdays):
            ttk.Label(dialog, text=day, style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=14, pady=7)
            var = StringVar(value=self.week_items.get(str(row), ""))
            ttk.Combobox(dialog, textvariable=var, values=values, width=28).grid(row=row, column=1, padx=8)
            ttk.Button(dialog, text="×", width=3, command=lambda v=var: v.set("")).grid(row=row, column=2)
            vars_by_day[str(row)] = var

        def save() -> None:
            self.week_items = {day: var.get().strip() for day, var in vars_by_day.items() if var.get().strip()}
            self.save_week_schedule()
            set_auto_start(True)
            self.start_scheduler()
            dialog.winfo_toplevel().destroy()
            self.status.set("星期切换已保存，已开启自启动后台。")

        ttk.Button(dialog, text="保存并开启自启动", command=save).grid(row=8, column=0, columnspan=3, sticky="ew", padx=14, pady=(12, 6))

    def create_dialog(self, title: str, width: int, height: int):
        top = Toplevel(self.root)
        top.title(title)
        top.geometry(f"{width}x{height}")
        top.configure(bg="#ffffff")
        top.transient(self.root)
        top.grab_set()
        frame = ttk.Frame(top, style="Panel.TFrame", padding=8)
        frame.pack(fill=BOTH, expand=True)
        return frame

    def refresh_schedule_list(self) -> None:
        return

    def validate_time(self, at: str) -> None:
        if not re.fullmatch(r"\d{2}:\d{2}", at):
            raise RuntimeError("时间格式必须是 HH:MM。")
        hour, minute = map(int, at.split(":"))
        if hour > 23 or minute > 59:
            raise RuntimeError("时间范围必须是 00:00 到 23:59。")

    def toggle_scheduler(self) -> None:
        self.scheduler_running = not self.scheduler_running
        if self.scheduler_running:
            self.start_scheduler()
        self.status.set("定时切换已启动。" if self.scheduler_running else "定时切换已停止。")

    def start_scheduler(self) -> None:
        self.scheduler_running = True
        if not self.scheduler_thread:
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()

    def scheduler_loop(self) -> None:
        while True:
            if self.scheduler_running:
                now = datetime.now().strftime("%H:%M")
                for item in list(self.schedule_items):
                    key = f"{datetime.now():%Y-%m-%d}|{item['time']}|{item['scheme']}"
                    if item["time"] == now and key != self.last_schedule_key:
                        try:
                            self.apply_saved_scheme(item["scheme"])
                            self.last_schedule_key = key
                            self.root.after(0, lambda name=item["scheme"]: self.status.set(f"定时已切换：{name}"))
                        except Exception as exc:
                            log_error("定时切换失败", exc)
                day = str(datetime.now().weekday())
                scheme = self.week_items.get(day)
                week_key = f"{datetime.now():%Y-%m-%d}|week|{scheme}"
                if scheme and week_key != self.last_schedule_key:
                    try:
                        self.apply_saved_scheme(scheme)
                        self.last_schedule_key = week_key
                        if hasattr(self, "root"):
                            self.root.after(0, lambda name=scheme: self.status.set(f"星期已切换：{name}"))
                    except Exception as exc:
                        log_error("星期切换失败", exc)
            time.sleep(20)


def main() -> None:
    if "--background" in sys.argv:
        run_background()
        return
    root_class = TkinterDnD.Tk if TkinterDnD else Tk
    root = root_class()
    CursorThemeBuilder(root)
    root.mainloop()


def run_background() -> None:
    lock = acquire_background_lock()
    if lock is None:
        return
    last_key = ""
    while True:
        try:
            items = []
            if SCHEDULE_FILE.exists():
                data = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
                items = data if isinstance(data, list) else []
            week_items = {}
            if WEEK_SCHEDULE_FILE.exists():
                data = json.loads(WEEK_SCHEDULE_FILE.read_text(encoding="utf-8"))
                week_items = data if isinstance(data, dict) else {}
            now = datetime.now()
            for item in items:
                key = f"{now:%Y-%m-%d}|{item.get('time')}|{item.get('scheme')}"
                if item.get("time") == now.strftime("%H:%M") and key != last_key:
                    apply_library_scheme(item.get("scheme", ""))
                    last_key = key
            scheme = week_items.get(str(now.weekday()))
            key = f"{now:%Y-%m-%d}|week|{scheme}"
            if scheme and key != last_key:
                apply_library_scheme(scheme)
                last_key = key
        except Exception as exc:
            log_error("后台切换失败", exc)
        time.sleep(30)


def apply_library_scheme(theme: str) -> None:
    scheme_dir = SCHEME_LIBRARY / theme
    manifest_path = scheme_dir / "scheme.json"
    if not manifest_path.exists():
        raise RuntimeError(f"方案库中没有找到：{theme}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files", {})
    apply_cursor_scheme(theme, {reg_name: str(scheme_dir / name) for reg_name, name in files.items()})


def ani_frame_paths(path: Path) -> list[Path]:
    data = path.read_bytes()
    frames: list[Path] = []
    offset = 0
    cache_dir = WORK_ROOT / "ani_frames" / sanitize_name(path.stem)
    cache_dir.mkdir(parents=True, exist_ok=True)
    while True:
        index = data.find(b"icon", offset)
        if index < 0 or index + 8 > len(data):
            break
        size = int.from_bytes(data[index + 4:index + 8], "little", signed=False)
        payload = data[index + 8:index + 8 + size]
        if len(payload) > 22:
            frame_path = cache_dir / f"frame_{len(frames):03d}.cur"
            frame_path.write_bytes(payload)
            frames.append(frame_path)
        offset = index + 8 + size + (size % 2)
    return frames[:60]


def scheme_manifest(theme: str) -> tuple[Path, dict[str, str]]:
    scheme_dir = SCHEME_LIBRARY / theme
    manifest_path = scheme_dir / "scheme.json"
    if not manifest_path.exists():
        return scheme_dir, {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return scheme_dir, manifest.get("files", {})


def _new_configure_style(self) -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    self.root.configure(bg="#f7f7f7")
    style.configure("TFrame", background="#f7f7f7")
    style.configure("Side.TFrame", background="#f4f4f4")
    style.configure("Panel.TFrame", background="#ffffff")
    style.configure("Row.TFrame", background="#ffffff")
    style.configure("Hover.Row.TFrame", background="#f1f6ff")
    style.configure("TLabel", background="#f7f7f7", foreground="#202020", font=("Segoe UI", 10))
    style.configure("Side.TLabel", background="#f4f4f4", foreground="#1f1f1f", font=("Segoe UI", 10))
    style.configure("Panel.TLabel", background="#ffffff", foreground="#202020", font=("Segoe UI", 10))
    style.configure("Muted.Panel.TLabel", background="#ffffff", foreground="#666666", font=("Segoe UI", 9))
    style.configure("Title.TLabel", background="#ffffff", foreground="#1f1f1f", font=("Segoe UI", 20, "bold"))
    style.configure("Nav.TButton", anchor="w", padding=(14, 8))
    style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
    style.configure("TButton", padding=(10, 6))


def _new_build_ui(self) -> None:
    self.root.title("鼠标指针配置生成器")
    self.root.geometry("1180x760")
    self.root.minsize(1040, 680)
    self.animation_after = None
    self.animation_frames = []
    self.animation_index = 0
    self.row_frames = {}
    self.autostart_enabled = IntVar(value=1 if self.is_auto_start_enabled() else 0)

    icon_path = resource_path("icon.png")
    if icon_path.exists():
        try:
            icon = ImageTk.PhotoImage(Image.open(icon_path).convert("RGBA").resize((32, 32)))
            self.preview_images["_window_icon"] = icon
            self.root.iconphoto(True, icon)
        except Exception as exc:
            log_error("加载窗口图标失败", exc)

    shell = ttk.Frame(self.root)
    shell.pack(fill=BOTH, expand=True)
    sidebar = ttk.Frame(shell, style="Side.TFrame", padding=(0, 10))
    sidebar.pack(side=LEFT, fill="y")
    ttk.Label(sidebar, text="  Mouse Theme", style="Side.TLabel", font=("Segoe UI", 11, "bold")).pack(fill="x", pady=(0, 16))
    for text, command in (
        ("  鼠标方案", lambda: None),
        ("  定时切换", self.open_time_schedule),
        ("  星期切换", self.open_week_schedule),
        ("  鼠标大小设置", self.open_pointer_settings),
    ):
        ttk.Button(sidebar, text=text, style="Nav.TButton", command=command).pack(fill="x", padx=8, pady=2)
    ttk.Label(sidebar, text="  建议调整大小后再应用。", style="Side.TLabel", wraplength=140).pack(side="bottom", fill="x", padx=8, pady=14)

    main = ttk.Frame(shell, style="Panel.TFrame", padding=18)
    main.pack(side=LEFT, fill=BOTH, expand=True)
    header = ttk.Frame(main, style="Panel.TFrame")
    header.pack(fill="x")
    ttk.Label(header, text="Personalization", style="Title.TLabel").pack(side=LEFT)
    ttk.Button(header, text="定时切换", command=self.open_time_schedule).pack(side=RIGHT, padx=(8, 0))
    ttk.Button(header, text="星期切换", command=self.open_week_schedule).pack(side=RIGHT)

    controls = ttk.Frame(main, style="Panel.TFrame")
    controls.pack(fill="x", pady=(18, 10))
    ttk.Label(controls, text="方案", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
    self.scheme_combo = ttk.Combobox(controls, textvariable=self.theme_name, width=22, state="readonly")
    self.scheme_combo.grid(row=0, column=1, padx=(8, 12), sticky="w")
    self.scheme_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_scheme_to_ui(self.theme_name.get()))
    ttk.Checkbutton(controls, text="自启动后台", variable=self.autostart_enabled, command=self.apply_autostart).grid(row=0, column=2, padx=(0, 12))
    ttk.Label(controls, text="Tips：建议调整大小后再应用。", style="Muted.Panel.TLabel").grid(row=0, column=3, sticky="w")
    ttk.Button(controls, text="导入", command=self.import_package).grid(row=0, column=4, padx=(12, 0))
    ttk.Button(controls, text="保存方案", command=self.save_current_scheme).grid(row=0, column=5, padx=(8, 0))
    controls.columnconfigure(3, weight=1)

    content = ttk.Frame(main, style="Panel.TFrame")
    content.pack(fill=BOTH, expand=True)
    list_panel = ttk.Frame(content, style="Panel.TFrame")
    list_panel.pack(side=LEFT, fill=BOTH, expand=True)
    ttk.Label(list_panel, text="Select mouse pointers", style="Panel.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
    canvas = Canvas(list_panel, bg="#ffffff", highlightthickness=1, highlightbackground="#e3e3e3")
    scrollbar = ttk.Scrollbar(list_panel, orient=VERTICAL, command=canvas.yview)
    self.rows = ttk.Frame(canvas, style="Panel.TFrame")
    self.rows.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=self.rows, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill="y")
    for index, role in enumerate(CURSOR_ROLES):
        self.add_row(index, role)

    preview = ttk.Frame(content, style="Panel.TFrame", padding=(16, 0, 0, 0))
    preview.pack(side=RIGHT, fill="y")
    ttk.Label(preview, text="Live preview", style="Panel.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
    self.large_preview = ttk.Label(preview, text="悬停或选择一行", style="Panel.TLabel", anchor="center")
    self.large_preview.pack(fill="both", expand=True, pady=(10, 8))
    self.large_preview_name = ttk.Label(preview, text="", style="Muted.Panel.TLabel", wraplength=260)
    self.large_preview_name.pack(anchor="w")

    actions = ttk.Frame(main, style="Panel.TFrame")
    actions.pack(fill="x", pady=(12, 0))
    ttk.Button(actions, text="应用", style="Primary.TButton", command=self.apply_now).pack(side=LEFT)
    ttk.Button(actions, text="生成安装包", command=self.build_installer).pack(side=LEFT, padx=8)
    ttk.Button(actions, text="打开输出", command=lambda: os.startfile(OUTPUT_DIR)).pack(side=LEFT)
    self.status = StringVar(value="选择方案或导入鼠标包。悬停下方配置会实时切换预览。")
    ttk.Label(actions, textvariable=self.status, style="Muted.Panel.TLabel").pack(side=RIGHT)


def _new_add_row(self, index: int, role: CursorRole) -> None:
    row = ttk.Frame(self.rows, style="Row.TFrame", padding=(10, 8))
    row.grid(row=index, column=0, sticky="ew")
    row.columnconfigure(2, weight=1)
    self.row_frames[role.reg_name] = row
    ref = ttk.Label(row, style="Panel.TLabel", width=6, anchor="center")
    ref.grid(row=0, column=0, sticky="w")
    ref_image = self.load_reference_icon(role)
    if ref_image:
        ref.configure(image=ref_image)
        self.ref_images[role.reg_name] = ref_image
    ttk.Label(row, text=role.label, style="Panel.TLabel", width=18).grid(row=0, column=1, sticky="w", padx=(8, 8))
    var = StringVar(value="未配置")
    self.path_vars[role.reg_name] = var
    path_label = ttk.Label(row, textvariable=var, style="Muted.Panel.TLabel", width=42)
    path_label.grid(row=0, column=2, sticky="ew")
    ttk.Button(row, text="选择", command=lambda r=role: self.pick_file(r)).grid(row=0, column=3, padx=8)
    preview = ttk.Label(row, text="", style="Panel.TLabel", width=12, anchor="center")
    preview.grid(row=0, column=4)
    self.preview_labels[role.reg_name] = preview

    def enter(_event=None, r=role):
        row.configure(style="Hover.Row.TFrame")
        path = self.selected.get(r.reg_name)
        if path:
            self.update_large_preview(path)
            self.status.set(f"预览：{r.label}")

    def leave(_event=None):
        row.configure(style="Row.TFrame")

    for widget in (row, ref, path_label, preview):
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        if DND_FILES:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda event, r=role: self.drop_file(event, r))


def _new_update_preview(self, role: CursorRole, path: Path) -> None:
    label = self.preview_labels[role.reg_name]
    image = cursor_preview_image(path, (92, 54))
    photo = ImageTk.PhotoImage(image)
    self.preview_images[role.reg_name] = photo
    label.configure(image=photo, text="")


def _new_update_large_preview(self, path: Path) -> None:
    if getattr(self, "animation_after", None):
        self.root.after_cancel(self.animation_after)
        self.animation_after = None
    frames = []
    if path.suffix.lower() == ".ani":
        for frame in ani_frame_paths(path):
            frames.append(cursor_preview_image(frame, (260, 220)))
    if not frames:
        frames = [cursor_preview_image(path, (260, 220))]
    self.animation_frames = [ImageTk.PhotoImage(frame) for frame in frames]
    self.animation_index = 0

    def tick():
        if not self.animation_frames:
            return
        self.large_preview.configure(image=self.animation_frames[self.animation_index], text="")
        self.preview_images["_large_current"] = self.animation_frames[self.animation_index]
        self.animation_index = (self.animation_index + 1) % len(self.animation_frames)
        if len(self.animation_frames) > 1:
            self.animation_after = self.root.after(120, tick)

    tick()
    self.large_preview_name.configure(text=str(path))


def _new_refresh_scheme_names(self) -> None:
    names = list(DEFAULT_SCHEME_NAMES)
    if SCHEME_LIBRARY.exists():
        names.extend(path.name for path in SCHEME_LIBRARY.iterdir() if path.is_dir() and path.name not in names)
    self.scheme_combo.configure(values=names)
    if self.theme_name.get() not in names and names:
        self.theme_name.set(names[0])
    if hasattr(self, "schedule_combo"):
        self.schedule_combo.configure(values=names)
    if names:
        self.load_scheme_to_ui(self.theme_name.get())


def _new_ensure_default_schemes(self) -> None:
    SCHEME_LIBRARY.mkdir(parents=True, exist_ok=True)
    archives = bundled_archives()[:2]
    old_names = [sanitize_name(path.stem) for path in archives]
    for old in old_names:
        old_dir = SCHEME_LIBRARY / old
        if old_dir.exists():
            shutil.rmtree(old_dir, ignore_errors=True)
    for index, archive in enumerate(archives):
        name = DEFAULT_SCHEME_NAMES[index]
        scheme_dir = SCHEME_LIBRARY / name
        if (scheme_dir / "scheme.json").exists():
            continue
        try:
            extracted = extract_import_package(archive)
            mapping = parse_inf_mapping(extracted)
            scheme_dir.mkdir(parents=True, exist_ok=True)
            files = {}
            for reg_name, source in mapping.items():
                role = ROLE_BY_REG.get(reg_name)
                if role:
                    output_name = f"{role.file_stem}{source.suffix.lower()}"
                    shutil.copy2(source, scheme_dir / output_name)
                    files[reg_name] = output_name
            self.save_library_manifest(name, files, scheme_dir)
        except Exception as exc:
            log_error(f"导入默认方案失败：{archive.name}", exc)


def _new_load_scheme_to_ui(self, theme: str) -> None:
    scheme_dir, files = scheme_manifest(theme)
    if not files:
        return
    self.clear_all()
    for reg_name, file_name in files.items():
        role = ROLE_BY_REG.get(reg_name)
        path = scheme_dir / file_name
        if role and path.exists():
            self.selected[reg_name] = path
            self.path_vars[reg_name].set(path.name)
            self.update_preview(role, path)
    first = next(iter(self.selected.values()), None)
    if first:
        self.update_large_preview(first)
    self.status.set(f"已切换方案：{theme}")


def _new_assign_file(self, role: CursorRole, path: Path) -> None:
    try:
        self.update_preview(role, path)
        self.update_large_preview(path)
    except Exception as exc:
        log_error("读取素材失败", exc)
        messagebox.showerror("无法读取素材", str(exc))
        return
    self.selected[role.reg_name] = path
    self.path_vars[role.reg_name].set(path.name)
    self.status.set(f"已选择：{role.label} -> {path.name}")


def _new_apply_now(self) -> None:
    overlay = Toplevel(self.root)
    overlay.title("正在应用")
    overlay.geometry("320x140")
    overlay.transient(self.root)
    overlay.grab_set()
    frame = ttk.Frame(overlay, style="Panel.TFrame", padding=24)
    frame.pack(fill=BOTH, expand=True)
    ttk.Label(frame, text="正在应用鼠标方案...", style="Panel.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
    progress = ttk.Progressbar(frame, mode="indeterminate")
    progress.pack(fill="x", pady=18)
    progress.start(12)
    self.root.update_idletasks()

    def work():
        try:
            set_auto_start(bool(self.autostart_enabled.get()))
            theme = sanitize_name(self.theme_name.get())
            if not self.selected:
                self.load_scheme_to_ui(theme)
            error = self.validate()
            if error:
                raise RuntimeError(error)
            package_dir = WORK_ROOT / "current_theme"
            files = self.prepare_assets(package_dir)
            target_dir = self.install_assets_to_scheme(theme, files, package_dir / "assets")
            apply_cursor_scheme(theme, {reg_name: str(target_dir / name) for reg_name, name in files.items()})
            self.save_library_manifest(theme, files, target_dir)
            self.root.after(0, lambda: self.status.set(f"已应用：{theme}"))
        except Exception as exc:
            log_error("应用失败", exc)
            self.root.after(0, lambda e=exc: messagebox.showerror("应用失败", str(e)))
        finally:
            self.root.after(0, overlay.destroy)

    threading.Thread(target=work, daemon=True).start()


def _is_auto_start_enabled(self) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, "MouseCursorThemeBuilder")
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _apply_autostart(self) -> None:
    try:
        set_auto_start(bool(self.autostart_enabled.get()))
        self.status.set("自启动已开启。" if self.autostart_enabled.get() else "自启动已关闭。")
    except Exception as exc:
        log_error("设置自启动失败", exc)
        messagebox.showerror("设置失败", str(exc))


CursorThemeBuilder.configure_style = _new_configure_style
CursorThemeBuilder.build_ui = _new_build_ui
CursorThemeBuilder.add_row = _new_add_row
CursorThemeBuilder.update_preview = _new_update_preview
CursorThemeBuilder.update_large_preview = _new_update_large_preview
CursorThemeBuilder.refresh_scheme_names = _new_refresh_scheme_names
CursorThemeBuilder.ensure_default_schemes = _new_ensure_default_schemes
CursorThemeBuilder.load_scheme_to_ui = _new_load_scheme_to_ui
CursorThemeBuilder.assign_file = _new_assign_file
CursorThemeBuilder.apply_now = _new_apply_now
CursorThemeBuilder.is_auto_start_enabled = _is_auto_start_enabled
CursorThemeBuilder.apply_autostart = _apply_autostart


def _ui_icon(self, name: str, size: int = 18) -> ImageTk.PhotoImage | None:
    path = resource_path(f"assets/ui_icons_png/{name}.png")
    if not path.exists():
        return None
    key = f"_ui_{name}_{size}"
    if key not in self.preview_images:
        image = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        self.preview_images[key] = ImageTk.PhotoImage(image)
    return self.preview_images[key]


def _clean_page(self) -> None:
    if getattr(self, "animation_after", None):
        try:
            self.root.after_cancel(self.animation_after)
        except Exception:
            pass
        self.animation_after = None
    if getattr(self, "resource_preview_after", None):
        try:
            self.root.after_cancel(self.resource_preview_after)
        except Exception:
            pass
        self.resource_preview_after = None
    for child in self.content.winfo_children():
        child.destroy()


def _v2_configure_style(self) -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    self.root.configure(bg="#f4f8ff")
    style.configure("Shell.TFrame", background="#f4f8ff")
    style.configure("Side.TFrame", background="#f7fbff")
    style.configure("Page.TFrame", background="#ffffff")
    style.configure("Card.TFrame", background="#ffffff")
    style.configure("Odd.TFrame", background="#ffffff")
    style.configure("Even.TFrame", background="#f7fbff")
    style.configure("Hover.TFrame", background="#eef6ff")
    style.configure("TLabel", background="#ffffff", foreground="#1f2937", font=("Microsoft YaHei UI", 10))
    style.configure("Side.TLabel", background="#f7fbff", foreground="#263449", font=("Microsoft YaHei UI", 10))
    style.configure("Muted.TLabel", background="#ffffff", foreground="#6b7280", font=("Microsoft YaHei UI", 9))
    style.configure("Title.TLabel", background="#ffffff", foreground="#111827", font=("Microsoft YaHei UI", 20, "bold"))
    style.configure("Nav.TButton", anchor="w", padding=(12, 10), relief="flat", borderwidth=0)
    style.map("Nav.TButton", background=[("active", "#eaf4ff")])
    style.configure("Soft.TButton", padding=(12, 8), relief="flat", borderwidth=1)
    style.map("Soft.TButton", background=[("active", "#eef6ff")])
    style.configure("Primary.TButton", padding=(16, 9), foreground="#ffffff", background="#3b82f6", borderwidth=0)
    style.map("Primary.TButton", background=[("active", "#2563eb")])
    style.configure("Danger.TButton", padding=(12, 8), foreground="#9f1239")
    style.configure("TCheckbutton", background="#ffffff")


def _v2_build_ui(self) -> None:
    self.root.title("鼠标指针配置生成器")
    self.root.geometry("1200x780")
    self.root.minsize(1060, 700)
    self.animation_after = None
    self.animation_frames = []
    self.animation_index = 0
    self.row_frames = {}
    self.autostart_enabled = IntVar(value=1 if self.is_auto_start_enabled() else 0)

    icon_path = resource_path("icon.png")
    if icon_path.exists():
        icon = ImageTk.PhotoImage(Image.open(icon_path).convert("RGBA").resize((32, 32)))
        self.preview_images["_window_icon"] = icon
        self.root.iconphoto(True, icon)

    shell = ttk.Frame(self.root, style="Shell.TFrame")
    shell.pack(fill=BOTH, expand=True)
    side = ttk.Frame(shell, style="Side.TFrame", padding=(10, 12))
    side.pack(side=LEFT, fill="y")
    ttk.Label(side, text="鼠标配置", style="Side.TLabel", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(0, 16))
    self.nav_buttons = {}
    for key, text, icon_name, command in (
        ("scheme", "鼠标方案", "mouse", self.show_scheme_page),
        ("library", "资源库", "folder", self.show_resource_page),
        ("time", "时间切换", "clock", self.show_time_page),
        ("week", "星期切换", "calendar", self.show_week_page),
    ):
        btn = ttk.Button(side, text=f"  {text}", image=self._ui_icon(icon_name), compound=LEFT, style="Nav.TButton", command=command)
        btn.pack(fill="x", pady=4)
        self.nav_buttons[key] = btn
    settings_btn = ttk.Button(side, text="  设置", image=self._ui_icon("settings"), compound=LEFT, style="Nav.TButton", command=self.show_settings_page)
    settings_btn.pack(side="bottom", fill="x", pady=4)
    self.nav_buttons["settings"] = settings_btn
    ttk.Label(side, text="清爽简约风格\n淡蓝与淡黄背景", style="Side.TLabel", wraplength=140).pack(side="bottom", anchor="w", pady=12)

    main = ttk.Frame(shell, style="Page.TFrame", padding=22)
    main.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 0))
    self.page_title = ttk.Label(main, text="", style="Title.TLabel")
    self.page_title.pack(anchor="w")
    self.page_subtitle = ttk.Label(main, text="", style="Muted.TLabel")
    self.page_subtitle.pack(anchor="w", pady=(4, 18))
    self.content = ttk.Frame(main, style="Page.TFrame")
    self.content.pack(fill=BOTH, expand=True)
    self.status = StringVar(value="请选择方案。")
    ttk.Label(main, textvariable=self.status, style="Muted.TLabel").pack(anchor="e", pady=(10, 0))
    self.show_scheme_page()


def _v2_show_scheme_page(self) -> None:
    self._clean_page()
    self.page_title.configure(text="鼠标方案")
    self.page_subtitle.configure(text="选择方案、导入配置或编辑每个鼠标状态。悬停到下方行会实时预览。")

    top = ttk.Frame(self.content, style="Card.TFrame")
    top.pack(fill="x", pady=(0, 12))
    ttk.Label(top, text="方案", font=("Microsoft YaHei UI", 11, "bold")).pack(side=LEFT)
    self.scheme_combo = ttk.Combobox(top, textvariable=self.theme_name, width=20, state="readonly")
    self.scheme_combo.pack(side=LEFT, padx=(10, 8))
    self.scheme_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_scheme_to_ui(self.theme_name.get()))
    ttk.Button(top, text="新建", image=self._ui_icon("plus"), compound=LEFT, style="Soft.TButton", command=self.new_scheme).pack(side=LEFT, padx=4)
    ttk.Button(top, text="删除", image=self._ui_icon("trash"), compound=LEFT, style="Danger.TButton", command=self.delete_scheme).pack(side=LEFT, padx=4)
    ttk.Button(top, text="导入", image=self._ui_icon("upload"), compound=LEFT, style="Soft.TButton", command=self.import_package).pack(side=LEFT, padx=4)
    ttk.Button(top, text="保存", image=self._ui_icon("folder"), compound=LEFT, style="Soft.TButton", command=self.save_current_scheme).pack(side=LEFT, padx=4)

    split = ttk.Frame(self.content, style="Page.TFrame")
    split.pack(fill=BOTH, expand=True)
    left = ttk.Frame(split, style="Card.TFrame")
    left.pack(side=LEFT, fill=BOTH, expand=True)
    right = ttk.Frame(split, style="Card.TFrame", padding=(18, 0, 0, 0))
    right.pack(side=RIGHT, fill=BOTH)

    canvas = Canvas(left, bg="#ffffff", highlightthickness=1, highlightbackground="#dbeafe")
    scrollbar = ttk.Scrollbar(left, orient=VERTICAL, command=canvas.yview)
    self.rows = ttk.Frame(canvas, style="Card.TFrame")
    self.rows.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=self.rows, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill="y")
    self.path_vars = {}
    self.preview_labels = {}
    self.row_frames = {}
    for index, role in enumerate(CURSOR_ROLES):
        self.add_row(index, role)

    ttk.Label(right, text="实时预览", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w")
    self.preview_canvas = Canvas(right, width=360, height=360, bg="#fbfdff", highlightthickness=1, highlightbackground="#dbeafe")
    self.preview_canvas.pack(fill=BOTH, expand=True, pady=(10, 8))
    self.preview_canvas.bind("<Motion>", self.preview_motion)
    self.preview_canvas.bind("<Leave>", self.preview_leave)
    self.large_preview_name = ttk.Label(right, text="", style="Muted.TLabel", wraplength=330)
    self.large_preview_name.pack(anchor="w")

    actions = ttk.Frame(self.content, style="Card.TFrame")
    actions.pack(fill="x", pady=(12, 0))
    ttk.Button(actions, text="应用", image=self._ui_icon("apply"), compound=LEFT, style="Primary.TButton", command=self.apply_now).pack(side=LEFT)
    ttk.Button(actions, text="鼠标大小设置", image=self._ui_icon("settings"), compound=LEFT, style="Soft.TButton", command=self.open_pointer_settings).pack(side=LEFT, padx=8)
    ttk.Button(actions, text="生成安装包", style="Soft.TButton", command=self.build_installer).pack(side=LEFT, padx=4)
    ttk.Checkbutton(actions, text="自启动后台", variable=self.autostart_enabled).pack(side=RIGHT)
    ttk.Label(actions, text="建议调整大小后再应用。", style="Muted.TLabel").pack(side=RIGHT, padx=14)

    self.refresh_scheme_names()


def _available_scheme_values() -> list[str]:
    names = list(DEFAULT_SCHEME_NAMES)
    if SCHEME_LIBRARY.exists():
        names.extend(path.name for path in SCHEME_LIBRARY.iterdir() if path.is_dir() and path.name not in names)
    return names


def _v2_add_row(self, index: int, role: CursorRole) -> None:
    style_name = "Even.TFrame" if index % 2 else "Odd.TFrame"
    row = ttk.Frame(self.rows, style=style_name, padding=(10, 8))
    row.grid(row=index, column=0, sticky="ew")
    row.columnconfigure(2, weight=1)
    self.row_frames[role.reg_name] = (row, style_name)
    ref = ttk.Label(row, width=7, anchor="center")
    ref.grid(row=0, column=0, sticky="w")
    ref_image = self.load_reference_icon(role)
    if ref_image:
        ref.configure(image=ref_image)
        self.ref_images[role.reg_name] = ref_image
    ttk.Label(row, text=role.label, width=18).grid(row=0, column=1, sticky="w", padx=(8, 8))
    var = StringVar(value="未配置")
    self.path_vars[role.reg_name] = var
    path_label = ttk.Label(row, textvariable=var, style="Muted.TLabel", width=42)
    path_label.grid(row=0, column=2, sticky="ew")
    ttk.Button(row, text="选择", style="Soft.TButton", command=lambda r=role: self.pick_file(r)).grid(row=0, column=3, padx=8)
    preview = ttk.Label(row, text="", width=10, anchor="center")
    preview.grid(row=0, column=4)
    self.preview_labels[role.reg_name] = preview

    def enter(_event=None, r=role):
        row.configure(style="Hover.TFrame")
        path = self.selected.get(r.reg_name)
        if path:
            self.update_large_preview(path)

    def leave(_event=None, original=style_name):
        row.configure(style=original)

    for widget in (row, ref, path_label, preview):
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        if DND_FILES:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda event, r=role: self.drop_file(event, r))


def _v2_update_preview(self, role: CursorRole, path: Path) -> None:
    label = self.preview_labels[role.reg_name]
    image = cursor_preview_image(path, (64, 64))
    photo = ImageTk.PhotoImage(image)
    self.preview_images[role.reg_name] = photo
    label.configure(image=photo, text="")


def _v2_update_large_preview(self, path: Path) -> None:
    if getattr(self, "animation_after", None):
        self.root.after_cancel(self.animation_after)
        self.animation_after = None
    frames = []
    if path.suffix.lower() == ".ani":
        for frame in ani_frame_paths(path):
            frames.append(cursor_preview_image(frame, (170, 170)))
    if not frames:
        frames = [cursor_preview_image(path, (170, 170))]
    self.animation_frames = [ImageTk.PhotoImage(frame) for frame in frames]
    self.animation_index = 0
    self.preview_x = 180
    self.preview_y = 180
    self.current_preview_path = path

    def tick():
        if not getattr(self, "preview_canvas", None) or not self.animation_frames:
            return
        try:
            self.preview_canvas.delete("cursor")
            photo = self.animation_frames[self.animation_index]
            self.preview_canvas.create_image(self.preview_x, self.preview_y, image=photo, tags="cursor")
            self.preview_images["_large_current"] = photo
            self.animation_index = (self.animation_index + 1) % len(self.animation_frames)
            if len(self.animation_frames) > 1:
                self.animation_after = self.root.after(120, tick)
        except Exception:
            self.animation_after = None

    tick()
    self.large_preview_name.configure(text=str(path))


def _preview_motion(self, event) -> None:
    if not getattr(self, "animation_frames", None):
        return
    self.preview_x = event.x
    self.preview_y = event.y
    self.preview_canvas.delete("cursor")
    photo = self.animation_frames[self.animation_index % len(self.animation_frames)]
    self.preview_canvas.create_image(self.preview_x, self.preview_y, image=photo, tags="cursor")
    self.preview_images["_large_current"] = photo


def _preview_leave(self, _event=None) -> None:
    if not getattr(self, "animation_frames", None):
        return
    self.preview_x = 180
    self.preview_y = 180
    self.preview_canvas.delete("cursor")
    photo = self.animation_frames[self.animation_index % len(self.animation_frames)]
    self.preview_canvas.create_image(self.preview_x, self.preview_y, image=photo, tags="cursor")
    self.preview_images["_large_current"] = photo


def _new_scheme(self) -> None:
    existing = set(self.scheme_combo.cget("values"))
    index = 1
    while f"新方案{index:02d}" in existing:
        index += 1
    name = f"新方案{index:02d}"
    self.theme_name.set(name)
    self.clear_all()
    self.save_library_manifest(name, {}, SCHEME_LIBRARY / name)
    self.refresh_scheme_names()
    self.status.set(f"已新建：{name}")


def _delete_scheme(self) -> None:
    name = self.theme_name.get()
    if name in DEFAULT_SCHEME_NAMES:
        messagebox.showwarning("不能删除", "默认方案不能删除。")
        return
    path = SCHEME_LIBRARY / name
    if path.exists():
        shutil.rmtree(path)
    self.theme_name.set(DEFAULT_SCHEME_NAMES[0])
    self.refresh_scheme_names()
    self.status.set(f"已删除：{name}")


def _v2_clear_file(self, role: CursorRole) -> None:
    self.selected.pop(role.reg_name, None)
    if role.reg_name in self.path_vars:
        self.path_vars[role.reg_name].set("未配置")
    if role.reg_name in self.preview_labels:
        self.preview_labels[role.reg_name].configure(text="", image="")
    self.preview_images.pop(role.reg_name, None)


def _v2_clear_all(self) -> None:
    for role in CURSOR_ROLES:
        self.clear_file(role)
    if hasattr(self, "preview_canvas"):
        self.preview_canvas.delete("cursor")
    if hasattr(self, "large_preview_name"):
        self.large_preview_name.configure(text="")
    self.selected = {}
    self.status.set("已清空当前方案配置。")


def _show_time_page(self) -> None:
    self._clean_page()
    self.page_title.configure(text="时间切换")
    self.page_subtitle.configure(text="设置亮色模式和暗色模式在指定时间切换到对应方案。")
    values = _available_scheme_values()
    current = {item.get("mode"): item for item in self.schedule_items}
    form = ttk.Frame(self.content, style="Card.TFrame")
    form.pack(fill="x")
    vars_by_mode = {}
    for row, (mode, label, default_time) in enumerate((("light", "亮色模式", "08:00"), ("dark", "暗色模式", "18:00"))):
        ttk.Label(form, text=label, font=("Microsoft YaHei UI", 11, "bold")).grid(row=row, column=0, sticky="w", padx=8, pady=12)
        time_var = StringVar(value=current.get(mode, {}).get("time", default_time))
        scheme_var = StringVar(value=current.get(mode, {}).get("scheme", values[0] if values else ""))
        ttk.Combobox(form, textvariable=time_var, values=[f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)], width=10, state="readonly").grid(row=row, column=1, padx=8)
        ttk.Combobox(form, textvariable=scheme_var, values=values, width=24, state="readonly").grid(row=row, column=2, padx=8)
        ttk.Button(form, text="×", style="Danger.TButton", width=3, command=lambda m=mode, tv=time_var, sv=scheme_var: self.clear_time_row(m, tv, sv)).grid(row=row, column=3, padx=8)
        vars_by_mode[mode] = (time_var, scheme_var)
    ttk.Checkbutton(form, text="自启动后台", variable=self.autostart_enabled).grid(row=3, column=0, sticky="w", padx=8, pady=16)
    ttk.Button(form, text="应用", image=self._ui_icon("apply"), compound=LEFT, style="Primary.TButton", command=lambda: self.save_time_page(vars_by_mode)).grid(row=3, column=2, sticky="e", padx=8)


def _save_time_page(self, vars_by_mode) -> None:
    try:
        items = [item for item in self.schedule_items if item.get("mode") not in {"light", "dark"}]
        for mode, (time_var, scheme_var) in vars_by_mode.items():
            at = time_var.get().strip()
            scheme = scheme_var.get().strip()
            if scheme:
                self.validate_time(at)
                items.append({"mode": mode, "time": at, "scheme": scheme})
        self.schedule_items = items
        self.save_schedule()
        set_auto_start(bool(self.autostart_enabled.get()))
        self.start_scheduler()
        self.status.set("时间切换已应用。")
    except Exception as exc:
        log_error("保存时间切换失败", exc)
        messagebox.showerror("保存失败", str(exc))


def _clear_time_row(self, mode: str, time_var: StringVar, scheme_var: StringVar) -> None:
    scheme_var.set("")
    self.clear_schedule_mode(mode)
    self.status.set("已清除该时间切换项。")


def _show_week_page(self) -> None:
    self._clean_page()
    self.page_title.configure(text="星期切换")
    self.page_subtitle.configure(text="为每一天选择要自动应用的鼠标方案。")
    values = [""] + _available_scheme_values()
    form = ttk.Frame(self.content, style="Card.TFrame")
    form.pack(fill="x")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    vars_by_day = {}
    for row, day in enumerate(weekdays):
        ttk.Label(form, text=day).grid(row=row, column=0, sticky="w", padx=8, pady=8)
        var = StringVar(value=self.week_items.get(str(row), ""))
        ttk.Combobox(form, textvariable=var, values=values, width=28, state="readonly").grid(row=row, column=1, padx=8)
        ttk.Button(form, text="×", style="Danger.TButton", width=3, command=lambda v=var: v.set("")).grid(row=row, column=2, padx=8)
        vars_by_day[str(row)] = var
    ttk.Checkbutton(form, text="自启动后台", variable=self.autostart_enabled).grid(row=8, column=0, sticky="w", padx=8, pady=16)
    ttk.Button(form, text="应用", image=self._ui_icon("apply"), compound=LEFT, style="Primary.TButton", command=lambda: self.save_week_page(vars_by_day)).grid(row=8, column=1, sticky="e", padx=8)


def _save_week_page(self, vars_by_day) -> None:
    self.week_items = {day: var.get().strip() for day, var in vars_by_day.items() if var.get().strip()}
    self.save_week_schedule()
    set_auto_start(bool(self.autostart_enabled.get()))
    self.start_scheduler()
    self.status.set("星期切换已应用。")


CursorThemeBuilder._ui_icon = _ui_icon
CursorThemeBuilder._clean_page = _clean_page
CursorThemeBuilder.configure_style = _v2_configure_style
CursorThemeBuilder.build_ui = _v2_build_ui
CursorThemeBuilder.show_scheme_page = _v2_show_scheme_page
CursorThemeBuilder.add_row = _v2_add_row
CursorThemeBuilder.update_preview = _v2_update_preview
CursorThemeBuilder.update_large_preview = _v2_update_large_preview
CursorThemeBuilder.preview_motion = _preview_motion
CursorThemeBuilder.preview_leave = _preview_leave
CursorThemeBuilder.new_scheme = _new_scheme
CursorThemeBuilder.delete_scheme = _delete_scheme
CursorThemeBuilder.clear_file = _v2_clear_file
CursorThemeBuilder.clear_all = _v2_clear_all
CursorThemeBuilder.show_time_page = _show_time_page
CursorThemeBuilder.save_time_page = _save_time_page
CursorThemeBuilder.clear_time_row = _clear_time_row
CursorThemeBuilder.show_week_page = _show_week_page
CursorThemeBuilder.save_week_page = _save_week_page


def _v3_available_values() -> list[str]:
    return _available_scheme_values()


def _v3_build_ui(self) -> None:
    self.root.title("鼠标指针配置生成器")
    self.root.geometry("1280x820")
    self.root.minsize(1180, 760)
    self.animation_after = None
    self.animation_frames = []
    self.animation_index = 0
    self.row_frames = {}
    self.tray_icon = None
    self.tray_running = False
    self.resource_preview_after = None
    self.resource_preview_frames = []
    self.resource_preview_labels = []
    self.resource_preview_index = 0
    self.autostart_enabled = IntVar(value=1 if self.is_auto_start_enabled() else 0)
    self.import_tip = StringVar(value="")

    icon_path = resource_path("icon.png")
    if icon_path.exists():
        icon = ImageTk.PhotoImage(Image.open(icon_path).convert("RGBA").resize((32, 32)))
        self.preview_images["_window_icon"] = icon
        self.root.iconphoto(True, icon)

    shell = ttk.Frame(self.root, style="Shell.TFrame")
    shell.pack(fill=BOTH, expand=True)
    side = ttk.Frame(shell, style="Side.TFrame", padding=(12, 14))
    side.pack(side=LEFT, fill="y")
    ttk.Label(side, text="鼠标配置", style="Side.TLabel", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor="w", pady=(0, 18))
    self.nav_buttons = {}
    for key, text, icon_name, command in (
        ("scheme", "鼠标方案", "mouse", self.show_scheme_page),
        ("library", "资源库", "folder", self.show_resource_page),
        ("time", "时间切换", "clock", self.show_time_page),
        ("week", "星期切换", "calendar", self.show_week_page),
    ):
        btn = ttk.Button(side, text=f"  {text}", image=self._ui_icon(icon_name), compound=LEFT, style="Nav.TButton", command=command)
        btn.pack(fill="x", pady=4)
        self.nav_buttons[key] = btn
    settings_btn = ttk.Button(side, text="  设置", image=self._ui_icon("settings"), compound=LEFT, style="Nav.TButton", command=self.show_settings_page)
    settings_btn.pack(side="bottom", fill="x", pady=4)
    self.nav_buttons["settings"] = settings_btn

    main = ttk.Frame(shell, style="Page.TFrame", padding=22)
    main.pack(side=LEFT, fill=BOTH, expand=True)
    self.page_title = ttk.Label(main, text="", style="Title.TLabel")
    self.page_title.pack(anchor="w")
    self.page_subtitle = ttk.Label(main, text="", style="Muted.TLabel")
    self.page_subtitle.pack(anchor="w", pady=(4, 18))
    self.content = ttk.Frame(main, style="Page.TFrame")
    self.content.pack(fill=BOTH, expand=True)
    self.status = StringVar(value="请选择方案。")
    ttk.Label(main, textvariable=self.status, style="Muted.TLabel").pack(anchor="e", pady=(10, 0))
    self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    self.show_scheme_page()


def _v3_configure_style(self) -> None:
    _v2_configure_style(self)
    style = ttk.Style()
    self.root.configure(bg="#eaf6ff")
    style.configure("Shell.TFrame", background="#eaf6ff")
    style.configure("Side.TFrame", background="#f4fbff")
    style.configure("Page.TFrame", background="#f3faff")
    style.configure("Card.TFrame", background="#ffffff")
    style.configure("Muted.TLabel", background="#ffffff", foreground="#5f6f82", font=("Microsoft YaHei UI", 9))
    style.configure("Title.TLabel", background="#f3faff", foreground="#102033", font=("Microsoft YaHei UI", 20, "bold"))
    style.configure("Yellow.TButton", padding=(15, 9), background="#fff3c4", foreground="#314056", borderwidth=0)
    style.map("Yellow.TButton", background=[("active", "#ffe7a3")])
    style.configure("Blue.TButton", padding=(15, 9), background="#dceeff", foreground="#1f4f82", borderwidth=0)
    style.map("Blue.TButton", background=[("active", "#c9e4ff")])


class CheckMark:
    def __init__(self, variable: IntVar, command) -> None:
        self.variable = variable
        self.command = command
        self.button = None

    def attach(self, parent) -> None:
        self.button = ttk.Button(parent, text=self.text(), style="Soft.TButton", command=self.toggle)
        self.button.pack(side=RIGHT)

    def text(self) -> str:
        return ("✓" if self.variable.get() else "□") + " 自启动并保留后台"

    def toggle(self) -> None:
        self.variable.set(0 if self.variable.get() else 1)
        self.button.configure(text=self.text())
        self.command()


def _v3_show_scheme_page(self) -> None:
    self._clean_page()
    self.page_title.configure(text="鼠标方案")
    self.page_subtitle.configure(text="选择方案、导入配置或编辑每个鼠标状态。悬停行会实时预览。")
    top = ttk.Frame(self.content, style="Card.TFrame")
    top.pack(fill="x", pady=(0, 12))
    ttk.Label(top, text="方案", font=("Microsoft YaHei UI", 11, "bold")).pack(side=LEFT)
    self.scheme_combo = ttk.Combobox(top, textvariable=self.theme_name, width=18, state="readonly")
    self.scheme_combo.pack(side=LEFT, padx=(10, 8))
    self.scheme_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_scheme_to_ui(self.theme_name.get()))
    ttk.Button(top, text="新建", image=self._ui_icon("plus"), compound=LEFT, style="Soft.TButton", command=self.new_scheme).pack(side=LEFT, padx=3)
    ttk.Button(top, text="重命名", style="Soft.TButton", command=self.rename_scheme).pack(side=LEFT, padx=3)
    ttk.Button(top, text="删除", image=self._ui_icon("trash"), compound=LEFT, style="Danger.TButton", command=self.delete_scheme).pack(side=LEFT, padx=3)
    import_btn = ttk.Button(top, text="导入", image=self._ui_icon("upload"), compound=LEFT, style="Soft.TButton", command=self.import_package)
    import_btn.pack(side=LEFT, padx=3)
    import_btn.bind("<Enter>", lambda _e: self.import_tip.set("支持直接拖入可执行文件。"))
    import_btn.bind("<Leave>", lambda _e: self.import_tip.set(""))
    ttk.Button(top, text="保存", image=self._ui_icon("folder"), compound=LEFT, style="Soft.TButton", command=self.save_current_scheme).pack(side=LEFT, padx=3)
    ttk.Label(top, textvariable=self.import_tip, style="Muted.TLabel").pack(side=LEFT, padx=(12, 0))

    split = ttk.Frame(self.content, style="Page.TFrame")
    split.pack(fill=BOTH, expand=True)
    left = ttk.Frame(split, style="Card.TFrame")
    left.pack(side=LEFT, fill=BOTH, expand=True)
    right = ttk.Frame(split, style="Card.TFrame", padding=(18, 0, 0, 0))
    right.pack(side=RIGHT, fill=BOTH)
    canvas = Canvas(left, bg="#ffffff", highlightthickness=1, highlightbackground="#dbeafe")
    self.rows = ttk.Frame(canvas, style="Card.TFrame")
    self.rows.columnconfigure(0, weight=1)
    self.rows.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    row_window = canvas.create_window((0, 0), window=self.rows, anchor="nw")
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(row_window, width=event.width))
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    def wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<MouseWheel>", wheel)
    self.rows.bind("<MouseWheel>", wheel)
    self.path_vars = {}
    self.preview_labels = {}
    self.row_frames = {}
    for index, role in enumerate(CURSOR_ROLES):
        self.add_row(index, role)
    ttk.Label(right, text="实时预览", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w")
    self.preview_canvas = Canvas(right, width=360, height=360, bg="#fbfdff", highlightthickness=1, highlightbackground="#dbeafe", cursor="none")
    self.preview_canvas.pack(fill=BOTH, expand=True, pady=(10, 8))
    self.preview_canvas.bind("<Motion>", self.preview_motion)
    self.preview_canvas.bind("<Leave>", self.preview_leave)
    self.large_preview_name = ttk.Label(right, text="", style="Muted.TLabel", wraplength=330)
    self.large_preview_name.pack(anchor="w")
    actions = ttk.Frame(self.content, style="Card.TFrame")
    actions.pack(fill="x", pady=(12, 0))
    ttk.Button(actions, text="鼠标大小设置", image=self._ui_icon("settings"), compound=LEFT, style="Yellow.TButton", command=self.open_pointer_settings).pack(side=LEFT, padx=(0, 8))
    ttk.Button(actions, text="应用", image=self._ui_icon("apply"), compound=LEFT, style="Primary.TButton", command=self.apply_now).pack(side=LEFT, padx=(0, 8))
    ttk.Button(actions, text="生成安装包", style="Blue.TButton", command=self.build_installer).pack(side=LEFT)
    self.autostart_check = CheckMark(self.autostart_enabled, lambda: self.apply_autostart())
    self.autostart_check.attach(actions)
    ttk.Label(actions, text="建议调整大小后再应用。", style="Muted.TLabel").pack(side=RIGHT, padx=14)
    self.refresh_scheme_names()


def _v3_add_row(self, index: int, role: CursorRole) -> None:
    style_name = "Even.TFrame" if index % 2 else "Odd.TFrame"
    row = ttk.Frame(self.rows, style=style_name, padding=(8, 6))
    row.grid(row=index, column=0, sticky="ew")
    row.columnconfigure(0, weight=0, minsize=54)
    row.columnconfigure(1, weight=0, minsize=120)
    row.columnconfigure(2, weight=1, minsize=180)
    row.columnconfigure(3, weight=0, minsize=52)
    row.columnconfigure(4, weight=0, minsize=72)
    self.row_frames[role.reg_name] = (row, style_name)
    ref = ttk.Label(row, width=6, anchor="center")
    ref.grid(row=0, column=0, sticky="w")
    ref_image = self.load_reference_icon(role)
    if ref_image:
        self.ref_images[role.reg_name] = ref_image
        ref.configure(image=ref_image)
    ttk.Label(row, text=role.label, width=14).grid(row=0, column=1, sticky="w", padx=(6, 6))
    var = StringVar(value="未配置")
    self.path_vars[role.reg_name] = var
    path_label = ttk.Label(row, textvariable=var, style="Muted.TLabel", wraplength=360)
    path_label.grid(row=0, column=2, sticky="ew")
    row.bind("<Configure>", lambda event, lbl=path_label: lbl.configure(wraplength=max(180, event.width - 310)))
    choose = ttk.Label(row, text="选择", foreground="#2563eb", cursor="hand2")
    choose.grid(row=0, column=3, padx=(10, 8))
    choose.bind("<Button-1>", lambda _e, r=role: self.pick_file(r))
    preview = ttk.Label(row, text="", width=7, anchor="center")
    preview.grid(row=0, column=4, sticky="e")
    self.preview_labels[role.reg_name] = preview
    def enter(_event=None, r=role):
        row.configure(style="Hover.TFrame")
        path = self.selected.get(r.reg_name)
        if path:
            self.update_large_preview(path)
    def leave(_event=None, original=style_name):
        row.configure(style=original)
    for widget in (row, ref, path_label, preview, choose):
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        widget.bind("<MouseWheel>", lambda event: self.rows.master.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        if DND_FILES:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", lambda event, r=role: self.drop_file(event, r))
            except Exception:
                pass


def _v3_load_reference_icon(self, role: CursorRole) -> ImageTk.PhotoImage | None:
    icon_path = resource_path(f"assets/role_icons/{role.file_stem}.png")
    if not icon_path.exists():
        return None
    image = Image.open(icon_path).convert("RGBA")
    image = centered_rgba(image, 38)
    return ImageTk.PhotoImage(image)


def _v3_update_preview(self, role: CursorRole, path: Path) -> None:
    image = cursor_preview_image(path, (54, 54))
    photo = ImageTk.PhotoImage(image)
    self.preview_images[role.reg_name] = photo
    self.preview_labels[role.reg_name].configure(image=photo, text="")


def _v3_update_large_preview(self, path: Path) -> None:
    if getattr(self, "animation_after", None):
        self.root.after_cancel(self.animation_after)
        self.animation_after = None
    frames = []
    if path.suffix.lower() == ".ani":
        for frame in ani_frame_paths(path):
            frames.append(cursor_preview_image(frame, (118, 118)))
    if not frames:
        frames = [cursor_preview_image(path, (118, 118))]
    self.animation_frames = [ImageTk.PhotoImage(frame) for frame in frames]
    self.animation_index = 0
    self.preview_x = int(self.preview_canvas.winfo_width() / 2) if hasattr(self, "preview_canvas") else 180
    self.preview_y = int(self.preview_canvas.winfo_height() / 2) if hasattr(self, "preview_canvas") else 180
    def tick():
        if not getattr(self, "preview_canvas", None) or not self.animation_frames:
            return
        try:
            self.preview_canvas.delete("cursor")
            photo = self.animation_frames[self.animation_index]
            self.preview_canvas.create_image(self.preview_x, self.preview_y, image=photo, tags="cursor")
            self.preview_images["_large_current"] = photo
            self.animation_index = (self.animation_index + 1) % len(self.animation_frames)
            if len(self.animation_frames) > 1:
                self.animation_after = self.root.after(120, tick)
        except Exception:
            self.animation_after = None
    tick()
    self.large_preview_name.configure(text=str(path))


def _v3_preview_leave(self, _event=None) -> None:
    if not getattr(self, "animation_frames", None):
        return
    self.preview_x = int(self.preview_canvas.winfo_width() / 2)
    self.preview_y = int(self.preview_canvas.winfo_height() / 2)
    self.preview_canvas.delete("cursor")
    photo = self.animation_frames[self.animation_index % len(self.animation_frames)]
    self.preview_canvas.create_image(self.preview_x, self.preview_y, image=photo, tags="cursor")
    self.preview_images["_large_current"] = photo


def _rename_scheme(self) -> None:
    old = self.theme_name.get()
    if old in DEFAULT_SCHEME_NAMES:
        messagebox.showwarning("不能重命名", "默认方案不能重命名。")
        return
    dialog = Toplevel(self.root)
    dialog.title("重命名方案")
    dialog.geometry("320x130")
    dialog.transient(self.root)
    frame = ttk.Frame(dialog, padding=14)
    frame.pack(fill=BOTH, expand=True)
    name_var = StringVar(value=old)
    ttk.Label(frame, text="新名称").pack(anchor="w")
    ttk.Entry(frame, textvariable=name_var).pack(fill="x", pady=8)
    def save():
        new = sanitize_name(name_var.get())
        if not new or new == old:
            dialog.destroy()
            return
        src = SCHEME_LIBRARY / old
        dst = SCHEME_LIBRARY / new
        if dst.exists():
            messagebox.showwarning("名称重复", "该方案名称已经存在。")
            return
        if src.exists():
            src.rename(dst)
            manifest = dst / "scheme.json"
            if manifest.exists():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                data["name"] = new
                manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.theme_name.set(new)
        self.refresh_scheme_names()
        dialog.destroy()
        self.status.set(f"已重命名为：{new}")
    ttk.Button(frame, text="确定", style="Primary.TButton", command=save).pack(anchor="e")


def _run_wait_task(self, title: str, text: str, work, on_success=None) -> None:
    dialog = Toplevel(self.root)
    dialog.title(title)
    dialog.transient(self.root)
    dialog.grab_set()
    dialog.resizable(False, False)
    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill=BOTH, expand=True)
    ttk.Label(frame, text=text, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="center", pady=(4, 12))
    progress = ttk.Progressbar(frame, mode="indeterminate")
    progress.pack(fill="x")
    progress.start(10)
    dialog.update_idletasks()
    width, height = 360, 150
    parent_x = self.root.winfo_rootx()
    parent_y = self.root.winfo_rooty()
    parent_w = max(self.root.winfo_width(), 1)
    parent_h = max(self.root.winfo_height(), 1)
    x = parent_x + (parent_w - width) // 2
    y = parent_y + (parent_h - height) // 2
    dialog.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
    result = {"done": False, "ok": False, "value": None}

    def target():
        try:
            result["value"] = work()
            result["ok"] = True
        except Exception as exc:
            result["value"] = exc
            result["ok"] = False
        finally:
            result["done"] = True

    def poll():
        if not result["done"]:
            self.root.after(80, poll)
            return
        progress.stop()
        dialog.grab_release()
        dialog.destroy()
        if result["ok"]:
            if on_success:
                on_success(result["value"])
        else:
            messagebox.showerror(title, str(result["value"]))

    threading.Thread(target=target, daemon=True).start()
    poll()


def _v4_apply_now(self) -> None:
    error = self.validate()
    if error:
        messagebox.showwarning("还不能应用", error)
        return
    theme = sanitize_name(self.theme_name.get())
    selected = dict(self.selected)
    backend_autostart = bool(self.autostart_enabled.get()) if hasattr(self, "autostart_enabled") else False

    def work():
        set_auto_start(backend_autostart)
        cursor_files = {reg: str(path) for reg, path in selected.items() if path.suffix.lower() in {".cur", ".ani"}}
        if len(cursor_files) == len(selected):
            apply_cursor_scheme(theme, cursor_files)
            return theme
        package_dir = WORK_ROOT / "current_theme"
        assets_dir = package_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
        assets_dir.mkdir(parents=True, exist_ok=True)
        files = {}
        for reg_name, source in selected.items():
            role = ROLE_BY_REG[reg_name]
            suffix = source.suffix.lower()
            output_name = f"{role.file_stem}{suffix if suffix in {'.cur', '.ani'} else '.cur'}"
            output = assets_dir / output_name
            convert_to_cursor(source, output.with_suffix(".cur") if suffix not in {".cur", ".ani"} else output, role, DEFAULT_CURSOR_SIZE)
            files[reg_name] = output_name
        target_dir = self.install_assets_to_scheme(theme, files, assets_dir)
        apply_cursor_scheme(theme, {reg_name: str(target_dir / name) for reg_name, name in files.items()})
        self.save_library_manifest(theme, files, target_dir)
        return theme

    def done(name):
        if backend_autostart:
            self.start_scheduler()
            self.ensure_tray_icon()
            self.notify_startup_changed()
        self.status.set(f"已应用：{name}")

    self._run_wait_task("正在应用", "正在应用鼠标方案，请稍等。", work, done)


def _v4_build_installer(self) -> None:
    error = self.validate()
    if error:
        messagebox.showwarning("还不能生成", error)
        return
    default_dir = configured_output_root()
    default_dir.mkdir(parents=True, exist_ok=True)
    folder = filedialog.askdirectory(title="选择安装包保存位置", initialdir=str(default_dir))
    if not folder:
        return
    output_dir = Path(folder)
    data = load_settings()
    data["output_root"] = str(output_dir.resolve())
    save_settings(data)
    theme = sanitize_name(self.theme_name.get())

    def work():
        package_dir = WORK_ROOT / "installer_package"
        package_dir.mkdir(parents=True, exist_ok=True)
        files = self.prepare_assets(package_dir)
        installer_py = package_dir / "install_cursor_theme.py"
        installer_py.write_text(installer_source(theme, files), encoding="utf-8")
        exe_name = f"{theme}_鼠标样式安装器"
        icon_path = self.installer_icon(package_dir)
        return self.build_pyinstaller_exe(installer_py, package_dir / "assets", exe_name, output_dir, icon_path)

    def done(path):
        self.status.set(f"已生成安装包：{path}")
        os.startfile(path.parent)
        messagebox.showinfo("生成完成", f"已生成安装包：\n{path}")

    self._run_wait_task("正在生成", "正在生成安装包，请稍等。", work, done)


def _installer_icon(self, package_dir: Path) -> Path | None:
    source = self.selected.get("Arrow") or next(iter(self.selected.values()), None)
    if not source:
        return None
    try:
        image = cursor_preview_image(source, (64, 64)).convert("RGBA")
        icon_path = package_dir / "installer_icon.ico"
        image.save(icon_path, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
        return icon_path
    except Exception as exc:
        log_error("生成安装包图标失败", exc)
        return None


def _v4_build_pyinstaller_exe(self, installer_py: Path, assets_dir: Path, exe_name: str, output_dir: Path | None = None, icon_path: Path | None = None) -> Path:
    python = find_python_with_pyinstaller()
    dist_dir = output_dir or configured_output_root()
    dist_dir.mkdir(parents=True, exist_ok=True)
    command = [
        python,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name",
        exe_name,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(WORK_ROOT / "pyinstaller"),
        "--specpath",
        str(WORK_ROOT / "spec"),
        "--add-data",
        f"{assets_dir};assets",
    ]
    if icon_path and icon_path.exists():
        command.extend(["--icon", str(icon_path)])
    command.append(str(installer_py))
    result = subprocess.run(command, cwd=APP_DIR, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        log_path = WORK_ROOT / "pyinstaller_error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8", errors="replace")
        raise RuntimeError(f"PyInstaller 打包失败，日志：{log_path}")
    return dist_dir / f"{exe_name}.exe"


def _v3_save_time_page(self, vars_by_mode) -> None:
    try:
        items = [item for item in self.schedule_items if item.get("mode") not in {"light", "dark"}]
        for mode, (time_var, scheme_var) in vars_by_mode.items():
            at = time_var.get().strip()
            scheme = scheme_var.get().strip()
            if scheme:
                self.validate_time(at)
                items.append({"mode": mode, "time": at, "scheme": scheme})
    except Exception as exc:
        log_error("保存时间切换失败", exc)
        messagebox.showerror("保存失败", str(exc))
        return

    def work():
        self.schedule_items = items
        self.save_schedule()
        set_auto_start(bool(self.autostart_enabled.get()))
        if self.autostart_enabled.get():
            self.start_scheduler()
        now = datetime.now().strftime("%H:%M")
        selected = None
        for item in sorted(self.schedule_items, key=lambda x: x.get("time", "")):
            if item.get("time", "") <= now:
                selected = item.get("scheme")
        if selected:
            self.apply_saved_scheme(selected)
        return selected

    def done(selected):
        if self.autostart_enabled.get():
            self.ensure_tray_icon()
            self.notify_startup_changed()
        if selected:
            self.status.set(f"时间切换已应用，并已切换到：{selected}")
        else:
            self.status.set("时间切换已应用。")

    self._run_wait_task("正在应用", "正在应用时间切换方案，请稍等。", work, done)


def _v3_save_week_page(self, vars_by_day) -> None:
    week_items = {day: var.get().strip() for day, var in vars_by_day.items() if var.get().strip()}

    def work():
        self.week_items = week_items
        self.save_week_schedule()
        set_auto_start(bool(self.autostart_enabled.get()))
        if self.autostart_enabled.get():
            self.start_scheduler()
        scheme = self.week_items.get(str(datetime.now().weekday()))
        if scheme:
            self.apply_saved_scheme(scheme)
        return scheme

    def done(scheme):
        if self.autostart_enabled.get():
            self.ensure_tray_icon()
            self.notify_startup_changed()
        if scheme:
            self.status.set(f"星期切换已应用，并已切换到：{scheme}")
        else:
            self.status.set("星期切换已应用。")

    self._run_wait_task("正在应用", "正在应用星期切换方案，请稍等。", work, done)


def _v4_apply_autostart(self) -> None:
    try:
        enabled = bool(self.autostart_enabled.get())
        set_auto_start(enabled)
        if enabled:
            self.start_scheduler()
            self.ensure_tray_icon()
            self.notify_startup_changed()
        else:
            self.scheduler_running = False
            self.stop_tray_icon()
        self.status.set("自启动和保留后台已开启。" if enabled else "自启动和保留后台已关闭。")
    except Exception as exc:
        log_error("设置自启动和保留后台失败", exc)
        messagebox.showerror("设置失败", str(exc))


def _on_close(self) -> None:
    if hasattr(self, "autostart_enabled") and self.autostart_enabled.get():
        try:
            set_auto_start(True)
            self.start_scheduler()
            self.ensure_tray_icon()
            self.root.withdraw()
            self.status.set("已保留后台运行。")
            return
        except Exception as exc:
            log_error("保留后台失败", exc)
    self.root.destroy()


def _ensure_tray_icon(self) -> None:
    if not pystray or getattr(self, "tray_running", False):
        return
    icon_path = resource_path("icon.png")
    if icon_path.exists():
        image = Image.open(icon_path).convert("RGBA")
    else:
        image = Image.new("RGBA", (64, 64), "#5b9dff")

    def exit_app(_icon=None, _item=None):
        self.root.after(0, self.exit_from_tray)

    self.tray_icon = pystray.Icon(
        "MouseCursorThemeBuilder",
        image,
        "鼠标配置生成器",
        menu=pystray.Menu(pystray.MenuItem("退出", exit_app)),
    )
    self.tray_icon.run_detached()
    self.tray_running = True


def _stop_tray_icon(self) -> None:
    icon = getattr(self, "tray_icon", None)
    if icon:
        try:
            icon.stop()
        except Exception:
            pass
    self.tray_icon = None
    self.tray_running = False


def _exit_from_tray(self) -> None:
    self.scheduler_running = False
    self.stop_tray_icon()
    self.root.destroy()


def _notify_startup_changed(self) -> None:
    icon = getattr(self, "tray_icon", None)
    if icon:
        try:
            icon.notify("启动选项已更改", "鼠标配置生成器已允许自启动并保留后台。")
            return
        except Exception as exc:
            log_error("显示启动项通知失败", exc)
    messagebox.showinfo("启动选项已更改", "鼠标配置生成器已允许自启动并保留后台。")


def _default_archives() -> list[Path]:
    archives = bundled_archives()
    selected: list[Path] = []
    for keyword in DEFAULT_ARCHIVE_KEYWORDS:
        match = next((archive for archive in archives if keyword in archive.name), None)
        if match:
            selected.append(match)
    if len(selected) < 2:
        for archive in archives:
            if archive not in selected:
                selected.append(archive)
            if len(selected) >= 2:
                break
    return selected[:2]


def _resource_archives() -> list[Path]:
    paths = []
    for folder in (RESOURCE_LIBRARY, APP_DIR):
        if folder.exists():
            paths.extend([p for p in folder.iterdir() if p.suffix.lower() in {".zip", ".rar", ".7z", ".exe"}])
    defaults = set(_default_archives())
    return [p for p in dict.fromkeys(paths) if p not in defaults]


def _v4_ensure_default_schemes(self) -> None:
    SCHEME_LIBRARY.mkdir(parents=True, exist_ok=True)
    archives = _default_archives()
    for index, archive in enumerate(archives):
        name = DEFAULT_SCHEME_NAMES[index]
        scheme_dir = SCHEME_LIBRARY / name
        if (scheme_dir / "scheme.json").exists():
            continue
        try:
            extracted = extract_import_package(archive)
            mapping = parse_inf_mapping(extracted)
            scheme_dir.mkdir(parents=True, exist_ok=True)
            files = {}
            for reg_name, source in mapping.items():
                role = ROLE_BY_REG.get(reg_name)
                if role:
                    output_name = f"{role.file_stem}{source.suffix.lower()}"
                    shutil.copy2(source, scheme_dir / output_name)
                    files[reg_name] = output_name
            self.save_library_manifest(name, files, scheme_dir)
        except Exception as exc:
            log_error(f"导入默认方案失败：{archive.name}", exc)


def _import_archive_as_scheme(self, archive: Path) -> bool:
    name = sanitize_name(archive.stem)
    if name in DEFAULT_SCHEME_NAMES:
        name = f"{name}_资源"
    scheme_dir = SCHEME_LIBRARY / name
    if (scheme_dir / "scheme.json").exists():
        return False
    extracted = extract_import_package(archive)
    mapping = parse_inf_mapping(extracted)
    if not mapping:
        raise RuntimeError(f"{archive.name} 没有识别到鼠标方案。")
    scheme_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for reg_name, source in mapping.items():
        role = ROLE_BY_REG.get(reg_name)
        if role:
            output_name = f"{role.file_stem}{source.suffix.lower()}"
            shutil.copy2(source, scheme_dir / output_name)
            files[reg_name] = output_name
    self.save_library_manifest(name, files, scheme_dir)
    return True


def _show_resource_page(self) -> None:
    self._clean_page()
    self.page_title.configure(text="资源库")
    self.page_subtitle.configure(text="打开在线资源库下载鼠标包，或把压缩包放进存储目录后点击刷新。")
    card = ttk.Frame(self.content, style="Card.TFrame", padding=18)
    card.pack(fill=BOTH, expand=True)
    ttk.Label(card, text="在线资源库", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor="w")
    ttk.Label(card, text="下载后的 zip、rar、7z 或自解压 exe 放到鼠标文件存放位置，点击刷新会自动解压并添加方案。", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(6, 16))
    buttons = ttk.Frame(card, style="Card.TFrame")
    buttons.pack(fill="x", pady=(0, 12))
    ttk.Button(buttons, text="打开资源库网页", image=self._ui_icon("folder"), compound=LEFT, style="Blue.TButton", command=self.open_resource_browser).pack(side=LEFT, padx=(0, 8))
    ttk.Button(buttons, text="打开鼠标文件存放位置", style="Yellow.TButton", command=lambda: os.startfile(RESOURCE_LIBRARY)).pack(side=LEFT, padx=(0, 8))
    ttk.Button(buttons, text="刷新", image=self._ui_icon("apply"), compound=LEFT, style="Primary.TButton", command=self.refresh_resource_library).pack(side=LEFT)
    drop = ttk.Label(card, text="也可以把 zip / rar / 7z / exe 拖到这里导入为新方案", style="Muted.TLabel", anchor="center")
    drop.pack(fill="x", pady=(2, 12), ipady=18)
    if DND_FILES:
        try:
            drop.drop_target_register(DND_FILES)
            drop.dnd_bind("<<Drop>>", self.drop_import_resource)
            card.drop_target_register(DND_FILES)
            card.dnd_bind("<<Drop>>", self.drop_import_resource)
        except Exception:
            pass
    self.resource_status = StringVar(value=f"存放位置：{RESOURCE_LIBRARY}")
    ttk.Label(card, textvariable=self.resource_status, style="Muted.TLabel", wraplength=760).pack(anchor="w", pady=8)
    ttk.Label(card, text="已有资源", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(14, 8))
    preview_canvas = Canvas(card, bg="#ffffff", highlightthickness=0, height=320)
    preview_canvas.pack(fill=BOTH, expand=True)
    preview_holder = ttk.Frame(preview_canvas, style="Card.TFrame")
    preview_window = preview_canvas.create_window((0, 0), window=preview_holder, anchor="nw")
    preview_holder.bind("<Configure>", lambda _event: preview_canvas.configure(scrollregion=preview_canvas.bbox("all")))
    preview_canvas.bind("<Configure>", lambda event: preview_canvas.itemconfigure(preview_window, width=event.width))
    preview_canvas.bind("<MouseWheel>", lambda event: preview_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
    self.resource_preview_container = preview_holder
    self.render_resource_previews()


def _refresh_resource_library(self) -> None:
    imported = 0
    errors = []
    RESOURCE_LIBRARY.mkdir(parents=True, exist_ok=True)
    for archive in _resource_archives():
        try:
            if self._import_archive_as_scheme(archive):
                imported += 1
        except Exception as exc:
            errors.append(f"{archive.name}: {exc}")
            log_error(f"资源库导入失败：{archive.name}", exc)
    self.refresh_scheme_names()
    if hasattr(self, "resource_preview_container"):
        self.render_resource_previews()
    message = f"已添加 {imported} 个方案。"
    if errors:
        message += f" 有 {len(errors)} 个文件未识别，详情见错误记录。"
    self.resource_status.set(message)
    self.status.set(message)


def _resource_scheme_names(self) -> list[str]:
    if not SCHEME_LIBRARY.exists():
        return []
    names = [p.name for p in SCHEME_LIBRARY.iterdir() if p.is_dir()]
    custom = [name for name in names if name not in DEFAULT_SCHEME_NAMES]
    return sorted(custom or names)


def _render_resource_previews(self) -> None:
    container = getattr(self, "resource_preview_container", None)
    if not container:
        return
    for child in container.winfo_children():
        child.destroy()
    self.resource_preview_frames = []
    self.resource_preview_labels = []
    self.resource_preview_index = 0
    names = self.resource_scheme_names()
    if not names:
        ttk.Label(container, text="暂无资源。把资源包拖到上方区域，或点击刷新。", style="Muted.TLabel").pack(anchor="w", pady=12)
        return
    for name in names:
        scheme_dir, files = scheme_manifest(name)
        card = ttk.Frame(container, style="Even.TFrame", padding=12)
        card.pack(fill="x", pady=(0, 10))
        ttk.Label(card, text=name, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        strip = ttk.Frame(card, style="Even.TFrame")
        strip.pack(fill="x")
        for reg_name in ROLE_BY_REG:
            file_name = files.get(reg_name)
            if not file_name:
                continue
            path = scheme_dir / file_name
            if not path.exists():
                continue
            label = ttk.Label(strip, width=8, anchor="center")
            label.pack(side=LEFT, padx=4, pady=2)
            frames = self.resource_icon_frames(path)
            if frames:
                label.configure(image=frames[0])
                self.resource_preview_labels.append(label)
                self.resource_preview_frames.append(frames)
    self.animate_resource_previews()


def _resource_icon_frames(self, path: Path) -> list[ImageTk.PhotoImage]:
    try:
        paths = ani_frame_paths(path)[:12] if path.suffix.lower() == ".ani" else [path]
        frames = []
        for item in paths:
            image = cursor_preview_image(item, (58, 58))
            frames.append(ImageTk.PhotoImage(image))
        key = f"_resource_{path}_{len(self.preview_images)}"
        self.preview_images[key] = frames
        return frames
    except Exception as exc:
        log_error(f"资源预览失败：{path}", exc)
        return []


def _animate_resource_previews(self) -> None:
    if not getattr(self, "resource_preview_labels", None):
        return
    for label, frames in zip(self.resource_preview_labels, self.resource_preview_frames):
        if frames:
            label.configure(image=frames[self.resource_preview_index % len(frames)])
    self.resource_preview_index += 1
    self.resource_preview_after = self.root.after(140, self.animate_resource_previews)


def _drop_import_resource(self, event) -> None:
    paths = self.root.tk.splitlist(event.data)
    archives = [Path(path) for path in paths if Path(path).suffix.lower() in {".zip", ".rar", ".7z", ".exe"}]
    if not archives:
        self.status.set("拖入的文件不是可识别的资源包。")
        return

    def work():
        imported = []
        for archive in archives:
            if self._import_archive_as_scheme(archive):
                imported.append(sanitize_name(archive.stem))
        return imported

    def done(imported):
        self.refresh_scheme_names()
        if imported:
            self.theme_name.set(imported[-1])
            self.load_scheme_to_ui(imported[-1])
            message = f"已导入 {len(imported)} 个资源包。"
        else:
            message = "资源包已存在或没有新增方案。"
        if hasattr(self, "resource_status"):
            self.resource_status.set(message)
        self.status.set(message)

    self._run_wait_task("正在导入", "正在解压并添加资源，请稍等。", work, done)


def _v4_drop_file(self, event, role: CursorRole) -> None:
    paths = [Path(path) for path in self.root.tk.splitlist(event.data)]
    if not paths:
        return
    source = paths[0]
    if source.suffix.lower() in {".zip", ".rar", ".7z", ".exe"}:
        def work():
            if not self._import_archive_as_scheme(source):
                return None
            return sanitize_name(source.stem)

        def done(name):
            self.refresh_scheme_names()
            if name:
                self.theme_name.set(name)
                self.load_scheme_to_ui(name)
                self.status.set(f"已导入为新方案：{name}")
            else:
                self.status.set("该资源包已存在或没有新增方案。")

        self._run_wait_task("正在导入", "正在解压并添加资源，请稍等。", work, done)
        return
    self.assign_file(role, source)


def _open_resource_browser(self) -> None:
    RESOURCE_LIBRARY.mkdir(parents=True, exist_ok=True)
    edge = shutil.which("msedge") or shutil.which("msedge.exe")
    edge_paths = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    if not edge:
        edge = str(next((p for p in edge_paths if p.exists()), ""))
    if edge:
        subprocess.Popen([
            edge,
            f"--app={RESOURCE_URL}",
            f"--user-data-dir={APP_DATA / 'resource_browser'}",
            f"--download-default-directory={RESOURCE_LIBRARY}",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(RESOURCE_URL)


def _show_settings_page(self) -> None:
    self._clean_page()
    self.page_title.configure(text="设置")
    self.page_subtitle.configure(text="设置鼠标文件存放位置、安装包默认保存位置和基础信息。")
    card = ttk.Frame(self.content, style="Card.TFrame", padding=18)
    card.pack(fill="x")
    ttk.Label(card, text="鼠标文件存放位置", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w")
    self.storage_path_var = StringVar(value=str(configured_storage_root()))
    ttk.Entry(card, textvariable=self.storage_path_var).pack(fill="x", pady=(8, 10))
    row = ttk.Frame(card, style="Card.TFrame")
    row.pack(fill="x")
    ttk.Button(row, text="选择文件夹", style="Yellow.TButton", command=self.pick_storage_folder).pack(side=LEFT)
    ttk.Button(row, text="应用设置", style="Primary.TButton", command=self.apply_settings_page).pack(side=LEFT, padx=8)
    ttk.Button(row, text="打开文件夹", style="Blue.TButton", command=lambda: os.startfile(Path(self.storage_path_var.get()))).pack(side=LEFT)

    ttk.Label(card, text="安装包默认保存位置", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(22, 0))
    self.output_path_var = StringVar(value=str(configured_output_root()))
    ttk.Entry(card, textvariable=self.output_path_var).pack(fill="x", pady=(8, 10))
    output_row = ttk.Frame(card, style="Card.TFrame")
    output_row.pack(fill="x")
    ttk.Button(output_row, text="选择文件夹", style="Yellow.TButton", command=self.pick_output_folder).pack(side=LEFT)
    ttk.Button(output_row, text="打开文件夹", style="Blue.TButton", command=lambda: os.startfile(Path(self.output_path_var.get()))).pack(side=LEFT, padx=8)
    ttk.Label(card, text="个人描述：By Asunny", style="Muted.TLabel").pack(anchor="w", pady=(18, 0))


def _pick_storage_folder(self) -> None:
    folder = filedialog.askdirectory(title="选择鼠标文件存放位置", initialdir=str(configured_storage_root()))
    if folder:
        self.storage_path_var.set(folder)


def _pick_output_folder(self) -> None:
    folder = filedialog.askdirectory(title="选择安装包默认保存位置", initialdir=str(configured_output_root()))
    if folder:
        self.output_path_var.set(folder)


def _apply_settings_page(self) -> None:
    try:
        root = Path(self.storage_path_var.get())
        output_root = Path(self.output_path_var.get())
        apply_storage_root(root)
        data = load_settings()
        data["storage_root"] = str(root.resolve())
        data["output_root"] = str(output_root.resolve())
        save_settings(data)
        output_root.mkdir(parents=True, exist_ok=True)
        self.ensure_default_schemes()
        self.refresh_scheme_names()
        self.status.set("设置已应用。")
    except Exception as exc:
        log_error("应用设置失败", exc)
        messagebox.showerror("设置失败", str(exc))


CursorThemeBuilder.ensure_default_schemes = _v4_ensure_default_schemes
CursorThemeBuilder.show_resource_page = _show_resource_page
CursorThemeBuilder.refresh_resource_library = _refresh_resource_library
CursorThemeBuilder.resource_scheme_names = _resource_scheme_names
CursorThemeBuilder.render_resource_previews = _render_resource_previews
CursorThemeBuilder.resource_icon_frames = _resource_icon_frames
CursorThemeBuilder.animate_resource_previews = _animate_resource_previews
CursorThemeBuilder.drop_import_resource = _drop_import_resource
CursorThemeBuilder.open_resource_browser = _open_resource_browser
CursorThemeBuilder._import_archive_as_scheme = _import_archive_as_scheme
CursorThemeBuilder.show_settings_page = _show_settings_page
CursorThemeBuilder.pick_storage_folder = _pick_storage_folder
CursorThemeBuilder.pick_output_folder = _pick_output_folder
CursorThemeBuilder.apply_settings_page = _apply_settings_page


CursorThemeBuilder.configure_style = _v3_configure_style
CursorThemeBuilder.build_ui = _v3_build_ui
CursorThemeBuilder.show_scheme_page = _v3_show_scheme_page
CursorThemeBuilder.add_row = _v3_add_row
CursorThemeBuilder.load_reference_icon = _v3_load_reference_icon
CursorThemeBuilder.update_preview = _v3_update_preview
CursorThemeBuilder.update_large_preview = _v3_update_large_preview
CursorThemeBuilder.preview_leave = _v3_preview_leave
CursorThemeBuilder.rename_scheme = _rename_scheme
CursorThemeBuilder.drop_file = _v4_drop_file
CursorThemeBuilder._run_wait_task = _run_wait_task
CursorThemeBuilder.apply_now = _v4_apply_now
CursorThemeBuilder.apply_autostart = _v4_apply_autostart
CursorThemeBuilder.on_close = _on_close
CursorThemeBuilder.ensure_tray_icon = _ensure_tray_icon
CursorThemeBuilder.stop_tray_icon = _stop_tray_icon
CursorThemeBuilder.exit_from_tray = _exit_from_tray
CursorThemeBuilder.notify_startup_changed = _notify_startup_changed
CursorThemeBuilder.installer_icon = _installer_icon
CursorThemeBuilder.build_installer = _v4_build_installer
CursorThemeBuilder.build_pyinstaller_exe = _v4_build_pyinstaller_exe
CursorThemeBuilder.save_time_page = _v3_save_time_page
CursorThemeBuilder.save_week_page = _v3_save_week_page


if __name__ == "__main__":
    main()
