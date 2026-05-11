from __future__ import annotations

import ctypes
import ctypes.wintypes
import base64
import io
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
import winreg
import zipfile
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import pystray
except Exception:
    pystray = None


IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_DATA = Path(os.environ.get("APPDATA", str(Path.home()))) / "MouseCursorThemeBuilder"
APP_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
APP_RUNTIME = APP_DATA / "runtime"
SETTINGS_FILE = APP_DATA / "settings.json"
DEFAULT_STORAGE_ROOT = APP_DATA / "mouse_files"
DEFAULT_OUTPUT_ROOT = APP_DATA / "installers"
WORK_ROOT = APP_RUNTIME if IS_FROZEN else APP_DIR / "build"
OUTPUT_DIR = DEFAULT_OUTPUT_ROOT if IS_FROZEN else APP_DIR / "dist"
SCHEME_LIBRARY = DEFAULT_STORAGE_ROOT / "schemes"
RESOURCE_LIBRARY = DEFAULT_STORAGE_ROOT / "resources"
INSTALLED_LIBRARY = DEFAULT_STORAGE_ROOT / "installed"
SCHEDULE_FILE = APP_DATA / "schedule.json"
WEEK_SCHEDULE_FILE = APP_DATA / "week_schedule.json"
CURSOR_BACKUP_FILE = APP_DATA / "cursor_backup.json"
ERROR_LOG = (APP_DATA if IS_FROZEN else APP_DIR) / "错误记录.txt"
ERROR_LOG_MAX_BYTES = 2 * 1024 * 1024
ERROR_LOG_MAX_ARCHIVES = 5
ERROR_LOG_KEEP_DAYS = 30
DEFAULT_CURSOR_SIZE = 64
DEFAULT_PREVIEW_SIZE_LEVEL = 3
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RESOURCE_URL = "http://8.135.33.2:5002/"
APP_NAME = "鼠标指针配置管理器"
SOFTWARE_MISSION = "让新手小白也能用，让鼠标指针制作者能方便编辑和生成。"
AUTO_START_VALUE = APP_NAME
LEGACY_AUTO_START_VALUE = "MouseCursorThemeBuilder"
SCHEDULED_TASK_NAME = "MousePointerBackground"
PIXEL_GUIDE_URL = "https://mp.weixin.qq.com/s/DyO-dBMKf7RrMetCqji4jg"
ASUNNY_URL = "https://asunny.top/"
DEFAULT_GITHUB_URL = "https://github.com/yuanyue1234/MousePointer"
APP_VERSION = "2.1.0"
BUILD_COMMIT = "source"
INSTALL_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / "MouseCursorPointerManager"
PORTABLE_EXE_NAME = "鼠标指针配置生成器_绿色程序.exe"
INSTALLER_EXE_NAME = "鼠标指针配置生成器_安装程序.exe"
PORTABLE_RELEASE_ASSET_NAME = "MousePointer_Portable.exe"
INSTALLER_RELEASE_ASSET_NAME = "MousePointer_Installer.exe"
CURSOR_FILE_ASSOCIATION_KEY = "cursor_file_association_enabled"
CUR_FILE_PROG_ID = "MousePointer.CursorFile"
ANI_FILE_PROG_ID = "MousePointer.AnimatedCursorFile"
_STARTUP_TIMING: dict[str, float] = {}


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
DEFAULT_CURSOR_FILES = {
    "Arrow": "aero_arrow.cur",
    "Help": "aero_helpsel.cur",
    "AppStarting": "aero_working.ani",
    "Wait": "aero_busy.ani",
    "Crosshair": "cross_r.cur",
    "IBeam": "beam_r.cur",
    "NWPen": "aero_pen.cur",
    "No": "aero_unavail.cur",
    "SizeNS": "aero_ns.cur",
    "SizeWE": "aero_ew.cur",
    "SizeNWSE": "aero_nwse.cur",
    "SizeNESW": "aero_nesw.cur",
    "SizeAll": "aero_move.cur",
    "UpArrow": "aero_up.cur",
    "Hand": "aero_link.cur",
    "Person": "aero_person.cur",
    "Pin": "aero_pin.cur",
}
DEFAULT_SCHEME_NAMES = ["01方案", "02方案"]
DEFAULT_ARCHIVE_KEYWORDS = ["小垚", "鼠鼠"]
RANDOM_SCHEME_VALUE = "__random__"
SUPPORTED_TYPES = (
    ("图片和光标", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico *.cur *.ani"),
    ("图片", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico"),
    ("Windows 光标", "*.cur *.ani"),
    ("所有文件", "*.*"),
)


def rotate_error_log() -> None:
    try:
        if not ERROR_LOG.exists() or ERROR_LOG.stat().st_size < ERROR_LOG_MAX_BYTES:
            return
        archive = ERROR_LOG.with_name(f"错误记录_{datetime.now():%Y%m%d_%H%M%S}.txt")
        ERROR_LOG.replace(archive)
        archives = sorted(ERROR_LOG.parent.glob("错误记录_*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
        cutoff = time.time() - ERROR_LOG_KEEP_DAYS * 24 * 60 * 60
        for index, path in enumerate(archives):
            try:
                if index >= ERROR_LOG_MAX_ARCHIVES or path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass
    except Exception:
        pass


def log_error(title: str, exc: BaseException | str) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    rotate_error_log()
    if isinstance(exc, BaseException):
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        detail = str(exc)
    with ERROR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {datetime.now():%Y-%m-%d %H:%M:%S} {title}\n\n```text\n{detail}\n```\n")


def startup_timing_reset() -> None:
    _STARTUP_TIMING.clear()
    _STARTUP_TIMING["_start"] = time.perf_counter()


def startup_timing_mark(name: str) -> None:
    if "_start" not in _STARTUP_TIMING:
        startup_timing_reset()
    _STARTUP_TIMING[name] = time.perf_counter() - _STARTUP_TIMING["_start"]


def startup_timing_flush() -> None:
    if "_start" not in _STARTUP_TIMING:
        return
    startup_timing_mark("startup.total")
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    rotate_error_log()
    with ERROR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {datetime.now():%Y-%m-%d %H:%M:%S} startup.diagnostics\n\n```text\n")
        for key, value in sorted(((k, v) for k, v in _STARTUP_TIMING.items() if k != "_start"), key=lambda item: item[1]):
            handle.write(f"{key}={value:.3f}s\n")
        handle.write("```\n")


def resource_path(relative: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return APP_DIR / relative


def default_cursor_path(role_or_reg) -> Path | None:
    reg_name = getattr(role_or_reg, "reg_name", str(role_or_reg))
    file_name = DEFAULT_CURSOR_FILES.get(reg_name)
    if not file_name:
        return None
    path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Cursors" / file_name
    return path if path.exists() else None


def set_system_cursor_size(pixels: int) -> None:
    pixels = max(1, min(256, int(pixels)))
    try:
        if get_current_cursor_size() == pixels:
            return
    except Exception:
        pass
    if pixels <= 32:
        level = 1
    elif pixels >= 256:
        level = 15
    else:
        level = max(1, min(15, int(round((pixels - 32) / 16.0)) + 1))
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "CursorBaseSize", 0, winreg.REG_DWORD, pixels)
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Accessibility", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "CursorSize", 0, winreg.REG_DWORD, level)
    except Exception:
        pass
    user32 = ctypes.windll.user32
    SPI_SETCURSORBASESIZE = 0x2029
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    if not user32.SystemParametersInfoW(SPI_SETCURSORBASESIZE, 0, ctypes.c_void_p(pixels), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE):
        raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
    broadcast_cursor_change(120)
    broadcast_cursor_change_for_area(r"SOFTWARE\Microsoft\Accessibility", 120)


def broadcast_cursor_change(timeout_ms: int = 120) -> None:
    broadcast_cursor_change_for_area("Control Panel\\Cursors", timeout_ms)


def broadcast_cursor_change_for_area(area: str, timeout_ms: int = 120) -> None:
    user32 = ctypes.windll.user32
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    message = ctypes.create_unicode_buffer(area)
    result = ctypes.c_size_t()
    try:
        user32.SendMessageTimeoutW(
            ctypes.c_void_p(HWND_BROADCAST),
            WM_SETTINGCHANGE,
            0,
            ctypes.cast(message, ctypes.c_void_p),
            SMTO_ABORTIFHUNG,
            timeout_ms,
            ctypes.byref(result),
        )
    except Exception:
        pass


def default_cursor_scheme_files() -> dict[str, str]:
    files = {}
    for role in CURSOR_ROLES:
        path = default_cursor_path(role)
        if path and path.exists():
            files[role.reg_name] = str(path)
    return files


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


def update_setting(key: str, value: str) -> None:
    data = load_settings()
    data[key] = value
    save_settings(data)


def remove_setting(key: str) -> None:
    data = load_settings()
    if key in data:
        data.pop(key, None)
        save_settings(data)


def setting_enabled(key: str, default: bool = False) -> bool:
    value = str(load_settings().get(key, "1" if default else "0")).strip().lower()
    return value in {"1", "true", "yes", "on", "是", "开启"}


def file_association_enabled() -> bool:
    return setting_enabled(CURSOR_FILE_ASSOCIATION_KEY, default=True)


def english_ui_enabled() -> bool:
    return setting_enabled("english_enabled", False)


def tray_text(text: str) -> str:
    if not english_ui_enabled():
        return text
    mapping = {
        "打开": "Open",
        "隐藏任务栏": "Hide tray",
        "退出": "Exit",
    }
    if text in mapping:
        return mapping[text]
    if text.startswith("当前配置："):
        return text.replace("当前配置：", "Current: ", 1)
    if text.startswith("下次切换："):
        return text.replace("下次切换：", "Next: ", 1)
    return text


def set_setting_enabled(key: str, enabled: bool) -> None:
    update_setting(key, "1" if enabled else "0")


def log_error_once(setting_key: str, title: str, exc: BaseException | str) -> None:
    detail = str(exc)
    data = load_settings()
    if data.get(setting_key) == detail:
        return
    log_error(title, exc)
    data[setting_key] = detail
    save_settings(data)


def is_installer_executable(name: str) -> bool:
    stem = Path(name).stem
    return "安装" in stem or "installer" in stem.lower()


def is_uninstaller_executable(name: str) -> bool:
    stem = Path(name).stem
    return "卸载" in stem or "uninstall" in stem.lower()


def configured_current_scheme() -> str:
    value = load_settings().get("current_scheme", "").strip()
    if value:
        return value
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_QUERY_VALUE) as key:
            current, _type = winreg.QueryValueEx(key, "")
            return str(current).strip() or "Windows 默认"
    except Exception:
        return "未知"


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


def configured_github_url() -> str:
    return load_settings().get("github_url", DEFAULT_GITHUB_URL).strip()


def preview_cursor_command(exe_path: Path | None = None) -> str:
    target = exe_path or Path(sys.executable if IS_FROZEN else Path(__file__).resolve())
    return f'{subprocess.list2cmdline([str(target), "--preview-cursor"])} "%1"'


def _classes_key(path: str, access: int = winreg.KEY_READ):
    return winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{path}", 0, access)


def read_hkcu_class_value(path: str, value_name: str = "") -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{path}", 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, value_name)
            return str(value)
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def read_class_value(path: str, value_name: str = "") -> str:
    for root, subkey in (
        (winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{path}"),
        (winreg.HKEY_CLASSES_ROOT, path),
    ):
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
                value, _kind = winreg.QueryValueEx(key, value_name)
                return str(value)
        except (FileNotFoundError, OSError):
            continue
    return ""


def read_machine_class_value(path: str, value_name: str = "") -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"Software\\Classes\\{path}", 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, value_name)
            return str(value)
    except (FileNotFoundError, OSError):
        return ""


def default_icon_for_cursor_extension(ext: str, current_prog_id: str = "") -> str:
    for prog_id in (current_prog_id, read_machine_class_value(ext), read_class_value(ext)):
        if not prog_id or prog_id in {CUR_FILE_PROG_ID, ANI_FILE_PROG_ID}:
            continue
        icon_value = read_class_value(f"{prog_id}\\DefaultIcon") or read_machine_class_value(f"{prog_id}\\DefaultIcon")
        if icon_value:
            return icon_value
    return ""


def write_hkcu_class_value(path: str, value: str, value_name: str = "") -> None:
    with _classes_key(path, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value)


def delete_hkcu_class_tree(path: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{path}", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                delete_hkcu_class_tree(f"{path}\\{child}")
    except FileNotFoundError:
        return
    except OSError:
        return
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{path}")
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _restore_extension_association(ext: str, prog_id: str, backup_key: str) -> None:
    current = read_hkcu_class_value(ext)
    saved = load_settings().get(backup_key, "")
    if current == prog_id:
        if saved:
            write_hkcu_class_value(ext, saved)
        else:
            delete_hkcu_class_tree(ext)


def register_cursor_file_associations(exe_path: Path | None = None) -> None:
    command = preview_cursor_command(exe_path)
    data = load_settings()
    for ext, prog_id, label, backup_key, icon_backup_key in (
        (".cur", CUR_FILE_PROG_ID, "Mouse Pointer Cursor File", "file_assoc_backup_cur", "file_assoc_backup_cur_icon"),
        (".ani", ANI_FILE_PROG_ID, "Mouse Pointer Animated Cursor File", "file_assoc_backup_ani", "file_assoc_backup_ani_icon"),
    ):
        current = read_hkcu_class_value(ext)
        if current != prog_id and backup_key not in data:
            data[backup_key] = current
        if current != prog_id and icon_backup_key not in data:
            data[icon_backup_key] = default_icon_for_cursor_extension(ext, current)
        write_hkcu_class_value(ext, prog_id)
        write_hkcu_class_value(prog_id, label)
        icon_value = str(data.get(icon_backup_key, "") or default_icon_for_cursor_extension(ext, current) or "")
        if icon_value:
            write_hkcu_class_value(f"{prog_id}\\DefaultIcon", icon_value)
        else:
            delete_hkcu_class_tree(f"{prog_id}\\DefaultIcon")
        write_hkcu_class_value(f"{prog_id}\\shell\\open\\command", command)
    data[CURSOR_FILE_ASSOCIATION_KEY] = "1"
    save_settings(data)
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass


def unregister_cursor_file_associations() -> None:
    _restore_extension_association(".cur", CUR_FILE_PROG_ID, "file_assoc_backup_cur")
    _restore_extension_association(".ani", ANI_FILE_PROG_ID, "file_assoc_backup_ani")
    delete_hkcu_class_tree(CUR_FILE_PROG_ID)
    delete_hkcu_class_tree(ANI_FILE_PROG_ID)
    data = load_settings()
    data[CURSOR_FILE_ASSOCIATION_KEY] = "0"
    data.pop("file_assoc_backup_cur", None)
    data.pop("file_assoc_backup_ani", None)
    data.pop("file_assoc_backup_cur_icon", None)
    data.pop("file_assoc_backup_ani_icon", None)
    save_settings(data)
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass


def apply_cursor_file_association_setting(enabled: bool, exe_path: Path | None = None) -> None:
    if enabled:
        register_cursor_file_associations(exe_path)
    else:
        unregister_cursor_file_associations()


def scheme_order_value(path: Path) -> float:
    manifest = path / "scheme.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for key in ("order", "created_at", "saved_at"):
                value = data.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str) and value:
                    try:
                        return datetime.fromisoformat(value).timestamp()
                    except ValueError:
                        pass
        except Exception:
            pass
    try:
        return path.stat().st_ctime
    except OSError:
        return 0


apply_storage_root(configured_storage_root())


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip(" ._")
    return cleaned or "我的鼠标样式"


def current_build_commit() -> str:
    if not IS_FROZEN:
        try:
            result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=APP_DIR, text=True, capture_output=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
    return BUILD_COMMIT


def github_repo_api_url(repo_url: str) -> str:
    match = re.search(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s#?]+)", repo_url.strip())
    if not match:
        raise RuntimeError("GitHub 源地址格式不正确。")
    owner = match.group("owner")
    repo = match.group("repo").removesuffix(".git")
    return f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"


def latest_commit_from_git(repo_url: str) -> dict[str, str]:
    clean_url = repo_url.strip().split("#", 1)[0].split("?", 1)[0].rstrip("/")
    candidates = [clean_url, clean_url.removesuffix(".git") + ".git"]
    last_error = ""
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    for candidate in dict.fromkeys(candidates):
        result = subprocess.run(["git", "ls-remote", candidate, "HEAD"], text=True, capture_output=True, check=False, creationflags=creationflags)
        if result.returncode == 0 and result.stdout.strip():
            sha = result.stdout.split()[0]
            return {
                "sha": sha,
                "short": sha[:7],
                "message": "远端 HEAD",
                "date": "",
                "url": clean_url,
            }
        last_error = result.stderr or result.stdout
    raise RuntimeError((last_error or "无法读取远端提交").strip())


def fetch_latest_github_commit(repo_url: str) -> dict[str, str]:
    if not repo_url:
        raise RuntimeError("还没有设置 GitHub 源地址。")
    request = urllib.request.Request(github_repo_api_url(repo_url), headers={"User-Agent": "MousePointer"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return latest_commit_from_git(repo_url)
        raise RuntimeError(f"GitHub 请求失败：HTTP {exc.code}") from exc
    if isinstance(data, list):
        if not data:
            raise RuntimeError("GitHub 仓库没有提交记录。")
        data = data[0]
    sha = str(data.get("sha", ""))
    commit = data.get("commit", {})
    return {
        "sha": sha,
        "short": sha[:7],
        "message": str(commit.get("message", "")).splitlines()[0] if commit else "",
        "date": str(commit.get("committer", {}).get("date", "")) if commit else "",
        "url": str(data.get("html_url", repo_url)),
    }


def github_repo_parts(repo_url: str) -> tuple[str, str]:
    match = re.search(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s#?]+)", repo_url.strip())
    if not match:
        raise RuntimeError("GitHub 源地址格式不正确。")
    return match.group("owner"), match.group("repo").removesuffix(".git")


def fetch_latest_release(repo_url: str) -> dict:
    if not repo_url:
        raise RuntimeError("还没有设置 GitHub 源地址。")
    owner, repo = github_repo_parts(repo_url)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
        headers={"User-Agent": "MousePointer", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError("仓库目前没有可用的 GitHub Release。自动更新需要先在 GitHub Releases 发布带 EXE 资产的版本。") from exc
        raise RuntimeError(f"GitHub Release 请求失败：HTTP {exc.code}") from exc


def version_tuple(value: str) -> tuple[int, ...]:
    value = value.strip().lstrip("vV")
    parts = re.findall(r"\d+", value)
    return tuple(int(part) for part in parts) if parts else (0,)


def is_newer_version(latest_tag: str, current_version: str) -> bool:
    return version_tuple(latest_tag) > version_tuple(current_version)


def release_asset_for_current_app(release: dict) -> dict:
    current_name = Path(sys.executable).name if IS_FROZEN else PORTABLE_EXE_NAME
    preferred_names = (
        (INSTALLER_EXE_NAME, INSTALLER_RELEASE_ASSET_NAME)
        if is_installer_executable(current_name)
        else (PORTABLE_EXE_NAME, PORTABLE_RELEASE_ASSET_NAME)
    )
    assets = release.get("assets", [])
    for name in (*preferred_names, PORTABLE_RELEASE_ASSET_NAME, INSTALLER_RELEASE_ASSET_NAME, PORTABLE_EXE_NAME, INSTALLER_EXE_NAME):
        for asset in assets:
            if asset.get("name") == name:
                return asset
    raise RuntimeError("Release 中没有找到可下载的程序文件。")


def download_release_asset(asset: dict) -> Path:
    url = asset.get("browser_download_url")
    name = asset.get("name") or PORTABLE_EXE_NAME
    if not url:
        raise RuntimeError("Release 资产缺少下载地址。")
    target = APP_DATA / "updates" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "MousePointer"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return target


def launch_update_replacer(downloaded: Path) -> None:
    if not IS_FROZEN:
        raise RuntimeError("源码运行模式不能自动替换程序，请使用打包后的 EXE。")
    current = Path(sys.executable).resolve()
    script = "\n".join([
        "Start-Sleep -Seconds 2",
        f"Copy-Item -LiteralPath {ps_quote(str(downloaded))} -Destination {ps_quote(str(current))} -Force",
        f"Start-Process -FilePath {ps_quote(str(current))}",
        f"Remove-Item -LiteralPath {ps_quote(str(downloaded))} -Force -ErrorAction SilentlyContinue",
    ])
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def image_from_path(path: Path) -> Image.Image:
    if path.suffix.lower() == ".svg":
        raise RuntimeError("SVG 只作为参考图使用。请先导出 PNG 后再作为鼠标素材。")
    return Image.open(path).convert("RGBA")


def centered_rgba(image: Image.Image, size: int) -> Image.Image:
    image = ImageOps.contain(image, (size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
    return canvas


def _cursor_name_parts(path: Path) -> tuple[set[str], str]:
    stem = path.stem.lower()
    tokens = {token for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", stem) if token}
    compact = "".join(tokens)
    return tokens, compact


def _cursor_name_matches(path: Path, keywords: list[str]) -> bool:
    tokens, compact = _cursor_name_parts(path)
    for keyword in keywords:
        normalized = "".join(re.split(r"[^a-z0-9\u4e00-\u9fff]+", keyword.lower()))
        if not normalized:
            continue
        if normalized in tokens or normalized == compact:
            return True
        if len(normalized) >= 4 and normalized in compact:
            return True
    return False


def preview_placeholder_image(path: Path, box: tuple[int, int], animated: bool = False) -> Image.Image:
    width, height = box
    image = Image.new("RGBA", box, (248, 250, 252, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6, 6, width - 6, height - 6), radius=12, outline=(203, 213, 225, 255), width=2, fill=(255, 255, 255, 255))
    draw.rounded_rectangle((14, 14, min(width - 14, 88), 42), radius=10, fill=(37, 99, 235, 230) if animated else (71, 85, 105, 230))
    font = ImageFont.load_default()
    badge = "ANI" if animated else (path.suffix.lstrip(".").upper() or "FILE")
    draw.text((24, 23), badge, fill=(255, 255, 255, 255), font=font, anchor="lm")
    name = path.stem.strip() or path.name
    if len(name) > 20:
        name = f"{name[:17]}..."
    draw.text((width // 2, max(56, height // 2)), name, fill=(15, 23, 42, 255), font=font, anchor="mm")
    tip = "animated cursor preview unavailable" if animated else "preview unavailable"
    draw.text((width // 2, min(height - 22, max(76, height // 2 + 20))), tip, fill=(100, 116, 139, 255), font=font, anchor="mm")
    return image


def hotspot_for(role: CursorRole, size: int) -> tuple[int, int]:
    x = int(round(role.hotspot_ratio[0] * (size - 1)))
    y = int(round(role.hotspot_ratio[1] * (size - 1)))
    return max(0, min(size - 1, x)), max(0, min(size - 1, y))


def hotspot_from_ratio(role: CursorRole, size: int, hotspot_ratio: tuple[float, float] | None = None) -> tuple[int, int]:
    ratio = hotspot_ratio or role.hotspot_ratio
    x = int(round(ratio[0] * (size - 1)))
    y = int(round(ratio[1] * (size - 1)))
    return max(0, min(size - 1, x)), max(0, min(size - 1, y))


def write_png_cursor(image: Image.Image, output_path: Path, role: CursorRole, size: int, hotspot_ratio: tuple[float, float] | None = None) -> None:
    cursor = centered_rgba(image, size)
    png = io.BytesIO()
    cursor.save(png, format="PNG")
    data = png.getvalue()
    hot_x, hot_y = hotspot_from_ratio(role, size, hotspot_ratio)
    header = struct.pack("<HHH", 0, 2, 1)
    width_byte = size if size < 256 else 0
    directory = struct.pack("<BBBBHHII", width_byte, width_byte, 0, 0, hot_x, hot_y, len(data), 22)
    output_path.write_bytes(header + directory + data)


def rewrite_cur_hotspot(source: Path, output_path: Path, hotspot_ratio: tuple[float, float]) -> None:
    data = bytearray(source.read_bytes())
    if len(data) < 6:
        shutil.copy2(source, output_path)
        return
    reserved, icon_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or icon_type != 2 or count <= 0:
        shutil.copy2(source, output_path)
        return
    for index in range(count):
        offset = 6 + index * 16
        if offset + 16 > len(data):
            break
        width = data[offset] or 256
        height = data[offset + 1] or 256
        hot_x = max(0, min(width - 1, int(round(hotspot_ratio[0] * (width - 1)))))
        hot_y = max(0, min(height - 1, int(round(hotspot_ratio[1] * (height - 1)))))
        struct.pack_into("<HH", data, offset + 4, hot_x, hot_y)
    output_path.write_bytes(data)


def convert_to_cursor(source: Path, output_path: Path, role: CursorRole, size: int, hotspot_ratio: tuple[float, float] | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".cur" and hotspot_ratio:
        rewrite_cur_hotspot(source, output_path.with_suffix(".cur"), hotspot_ratio)
        return
    if source.suffix.lower() in {".cur", ".ani"}:
        shutil.copy2(source, output_path.with_suffix(source.suffix.lower()))
        return
    write_png_cursor(image_from_path(source), output_path, role, size, hotspot_ratio)


def current_cursor_scheme_data() -> dict:
    data = {"saved_at": datetime.now().isoformat(), "values": {}}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_QUERY_VALUE) as key:
        for name in ["", "Scheme Source", *[role.reg_name for role in CURSOR_ROLES]]:
            try:
                value, value_type = winreg.QueryValueEx(key, name)
                data["values"][name] = {"value": value, "type": value_type}
            except FileNotFoundError:
                continue
    return data


def backup_current_cursor_scheme() -> None:
    try:
        CURSOR_BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
        CURSOR_BACKUP_FILE.write_text(json.dumps(current_cursor_scheme_data(), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        log_error("备份当前鼠标方案失败", exc)


def restore_cursor_backup() -> None:
    if not CURSOR_BACKUP_FILE.exists():
        raise RuntimeError("还没有可恢复的鼠标方案备份。")
    data = json.loads(CURSOR_BACKUP_FILE.read_text(encoding="utf-8"))
    values = data.get("values", {})
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        for name, item in values.items():
            value = item.get("value", "")
            value_type = int(item.get("type", winreg.REG_EXPAND_SZ))
            winreg.SetValueEx(key, name, 0, value_type, value)
    refresh_mouse_parameters()


def get_current_cursor_size() -> int:
    """读取当前系统鼠标大小（像素）"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_QUERY_VALUE) as key:
            size, _ = winreg.QueryValueEx(key, "CursorBaseSize")
            return int(size)
    except Exception:
        return 48  # 默认 48px


def apply_cursor_scheme(theme_name: str, cursor_files: dict[str, str], backup: bool = True, cursor_size_pixels: int | None = None) -> None:
    if backup:
        backup_current_cursor_scheme()

    # 保留已有鼠标大小（或使用传入的值）
    size_to_apply = cursor_size_pixels if cursor_size_pixels else get_current_cursor_size()

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, theme_name)
        winreg.SetValueEx(key, "Scheme Source", 0, winreg.REG_DWORD, 2)
        winreg.SetValueEx(key, "CursorBaseSize", 0, winreg.REG_DWORD, size_to_apply)
        for reg_name, file_path in cursor_files.items():
            winreg.SetValueEx(key, reg_name, 0, winreg.REG_EXPAND_SZ, file_path)
    refresh_mouse_parameters()
    update_setting("current_scheme", theme_name)


def refresh_mouse_parameters() -> None:
    user32 = ctypes.windll.user32
    SPI_SETCURSORS = 0x0057
    # SPIF_UPDATEINIFILES = 0x01（写 ini），SPIF_SENDCHANGE = 0x02（广播），SPIF_SENDWININICHANGE = 0x02
    SPIF_UPDATEINIFILES = 0x01
    SPIF_SENDWININICHANGE = 0x02

    # 步骤1：让系统重新加载 HKCU\Control Panel\Cursors 里的所有光标资源
    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, SPIF_UPDATEINIFILES | SPIF_SENDWININICHANGE)

    # 步骤2：强制重新加载系统默认箭头光标，触发 Windows 真正重绘光标
    # IMAGE_CURSOR = 2，LR_SHARED = 0x8000，LR_DEFAULTSIZE = 0x0040，IDI_APPLICATION = 32512
    IDC_ARROW = 32512
    IMAGE_CURSOR = 2
    LR_SHARED = 0x8000
    LR_DEFAULTSIZE = 0x0040
    try:
        hCursor = user32.LoadImageW(None, MAKEINTRESOURCE(IDC_ARROW), IMAGE_CURSOR, 0, 0, LR_SHARED | LR_DEFAULTSIZE)
        if hCursor:
            user32.DestroyCursor(hCursor)
    except Exception:
        pass

    # 步骤3：再次通知所有窗口刷新，确保所有程序都收到 WM_SETTINGCHANGE
    broadcast_cursor_change()

    # 步骤4：用新光标替换当前前台窗口的光标，确保当前进程立即看到变化
    hwnd = user32.GetForegroundWindow()
    if hwnd:
        # 先让前台窗口重绘一次
        user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0100)  # RDW_INVALIDATE | RDW_UPDATENOW


# 辅助：把整数转成 Windows 资源 ID（LOWORD）
def MAKEINTRESOURCE(word: int) -> ctypes.c_void_p:
    return ctypes.c_void_p(word & 0xFFFF)


def reset_to_default_cursor_scheme() -> None:
    defaults = default_cursor_scheme_files()
    if not defaults:
        raise RuntimeError("未找到 Windows 默认鼠标指针文件。")
    apply_cursor_scheme("Windows 默认", defaults, backup=False)


def apply_refreshed_cursor_scheme(theme_name: str, cursor_files: dict[str, str], cursor_size_pixels: int | None = None) -> None:
    if cursor_size_pixels:
        backup_current_cursor_scheme()
        set_system_cursor_size(cursor_size_pixels)
        apply_cursor_scheme(theme_name, cursor_files, backup=False, cursor_size_pixels=cursor_size_pixels)
        return
    apply_cursor_scheme(theme_name, cursor_files, backup=True)


def installer_source(theme_name: str, files: dict[str, str], cursor_size_pixels: int | None = None) -> str:
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
CURSOR_SIZE_PIXELS = {json.dumps(cursor_size_pixels)}


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return Path(__file__).resolve().parent / relative


def log_error(exc):
    log = Path(__file__).resolve().with_name("错误记录.txt")
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"\\n## {{datetime.now():%Y-%m-%d %H:%M:%S}} 安装失败\\n\\n```text\\n{{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))}}\\n```\\n")


def broadcast_settings_change(area):
    message = ctypes.create_unicode_buffer(area)
    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, ctypes.cast(message, ctypes.c_void_p), 0x0002, 1000, ctypes.byref(result))


def apply_cursor_size(size):
    if not size:
        return
    size = max(1, min(256, int(size)))
    if size <= 32:
        step = 1
    elif size >= 256:
        step = 15
    else:
        step = max(1, min(15, int(round((size - 32) / 16.0)) + 1))
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "CursorBaseSize", 0, winreg.REG_DWORD, size)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Accessibility", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "CursorSize", 0, winreg.REG_DWORD, step)
    if not ctypes.windll.user32.SystemParametersInfoW(0x2029, 0, ctypes.c_void_p(size), 0x01 | 0x02):
        raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
    broadcast_settings_change("Control Panel\\\\Cursors")
    broadcast_settings_change("SOFTWARE\\\\Microsoft\\\\Accessibility")


def install():
    target_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "MouseCursorThemes" / THEME_NAME
    target_dir.mkdir(parents=True, exist_ok=True)
    installed = {{}}
    for reg_name, file_name in CURSOR_FILES.items():
        src = resource_path("assets") / file_name
        dst = target_dir / file_name
        shutil.copy2(src, dst)
        installed[reg_name] = str(dst)

    apply_cursor_size(CURSOR_SIZE_PIXELS)
    ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0x01 | 0x02)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\\Cursors", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, THEME_NAME)
        winreg.SetValueEx(key, "Scheme Source", 0, winreg.REG_DWORD, 2)
        if CURSOR_SIZE_PIXELS:
            winreg.SetValueEx(key, "CursorBaseSize", 0, winreg.REG_DWORD, int(CURSOR_SIZE_PIXELS))
        for reg_name, file_path in installed.items():
            winreg.SetValueEx(key, reg_name, 0, winreg.REG_EXPAND_SZ, file_path)

    ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0x01 | 0x02)
    broadcast_settings_change("Control Panel\\\\Cursors")
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
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    if not IS_FROZEN:
        return sys.executable
    candidates = [
        resource_path("runtime/python/Scripts/python.exe"),
        resource_path("runtime/python/python.exe"),
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
        result = subprocess.run(
            [str(path), "-c", "import PyInstaller"],
            text=True,
            capture_output=True,
            check=False,
            creationflags=creationflags,
        )
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


def find_bundled_7zip() -> Path | None:
    for relative in ("runtime/7zip/7z.exe", "runtime/7zip/7za.exe"):
        candidate = resource_path(relative)
        if candidate.exists():
            return candidate
    return None


def run_archive_tool(command: list[str]) -> subprocess.CompletedProcess:
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    return subprocess.run(command, text=True, capture_output=True, check=False, creationflags=creationflags)


def extract_rar_with_7zip(source: Path, target: Path, executable: Path) -> None:
    result = run_archive_tool([str(executable), "x", "-y", f"-o{target}", str(source)])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or f"7-Zip exit code {result.returncode}"
        raise RuntimeError(detail)


def extract_rar_with_winrar(source: Path, target: Path, executable: Path) -> None:
    result = run_archive_tool([str(executable), "x", "-ibck", "-inul", "-y", str(source), f"{target}\\"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or f"WinRAR exit code {result.returncode}"
        raise RuntimeError(detail)


def classify_rar_error(messages: list[str]) -> str:
    joined = " | ".join(message for message in messages if message).lower()
    if any(flag in joined for flag in ("password", "encrypted", "crypt", "加密", "密码")):
        return "暂不支持导入加密的 RAR 压缩包。"
    if any(flag in joined for flag in ("not found", "cannot execute", "no such file", "unrar", "7-zip", "winrar")):
        return "无法导入 RAR：缺少可用的解压运行时，请安装 WinRAR/7-Zip 或在打包时附带 runtime/7zip。"
    if joined:
        return f"无法导入 RAR：{messages[0]}"
    return "无法导入 RAR：没有可用的解压方式。"


def parse_drop_paths(data: str, tk_root: Tk) -> list[Path]:
    return [Path(item) for item in tk_root.tk.splitlist(data)]


def cursor_preview_image(path: Path, box: tuple[int, int] = (180, 140)) -> Image.Image:
    return cursor_preview_image_sized(path, box)


def cursor_preview_image_sized(path: Path, box: tuple[int, int] = (180, 140), cursor_size: int | None = None) -> Image.Image:
    margin = 8
    if path.suffix.lower() in {".cur", ".ani"}:
        size = cursor_size or max(24, min(box) - margin * 2)
        rendered = render_cursor_with_windows(path, size)
        if rendered:
            bg = Image.new("RGBA", box, (248, 250, 252, 255))
            bg.alpha_composite(rendered, ((box[0] - rendered.width) // 2, (box[1] - rendered.height) // 2))
            return bg
    try:
        image = centered_rgba(image_from_path(path), cursor_size or max(16, min(box) - margin * 2))
    except Exception:
        return preview_placeholder_image(path, box, animated=path.suffix.lower() == ".ani")
    bg = Image.new("RGBA", box, (248, 250, 252, 255))
    bg.alpha_composite(image, ((box[0] - image.width) // 2, (box[1] - image.height) // 2))
    return bg


def size_level_to_pixels(level: int) -> int:
    return max(1, min(15, int(level))) * 16 + 16


def pixels_to_size_level(pixels: int) -> int:
    return max(1, min(15, int(round((max(1, min(256, int(pixels))) - 16) / 16.0))))


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
    candidates = [p for p in files if p.suffix.lower() in {".cur", ".ani"}]
    rules = [
        ("Hand", ["hand", "link", "pointer_hand", "pointerhand", "pointing_hand", "pointinghand", "手指", "链接", "链接选择"]),
        ("NWPen", ["pen", "nwpen", "handwriting", "ink", "hand_write", "手写"]),
        ("Crosshair", ["cross", "crosshair", "precision", "precise", "precision_select", "precisionselect", "十字", "精确选择"]),
        ("Pin", ["pin", "location", "locate", "position", "geo", "地图", "位置", "位置选择"]),
        ("Person", ["person", "people", "user", "contact", "individual", "个人", "个人选择"]),
        ("Arrow", ["arrow", "normal", "default", "left_ptr", "leftptr", "pointer_default", "正常选择"]),
        ("Help", ["help", "question", "help_select", "helpsel", "帮助选择"]),
        ("AppStarting", ["appstarting", "app_starting", "working", "starting", "后台运行"]),
        ("Wait", ["busy", "wait", "waiting", "忙", "等待"]),
        ("IBeam", ["beam", "ibeam", "text", "text_select", "textselect", "文本", "文本选择"]),
        ("No", ["no", "unavailable", "forbidden", "blocked", "禁用", "不可用"]),
        ("SizeNS", ["sizens", "size_ns", "vert", "vertical", "上下"]),
        ("SizeWE", ["sizewe", "size_we", "horiz", "horizontal", "左右"]),
        ("SizeNWSE", ["nwse", "size_nwse"]),
        ("SizeNESW", ["nesw", "size_nesw"]),
        ("SizeAll", ["all", "move", "sizeall", "move_cursor", "移动"]),
        ("UpArrow", ["up", "uparrow", "alternate", "up_arrow", "向上"]),
    ]
    for reg, keys in rules:
        for path in candidates:
            if path in mapping.values():
                continue
            if _cursor_name_matches(path, keys):
                mapping[reg] = path
                break
    numbered = {p.stem: p for p in candidates if p.stem.isdigit()}
    for index, role in enumerate(CURSOR_ROLES, start=1):
        key = f"{index:02d}"
        if role.reg_name not in mapping and key in numbered:
            mapping[role.reg_name] = numbered[key]
    return mapping


def _strip_inf_comment(line: str) -> str:
    in_quote = False
    for index, char in enumerate(line):
        if char == '"':
            in_quote = not in_quote
        elif char == ";" and not in_quote:
            return line[:index]
    return line


def _decode_inf_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "gbk", "cp936", "latin1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="ignore")


def _split_inf_fields(value: str) -> list[str]:
    fields: list[str] = []
    buffer: list[str] = []
    in_quote = False
    for char in value:
        if char == '"':
            in_quote = not in_quote
            continue
        if char == "," and not in_quote:
            fields.append("".join(buffer).strip())
            buffer = []
            continue
        buffer.append(char)
    fields.append("".join(buffer).strip())
    return fields


def _parse_inf_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"": []}
    current = ""
    for raw_line in text.splitlines():
        line = _strip_inf_comment(raw_line).strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            current = line[1:line.index("]")].strip().lower()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _inf_strings(sections: dict[str, list[str]]) -> dict[str, str]:
    strings: dict[str, str] = {}
    for line in sections.get("strings", []):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().strip("%").lower()
        parts = _split_inf_fields(value)
        strings[key] = (parts[0] if parts else value).strip().strip('"')
    return strings


def _expand_inf_vars(value: str, strings: dict[str, str], depth: int = 0) -> str:
    if depth > 8:
        return value

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip().lower()
        if key.isdigit():
            return ""
        replacement = strings.get(key)
        if replacement is None:
            return match.group(0)
        return _expand_inf_vars(replacement, strings, depth + 1)

    return re.sub(r"%([^%]+)%", replace, value)


def _normalize_inf_alias(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.strip().strip("%").strip('"').lower())


def _inf_alias_to_reg() -> dict[str, str]:
    aliases: dict[str, list[str]] = {
        "Arrow": ["arrow", "normal", "default", "left_ptr", "leftptr", "pointer", "cursor", "normal_select", "normalselect", "normalcursor", "正常选择"],
        "Help": ["help", "helpsel", "help_select", "helpselect", "question", "帮助选择"],
        "AppStarting": ["work", "working", "appstarting", "app_starting", "background", "busy_wait", "后台运行"],
        "Wait": ["busy", "wait", "waiting", "等待"],
        "Crosshair": ["cross", "crosshair", "precision", "precision_select", "precisionselect", "精确选择"],
        "IBeam": ["text", "ibeam", "beam", "text_select", "textselect", "文本选择"],
        "NWPen": ["pen", "nwpen", "handwriting", "hand_write", "write", "ink", "手写"],
        "No": ["unavailable", "unavailiable", "forbidden", "blocked", "no", "不可用"],
        "SizeNS": ["vert", "vertical", "sizens", "size_ns", "ns", "上下"],
        "SizeWE": ["horz", "horiz", "horizontal", "sizewe", "size_we", "we", "左右"],
        "SizeNWSE": ["dgn1", "nwse", "size_nwse", "对角线1"],
        "SizeNESW": ["dgn2", "nesw", "size_nesw", "对角线2"],
        "SizeAll": ["move", "all", "sizeall", "size_all", "移动"],
        "UpArrow": ["alternate", "up", "uparrow", "up_arrow", "候选"],
        "Hand": ["hand", "link", "pointerhand", "pointer_hand", "pointinghand", "handcursor", "链接选择"],
        "Pin": ["pin", "location", "locate", "position", "geo", "place", "位置选择", "位置"],
        "Person": ["person", "people", "user", "contact", "individual", "个人选择", "个人"],
    }
    result: dict[str, str] = {}
    for reg in ROLE_BY_REG:
        result[_normalize_inf_alias(reg)] = reg
    for reg, names in aliases.items():
        for name in names:
            result[_normalize_inf_alias(name)] = reg
    return result


def _cursor_path_from_inf_value(
    value: str,
    root: Path,
    by_name: dict[str, Path],
    by_relative: dict[str, Path],
    strings: dict[str, str],
) -> Path | None:
    expanded = _expand_inf_vars(value.strip().strip('"'), strings)
    if not expanded:
        return None
    candidates = _split_inf_fields(expanded)
    candidates.append(expanded)
    for candidate in candidates:
        cleaned = candidate.strip().strip('"').replace("\\", "/")
        if not cleaned:
            continue
        relative_key = cleaned.lstrip("/").lower()
        if relative_key in by_relative:
            return by_relative[relative_key]
        name = Path(cleaned).name.lower()
        if name in by_name:
            return by_name[name]
        if cleaned.lower().endswith((".cur", ".ani")):
            maybe_path = (root / cleaned).resolve()
            try:
                if maybe_path.exists():
                    return maybe_path
            except OSError:
                pass
    return None


def parse_inf_mapping(root: Path) -> dict[str, Path]:
    infs = sorted(root.rglob("*.inf"))
    files = [p for p in root.rglob("*") if p.suffix.lower() in {".cur", ".ani"}]
    if not infs:
        return map_files_to_roles(files)
    mapping: dict[str, Path] = {}
    by_name = {p.name.lower(): p for p in files}
    by_relative = {
        str(p.relative_to(root)).replace("\\", "/").lower(): p
        for p in files
    }
    alias_to_reg = _inf_alias_to_reg()
    for inf in infs:
        sections = _parse_inf_sections(_decode_inf_text(inf))
        strings = _inf_strings(sections)
        for lines in sections.values():
            for line in lines:
                fields = _split_inf_fields(line)
                normalized_fields = [field.replace("/", "\\").lower() for field in fields]
                for index, field in enumerate(normalized_fields):
                    if "control panel\\cursors" not in field:
                        continue
                    if index + 1 >= len(fields):
                        continue
                    reg = alias_to_reg.get(_normalize_inf_alias(_expand_inf_vars(fields[index + 1], strings)))
                    if not reg:
                        continue
                    for candidate in reversed(fields[index + 2:]):
                        path = _cursor_path_from_inf_value(candidate, root, by_name, by_relative, strings)
                        if path:
                            mapping[reg] = path
                            break
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                reg = alias_to_reg.get(_normalize_inf_alias(_expand_inf_vars(key, strings)))
                if not reg:
                    continue
                path = _cursor_path_from_inf_value(value, root, by_name, by_relative, strings)
                if path:
                    mapping[reg] = path
    mapping.update({k: v for k, v in map_files_to_roles(files).items() if k not in mapping})
    return mapping


def extract_import_package(source: Path) -> Path:
    if source.is_dir():
        return source
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
        errors: list[str] = []
        bundled_7zip = find_bundled_7zip()
        if bundled_7zip:
            try:
                extract_rar_with_7zip(source, target, bundled_7zip)
                return target
            except Exception as exc:
                errors.append(f"7-Zip: {exc}")
        winrar = find_winrar()
        if winrar:
            try:
                extract_rar_with_winrar(source, target, winrar)
                return target
            except Exception as exc:
                errors.append(f"WinRAR: {exc}")
        try:
            import rarfile
            with rarfile.RarFile(source) as archive:
                archive.extractall(target)
            return target
        except Exception as exc:
            errors.append(f"rarfile: {exc}")
        raise RuntimeError(classify_rar_error(errors))
    if source.suffix.lower() == ".exe":
        if extract_pyinstaller_assets(source, target):
            return target
    result = subprocess.run(["tar", "-xf", str(source), "-C", str(target)], text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return target
    raise RuntimeError(f"无法解压 {source.name}。该文件可能不是可读取的压缩包，或 EXE 不是自解压格式。")


def startup_folder() -> Path:
    startup = Path(os.environ.get("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    return startup


def startup_script_path() -> Path:
    return startup_folder() / f"{APP_NAME}后台.lnk"


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_hidden_powershell(script: str) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        text=True,
        capture_output=True,
        check=False,
        creationflags=creationflags,
    )


def create_shortcut(link_path: Path, target: Path, arguments: str = "", working_dir: Path | None = None, icon: Path | None = None) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    working_dir = working_dir or target.parent
    icon = icon or target
    script = "\n".join([
        "$shell = New-Object -ComObject WScript.Shell",
        f"$shortcut = $shell.CreateShortcut({ps_quote(str(link_path))})",
        f"$shortcut.TargetPath = {ps_quote(str(target))}",
        f"$shortcut.Arguments = {ps_quote(arguments)}",
        f"$shortcut.WorkingDirectory = {ps_quote(str(working_dir))}",
        "$shortcut.WindowStyle = 7",
        f"$shortcut.IconLocation = {ps_quote(str(icon) + ',0')}",
        "$shortcut.Save()",
    ])
    result = run_hidden_powershell(script)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "创建快捷方式失败").strip())


def create_desktop_app_shortcut() -> Path:
    command = gui_command()
    target = Path(command[0])
    arguments = subprocess.list2cmdline(command[1:])
    link_path = desktop_folder() / f"{APP_NAME}.lnk"
    create_shortcut(link_path, target, arguments, APP_DIR, target)
    return link_path


def write_startup_script(_command: str) -> None:
    command = startup_command()
    target = Path(command[0])
    arguments = subprocess.list2cmdline(command[1:])
    create_shortcut(startup_script_path(), target, arguments, APP_DIR, target)


def scheduled_task_command() -> str:
    return subprocess.list2cmdline(startup_command())


def scheduled_task_exists() -> bool:
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", SCHEDULED_TASK_NAME],
        text=True,
        capture_output=True,
        check=False,
        creationflags=creationflags,
    )
    return result.returncode == 0


def run_auto_start_exists() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            for value_name in (AUTO_START_VALUE, LEGACY_AUTO_START_VALUE):
                try:
                    value, _ = winreg.QueryValueEx(key, value_name)
                except FileNotFoundError:
                    continue
                if value:
                    return True
    except FileNotFoundError:
        return False
    return False


def auto_start_enabled() -> bool:
    return run_auto_start_exists() or startup_script_path().exists() or scheduled_task_exists()


def startup_status_text() -> str:
    run_item = run_auto_start_exists()
    startup_link = startup_script_path().exists()
    task = scheduled_task_exists()
    if not (run_item or startup_link or task):
        return "自启动状态：未开启"
    parts = []
    if run_item:
        parts.append("注册表")
    if startup_link:
        parts.append("启动文件夹")
    if task:
        parts.append("任务计划")
    status = "自启动状态：正常（" + "、".join(parts) + "）"
    if startup_task_blocked() and not task:
        status += "；任务计划受限，已使用普通自启动方式"
    return status


def startup_task_blocked() -> bool:
    return load_settings().get("startup_task_blocked") == "1"


def access_denied_error(exc: BaseException | str) -> bool:
    text = str(exc).lower()
    return "拒绝访问" in text or "access is denied" in text or "access denied" in text


def set_startup_task(enabled: bool) -> None:
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    if enabled:
        command = [
            "schtasks.exe",
            "/Create",
            "/TN",
            SCHEDULED_TASK_NAME,
            "/SC",
            "ONLOGON",
            "/TR",
            scheduled_task_command(),
            "/RL",
            "LIMITED",
            "/F",
        ]
    else:
        command = ["schtasks.exe", "/Delete", "/TN", SCHEDULED_TASK_NAME, "/F"]
    result = subprocess.run(command, text=True, capture_output=True, check=False, creationflags=creationflags)
    if enabled and result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "创建任务计划失败").strip())


def try_enable_startup_task() -> None:
    if startup_task_blocked():
        return
    try:
        set_startup_task(True)
        remove_setting("startup_task_error")
        remove_setting("startup_task_blocked")
    except Exception as exc:
        if access_denied_error(exc):
            update_setting("startup_task_blocked", "1")
        log_error_once("startup_task_error", "创建任务计划自启动失败，已使用注册表和启动文件夹自启动", exc)


def remove_startup_script() -> None:
    for name in (
        f"{APP_NAME}后台.lnk",
        f"{APP_NAME}后台.vbs",
        f"{APP_NAME}后台.cmd",
        "MouseCursorThemeBuilder.lnk",
        "MouseCursorThemeBuilder.vbs",
        "MouseCursorThemeBuilder.cmd",
    ):
        path = startup_folder() / name
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def set_auto_start(enabled: bool) -> None:
    command = subprocess.list2cmdline(startup_command())
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, AUTO_START_VALUE, 0, winreg.REG_SZ, command)
            try:
                winreg.DeleteValue(key, LEGACY_AUTO_START_VALUE)
            except FileNotFoundError:
                pass
        else:
            for value_name in (AUTO_START_VALUE, LEGACY_AUTO_START_VALUE):
                try:
                    winreg.DeleteValue(key, value_name)
                except FileNotFoundError:
                    pass
    if enabled:
        try:
            write_startup_script(command)
        except Exception as exc:
            log_error_once("startup_shortcut_error", "创建启动文件夹快捷方式失败，已保留注册表自启动", exc)
        try_enable_startup_task()
    else:
        remove_startup_script()
        if scheduled_task_exists():
            try:
                set_startup_task(False)
            except Exception as exc:
                log_error_once("startup_task_delete_error", "删除任务计划自启动失败", exc)


def app_command(argument: str) -> list[str]:
    if IS_FROZEN:
        return [str(Path(sys.executable).resolve()), argument]
    return [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), argument]


def hide_taskbar_icon_enabled() -> bool:
    return setting_enabled("hide_taskbar_icon", False)


def startup_command() -> list[str]:
    return background_command() if hide_taskbar_icon_enabled() else tray_command()


def tray_command() -> list[str]:
    return app_command("--tray")


def background_command() -> list[str]:
    return app_command("--background")


def gui_command() -> list[str]:
    if IS_FROZEN:
        return [str(Path(sys.executable).resolve())]
    return [str(Path(sys.executable).resolve()), str(Path(__file__).resolve())]


def acquire_process_lock(pid_file: Path):
    APP_DATA.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(pid_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            payload = {
                "pid": os.getpid(),
                "exe": str(Path(sys.executable).resolve()),
                "started_at": datetime.now().isoformat(timespec="seconds"),
            }
            os.write(fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return fd
        except FileExistsError:
            pid, exe = read_background_pid_file(pid_file)
            if not pid:
                remove_pid_file(pid_file)
                continue
            if pid and background_process_alive(pid, exe):
                return None
            remove_pid_file(pid_file)
        except Exception:
            return None


def start_detached_process(command: list[str]) -> None:
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS
    env = os.environ.copy()
    if IS_FROZEN:
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen(
        command,
        cwd=str(APP_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        env=env,
    )


def start_background_process() -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    pid, exe = read_background_pid_file(APP_DATA / "background.pid")
    if pid and background_process_alive(pid, exe):
        return
    start_detached_process(background_command())


def start_tray_process() -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    pid_file = APP_DATA / "tray.pid"
    pid, exe = read_background_pid_file(pid_file)
    if pid and background_process_alive(pid, exe):
        return
    remove_pid_file(pid_file)
    start_detached_process(tray_command())


def acquire_background_lock():
    return acquire_process_lock(APP_DATA / "background.pid")


def acquire_tray_lock():
    return acquire_process_lock(APP_DATA / "tray.pid")


def acquire_gui_lock():
    return acquire_process_lock(APP_DATA / "gui.pid")


def gui_command_state_path() -> Path:
    return APP_DATA / "gui_command.json"


def write_gui_command_state(port: int, token: str) -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "exe": str(Path(sys.executable).resolve()),
        "port": int(port),
        "token": token,
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    gui_command_state_path().write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def clear_gui_command_state() -> None:
    try:
        gui_command_state_path().unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def notify_existing_gui(command: str = "show") -> bool:
    try:
        state = json.loads(gui_command_state_path().read_text(encoding="utf-8"))
        pid = int(state.get("pid") or 0)
        port = int(state.get("port") or 0)
        token = str(state.get("token") or "")
        exe = str(state.get("exe") or "")
        if not pid or not port or not token or not background_process_alive(pid, exe):
            clear_gui_command_state()
            remove_pid_file(APP_DATA / "gui.pid")
            return False
        payload = json.dumps({"token": token, "command": command}, ensure_ascii=False).encode("utf-8")
        with socket.create_connection(("127.0.0.1", port), timeout=0.5) as client:
            client.sendall(payload)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def remove_pid_file(pid_file: Path) -> None:
    for _ in range(5):
        try:
            pid_file.unlink()
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(0.1)


def read_background_pid_file(pid_file: Path) -> tuple[int, str]:
    try:
        text = pid_file.read_text(encoding="utf-8").strip()
        if not text:
            return 0, ""
        if text.startswith("{"):
            data = json.loads(text)
            return int(data.get("pid") or 0), str(data.get("exe") or "")
        return int(text), ""
    except Exception:
        return 0, ""


def process_image_path(pid: int) -> str:
    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return ""
    try:
        size = ctypes.wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ""
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def same_windows_path(left: str | Path, right: str | Path) -> bool:
    try:
        return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()
    except Exception:
        return str(left).casefold() == str(right).casefold()


def process_exists(pid: int) -> bool:
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def background_process_alive(pid: int, recorded_exe: str = "") -> bool:
    if not process_exists(pid):
        return False
    current_exe = str(Path(sys.executable).resolve())
    image = process_image_path(pid)
    if image:
        if not IS_FROZEN and Path(image).name.lower().startswith("python"):
            return True
        return same_windows_path(image, current_exe)
    if recorded_exe:
        return same_windows_path(recorded_exe, current_exe)
    return False


def terminate_background_process() -> None:
    pid_file = APP_DATA / "background.pid"
    pid, exe = read_background_pid_file(pid_file)
    if not pid or not background_process_alive(pid, exe):
        remove_pid_file(pid_file)
        return
    handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
    if handle:
        try:
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    remove_pid_file(pid_file)


def terminate_tray_process() -> None:
    pid_file = APP_DATA / "tray.pid"
    pid, exe = read_background_pid_file(pid_file)
    if not pid or not background_process_alive(pid, exe):
        remove_pid_file(pid_file)
        return
    handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
    if handle:
        try:
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    remove_pid_file(pid_file)


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



def validate_time(at: str) -> None:
    datetime.strptime(at, "%H:%M")


def main() -> None:
    startup_timing_reset()
    startup_timing_mark("startup.args")
    if "--preview-cursor" in sys.argv:
        try:
            index = sys.argv.index("--preview-cursor")
            raw_target = sys.argv[index + 1] if index + 1 < len(sys.argv) else ""
            target = Path(raw_target).expanduser()
            if raw_target and not target.exists() and index + 2 < len(sys.argv):
                joined = " ".join(sys.argv[index + 1 :])
                joined_target = Path(joined).expanduser()
                if joined_target.exists():
                    target = joined_target
        except Exception:
            target = Path("")
        try:
            import cursor_preview_light
            startup_timing_mark("startup.preview_imports")
            cursor_preview_light.run_cursor_preview_app(sys.modules[__name__], target)
            return
        except Exception as exc:
            log_error("启动光标预览失败", exc)
            try:
                ctypes.windll.user32.MessageBoxW(0, str(exc), APP_NAME, 0x10)
            except Exception:
                pass
            raise SystemExit(1)
    if "--background" in sys.argv:
        run_background()
        return
    if "--tray" in sys.argv:
        try:
            if pystray:
                run_pystray_tray()
                return
        except Exception as exc:
            log_error("启动轻量托盘失败，尝试 Qt 托盘", exc)
        try:
            import fluent_ui

            fluent_ui.run_tray_app(sys.modules[__name__])
            return
        except Exception as exc:
            log_error("启动托盘后台失败", exc)
            run_background()
            return
    exe_name = Path(sys.executable).name if IS_FROZEN else ""
    if "--install" in sys.argv or (IS_FROZEN and is_installer_executable(exe_name)):
        install_application()
        return
    if "--uninstall" in sys.argv or (IS_FROZEN and is_uninstaller_executable(exe_name)):
        uninstall_application()
        return
    try:
        if file_association_enabled():
            apply_cursor_file_association_setting(True)
        startup_timing_mark("startup.settings")
        if notify_existing_gui("show"):
            return
        startup_timing_mark("startup.single_instance")
        terminate_background_process()
        terminate_tray_process()
        startup_timing_mark("startup.stop_background")
        import fluent_ui
        startup_timing_mark("startup.imports")
        fluent_ui.run_app(sys.modules[__name__])
        return
    except Exception as exc:
        log_error("启动 Fluent 界面失败", exc)
        try:
            ctypes.windll.user32.MessageBoxW(0, str(exc), APP_NAME, 0x10)
        except Exception:
            pass
        raise SystemExit(1)


def run_pystray_tray() -> None:
    lock = acquire_tray_lock()
    if lock is None:
        return
    stop_event = threading.Event()
    state = {"last_key": "", "last_timer_at": 0.0, "timer_index": 0}

    def icon_image() -> Image.Image:
        for path in (resource_path("icon终.png"), resource_path("icon.png")):
            if path.exists():
                return Image.open(path).convert("RGBA")
        return Image.new("RGBA", (64, 64), "#4f8cff")

    def cleanup() -> None:
        stop_event.set()
        try:
            os.close(lock)
        except Exception:
            pass
        remove_pid_file(APP_DATA / "tray.pid")

    def open_app(icon, _item=None) -> None:
        start_detached_process(gui_command())
        cleanup()
        icon.stop()

    def hide_tray(icon, _item=None) -> None:
        set_setting_enabled("hide_taskbar_icon", True)
        start_background_process()
        cleanup()
        icon.stop()

    def exit_app(icon, _item=None) -> None:
        cleanup()
        icon.stop()

    def apply_scheduled_once() -> None:
        schedule_items, week_items = load_schedule_state()
        now = datetime.now()
        for item in schedule_items:
            if item.get("mode") == "input":
                state_name = current_input_state()
                scheme = item.get(f"{state_name}_scheme", "")
                key = f"input|{state_name}|{scheme}"
                if scheme and key != state["last_key"]:
                    picked = resolve_input_switch_scheme(item, state_name)
                    if picked:
                        apply_library_scheme(picked)
                    state["last_key"] = key
                continue
            if item.get("mode") == "timer":
                interval = max(1, int(item.get("interval_seconds") or 0))
                if time.time() - state["last_timer_at"] >= interval:
                    scheme = pick_scheduled_scheme(item.get("scheme", ""), item.get("order", "顺序"), state["timer_index"], item.get("selected_schemes"))
                    state["timer_index"] += 1
                    state["last_timer_at"] = time.time()
                    if scheme:
                        apply_library_scheme(scheme)
                continue
            scheme = item.get("scheme", "")
            key = f"{now:%Y-%m-%d}|{item.get('time')}|{scheme}"
            if scheme and item.get("time") == now.strftime("%H:%M") and key != state["last_key"]:
                picked = pick_scheduled_scheme(scheme, item.get("order", "顺序"), 0)
                if picked:
                    apply_library_scheme(picked)
                state["last_key"] = key
                return
        scheme = week_items.get(str(now.weekday()))
        key = f"{now:%Y-%m-%d}|week|{scheme}"
        if scheme and key != state["last_key"]:
            picked = pick_scheduled_scheme(scheme, "随机", 0) if scheme == RANDOM_SCHEME_VALUE else scheme
            if picked:
                apply_library_scheme(picked)
            state["last_key"] = key

    def schedule_loop() -> None:
        while not stop_event.is_set():
            try:
                schedule_items, _week_items = load_schedule_state()
                apply_scheduled_once()
                if any(item.get("mode") == "input" for item in schedule_items):
                    delay = 0.12
                elif any(item.get("mode") == "timer" for item in schedule_items):
                    delay = 0.5
                else:
                    delay = 10.0
            except Exception as exc:
                log_error("轻量托盘后台切换失败", exc)
                delay = 10.0
            stop_event.wait(delay)

    threading.Thread(target=schedule_loop, daemon=True).start()
    menu = pystray.Menu(
        pystray.MenuItem(lambda _item: tray_text("打开"), open_app, default=True),
        pystray.MenuItem(lambda _item: tray_text(f"当前配置：{configured_current_scheme()}"), None, enabled=False),
        pystray.MenuItem(lambda _item: tray_text(f"下次切换：{next_switch_text(*load_schedule_state())}"), None, enabled=False),
        pystray.MenuItem(lambda _item: tray_text("隐藏任务栏"), hide_tray),
        pystray.MenuItem(lambda _item: tray_text("退出"), exit_app),
    )
    icon = pystray.Icon(APP_NAME, icon_image(), APP_NAME, menu=menu)
    try:
        icon.run()
    finally:
        cleanup()


def run_background() -> None:
    lock = acquire_background_lock()
    if lock is None:
        return
    last_key = ""
    last_timer_at = 0.0
    timer_index = 0
    fast_schedule = False
    input_schedule = False
    timer_schedule = False
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
            input_schedule = any(item.get("mode") == "input" for item in items)
            timer_schedule = any(item.get("mode") == "timer" for item in items)
            fast_schedule = input_schedule or timer_schedule
            for item in items:
                if item.get("mode") == "input":
                    state = current_input_state()
                    scheme = item.get(f"{state}_scheme", "")
                    key = f"input|{state}|{scheme}"
                    if scheme and key != last_key:
                        picked = resolve_input_switch_scheme(item, state)
                        if picked:
                            apply_library_scheme(picked)
                        last_key = key
                    continue
                if item.get("mode") == "timer":
                    interval = max(1, int(item.get("interval_seconds") or 0))
                    if time.time() - last_timer_at >= interval:
                        scheme = pick_scheduled_scheme(item.get("scheme", ""), item.get("order", "顺序"), timer_index, item.get("selected_schemes"))
                        timer_index += 1
                        last_timer_at = time.time()
                        if scheme:
                            apply_library_scheme(scheme)
                    continue
                key = f"{now:%Y-%m-%d}|{item.get('time')}|{item.get('scheme')}"
                if item.get("time") == now.strftime("%H:%M") and key != last_key:
                    scheme = pick_scheduled_scheme(item.get("scheme", ""), item.get("order", "顺序"), 0)
                    if scheme:
                        apply_library_scheme(scheme)
                    last_key = key
            scheme = week_items.get(str(now.weekday()))
            key = f"{now:%Y-%m-%d}|week|{scheme}"
            if scheme and key != last_key:
                picked = pick_scheduled_scheme(scheme, "随机", 0) if scheme == RANDOM_SCHEME_VALUE else scheme
                if picked:
                    apply_library_scheme(picked)
                last_key = key
        except Exception as exc:
            log_error("后台切换失败", exc)
        time.sleep(0.12 if input_schedule else (0.25 if timer_schedule else 30))


def available_scheme_names() -> list[str]:
    if not SCHEME_LIBRARY.exists():
        return []
    names = []
    for path in SCHEME_LIBRARY.iterdir():
        if path.is_dir() and (path / "scheme.json").exists():
            names.append(path.name)
    return sorted(names, key=lambda name: scheme_order_value(SCHEME_LIBRARY / name))


def pick_scheduled_scheme(value: str, order: str = "顺序", index: int = 0, selected_schemes: list[str] | None = None) -> str:
    all_names = available_scheme_names()
    selected = [name for name in (selected_schemes or []) if name in all_names]
    names = selected or all_names
    if not names:
        return ""
    if value == RANDOM_SCHEME_VALUE or order == "随机":
        return random.choice(names)
    # 顺序：按 scheme_library 中的排序依次切换
    if value == "顺序":
        if selected:
            return names[index % len(names)]
        try:
            current = SCHEDULE_FILE.exists() and json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            current = None
        seq_index = 0
        if isinstance(current, list):
            for item in current:
                if item.get("mode") == "timer":
                    seq_index = int(item.get("sequential_index", 0) or 0)
                    break
        seq_index = (seq_index + 1) % len(names)
        if isinstance(current, list):
            for item in current:
                if item.get("mode") == "timer":
                    item["sequential_index"] = seq_index
                    break
            try:
                SCHEDULE_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        return names[seq_index]
    # 固定方案名
    return value


def resolve_input_switch_scheme(item: dict, state: str) -> str:
    scheme = str(item.get(f"{state}_scheme", "") or "").strip()
    if not scheme or scheme == RANDOM_SCHEME_VALUE:
        return ""
    return scheme if scheme in available_scheme_names() else ""


def focused_window_handle() -> int:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
    user32.GetGUIThreadInfo.argtypes = [ctypes.wintypes.DWORD, ctypes.c_void_p]
    user32.GetGUIThreadInfo.restype = ctypes.wintypes.BOOL
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0
    thread_id = user32.GetWindowThreadProcessId(hwnd, None)
    size = 72 if ctypes.sizeof(ctypes.c_void_p) == 8 else 48
    buf = ctypes.create_string_buffer(size)
    struct.pack_into("<I", buf, 0, size)
    if user32.GetGUIThreadInfo(thread_id, ctypes.byref(buf)):
        focus_offset = 16 if ctypes.sizeof(ctypes.c_void_p) == 8 else 12
        focused = struct.unpack_from("<Q" if ctypes.sizeof(ctypes.c_void_p) == 8 else "<I", buf, focus_offset)[0]
        if focused:
            return focused
    return hwnd


def ime_status_values(hwnd: int, timeout_ms: int = 15) -> tuple[int, int]:
    user32 = ctypes.windll.user32
    imm32 = ctypes.windll.imm32
    imm32.ImmGetDefaultIMEWnd.argtypes = [ctypes.c_void_p]
    imm32.ImmGetDefaultIMEWnd.restype = ctypes.wintypes.HWND
    user32.SendMessageTimeoutW.argtypes = [
        ctypes.c_void_p,
        ctypes.wintypes.UINT,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.wintypes.UINT,
        ctypes.wintypes.UINT,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    user32.SendMessageTimeoutW.restype = ctypes.wintypes.LPARAM
    ime_hwnd = imm32.ImmGetDefaultIMEWnd(hwnd)
    if not ime_hwnd:
        return 0, 0
    WM_IME_CONTROL = 0x0283
    IMC_GETCONVERSIONMODE = 0x0001
    IMC_GETOPENSTATUS = 0x0005
    SMTO_ABORTIFHUNG = 0x0002

    def send(command: int) -> int:
        result = ctypes.c_size_t()
        ok = user32.SendMessageTimeoutW(ime_hwnd, WM_IME_CONTROL, command, None, SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result))
        return int(result.value) if ok else 0

    return send(IMC_GETOPENSTATUS), send(IMC_GETCONVERSIONMODE)


def current_input_state(timeout_ms: int = 15) -> str:
    user32 = ctypes.windll.user32
    caps_on = bool(user32.GetKeyState(0x14) & 1)
    if caps_on:
        return "upper"
    hwnd = focused_window_handle()
    open_status, conversion_mode = ime_status_values(hwnd, timeout_ms)
    return "zh" if open_status and (conversion_mode & 1) else "en"


def apply_library_scheme(theme: str) -> None:
    scheme_dir = SCHEME_LIBRARY / theme
    manifest_path = scheme_dir / "scheme.json"
    if not manifest_path.exists():
        raise RuntimeError(f"方案库中没有找到：{theme}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files", {})
    apply_refreshed_cursor_scheme(theme, {reg_name: str(scheme_dir / name) for reg_name, name in files.items()})


def next_switch_text(schedule_items: list[dict[str, str]], week_items: dict[str, str]) -> str:
    now = datetime.now()
    candidates = []
    for item in schedule_items:
        if item.get("mode") == "timer":
            interval = int(item.get("interval_seconds") or 0)
            if interval > 0:
                selected = item.get("selected_schemes")
                if isinstance(selected, list) and selected:
                    scheme = f"{item.get('order', '顺序')} {len(selected)} 个方案"
                else:
                    scheme = item.get("scheme", "")
                candidates.append((now + timedelta(seconds=interval), scheme))
            continue
        at = item.get("time", "")
        scheme = item.get("scheme", "")
        if re.fullmatch(r"\d{2}:\d{2}", at) and scheme:
            hour, minute = map(int, at.split(":"))
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target < now:
                target = target.replace(day=target.day) + timedelta(days=1)
            candidates.append((target, scheme))
    for offset in range(7):
        day = (now.weekday() + offset) % 7
        scheme = week_items.get(str(day))
        if not scheme:
            continue
        target = (now + timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=7)
        candidates.append((target, scheme))
    if not candidates:
        return ""
    target, scheme = min(candidates, key=lambda item: item[0])
    return f"{target:%m-%d %H:%M} {scheme}"


def load_schedule_state() -> tuple[list[dict[str, str]], dict[str, str]]:
    items: list[dict[str, str]] = []
    week_items: dict[str, str] = {}
    try:
        if SCHEDULE_FILE.exists():
            data = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else []
    except Exception as exc:
        log_error("读取时间切换配置失败", exc)
    try:
        if WEEK_SCHEDULE_FILE.exists():
            data = json.loads(WEEK_SCHEDULE_FILE.read_text(encoding="utf-8"))
            week_items = data if isinstance(data, dict) else {}
    except Exception as exc:
        log_error("读取星期切换配置失败", exc)
    return items, week_items


def desktop_folder() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def start_menu_folder() -> Path:
    folder = Path(os.environ.get("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def installed_main_exe() -> Path:
    return INSTALL_ROOT / f"{APP_NAME}.exe"


def installed_uninstaller_exe() -> Path:
    return INSTALL_ROOT / f"卸载{APP_NAME}.exe"


def remove_app_shortcuts() -> None:
    for path in [
        desktop_folder() / f"{APP_NAME}.lnk",
        desktop_folder() / "打开鼠标指针文件夹.lnk",
        start_menu_folder() / f"{APP_NAME}.lnk",
        start_menu_folder() / f"卸载{APP_NAME}.lnk",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        start_menu_folder().rmdir()
    except OSError:
        pass


def create_open_folder_shortcut(folder: Path) -> None:
    explorer = Path(os.environ.get("WINDIR", r"C:\Windows")) / "explorer.exe"
    create_shortcut(desktop_folder() / "打开鼠标指针文件夹.lnk", explorer, str(folder), folder, explorer)


def native_message(title: str, text: str, flags: int = 0x40) -> int:
    try:
        return int(ctypes.windll.user32.MessageBoxW(0, text, title, flags))
    except Exception:
        return 0


def install_application() -> None:
    if not IS_FROZEN:
        raise RuntimeError("安装模式需要先打包成 EXE。")
    source = Path(sys.executable).resolve()
    INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
    main_exe = installed_main_exe()
    uninstaller_exe = installed_uninstaller_exe()
    if source != main_exe:
        shutil.copy2(source, main_exe)
    shutil.copy2(source, uninstaller_exe)
    create_shortcut(desktop_folder() / f"{APP_NAME}.lnk", main_exe, "", INSTALL_ROOT, main_exe)
    create_shortcut(start_menu_folder() / f"{APP_NAME}.lnk", main_exe, "", INSTALL_ROOT, main_exe)
    create_shortcut(start_menu_folder() / f"卸载{APP_NAME}.lnk", uninstaller_exe, "", INSTALL_ROOT, uninstaller_exe)
    try:
        create_open_folder_shortcut(configured_storage_root())
    except Exception as exc:
        log_error("创建鼠标文件夹快捷方式失败", exc)
    if file_association_enabled():
        try:
            register_cursor_file_associations(main_exe)
        except Exception as exc:
            log_error("写入文件关联失败", exc)
    native_message("安装完成", f"{APP_NAME} 已安装到：\n{INSTALL_ROOT}\n\n桌面和开始菜单快捷方式已创建。")


def ask_uninstall_choice() -> str:
    result = native_message(
        "卸载",
        "卸载后是否保留鼠标指针文件？\n\n"
        f"鼠标文件夹：{configured_storage_root()}\n\n"
        "是：保留并打开文件夹\n否：保留\n取消：不保留",
        0x00000003 | 0x00000020,
    )
    if result == 6:
        return "keep_open"
    if result == 2:
        return "delete"
    return "keep"


def schedule_install_dir_cleanup() -> None:
    script = "\n".join([
        "Start-Sleep -Seconds 2",
        "for ($i = 0; $i -lt 45; $i++) {",
        f"  Remove-Item -LiteralPath {ps_quote(str(INSTALL_ROOT))} -Recurse -Force -ErrorAction SilentlyContinue",
        f"  if (-not (Test-Path -LiteralPath {ps_quote(str(INSTALL_ROOT))})) {{ break }}",
        "  Start-Sleep -Seconds 1",
        "}",
    ])
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def uninstall_application() -> None:
    choice = ask_uninstall_choice()
    try:
        unregister_cursor_file_associations()
        set_auto_start(False)
        terminate_background_process()
        remove_app_shortcuts()
        if choice == "delete":
            shutil.rmtree(configured_storage_root(), ignore_errors=True)
        else:
            configured_storage_root().mkdir(parents=True, exist_ok=True)
            try:
                create_open_folder_shortcut(configured_storage_root())
            except Exception as exc:
                log_error("创建保留文件夹快捷方式失败", exc)
        schedule_install_dir_cleanup()
        if choice == "keep_open":
            os.startfile(configured_storage_root())
        native_message("卸载完成", "卸载已完成。")
    except Exception as exc:
        log_error("卸载失败", exc)
        native_message("卸载失败", str(exc), 0x10)


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



if __name__ == "__main__":
    main()
