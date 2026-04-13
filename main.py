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
import threading
import time
import traceback
import winreg
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, VERTICAL, Canvas, IntVar, StringVar, Tk, filedialog, messagebox, ttk

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
ERROR_LOG = APP_DIR / "错误记录.md"


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
DEFAULT_SCHEME_NAMES = ["我的鼠标样式", "亮色指针", "暗色指针", "游戏指针", "办公指针", "演示大指针"]
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


class CursorThemeBuilder:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("鼠标指针配置生成器")
        self.root.geometry("1180x780")
        self.root.minsize(980, 680)

        self.theme_name = StringVar(value=DEFAULT_SCHEME_NAMES[0])
        self.cursor_size = IntVar(value=64)
        self.selected: dict[str, Path] = {}
        self.path_vars: dict[str, StringVar] = {}
        self.ref_images: dict[str, ImageTk.PhotoImage] = {}
        self.preview_images: dict[str, ImageTk.PhotoImage] = {}
        self.preview_labels: dict[str, ttk.Label] = {}
        self.schedule_items: list[dict[str, str]] = []
        self.scheduler_running = False
        self.scheduler_thread: threading.Thread | None = None
        self.last_schedule_key = ""

        self.configure_style()
        self.load_schedule()
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

        controls = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        controls.pack(fill="x", pady=(12, 10))
        ttk.Label(controls, text="方案名称", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.scheme_combo = ttk.Combobox(controls, textvariable=self.theme_name, values=DEFAULT_SCHEME_NAMES, width=24)
        self.scheme_combo.grid(row=0, column=1, sticky="w", padx=(8, 16))
        ttk.Label(controls, text="鼠标大小", style="Panel.TLabel").grid(row=0, column=2, sticky="w")
        size = ttk.Scale(controls, from_=32, to=128, orient="horizontal", variable=self.cursor_size, command=lambda _v: self.on_size_change())
        size.grid(row=0, column=3, sticky="ew", padx=8)
        self.size_text = ttk.Label(controls, text="64 px", style="Panel.TLabel", width=8)
        self.size_text.grid(row=0, column=4, sticky="w")
        ttk.Button(controls, text="系统鼠标大小设置", command=self.open_pointer_settings).grid(row=0, column=5, padx=(12, 0))
        ttk.Button(controls, text="保存到方案库", command=self.save_current_scheme).grid(row=0, column=6, padx=(8, 0))
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
        ttk.Label(side, text="定时切换", style="Panel.TLabel", font=("Microsoft YaHei UI", 13, "bold")).pack(anchor="w")
        ttk.Label(side, text="程序运行时，到点自动应用方案库里的方案。", style="Small.Panel.TLabel", wraplength=260).pack(anchor="w", pady=(2, 10))
        self.schedule_time = StringVar(value="09:00")
        self.schedule_scheme = StringVar(value=self.theme_name.get())
        ttk.Label(side, text="时间 HH:MM", style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(side, textvariable=self.schedule_time, width=12).pack(anchor="w", pady=(2, 8))
        ttk.Label(side, text="方案", style="Panel.TLabel").pack(anchor="w")
        self.schedule_combo = ttk.Combobox(side, textvariable=self.schedule_scheme, width=24)
        self.schedule_combo.pack(anchor="w", pady=(2, 8))
        ttk.Button(side, text="添加定时", command=self.add_schedule).pack(fill="x")
        ttk.Button(side, text="启动/停止定时", command=self.toggle_scheduler).pack(fill="x", pady=(8, 0))
        self.schedule_list = Canvas(side, width=270, height=250, bg="#f8fafc", highlightthickness=1, highlightbackground="#dbe3ef")
        self.schedule_list.pack(fill="both", pady=10)
        ttk.Button(side, text="清空定时", command=self.clear_schedule).pack(fill="x")

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
        self.status.set(f"已选择：{role.label} -> {path.name}")

    def update_preview(self, role: CursorRole, path: Path) -> None:
        label = self.preview_labels[role.reg_name]
        preview_size = max(36, min(96, int(self.cursor_size.get() * 0.75)))
        if path.suffix.lower() in {".cur", ".ani"}:
            label.configure(text=path.suffix.upper(), image="")
            return
        image = centered_rgba(image_from_path(path), preview_size)
        bg = Image.new("RGBA", (104, 72), (248, 250, 252, 255))
        draw = ImageDraw.Draw(bg)
        draw.rectangle((0, 0, 103, 71), outline=(203, 213, 225, 255))
        bg.alpha_composite(image, ((104 - image.width) // 2, (72 - image.height) // 2))
        photo = ImageTk.PhotoImage(bg)
        self.preview_images[role.reg_name] = photo
        label.configure(image=photo, text="")

    def on_size_change(self) -> None:
        value = int(round(self.cursor_size.get()))
        self.cursor_size.set(value)
        self.size_text.configure(text=f"{value} px")
        for role in CURSOR_ROLES:
            path = self.selected.get(role.reg_name)
            if path:
                try:
                    self.update_preview(role, path)
                except Exception as exc:
                    log_error("刷新预览失败", exc)

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
        self.schedule_combo.configure(values=names)

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
        size = int(self.cursor_size.get())
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
        manifest = {"name": theme, "files": files, "size": int(self.cursor_size.get()), "saved_at": datetime.now().isoformat()}
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
                self.schedule_items = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            log_error("读取定时配置失败", exc)
            self.schedule_items = []

    def save_schedule(self) -> None:
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_FILE.write_text(json.dumps(self.schedule_items, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_schedule(self) -> None:
        at = self.schedule_time.get().strip()
        theme = self.schedule_scheme.get().strip()
        if not re.fullmatch(r"\d{2}:\d{2}", at):
            messagebox.showwarning("时间格式错误", "请使用 HH:MM，例如 09:30。")
            return
        hour, minute = map(int, at.split(":"))
        if hour > 23 or minute > 59:
            messagebox.showwarning("时间格式错误", "小时必须 00-23，分钟必须 00-59。")
            return
        self.schedule_items.append({"time": at, "scheme": theme})
        self.save_schedule()
        self.refresh_schedule_list()

    def clear_schedule(self) -> None:
        self.schedule_items = []
        self.save_schedule()
        self.refresh_schedule_list()

    def refresh_schedule_list(self) -> None:
        self.schedule_list.delete("all")
        y = 14
        for item in self.schedule_items:
            self.schedule_list.create_text(12, y, text=f"{item['time']}  ->  {item['scheme']}", anchor="nw", fill="#172033", font=("Microsoft YaHei UI", 10))
            y += 28

    def toggle_scheduler(self) -> None:
        self.scheduler_running = not self.scheduler_running
        if self.scheduler_running and not self.scheduler_thread:
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()
        self.status.set("定时切换已启动。" if self.scheduler_running else "定时切换已停止。")

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
            time.sleep(20)


def main() -> None:
    root_class = TkinterDnD.Tk if TkinterDnD else Tk
    root = root_class()
    CursorThemeBuilder(root)
    root.mainloop()


if __name__ == "__main__":
    main()
