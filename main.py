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
import winreg
import zipfile
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


IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
WORK_ROOT = APP_DIR / "_build" if IS_FROZEN else APP_DIR / "build"
OUTPUT_DIR = APP_DIR if IS_FROZEN else APP_DIR / "dist"
APP_DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MouseCursorThemeBuilder"
SCHEME_LIBRARY = APP_DATA / "schemes"
SCHEDULE_FILE = APP_DATA / "schedule.json"
WEEK_SCHEDULE_FILE = APP_DATA / "week_schedule.json"
ERROR_LOG = APP_DIR / "错误记录.md"
DEFAULT_CURSOR_SIZE = 64
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


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
    target_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MouseCursorThemes" / THEME_NAME
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
    if path.suffix.lower() in {".cur", ".ani"}:
        rendered = render_cursor_with_windows(path, 96)
        if rendered:
            bg = Image.new("RGBA", box, (248, 250, 252, 255))
            bg.alpha_composite(rendered, ((box[0] - rendered.width) // 2, (box[1] - rendered.height) // 2))
            return bg
    image = centered_rgba(image_from_path(path), min(box) - 28)
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
            name = Path(match.group(1).strip()).name.lower()
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
    result = subprocess.run(["tar", "-xf", str(source), "-C", str(target)], text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return target
    raise RuntimeError(f"无法解压 {source.name}。该文件可能不是可读取的压缩包，或 EXE 不是自解压格式。")


def set_auto_start(enabled: bool) -> None:
    if IS_FROZEN:
        command = f'"{Path(sys.executable).resolve()}" --background'
    else:
        command = f'"{Path(sys.executable).resolve()}" "{Path(__file__).resolve()}" --background'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "MouseCursorThemeBuilder", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "MouseCursorThemeBuilder")
            except FileNotFoundError:
                pass


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
        target_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MouseCursorThemes" / theme
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
        ("time", "时间切换", "clock", self.show_time_page),
        ("week", "星期切换", "calendar", self.show_week_page),
    ):
        btn = ttk.Button(side, text=f"  {text}", image=self._ui_icon(icon_name), compound=LEFT, style="Nav.TButton", command=command)
        btn.pack(fill="x", pady=4)
        self.nav_buttons[key] = btn
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


if __name__ == "__main__":
    main()
