from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QMimeData, QPoint, QRect, Qt, QUrl, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QDrag, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    QSystemTrayIcon,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
    EditableComboBox,
    FluentIcon as FIF,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    NavigationItemPosition,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    Theme,
    ToggleButton,
    setTheme,
    setThemeColor,
)


CN_TO_EN = {
    "鼠标指针配置管理器": "Mouse Pointer Manager",
    "鼠标指针配置生成器": "Mouse Pointer Builder",
    "鼠标方案": "Schemes",
    "资源库": "Library",
    "方案切换": "Switching",
    "设置": "Settings",
    "推荐": "推荐",
    "时间切换": "Time switching",
    "计时切换": "Timer switching",
    "星期切换": "Weekday switching",
    "中英文切换": "Input language switching",
    "时间切换、计时切换、星期切换、中英文切换只能启用一种。开启或修改后会自动保存。": "Only one switching mode can be enabled. Changes are saved automatically.",
    "亮色模式": "Light mode",
    "暗色模式": "Dark mode",
    "每": "Every",
    "秒": "Seconds",
    "分钟": "Minutes",
    "随机": "Random",
    "顺序": "Sequential",
    "随机方案": "Random scheme",
    "中文输入": "Chinese input",
    "英文输入": "English input",
    "大写锁定": "Caps Lock",
    "后台根据当前前台窗口输入状态切换；大写锁定优先。": "The background service switches by the active input state. Caps Lock has priority.",
    "打开 Auto Dark Mode": "Open Auto Dark Mode",
    "打开 InputTip": "Open InputTip",
    "中英文切换鼠标指针资源（InputTip）": "InputTip cursor resources",
    "打开指针资源": "Open cursor resources",
    "鼠标文件存放位置": "Cursor file location",
    "选择": "Choose",
    "打开文件夹": "Open folder",
    "添加桌面快捷方式": "Add desktop shortcut",
    "自启动后台": "Start with Windows",
    "修复自启动": "Repair startup",
    "自启动状态：未开启": "Startup: Off",
    "自启动状态：正常": "Startup: OK",
    "任务计划受限，已使用普通自启动方式": "Task Scheduler is restricted; regular startup is being used.",
    "隐藏任务栏": "Hide tray",
    "开启后开机只保留后台进程；关闭窗口也不会显示托盘图标。": "When enabled, only the background service is kept and no tray icon is shown after closing.",
    "语言：英文": "Language: English",
    "保存设置": "Save settings",
    "检测更新": "Check updates",
    "GitHub 源地址": "GitHub source",
    "打开": "Open",
    "退出": "Exit",
    "新建": "New",
    "重命名": "Rename",
    "删除": "Delete",
    "导入": "Import",
    "导入文件夹": "Explorer",
    "保存": "Save",
    "截图导出": "Export screenshot",
    "方案预览截图": "Scheme preview",
    "导出完成": "Export complete",
    "已导出": "Exported",
    "没有可导出的方案内容。": "There is no scheme content to export.",
    "没有可导出的鼠标指针资源。": "There are no cursor resources to export.",
    "请选择导出位置": "Choose export location",
    "是否在桌面添加快捷方式？": "Add a desktop shortcut?",
    "后续也可以在设置里添加桌面快捷方式。": "You can also add it later from Settings.",
    "创建快捷方式": "Create shortcut",
    "快捷方式已创建": "Shortcut created",
    "自动保存": "Auto save",
    "已自动保存": "Auto saved",
    "版本：": "Version: ",
    "当前配置：": "Current: ",
    "下次切换：": "Next: ",
    "调整鼠标焦点": "Adjust cursor hotspot",
    " 焦点位置": " hotspot",
    "红色十字就是鼠标真正点击的位置。箭头一般在左上角，文本选择通常在中线附近。": "The red cross is the real click point. Arrows usually use the top-left area; text cursors are usually near the center line.",
    "焦点：X ": "Hotspot: X ",
    "已载入：": "Loaded: ",
    "载入失败": "Load failed",
    "添加可替换指针资源": "Add replacement cursor resources",
    "替换鼠标指针[": "Replacement cursors [",
    "已替换：": "Replaced: ",
    "已设置焦点：": "Hotspot saved: ",
    "选择鼠标文件": "Choose cursor file",
    "导入安装包、压缩包或光标文件": "Import installers, archives, or cursor files",
    "导入鼠标指针文件夹": "Import cursor folder",
    "批量导入": "Batch import",
    "识别到 ": "Detected ",
    " 份鼠标指针，正在批量添加。": " cursor schemes. Importing them now.",
    "发现重复方案": "Duplicate scheme",
    " 已存在，是否继续导入为新副本？\n选择“否”将跳过该方案。": " already exists. Import as a new copy?\nChoose No to skip it.",
    "已跳过": "Skipped",
    " 已存在，未重复导入。": " already exists and was skipped.",
    "导入失败": "Import failed",
    "导入完成": "Import complete",
    "已添加：": "Added: ",
    "请至少选择一个鼠标状态文件。": "Choose at least one cursor state file.",
    "文件不存在：": "File does not exist: ",
    "还不能保存": "Cannot save yet",
    "保存完成": "Save complete",
    "已保存：": "Saved: ",
    "保存失败": "Save failed",
    "还不能应用": "Cannot apply yet",
    "应用完成": "Apply complete",
    "正在应用鼠标方案": "Applying cursor scheme",
    "还不能生成": "Cannot build yet",
    "选择安装包保存位置": "Choose installer output folder",
    "生成完成": "Build complete",
    "正在生成安装包": "Building installer",
    "已恢复": "Restored",
    "已恢复应用前鼠标方案": "Restored the previous cursor scheme",
    "正在恢复鼠标方案": "Restoring cursor scheme",
    "删除完成": "Delete complete",
    "已删除：": "Deleted: ",
    "删除失败": "Delete failed",
    "操作失败": "Operation failed",
    "完成": "Complete",
    "失败": "Failed",
    "九宫格": "Grid",
    "资源已添加": "Resources added",
    "已导入 ": "Imported ",
    " 个方案": " schemes",
    " 个鼠标状态": " cursor states",
    "导入资源包或安装器": "Import resource package or installer",
    "导入资源文件夹": "Import resource folder",
    "点击时间框可选择时间，也可以手写具体时间。留空则不切换。": "Click a time field to choose a time, or type one manually. Leave blank to skip.",
    "应用时间切换": "Apply time switching",
    "时间切换已保存并开启后台自启动": "Time switching was saved and background startup was enabled.",
    "按固定间隔自动切换方案。选择“随机方案”时每次从方案库随机挑选。": "Switch at a fixed interval. Random scheme picks from the library each time.",
    "启用计时切换": "Enable timer switching",
    "应用计时切换": "Apply timer switching",
    "计时切换已保存并开启后台自启动": "Timer switching was saved and background startup was enabled.",
    "切换设置已保存": "Switching settings saved",
    "切换设置已保存并按当前状态应用": "Switching settings saved and applied to the current state.",
    "星期切换已保存并开启后台自启动": "Weekday switching was saved and background startup was enabled.",
    "选择鼠标文件存放位置": "Choose cursor file location",
    "设置已应用": "Settings applied",
    "没有可用的 GitHub Release": "No available GitHub Release",
    "仓库暂无 Release，不能自动下载。最新提交：": "The repository has no Release for automatic download. Latest commit: ",
    "当前已是最新版本：": "You are already on the latest version: ",
    "已下载：": "Downloaded: ",
    "。源码模式不会自动替换。": ". Source mode will not replace the app automatically.",
    "恢复鼠标方案": "Restore cursor scheme",
    "程序：": "App: ",
    "版本：": "Version: ",
    "当前提交：": "Commit: ",
    "程序目录：": "App folder: ",
    "数据目录：": "Data folder: ",
    "鼠标文件目录：": "Cursor folder: ",
    "安装包目录：": "Installer folder: ",
    "自启动启用：": "Startup enabled: ",
    "Run 项：": "Run entry: ",
    "启动快捷方式：": "Startup shortcut: ",
    "任务计划：": "Scheduled task: ",
    "诊断信息已复制到剪贴板": "Diagnostic info copied to clipboard.",
    "替换鼠标指针": "Replacement cursors",
    "添加资源": "Add resource",
    "清空资源": "Clear resources",
    "实时预览": "Live preview",
    "鼠标移入左侧配置行时同步切换": "Hover rows on the left to preview them here.",
    "预览大小": "Preview size",
    "鼠标大小": "Cursor size",
    "实时更新鼠标大小": "Live cursor size",
    "拖动可实时调整系统鼠标大小，应用和安装包会包含当前大小。": "Drag to update Windows cursor size live. Apply and installers include this size.",
    "正常选择": "Normal select",
    "帮助选择": "Help select",
    "后台运行": "Working in background",
    "忙": "Busy",
    "精确选择": "Precision select",
    "文本选择": "Text select",
    "手写": "Handwriting",
    "不可用": "Unavailable",
    "垂直调整大小": "Vertical resize",
    "水平调整大小": "Horizontal resize",
    "沿对角线调整大小 1": "Diagonal resize 1",
    "沿对角线调整大小 2": "Diagonal resize 2",
    "移动": "Move",
    "候选": "Alternate select",
    "链接选择": "Link select",
    "位置选择": "Location select",
    "个人选择": "Person select",
    "普通箭头": "Default pointer",
    "帮助提示": "Help pointer",
    "系统忙碌": "System busy",
    "准星": "Crosshair",
    "文本输入": "Text input",
    "手写笔": "Pen",
    "禁止": "Blocked",
    "上下拖动": "Vertical drag",
    "左右拖动": "Horizontal drag",
    "左上右下": "Top-left to bottom-right",
    "右上左下": "Top-right to bottom-left",
    "四向移动": "Four-way move",
    "候选选择": "Alternate choice",
    "链接": "Link",
    "位置": "Location",
    "个人": "Person",
    "鼠标大小设置": "Cursor size settings",
    "应用": "Apply",
    "生成安装包": "Build installer",
    "恢复": "Restore",
    "选择、导入、预览并应用鼠标指针方案": "Choose, import, preview, and apply cursor schemes.",
    "打开在线资源库下载文件，放入鼠标文件目录后点击刷新。": "Open the online library, download files into the cursor folder, then refresh.",
    "在线资源库": "Online library",
    "导入资源": "Import resources",
    "刷新": "Refresh",
    "恢复上一份鼠标方案": "Restore previous scheme",
    "暂无资源": "No resources",
    "拖动鼠标资源到此可以快速替换鼠标文件": "Drop cursor resources here to replace files quickly.",
    "拖入文件即可导入或替换当前选中项": "Drop files to import or replace the selected item.",
    "支持拖入 .cur / .ani / 图片 / zip / rar / 7z / exe": "Supports .cur / .ani / images / zip / rar / 7z / exe.",
    "拖入压缩包、安装器或文件夹添加到资源库": "Drop archives, installers, or folders to add to the library.",
    "未选择": "Not selected",
    "星期一": "Monday",
    "星期二": "Tuesday",
    "星期三": "Wednesday",
    "星期四": "Thursday",
    "星期五": "Friday",
    "星期六": "Saturday",
    "星期日": "Sunday",
    "根据星期自动应用对应方案。留空则当天不切换。": "Apply schemes by weekday. Leave empty to skip that day.",
    "应用星期切换": "Apply weekday switching",
}


EN_TO_CN = {value: key for key, value in CN_TO_EN.items()}


def ui_english_enabled(backend) -> bool:
    return backend.load_settings().get("english_enabled", "false").lower() in {"1", "true", "yes", "on"}


def tr_text(text: str, english: bool) -> str:
    if not english:
        return text
    if text in CN_TO_EN:
        return CN_TO_EN[text]
    if text == "让新手小白也能用，让鼠标指针制作者能方便编辑和生成。":
        return "Mission: make cursor management simple for beginners and practical for cursor creators."
    if text.startswith("当前配置："):
        return text.replace("当前配置：", "Current: ", 1)
    if text.startswith("下次切换："):
        return text.replace("下次切换：", "Next: ", 1)
    if text.startswith("自启动状态：未开启"):
        return text.replace("自启动状态：未开启", "Startup: Off", 1)
    if text.startswith("自启动状态：正常"):
        return text.replace("自启动状态：正常", "Startup: OK", 1).replace("注册表", "Registry").replace("启动文件夹", "Startup folder").replace("任务计划", "Task Scheduler").replace("任务计划受限，已使用普通自启动方式", "Task Scheduler is restricted; regular startup is being used.")
    if text.startswith("版本："):
        return text.replace("版本：", "Version: ", 1).replace("当前提交：", "Commit: ")
    return text


def set_translated_text(widget, text: str, backend) -> None:
    widget.setProperty("_zh_text", text)
    widget.setText(tr_text(text, ui_english_enabled(backend)))


def restore_cn_text(text: str) -> str:
    return EN_TO_CN.get(text, text)


def apply_widget_language(root: QWidget, english: bool) -> None:
    widgets = list(root.findChildren(QLabel)) + list(root.findChildren(QAbstractButton))
    for widget in widgets:
        text = widget.text()
        if not text:
            continue
        original = widget.property("_zh_text")
        if original is None:
            original = restore_cn_text(text)
            widget.setProperty("_zh_text", original)
        widget.setText(tr_text(str(original), english))


class TaskSignal(QObject):
    finished = Signal(object)
    failed = Signal(str)


class GuiCommandBridge(QObject):
    showRequested = Signal()


class DropArea(CardWidget):
    dropped = Signal(list)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        self.title = StrongBodyLabel(text)
        self.tip = CaptionLabel("支持拖入 .cur / .ani / 图片 / zip / rar / 7z / exe")
        self.tip.setTextColor("#64748b", "#94a3b8")
        layout.addWidget(self.title)
        layout.addWidget(self.tip)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.toLocalFile()]
        if paths:
            self.dropped.emit(paths)


class SegmentedSizeBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 3
        self.setFixedHeight(20)
        self.setMinimumWidth(180)

    def setValue(self, value: int) -> None:
        self.value = max(1, min(15, int(value)))
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gap = 4
        count = 15
        width = max(2, int((self.width() - gap * (count - 1)) / count))
        height = 8
        y = int((self.height() - height) / 2)
        for index in range(count):
            x = index * (width + gap)
            active = index < self.value
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#4f8cff" if active else "#dbeafe"))
            painter.drawRoundedRect(QRect(x, y, width, height), 4, 4)


def role_icon_path(backend, role) -> Path:
    return backend.resource_path(f"assets/role_icons/{role.file_stem}.png")


EXTRA_RESOURCE_EXTS = {".cur", ".ani", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"}
ARCHIVE_RESOURCE_EXTS = {".zip", ".rar", ".7z", ".exe"}


def pixmap_from_image(image: Image.Image, target_size: int | None = None) -> QPixmap:
    qimage = ImageQt(image.convert("RGBA"))
    pixmap = QPixmap.fromImage(qimage)
    if target_size:
        return pixmap.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pixmap


def cursor_kind_badge(path: Path | None) -> str:
    if not path:
        return ""
    suffix = path.suffix.lower()
    if suffix == ".ani":
        return "\u52a8"
    if suffix == ".cur":
        return "\u9759"
    return ""


def cursor_kind_summary(scheme_dir: Path, files: dict[str, str]) -> tuple[int, int]:
    ani_count = 0
    cur_count = 0
    for file_name in files.values():
        suffix = (scheme_dir / file_name).suffix.lower()
        if suffix == ".ani":
            ani_count += 1
        elif suffix == ".cur":
            cur_count += 1
    return ani_count, cur_count


def cursor_kind_summary_text(scheme_dir: Path, files: dict[str, str]) -> str:
    ani_count, cur_count = cursor_kind_summary(scheme_dir, files)
    parts = []
    if ani_count:
        parts.append(f"\u52a8 {ani_count}")
    if cur_count:
        parts.append(f"\u9759 {cur_count}")
    return "  ".join(parts)


def style_kind_chip(label: QLabel, text: str) -> None:
    label.setText(text)
    label.setVisible(bool(text))
    label.setAlignment(Qt.AlignCenter)
    label.setFixedHeight(20)
    label.setMinimumWidth(30)
    label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    label.setStyleSheet(
        "QLabel { background: #eef6ff; color: #1d4ed8; border: 1px solid #bfdbfe; "
        "border-radius: 10px; padding: 1px 7px; font-size: 11px; font-weight: 700; }"
    )
    if text:
        label.setToolTip("动画指针" if text.startswith("动") else "静态指针")
    else:
        label.setToolTip("")


def style_summary_chip(label: QLabel, text: str) -> None:
    label.setText(text)
    label.setVisible(bool(text))
    label.setAlignment(Qt.AlignCenter)
    label.setFixedHeight(22)
    label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    label.setStyleSheet(
        "QLabel { background: #f8fafc; color: #334155; border: 1px solid #dbe4f0; "
        "border-radius: 11px; padding: 2px 8px; font-size: 11px; font-weight: 700; }"
    )


POPUP_LAYER_QSS = """
QMenu {
    background-color: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 8px;
    padding: 5px;
    color: #0f172a;
}
QMenu::item {
    min-height: 26px;
    padding: 6px 18px;
    border-radius: 6px;
    background-color: transparent;
}
QMenu::item:selected {
    background-color: #eef6ff;
    color: #0f172a;
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 5px 8px;
}
QListView, QListWidget {
    background-color: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 8px;
    padding: 4px;
    color: #0f172a;
    outline: 0;
    selection-background-color: #eef6ff;
    selection-color: #0f172a;
}
QListView::item, QListWidget::item {
    min-height: 28px;
    padding: 5px 8px;
    border-radius: 6px;
}
QListView::item:selected, QListWidget::item:selected {
    background-color: #eef6ff;
    color: #0f172a;
}
"""


def apply_popup_layer_style(app: QApplication, *, force: bool = False) -> None:
    if app.property("mousePointerPopupLayerStyled") and not force:
        return
    current = app.styleSheet() or ""
    if POPUP_LAYER_QSS.strip() not in current:
        app.setStyleSheet(current + "\n" + POPUP_LAYER_QSS)
    app.setProperty("mousePointerPopupLayerStyled", True)


def style_popup_menu(menu: QMenu) -> QMenu:
    menu.setStyleSheet(POPUP_LAYER_QSS)
    return menu


class CursorPreview(QLabel):
    def __init__(self, size: int = 46, parent=None):
        super().__init__(parent)
        self.badgeText = ""
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border-radius: 8px; background: #f8fbff;")

    def setPath(self, backend, path: Path | None, size: int = 42, role=None, showBadge: bool = True) -> None:
        self.badgeText = ""
        kind = cursor_kind_badge(path) if showBadge else ""
        if path:
            suffix_tip = f" · {'动画指针' if kind == '动' else '静态指针'}" if kind else ""
            self.setToolTip(f"{path.name}{suffix_tip}")
        else:
            self.setToolTip("")
        if not path or not path.exists():
            self.setRoleIcon(backend, role, size)
            self.update()
            return
        try:
            image = backend.cursor_preview_image_sized(path, (size * 3, size * 3), min(size * 2, 128)).convert("RGBA")
            pixmap = pixmap_from_image(image)
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.setText("...")
        self.update()

    def setRoleIcon(self, backend, role, size: int = 42) -> None:
        if not role:
            self.badgeText = ""
            self.clear()
            return
        try:
            cursor_path = backend.default_cursor_path(role)
            if cursor_path and cursor_path.exists():
                image = backend.cursor_preview_image_sized(cursor_path, (size * 3, size * 3), min(size * 2, 128)).convert("RGBA")
                pixmap = pixmap_from_image(image)
            else:
                icon = role_icon_path(backend, role)
                if not icon.exists():
                    self.badgeText = ""
                    self.clear()
                    return
                pixmap = QPixmap(str(icon))
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.badgeText = ""
            self.clear()


class ReplacementDropArea(QWidget):
    dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = [url for url in event.mimeData().urls() if url.isLocalFile()]
        if not urls:
            return
        self.dropped.emit([Path(url.toLocalFile()) for url in urls])
        event.acceptProposedAction()


class PreviewPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 380)
        self.setMouseTracking(True)
        self.setCursor(Qt.BlankCursor)
        self.pixmap = QPixmap()
        self.follow = False
        self.pointer = QPoint()

    def setPreview(self, pixmap: QPixmap):
        self.pixmap = pixmap
        if self.pointer.isNull():
            self.pointer = QPoint(self.width() // 2, self.height() // 2)
        self.update()

    def clearPreview(self):
        self.pixmap = QPixmap()
        self.update()

    def enterEvent(self, event) -> None:
        self.follow = True
        self.pointer = event.position().toPoint() if hasattr(event, "position") else self.rect().center()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        self.follow = True
        self.pointer = event.position().toPoint()
        self.update()

    def leaveEvent(self, event) -> None:
        self.follow = False
        self.pointer = self.rect().center()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self.follow:
            self.pointer = self.rect().center()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#dbeafe"), 1))
        painter.setBrush(QColor("#f8fbff"))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)
        if self.pixmap.isNull():
            return
        pos = self.pointer if self.follow else self.rect().center()
        x = int(pos.x() - self.pixmap.width() * 0.12)
        y = int(pos.y() - self.pixmap.height() * 0.12)
        x = max(10, min(x, self.width() - self.pixmap.width() - 10))
        y = max(10, min(y, self.height() - self.pixmap.height() - 10))
        painter.drawPixmap(x, y, self.pixmap)


class HotspotCanvas(QWidget):
    ratioChanged = Signal(float, float)

    def __init__(self, pixmap: QPixmap, ratio: tuple[float, float], parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.ratio = ratio
        self.setMinimumSize(360, 360)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#cbd5e1"), 1, Qt.DashLine))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        if self.pixmap.isNull():
            return
        target = self.targetRect()
        painter.drawPixmap(target, self.pixmap)
        x = target.x() + self.ratio[0] * target.width()
        y = target.y() + self.ratio[1] * target.height()
        painter.setPen(QPen(QColor("#ef4444"), 2))
        painter.drawLine(int(x) - 12, int(y), int(x) + 12, int(y))
        painter.drawLine(int(x), int(y) - 12, int(x), int(y) + 12)
        painter.setPen(QPen(QColor("#0f172a"), 1))
        painter.drawEllipse(QPoint(int(x), int(y)), 4, 4)

    def targetRect(self):
        size = self.pixmap.size()
        scaled = size.scaled(self.rect().adjusted(18, 18, -18, -18).size(), Qt.KeepAspectRatio)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return QRect(x, y, scaled.width(), scaled.height())

    def mousePressEvent(self, event) -> None:
        target = self.targetRect()
        if target.width() <= 0 or target.height() <= 0:
            return
        pos = event.position().toPoint()
        x = max(target.left(), min(pos.x(), target.right()))
        y = max(target.top(), min(pos.y(), target.bottom()))
        self.ratio = ((x - target.x()) / max(1, target.width()), (y - target.y()) / max(1, target.height()))
        self.ratioChanged.emit(self.ratio[0], self.ratio[1])
        self.update()


class HotspotDialog(QDialog):
    def __init__(self, backend, role, path: Path | None, ratio: tuple[float, float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("调整鼠标焦点")
        self.ratio = ratio
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        title = SubtitleLabel(f"{role.label} 焦点位置")
        tip = CaptionLabel("红色十字就是鼠标真正点击的位置。箭头一般在左上角，文本选择通常在中线附近。")
        tip.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(tip)
        pixmap = self.buildPixmap(backend, role, path)
        self.canvas = HotspotCanvas(pixmap, ratio)
        self.canvas.ratioChanged.connect(self.onRatioChanged)
        layout.addWidget(self.canvas)
        self.valueText = CaptionLabel("")
        self.valueText.setTextColor("#64748b", "#94a3b8")
        layout.addWidget(self.valueText)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.onRatioChanged(*ratio)

    def buildPixmap(self, backend, role, path: Path | None) -> QPixmap:
        size = 256
        try:
            if path and path.exists():
                image = None
                if path.suffix.lower() == ".ani":
                    frames = backend.ani_frame_paths(path)
                    if frames:
                        path = frames[0]
                if path.suffix.lower() in {".cur", ".ani"}:
                    image = backend.render_cursor_with_windows(path, size)
                if image is None:
                    image = backend.centered_rgba(backend.image_from_path(path), size)
                return pixmap_from_image(image)
        except Exception:
            pass
        cursor_path = backend.default_cursor_path(role)
        if cursor_path and cursor_path.exists():
            try:
                image = backend.cursor_preview_image_sized(cursor_path, (size, size), size).convert("RGBA")
                return pixmap_from_image(image)
            except Exception:
                pass
        return QPixmap(str(role_icon_path(backend, role))).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def onRatioChanged(self, x: float, y: float):
        self.ratio = (x, y)
        self.valueText.setText(f"焦点：X {x:.2f} / Y {y:.2f}")


class CursorPreviewWindow(QDialog):
    def __init__(self, backend, path: Path, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.path = path
        self.frames: list[QPixmap] = []
        self.frameIndex = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.nextFrame)
        self.setWindowTitle(f"{backend.APP_NAME} - 光标预览")
        self.setMinimumSize(520, 420)
        app_command = [str(Path(sys.executable).resolve())] if backend.IS_FROZEN else [str(Path(sys.executable).resolve()), str(backend.APP_DIR / "main.py")]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = StrongBodyLabel(path.name if path.name else "未选择文件")
        subtitle = CaptionLabel(str(path) if path else "")
        subtitle.setWordWrap(True)
        subtitle.setTextColor("#64748b", "#94a3b8")
        self.kind = CaptionLabel("")
        self.kind.setTextColor("#2563eb", "#60a5fa")
        self.preview = QLabel()
        self.preview.setFixedHeight(220)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background: #f8fbff; border: 1px solid #dbeafe; border-radius: 12px;")
        self.message = CaptionLabel("")
        self.message.setWordWrap(True)
        self.message.setTextColor("#475569", "#cbd5e1")

        actions = QHBoxLayout()
        open_main = PrimaryPushButton("打开完整软件")
        open_main.clicked.connect(lambda: backend.start_detached_process(app_command))
        copy_path = PushButton("复制路径")
        copy_path.clicked.connect(lambda: QApplication.clipboard().setText(str(path)))
        close_button = PushButton("关闭")
        close_button.clicked.connect(self.close)
        actions.addWidget(open_main)
        actions.addWidget(copy_path)
        actions.addStretch(1)
        actions.addWidget(close_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.kind)
        layout.addWidget(self.preview)
        layout.addWidget(self.message)
        layout.addLayout(actions)
        self.loadPreview()

    def loadPreview(self) -> None:
        path = self.path
        if not path or not path.exists():
            self.kind.setText("文件不存在")
            self.message.setText("指定的鼠标文件不存在，无法预览。")
            return
        badge = cursor_kind_badge(path)
        self.kind.setText(f"类型：{path.suffix.lower()}  {'动' if badge == '动' else '静' if badge == '静' else ''}".strip())
        try:
            if path.suffix.lower() == ".ani":
                frame_paths = self.backend.ani_frame_paths(path)[:36]
                if frame_paths:
                    self.frames = [pixmap_from_image(self.backend.cursor_preview_image_sized(frame, (200, 200), 128), 200) for frame in frame_paths]
                else:
                    self.frames = [pixmap_from_image(self.backend.cursor_preview_image_sized(path, (200, 200), 128), 200)]
            else:
                self.frames = [pixmap_from_image(self.backend.cursor_preview_image_sized(path, (200, 200), 128), 200)]
            if not self.frames:
                raise RuntimeError("没有生成可用预览。")
            self.preview.setPixmap(self.frames[0])
            if len(self.frames) > 1:
                self.timer.start(90)
            self.message.setText("双击文件时可直接进入这个轻量预览窗口，不会打开完整主界面。")
        except Exception as exc:
            self.backend.log_error("光标轻量预览失败", exc)
            self.preview.setText("预览失败")
            self.message.setText(f"无法预览该文件：{exc}")

    def nextFrame(self) -> None:
        if not self.frames:
            return
        self.preview.setPixmap(self.frames[self.frameIndex % len(self.frames)])
        self.frameIndex += 1


class CursorRow(QWidget):
    hovered = Signal(str)
    picked = Signal(str)
    dropped = Signal(str, object)
    previewClicked = Signal(str)
    removeRequested = Signal(str)

    def __init__(self, backend, role, index: int = 0, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.role = role
        self.path: Path | None = None
        self.setAcceptDrops(True)
        self.setMinimumHeight(84)
        self.setObjectName("cursorRow")
        self.setStyleSheet("#cursorRow { background: #ffffff; border: none; border-radius: 8px; } #cursorRow:hover { background: #f4fbff; }")

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(12)
        layout.setColumnStretch(1, 1)

        self.previewFrame = QWidget()
        self.previewFrame.setObjectName("previewFrame")
        self.previewFrame.setFixedSize(72, 72)
        self.previewFrame.setCursor(Qt.PointingHandCursor)
        self.previewFrame.setStyleSheet("#previewFrame { border: 1px solid transparent; border-radius: 10px; background: #ffffff; }")
        preview_layout = QGridLayout(self.previewFrame)
        preview_layout.setContentsMargins(3, 3, 3, 3)
        preview_layout.setSpacing(0)
        self.preview = CursorPreview(66)
        self.preview.setStyleSheet("border-radius: 8px; background: #ffffff;")
        self.preview.mousePressEvent = lambda _event: self.previewClicked.emit(self.role.reg_name)
        self.previewFrame.mousePressEvent = lambda _event: self.previewClicked.emit(self.role.reg_name)
        self.removeButton = QPushButton("×")
        self.removeButton.setFixedSize(22, 22)
        self.removeButton.setCursor(Qt.PointingHandCursor)
        self.removeButton.setToolTip("移回替换资源池")
        self.removeButton.setStyleSheet(
            "QPushButton { background: #ef4444; color: white; border: 2px solid white; border-radius: 11px; "
            "font-weight: 700; } QPushButton:hover { background: #dc2626; }"
        )
        self.removeButton.hide()
        self.removeButton.clicked.connect(lambda _checked=False: self.removeRequested.emit(self.role.reg_name))
        preview_layout.addWidget(self.preview, 0, 0)
        preview_layout.addWidget(self.removeButton, 0, 0, Qt.AlignTop | Qt.AlignRight)
        self.name = StrongBodyLabel(role.label)
        self.kindChip = QLabel()
        style_kind_chip(self.kindChip, "")
        self.tip = CaptionLabel(role.tip)
        self.tip.setTextColor("#64748b", "#94a3b8")

        text_box = QWidget()
        text_box.setObjectName("roleText")
        text_box.setCursor(Qt.PointingHandCursor)
        text_box.mousePressEvent = lambda _event: self.picked.emit(self.role.reg_name)
        text_box.setStyleSheet("#roleText { background: #f8fbff; border-radius: 8px; } #roleText:hover { background: #eef7ff; }")
        text_layout = QVBoxLayout(text_box)
        text_layout.setContentsMargins(10, 8, 10, 8)
        text_layout.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_row.addWidget(self.name)
        title_row.addWidget(self.kindChip)
        title_row.addStretch(1)
        text_layout.addLayout(title_row)
        text_layout.addWidget(self.tip)

        layout.addWidget(self.previewFrame, 0, 0, 2, 1)
        layout.addWidget(text_box, 0, 1, 2, 1)

    def enterEvent(self, event) -> None:
        self.hovered.emit(self.role.reg_name)
        self.setPreviewHover(True)
        self.wobblePreview()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setPreviewHover(False)
        super().leaveEvent(event)

    def setPreviewHover(self, active: bool) -> None:
        if active and self.path:
            self.removeButton.show()
        else:
            self.removeButton.hide()
        border = "#2563eb" if active else "transparent"
        background = "#f8fbff" if active else "#ffffff"
        self.previewFrame.setStyleSheet(
            f"#previewFrame {{ border: 1px dashed {border}; border-radius: 10px; background: {background}; }}"
        )

    def wobblePreview(self) -> None:
        start = self.previewFrame.pos()
        self.previewFrame.move(start.x() + 2, start.y())
        QTimer.singleShot(70, lambda: self.previewFrame.move(start.x() - 2, start.y()))
        QTimer.singleShot(140, lambda: self.previewFrame.move(start))

    def setPath(self, path: Path | None) -> None:
        self.path = path
        self.setToolTip(str(path) if path else "")
        self.preview.setPath(self.backend, path, role=self.role)
        style_kind_chip(self.kindChip, cursor_kind_badge(path))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.exists() and path.suffix.lower() in EXTRA_RESOURCE_EXTS:
            self.dropped.emit(self.role.reg_name, path)
            event.acceptProposedAction()


class ExtraResourceItem(QWidget):
    deleteRequested = Signal(object)

    def __init__(self, backend, path: Path, parent=None):
        super().__init__(parent)
        self.path = path
        self.dragStart = QPoint()
        self.setFixedSize(68, 76)
        self.setToolTip(path.name)
        self.setObjectName("extraResourceItem")
        self.setStyleSheet("#extraResourceItem { background: #ffffff; border: none; border-radius: 8px; } #extraResourceItem:hover { background: #eef7ff; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 4)
        layout.setSpacing(3)
        preview_box = QWidget()
        preview_box.setFixedSize(56, 52)
        preview_layout = QGridLayout(preview_box)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        preview = CursorPreview(46)
        preview.setPath(backend, path, 40)
        preview_layout.addWidget(preview, 0, 0, alignment=Qt.AlignCenter)
        self.closeButton = QLabel("×")
        self.closeButton.setFixedSize(16, 16)
        self.closeButton.setAlignment(Qt.AlignCenter)
        self.closeButton.setCursor(Qt.PointingHandCursor)
        self.closeButton.setStyleSheet("background: #ef4444; color: white; border-radius: 8px; font-weight: 700;")
        self.closeButton.hide()
        self.closeButton.mousePressEvent = lambda _event: self.deleteRequested.emit(self.path)
        preview_layout.addWidget(self.closeButton, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)
        layout.addWidget(preview_box, alignment=Qt.AlignCenter)
        self.kindChip = QLabel()
        style_kind_chip(self.kindChip, cursor_kind_badge(path))
        layout.addWidget(self.kindChip, alignment=Qt.AlignCenter)

    def enterEvent(self, event) -> None:
        self.closeButton.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.closeButton.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.dragStart = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if not event.buttons() & Qt.LeftButton:
            return
        if (event.position().toPoint() - self.dragStart).manhattanLength() < QApplication.startDragDistance():
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.path))])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class SchemePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.rows: dict[str, CursorRow] = {}
        self.selected: dict[str, Path] = {}
        self.hotspots: dict[str, tuple[float, float]] = {}
        self.extraFiles: list[Path] = []
        self.current_preview = "Arrow"
        self.sizeLevel = 3
        self._schemeNamesCache: list[str] | None = None
        self.animationFrames: list[QPixmap] = []
        self.animationIndex = 0
        self.loadingScheme = False
        self.importSkipped: list[str] = []
        self.importFailed: list[str] = []
        self.animationTimer = QTimer(self)
        self.animationTimer.timeout.connect(self.nextAnimationFrame)
        self.sizeApplyTimer = QTimer(self)
        self.sizeApplyTimer.setSingleShot(True)
        self.sizeApplyTimer.timeout.connect(self.applyCurrentCursorSize)

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(18)

        left = QWidget()
        left.setMinimumWidth(500)
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(SubtitleLabel("鼠标方案"))
        title_box.addWidget(CaptionLabel("选择、导入、预览并应用鼠标指针方案"))
        header.addLayout(title_box)
        header.addStretch(1)
        self.schemeBox = ComboBox()
        self.schemeBox.setMinimumWidth(220)
        self.schemeBox.setMaximumWidth(280)
        self.schemeBox.currentTextChanged.connect(self.loadScheme)
        header.addWidget(self.schemeBox)
        left_layout.addLayout(header)

        toolbar = QHBoxLayout()
        self.newButton = PushButton("新建")
        self.newButton.setIcon(FIF.ADD)
        self.renameButton = PushButton("重命名")
        self.renameButton.setIcon(FIF.EDIT)
        self.deleteButton = PushButton("删除")
        self.deleteButton.setIcon(FIF.DELETE)
        self.importButton = PushButton("导入")
        self.importButton.setIcon(FIF.DOWNLOAD)
        self.importFolderButton = PushButton("导入文件夹")
        self.importFolderButton.setIcon(FIF.FOLDER)
        self.exportPreviewButton = PushButton("截图导出")
        self.exportPreviewButton.setIcon(FIF.PHOTO)
        for button in [self.newButton, self.renameButton, self.deleteButton, self.importButton, self.importFolderButton, self.exportPreviewButton]:
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        left_layout.addLayout(toolbar)

        self.dropArea = DropArea("拖入文件即可导入或替换当前选中项")
        self.dropArea.dropped.connect(self.handleDropped)
        left_layout.addWidget(self.dropArea)

        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        self.rowWidget = QWidget()
        self.rowWidget.setStyleSheet("background: transparent;")
        self.rowLayout = QGridLayout(self.rowWidget)
        self.rowLayout.setContentsMargins(2, 2, 8, 2)
        self.rowLayout.setHorizontalSpacing(10)
        self.rowLayout.setVerticalSpacing(10)
        for role in self.backend.CURSOR_ROLES:
            row = CursorRow(backend, role, len(self.rows))
            row.hovered.connect(self.updateLargePreview)
            row.picked.connect(self.pickFileForRole)
            row.dropped.connect(self.applyFileToRole)
            row.previewClicked.connect(self.editHotspotForRole)
            row.removeRequested.connect(self.unassignRoleToPool)
            self.rows[role.reg_name] = row
            index = len(self.rows) - 1
            self.rowLayout.addWidget(row, index // 2, index % 2)
        self.rowLayout.setColumnStretch(0, 1)
        self.rowLayout.setColumnStretch(1, 1)
        self.scroll.setWidget(self.rowWidget)
        left_layout.addWidget(self.scroll, 1)

        self.extraBox = ReplacementDropArea()
        self.extraBox.setObjectName("extraBox")
        self.extraBox.setMinimumHeight(184)
        self.extraBox.setMaximumHeight(220)
        self.extraBox.setStyleSheet("#extraBox { background: rgba(255, 255, 255, 0.82); border: none; border-radius: 8px; }")
        self.extraBox.dropped.connect(self.handleExtraDropped)
        extra_layout = QVBoxLayout(self.extraBox)
        extra_layout.setContentsMargins(12, 10, 12, 10)
        extra_layout.setSpacing(8)
        extra_header = QHBoxLayout()
        self.extraTitle = StrongBodyLabel("替换鼠标指针")
        self.extraAddButton = PushButton("添加资源")
        self.extraAddButton.setIcon(FIF.ADD)
        self.extraAddButton.setMinimumWidth(118)
        self.extraClearButton = PushButton("清空资源")
        self.extraClearButton.setIcon(FIF.DELETE)
        self.extraClearButton.setMinimumWidth(118)
        extra_header.addWidget(self.extraTitle)
        extra_header.addStretch(1)
        extra_header.addWidget(self.extraAddButton)
        extra_header.addWidget(self.extraClearButton)
        extra_layout.addLayout(extra_header)
        self.extraScroll = ScrollArea()
        self.extraScroll.setWidgetResizable(True)
        self.extraScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.extraScroll.setStyleSheet("QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        self.extraWidget = QWidget()
        self.extraWidget.setStyleSheet("background: transparent;")
        self.extraGrid = QGridLayout(self.extraWidget)
        self.extraGrid.setContentsMargins(0, 0, 0, 0)
        self.extraGrid.setHorizontalSpacing(8)
        self.extraGrid.setVerticalSpacing(8)
        self.extraScroll.setWidget(self.extraWidget)
        extra_layout.addWidget(self.extraScroll, 1)
        left_layout.addWidget(self.extraBox)

        right = CardWidget()
        right.setFixedWidth(460)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        right_layout.addWidget(SubtitleLabel("实时预览"))
        preview_tip = CaptionLabel("鼠标移入左侧配置行时同步切换")
        preview_tip.setWordWrap(True)
        right_layout.addWidget(preview_tip)

        size_row = QHBoxLayout()
        size_row.addWidget(BodyLabel("鼠标大小"))
        self.sizeText = CaptionLabel("3 / 64px")
        self.sizeText.setTextColor("#64748b", "#94a3b8")
        size_row.addStretch(1)
        size_row.addWidget(self.sizeText)
        right_layout.addLayout(size_row)
        self.sizeLevel = self.backend.pixels_to_size_level(self.backend.get_current_cursor_size())
        size_control = QHBoxLayout()
        size_control.setSpacing(8)
        self.sizeMinusButton = PushButton("-")
        self.sizeMinusButton.setFixedWidth(38)
        self.sizePlusButton = PushButton("+")
        self.sizePlusButton.setFixedWidth(38)
        self.sizeProgress = SegmentedSizeBar()
        self.sizeProgress.setValue(self.sizeLevel)
        size_control.addWidget(self.sizeMinusButton)
        size_control.addWidget(self.sizeProgress, 1)
        size_control.addWidget(self.sizePlusButton)
        right_layout.addLayout(size_control)
        live_size_row = QHBoxLayout()
        live_size_row.addWidget(BodyLabel("实时更新鼠标大小"))
        self.liveSizeSwitch = SwitchButton()
        self.liveSizeSwitch.setChecked(False)
        live_size_row.addWidget(self.liveSizeSwitch)
        live_size_row.addStretch(1)
        right_layout.addLayout(live_size_row)
        self.applyTip = CaptionLabel("使用 + / - 调整鼠标大小；开启实时更新后才会立刻写入系统。应用和安装包会包含当前大小。")
        self.applyTip.setWordWrap(True)
        self.applyTip.setTextColor("#64748b", "#94a3b8")
        right_layout.addWidget(self.applyTip)

        self.largePreview = PreviewPane()
        right_layout.addWidget(self.largePreview, 1)
        self.previewName = StrongBodyLabel("正常选择")
        self.previewFile = CaptionLabel("")
        self.previewFile.setWordWrap(True)
        self.previewFile.setTextColor("#64748b", "#94a3b8")
        right_layout.addWidget(self.previewName)
        right_layout.addWidget(self.previewFile)

        action_row = QGridLayout()
        action_row.setHorizontalSpacing(8)
        action_row.setVerticalSpacing(8)
        self.sizeSettingsButton = PushButton("鼠标大小设置")
        self.sizeSettingsButton.setIcon(FIF.SETTING)
        self.applyButton = PrimaryPushButton("应用")
        self.applyButton.setIcon(FIF.ACCEPT)
        self.buildButton = PushButton("生成安装包")
        self.buildButton.setIcon(FIF.APPLICATION)
        self.restoreButton = PushButton("恢复")
        self.restoreButton.setIcon(FIF.RETURN)
        action_row.addWidget(self.sizeSettingsButton, 0, 0)
        action_row.addWidget(self.buildButton, 0, 1)
        action_row.addWidget(self.restoreButton, 1, 0)
        action_row.addWidget(self.applyButton, 1, 1)
        right_layout.addLayout(action_row)
        self.status = CaptionLabel("")
        self.status.setWordWrap(True)
        self.status.setTextColor("#64748b", "#94a3b8")
        right_layout.addWidget(self.status)
        self.currentSchemeStatus = CaptionLabel("")
        self.currentSchemeStatus.setTextColor("#64748b", "#94a3b8")
        self.currentSchemeStatus.setWordWrap(True)
        self.nextSwitchStatus = CaptionLabel("")
        self.nextSwitchStatus.setTextColor("#64748b", "#94a3b8")
        self.nextSwitchStatus.setWordWrap(True)
        right_layout.addWidget(self.currentSchemeStatus)
        right_layout.addWidget(self.nextSwitchStatus)

        root.addWidget(left, 1)
        root.addWidget(right, 0)

        self.importButton.clicked.connect(self.importPackage)
        self.importFolderButton.clicked.connect(self.importFolder)
        self.newButton.clicked.connect(self.newScheme)
        self.deleteButton.clicked.connect(self.deleteScheme)
        self.renameButton.clicked.connect(self.renameScheme)
        self.applyButton.clicked.connect(self.applyScheme)
        self.buildButton.clicked.connect(self.buildInstaller)
        self.exportPreviewButton.clicked.connect(self.exportPreviewScreenshot)
        self.restoreButton.clicked.connect(self.restoreCursor)
        self.sizeSettingsButton.clicked.connect(self.openPointerSettings)
        self.extraAddButton.clicked.connect(self.importExtraResources)
        self.extraClearButton.clicked.connect(self.clearExtraResources)
        self.sizeMinusButton.clicked.connect(lambda: self.changeSizeLevel(-1))
        self.sizePlusButton.clicked.connect(lambda: self.changeSizeLevel(1))
        self.liveSizeSwitch.checkedChanged.connect(self.onLiveSizeChanged)
        self.onSizeChanged(self.sizeLevel)
        self.schemeBox.addItem("正在加载方案...")
        self.updateRuntimeInfo()

    def openPointerSettings(self):
        try:
            os.startfile("ms-settings:easeofaccess-mousepointer")
        except Exception:
            os.startfile("control.exe")

    def schemeNames(self) -> list[str]:
        if self._schemeNamesCache is not None:
            return list(self._schemeNamesCache)
        root = self.backend.SCHEME_LIBRARY
        if not root.exists():
            return []
        names = []
        for path in root.iterdir():
            if not path.is_dir():
                continue
            try:
                _scheme_dir, files = self.backend.scheme_manifest(path.name)
            except Exception:
                continue
            if files and any((path / name).exists() for name in files.values()):
                names.append(path.name)
        self._schemeNamesCache = sorted(names, key=lambda name: self.backend.scheme_order_value(root / name))
        return list(self._schemeNamesCache)

    def invalidateSchemeCache(self) -> None:
        self._schemeNamesCache = None

    def currentSchemeDir(self) -> Path | None:
        name = self.schemeBox.currentText().strip()
        if not name:
            return None
        return self.backend.SCHEME_LIBRARY / self.backend.sanitize_name(name)

    def readManifest(self, name: str) -> tuple[Path, dict]:
        scheme_dir = self.backend.SCHEME_LIBRARY / self.backend.sanitize_name(name)
        manifest_path = scheme_dir / "scheme.json"
        if not manifest_path.exists():
            return scheme_dir, {}
        return scheme_dir, json.loads(manifest_path.read_text(encoding="utf-8"))

    def refreshSchemes(self):
        self.invalidateSchemeCache()
        current = self.schemeBox.currentText()
        self.schemeBox.clear()
        names = self.schemeNames()
        self.schemeBox.addItems(names)
        if current in names:
            self.schemeBox.setCurrentText(current)
            self.loadScheme(current)
        elif names:
            self.schemeBox.setCurrentIndex(0)
            self.loadScheme(names[0])
        else:
            self.clearSelection()
        self.updateRuntimeInfo()

    def clearSelection(self):
        self.selected.clear()
        self.hotspots.clear()
        self.extraFiles = []
        for row in self.rows.values():
            row.setPath(None)
        self.updateLargePreview("Arrow")
        self.updateExtraBox()
        self.updateRuntimeInfo()

    def loadScheme(self, name: str):
        if not name:
            return
        self.loadingScheme = True
        try:
            scheme_dir, files = self.backend.scheme_manifest(name)
            _manifest_dir, manifest = self.readManifest(name)
            self.selected = {reg: scheme_dir / file_name for reg, file_name in files.items() if (scheme_dir / file_name).exists()}
            self.hotspots = {}
            for reg, value in manifest.get("hotspots", {}).items():
                if isinstance(value, list) and len(value) == 2:
                    self.hotspots[reg] = (float(value[0]), float(value[1]))
            self.extraFiles = []
            for file_name in manifest.get("extras", []):
                path = scheme_dir / file_name
                if path.exists() and path.suffix.lower() in EXTRA_RESOURCE_EXTS:
                    self.extraFiles.append(path)
            for reg, row in self.rows.items():
                row.setPath(self.selected.get(reg))
            self.updateLargePreview(self.current_preview)
            self.updateExtraBox()
            self.status.setText(f"已载入：{name}")
            self.updateRuntimeInfo()
        except Exception as exc:
            self.showError("载入失败", exc)
        finally:
            self.loadingScheme = False
        self.updateRuntimeInfo()

    def clearGrid(self, layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def updateExtraBox(self) -> None:
        name = self.schemeBox.currentText().strip()
        title = f"替换鼠标指针[{name}]" if name else "替换鼠标指针"
        if ui_english_enabled(self.backend):
            title = f"{tr_text('替换鼠标指针', True)}[{name}]" if name else tr_text("替换鼠标指针", True)
        self.extraTitle.setText(title)
        self.clearGrid(self.extraGrid)
        if not self.extraFiles:
            empty = CaptionLabel(tr_text("拖动鼠标资源到此可以快速替换鼠标文件", ui_english_enabled(self.backend)))
            empty.setAlignment(Qt.AlignCenter)
            empty.setTextColor("#64748b", "#94a3b8")
            self.extraGrid.addWidget(empty, 0, 0)
            return
        for index, path in enumerate(self.extraFiles):
            row = index // 6
            col = index % 6
            item = ExtraResourceItem(self.backend, path)
            item.deleteRequested.connect(self.removeExtraResource)
            self.extraGrid.addWidget(item, row, col)
        self.extraGrid.setRowStretch(max(2, (len(self.extraFiles) + 5) // 6), 1)

    def handleExtraDropped(self, paths: list[Path]) -> None:
        added = False
        blocked = False
        for path in paths:
            if path.is_dir() or path.suffix.lower() in ARCHIVE_RESOURCE_EXTS:
                blocked = True
                continue
            if path.suffix.lower() not in EXTRA_RESOURCE_EXTS:
                blocked = True
                continue
            self.appendExtraResource(path)
            added = True
        self.updateExtraBox()
        if added:
            if blocked:
                self.status.setText("已添加可用替换资源；压缩包、安装器、文件夹或不支持格式已跳过，请到资源库导入。")
            else:
                self.status.setText("已添加替换资源")
            self.autoSaveCurrentScheme()
        elif paths or blocked:
            self.status.setText("替换资源池仅接受 .cur / .ani / 图片文件；压缩包、安装器或文件夹请到资源库导入。")

    def updateRuntimeInfo(self) -> None:
        current = self.backend.configured_current_scheme()
        next_text = self.backend.next_switch_text(*self.backend.load_schedule_state()) or "未设置"
        english = ui_english_enabled(self.backend)
        current_prefix = "Current: " if english else "当前配置："
        next_prefix = "Next: " if english else "下次切换："
        if english and next_text == "未设置":
            next_text = "Not set"
        self.currentSchemeStatus.setText(f"{current_prefix}{current}")
        self.nextSwitchStatus.setText(f"{next_prefix}{next_text}")
        window = self.window()
        if hasattr(window, "refreshRuntimeStatus"):
            window.refreshRuntimeStatus()

    def appendExtraResource(self, path: Path) -> None:
        if not path.exists() or path.suffix.lower() not in EXTRA_RESOURCE_EXTS:
            return
        try:
            resolved = path.resolve()
            if any(item.exists() and item.resolve() == resolved for item in self.extraFiles):
                return
        except Exception:
            pass
        self.extraFiles.append(path)

    def removeExtraResource(self, path: Path) -> None:
        try:
            target = path.resolve()
            self.extraFiles = [item for item in self.extraFiles if not (item.exists() and item.resolve() == target)]
        except Exception:
            self.extraFiles = [item for item in self.extraFiles if item != path]
        self.updateExtraBox()
        QApplication.processEvents()
        self.autoSaveCurrentScheme()

    def clearExtraResources(self) -> None:
        self.extraFiles = []
        self.updateExtraBox()
        QApplication.processEvents()
        self.autoSaveCurrentScheme()

    def uniqueFileName(self, folder: Path, file_name: str) -> str:
        candidate = self.backend.sanitize_name(Path(file_name).stem) or "resource"
        suffix = Path(file_name).suffix.lower()
        output = f"{candidate}{suffix}"
        index = 2
        while (folder / output).exists():
            output = f"{candidate}_{index}{suffix}"
            index += 1
        return output

    def stageExtraFiles(self, staging_dir: Path, sources: list[Path] | None = None) -> list[Path]:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)
        staged = []
        source_list = self.extraFiles if sources is None else sources
        for source in source_list:
            if not source.exists() or source.suffix.lower() not in EXTRA_RESOURCE_EXTS:
                continue
            output_name = self.uniqueFileName(staging_dir, source.name)
            target = staging_dir / output_name
            shutil.copy2(source, target)
            staged.append(target)
        return staged

    def copyExtraFilesToScheme(self, scheme_dir: Path, sources: list[Path] | None = None) -> list[str]:
        extras_dir = scheme_dir / "extras"
        if extras_dir.exists():
            shutil.rmtree(extras_dir)
        extras_dir.mkdir(parents=True, exist_ok=True)
        extra_names: list[str] = []
        source_list = self.extraFiles if sources is None else sources
        for source in source_list:
            if not source.exists() or source.suffix.lower() not in EXTRA_RESOURCE_EXTS:
                continue
            output_name = self.uniqueFileName(extras_dir, source.name)
            target = extras_dir / output_name
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            extra_names.append(f"extras/{output_name}")
        return extra_names

    def persistExtraFiles(self, refresh_ui: bool = True) -> None:
        scheme_dir = self.currentSchemeDir()
        if not scheme_dir or not (scheme_dir / "scheme.json").exists():
            return
        staged = self.stageExtraFiles(self.backend.WORK_ROOT / "fluent_extra_stage")
        extra_names = self.copyExtraFilesToScheme(scheme_dir, staged)
        manifest_path = scheme_dir / "scheme.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["extras"] = extra_names
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.extraFiles = [scheme_dir / name for name in extra_names if (scheme_dir / name).exists()]
        if refresh_ui:
            self.updateExtraBox()

    def ensureSchemeInBox(self, theme: str) -> None:
        exists = False
        for index in range(self.schemeBox.count()):
            if self.schemeBox.itemText(index) == theme:
                exists = True
                break
        if not exists:
            blocked = self.schemeBox.blockSignals(True)
            self.schemeBox.addItem(theme)
            self.schemeBox.setCurrentText(theme)
            self.schemeBox.blockSignals(blocked)

    def autoSaveCurrentScheme(self) -> None:
        if self.loadingScheme:
            return
        theme = self.backend.sanitize_name(self.schemeBox.currentText() or "新方案")
        try:
            package_dir = self.backend.WORK_ROOT / "fluent_autosave"
            extra_stage = self.backend.WORK_ROOT / "fluent_autosave_extra_stage"
            files = self.prepareAssets(package_dir)
            staged_extras = self.stageExtraFiles(extra_stage)
            scheme_dir = self.backend.SCHEME_LIBRARY / theme
            if scheme_dir.exists():
                shutil.rmtree(scheme_dir)
            shutil.copytree(package_dir / "assets", scheme_dir)
            extra_names = self.copyExtraFilesToScheme(scheme_dir, staged_extras)
            self.writeManifest(theme, files, scheme_dir, extra_names)
            self.selected = {reg_name: scheme_dir / file_name for reg_name, file_name in files.items() if (scheme_dir / file_name).exists()}
            self.extraFiles = [scheme_dir / name for name in extra_names if (scheme_dir / name).exists()]
            for reg_name, row in self.rows.items():
                row.setPath(self.selected.get(reg_name))
            self.ensureSchemeInBox(theme)
            self.updateExtraBox()
            self.updateLargePreview(self.current_preview)
            self.status.setText("已自动保存")
        except Exception as exc:
            self.backend.log_error("Fluent 自动保存失败", exc)
            self.status.setText(f"自动保存失败：{exc}")

    def importExtraResources(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "添加可替换指针资源",
            str(self.backend.configured_storage_root()),
            "可替换资源 (*.cur *.ani *.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico);;所有文件 (*.*)",
        )
        if not files:
            return
        for file in files:
            self.appendExtraResource(Path(file))
        self.autoSaveCurrentScheme()
        self.updateExtraBox()

    def applyFileToRole(self, reg_name: str, path: Path) -> None:
        old_path = self.selected.get(reg_name)
        if old_path and old_path.exists():
            try:
                if old_path.resolve() != path.resolve():
                    self.appendExtraResource(old_path)
            except Exception:
                self.appendExtraResource(old_path)
        self.selected[reg_name] = path
        self.rows[reg_name].setPath(path)
        self.removeExtraFromMemory(path)
        self.updateExtraBox()
        self.updateLargePreview(reg_name)
        self.status.setText(f"已替换：{self.backend.ROLE_BY_REG[reg_name].label}")
        self.autoSaveCurrentScheme()

    def unassignRoleToPool(self, reg_name: str) -> None:
        role = self.backend.ROLE_BY_REG.get(reg_name)
        path = self.selected.pop(reg_name, None)
        if path and path.exists():
            self.appendExtraResource(path)
        if reg_name in self.rows:
            self.rows[reg_name].setPath(None)
        self.hotspots.pop(reg_name, None)
        self.updateExtraBox()
        self.updateLargePreview(reg_name)
        label = role.label if role else reg_name
        self.status.setText(f"已移回替换资源池：{label}")
        self.autoSaveCurrentScheme()

    def removeExtraFromMemory(self, path: Path) -> None:
        try:
            target = path.resolve()
            self.extraFiles = [item for item in self.extraFiles if not (item.exists() and item.resolve() == target)]
        except Exception:
            self.extraFiles = [item for item in self.extraFiles if item != path]

    def editHotspotForRole(self, reg_name: str) -> None:
        role = self.backend.ROLE_BY_REG.get(reg_name)
        if not role:
            return
        path = self.selected.get(reg_name)
        ratio = self.hotspots.get(reg_name, role.hotspot_ratio)
        dialog = HotspotDialog(self.backend, role, path, ratio, self)
        if dialog.exec() == QDialog.Accepted:
            self.hotspots[reg_name] = dialog.ratio
            self.status.setText(f"已设置焦点：{role.label}")
            self.autoSaveCurrentScheme()

    def updateLargePreview(self, reg_name: str):
        self.current_preview = reg_name
        self.animationTimer.stop()
        self.animationFrames = []
        self.animationIndex = 0
        role = self.backend.ROLE_BY_REG.get(reg_name)
        path = self.selected.get(reg_name)
        if role:
            set_translated_text(self.previewName, role.label, self.backend)
        self.previewFile.setText(str(path) if path else tr_text("未选择", ui_english_enabled(self.backend)))
        if not path or not path.exists():
            self.largePreview.setPreview(self.renderRoleIconPixmap(role))
            return
        try:
            if path.suffix.lower() == ".ani":
                frames = self.backend.ani_frame_paths(path)
                if frames:
                    self.animationFrames = [self.renderPreviewPixmap(frame) for frame in frames[:60]]
                    self.nextAnimationFrame()
                    self.animationTimer.start(90)
                    return
            self.largePreview.setPreview(self.renderPreviewPixmap(path))
        except Exception as exc:
            self.largePreview.clearPreview()
            self.backend.log_error("Fluent 预览失败", exc)

    def renderPreviewPixmap(self, path: Path) -> QPixmap:
        cursor_size = self.backend.size_level_to_pixels(self.sizeLevel)
        image = self.backend.cursor_preview_image_sized(path, (cursor_size, cursor_size), cursor_size)
        return pixmap_from_image(image)

    def renderRoleIconPixmap(self, role) -> QPixmap:
        if not role:
            return QPixmap()
        cursor_path = self.backend.default_cursor_path(role)
        if cursor_path and cursor_path.exists():
            try:
                size = min(180, max(96, self.backend.size_level_to_pixels(self.sizeLevel)))
                image = self.backend.cursor_preview_image_sized(cursor_path, (size, size), size).convert("RGBA")
                return pixmap_from_image(image)
            except Exception:
                pass
        icon = role_icon_path(self.backend, role)
        if icon.exists():
            pixmap = QPixmap(str(icon))
            size = min(180, max(96, self.backend.size_level_to_pixels(self.sizeLevel)))
            return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap()

    def nextAnimationFrame(self):
        if not self.animationFrames:
            return
        self.largePreview.setPreview(self.animationFrames[self.animationIndex % len(self.animationFrames)])
        self.animationIndex += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateLargePreview(self.current_preview)

    def onSizeChanged(self, value: int):
        self.sizeLevel = max(1, min(15, int(value)))
        pixels = self.backend.size_level_to_pixels(self.sizeLevel)
        self.sizeText.setText(f"{self.sizeLevel} / {pixels}px")
        if hasattr(self, "sizeProgress"):
            self.sizeProgress.setValue(self.sizeLevel)
        if hasattr(self, "sizeMinusButton"):
            self.sizeMinusButton.setEnabled(self.sizeLevel > 1)
        if hasattr(self, "sizePlusButton"):
            self.sizePlusButton.setEnabled(self.sizeLevel < 15)
        if getattr(self, "liveSizeSwitch", None) and self.liveSizeSwitch.isChecked():
            self.sizeApplyTimer.start(120)
        self.updateLargePreview(self.current_preview)

    def onLiveSizeChanged(self, checked: bool):
        if checked:
            self.sizeApplyTimer.start(0)

    def changeSizeLevel(self, delta: int):
        self.onSizeChanged(self.sizeLevel + delta)

    def applyCurrentCursorSize(self) -> None:
        pixels = self.backend.size_level_to_pixels(self.sizeLevel)

        def work():
            try:
                self.backend.set_system_cursor_size(pixels)
            except Exception as exc:
                self.backend.log_error("Fluent 实时调整鼠标大小失败", exc)

        threading.Thread(target=work, daemon=True).start()

    def pickFileForRole(self, reg_name: str):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择鼠标文件",
            str(self.backend.configured_storage_root()),
            "鼠标和图片 (*.cur *.ani *.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico);;所有文件 (*.*)",
        )
        if not file_name:
            return
        path = Path(file_name)
        self.selected[reg_name] = path
        self.rows[reg_name].setPath(path)
        self.updateLargePreview(reg_name)
        self.autoSaveCurrentScheme()

    def beginImportBatch(self) -> None:
        self.importSkipped = []
        self.importFailed = []

    def showImportSummary(self, imported: list[str]) -> None:
        imported = [name for name in imported if name]
        lines = [f"成功：{len(imported)} 个"]
        if imported:
            preview = "、".join(imported[:6])
            if len(imported) > 6:
                preview += f" 等 {len(imported)} 个"
            lines.append(preview)
        if self.importSkipped:
            lines.append(f"跳过重复：{len(self.importSkipped)} 个")
        if self.importFailed:
            lines.append(f"失败：{len(self.importFailed)} 个，详情见错误记录。")
        content = "\n".join(lines)
        if imported:
            self.showInfo("导入完成", content)
        elif self.importSkipped:
            self.showWarn("导入完成", content)
        elif self.importFailed:
            self.showWarn("导入失败", content)

    def handleDropped(self, paths: list[Path]):
        packages = [p for p in paths if p.is_dir() or p.suffix.lower() in {".zip", ".rar", ".7z", ".exe"}]
        if packages:
            self.beginImportBatch()
            imported = []
            for package in packages:
                imported.extend(self.importPackagePath(package))
            self.refreshSchemes()
            self.showImportSummary(imported)
            return
        files = [p for p in paths if p.suffix.lower() in {".cur", ".ani", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"}]
        for path in files:
            self.selected[self.current_preview] = path
            self.rows[self.current_preview].setPath(path)
        self.updateLargePreview(self.current_preview)
        if files:
            self.autoSaveCurrentScheme()

    def importPackage(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "导入安装包、压缩包或光标文件",
            str(self.backend.configured_storage_root()),
            "资源包和光标 (*.zip *.rar *.7z *.exe *.cur *.ani);;所有文件 (*.*)",
        )
        imported = []
        self.beginImportBatch()
        for file_name in files:
            path = Path(file_name)
            if path.suffix.lower() in {".cur", ".ani"}:
                self.selected[self.current_preview] = path
                self.rows[self.current_preview].setPath(path)
                self.updateLargePreview(self.current_preview)
                self.autoSaveCurrentScheme()
            else:
                imported.extend(self.importPackagePath(path))
        if files:
            self.refreshSchemes()
            if imported or self.importSkipped or self.importFailed:
                self.showImportSummary(imported)

    def importFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "导入鼠标指针文件夹", str(self.backend.configured_storage_root()))
        if folder:
            self.beginImportBatch()
            imported = self.importPackagePath(Path(folder))
            self.refreshSchemes()
            self.showImportSummary(imported)

    def importPackagePath(self, package: Path) -> list[str]:
        imported = []
        try:
            extracted = self.backend.extract_import_package(package)
            roots = self.detectSchemeRoots(extracted)
            if len(roots) > 1:
                self.showInfo("批量导入", f"识别到 {len(roots)} 份鼠标指针，正在批量添加。")
            for root in roots:
                name = package.stem if len(roots) == 1 else root.name
                search_root = extracted if len(roots) == 1 else root.parent
                imported_name = self.importRootAsScheme(root, name, search_root)
                if imported_name:
                    imported.append(imported_name)
            return imported
        except Exception as exc:
            self.importFailed.append(f"{package.name}: {exc}")
            self.showError("导入失败", exc)
            return imported

    def detectSchemeRoots(self, extracted: Path) -> list[Path]:
        inf_roots = []
        for inf in extracted.rglob("*.inf"):
            root = inf.parent
            if any(p.suffix.lower() in {".cur", ".ani"} for p in root.rglob("*")):
                inf_roots.append(root)
        unique = list(dict.fromkeys(inf_roots))
        if unique:
            return unique
        child_roots = []
        for child in (extracted.iterdir() if extracted.exists() else []):
            if child.is_dir() and any(p.suffix.lower() in {".cur", ".ani"} for p in child.rglob("*")):
                child_roots.append(child)
        if len(child_roots) > 1:
            return child_roots
        return [extracted]

    def extraResourcesFromRoot(self, root: Path, mapping: dict[str, Path], search_root: Path | None = None) -> list[Path]:
        base = search_root or root
        mapped = {path.resolve() for path in mapping.values() if path.exists()}
        extras = []
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTRA_RESOURCE_EXTS:
                continue
            try:
                if path.resolve() in mapped:
                    continue
            except Exception:
                pass
            extras.append(path)
        return extras

    def importRootAsScheme(self, root: Path, raw_name: str, search_root: Path | None = None) -> str:
        try:
            name = self.backend.sanitize_name(raw_name)
            if name in self.backend.DEFAULT_SCHEME_NAMES:
                name = f"{name}_资源"
            scheme_dir = self.backend.SCHEME_LIBRARY / name
            if (scheme_dir / "scheme.json").exists():
                result = QMessageBox.question(self, "发现重复方案", f"{name} 已存在，是否继续导入为新副本？\n选择“否”将跳过该方案。")
                if result != QMessageBox.Yes:
                    self.importSkipped.append(name)
                    self.showWarn("已跳过", f"{name} 已存在，未重复导入。")
                    return ""
                base = name
                index = 2
                while (self.backend.SCHEME_LIBRARY / f"{base}_{index}" / "scheme.json").exists():
                    index += 1
                name = f"{base}_{index}"
                scheme_dir = self.backend.SCHEME_LIBRARY / name
            mapping = self.backend.parse_inf_mapping(root)
            if not mapping:
                raise RuntimeError(f"{root.name} 没有识别到鼠标方案。")
            scheme_dir.mkdir(parents=True, exist_ok=True)
            files = {}
            for reg_name, source in mapping.items():
                role = self.backend.ROLE_BY_REG.get(reg_name)
                if not role:
                    continue
                output_name = f"{role.file_stem}{source.suffix.lower()}"
                shutil.copy2(source, scheme_dir / output_name)
                files[reg_name] = output_name
            extra_names = self.copyExtraFilesToScheme(scheme_dir, self.extraResourcesFromRoot(root, mapping, search_root))
            self.writeManifest(name, files, scheme_dir, extra_names, {})
            self.status.setText(f"已添加：{name}")
            return name
        except Exception as exc:
            self.importFailed.append(f"{raw_name}: {exc}")
            self.showError("导入失败", exc)
            return ""

    def validate(self) -> str | None:
        if not self.selected:
            return "请至少选择一个鼠标状态文件。"
        for path in self.selected.values():
            if not path.exists():
                return f"文件不存在：{path}"
        return None

    def prepareAssets(self, package_dir: Path) -> dict[str, str]:
        assets_dir = package_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
        assets_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        cursor_size = self.backend.size_level_to_pixels(self.sizeLevel)
        for reg_name, source in self.selected.items():
            role = self.backend.ROLE_BY_REG[reg_name]
            suffix = source.suffix.lower()
            output_name = f"{role.file_stem}{suffix if suffix in {'.cur', '.ani'} else '.cur'}"
            output = assets_dir / output_name
            self.backend.convert_to_cursor(source, output.with_suffix(".cur") if suffix not in {".cur", ".ani"} else output, role, cursor_size, self.hotspots.get(reg_name))
            files[reg_name] = output_name
        return files

    def installAssetsToScheme(self, theme: str, files: dict[str, str], assets_dir: Path) -> Path:
        target_dir = self.backend.INSTALLED_LIBRARY / theme
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in files.values():
            shutil.copy2(assets_dir / name, target_dir / name)
        return target_dir

    def writeManifest(self, theme: str, files: dict[str, str], folder: Path, extras: list[str] | None = None, hotspots: dict[str, tuple[float, float]] | None = None):
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {"name": theme, "files": files, "order": self.backend.time.time(), "saved_at": datetime.now().isoformat()}
        if extras:
            manifest["extras"] = extras
        hotspot_data = self.hotspots if hotspots is None else hotspots
        if hotspot_data:
            manifest["hotspots"] = {reg: [ratio[0], ratio[1]] for reg, ratio in hotspot_data.items()}
        (folder / "scheme.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def saveScheme(self):
        error = self.validate()
        if error:
            self.showWarn("还不能保存", error)
            return
        theme = self.backend.sanitize_name(self.schemeBox.currentText() or "新方案")
        try:
            package_dir = self.backend.WORK_ROOT / "fluent_library_save"
            files = self.prepareAssets(package_dir)
            scheme_dir = self.backend.SCHEME_LIBRARY / theme
            staged_extras = self.stageExtraFiles(self.backend.WORK_ROOT / "fluent_library_extra_stage")
            if scheme_dir.exists():
                shutil.rmtree(scheme_dir)
            shutil.copytree(package_dir / "assets", scheme_dir)
            extra_names = self.copyExtraFilesToScheme(scheme_dir, staged_extras)
            self.writeManifest(theme, files, scheme_dir, extra_names)
            self.refreshSchemes()
            self.schemeBox.setCurrentText(theme)
            self.loadScheme(theme)
            self.showInfo("保存完成", f"已保存：{theme}")
        except Exception as exc:
            self.showError("保存失败", exc)

    def applyScheme(self):
        error = self.validate()
        if error:
            self.showWarn("还不能应用", error)
            return
        theme = self.backend.sanitize_name(self.schemeBox.currentText() or "当前方案")
        pixels = self.backend.size_level_to_pixels(self.sizeLevel)

        def work():
            direct_files = {
                reg_name: str(path)
                for reg_name, path in self.selected.items()
                if path.exists() and path.suffix.lower() in {".cur", ".ani"}
            }
            if len(direct_files) == len(self.selected):
                self.backend.apply_refreshed_cursor_scheme(theme, direct_files, pixels)
            else:
                package_dir = self.backend.WORK_ROOT / "fluent_current_theme"
                files = self.prepareAssets(package_dir)
                target_dir = self.installAssetsToScheme(theme, files, package_dir / "assets")
                self.backend.apply_refreshed_cursor_scheme(theme, {reg: str(target_dir / name) for reg, name in files.items()}, pixels)
                self.writeManifest(theme, files, target_dir)
            return f"{theme}（{pixels}px）"

        self.runTask("正在应用鼠标方案", work, lambda name: self.showInfo("应用完成", f"已应用：{name}"))

    def exportPreviewScreenshot(self):
        resources = [
            (self.backend.ROLE_BY_REG[reg_name], path)
            for reg_name, path in self.selected.items()
            if path and path.exists() and reg_name in self.backend.ROLE_BY_REG
        ]
        if not resources:
            self.showWarn("截图导出", "没有可导出的鼠标指针资源。")
            return
        default_dir = self.backend.configured_output_root()
        default_dir.mkdir(parents=True, exist_ok=True)
        theme = self.backend.sanitize_name(self.schemeBox.currentText() or "鼠标方案")
        default_path = default_dir / f"{theme}_方案预览截图.gif"
        file_name, _ = QFileDialog.getSaveFileName(self, "请选择导出位置", str(default_path), "GIF (*.gif)")
        if not file_name:
            return
        target = Path(file_name)
        if target.suffix.lower() != ".gif":
            target = target.with_suffix(".gif")
        target.parent.mkdir(parents=True, exist_ok=True)

        def work():
            columns = 5
            tile_w = 168
            tile_h = 162
            padding = 24
            header_h = 58
            rows = (len(resources) + columns - 1) // columns
            width = padding * 2 + columns * tile_w
            height = padding * 2 + header_h + rows * tile_h
            title_font = self.previewExportFont(24, bold=True)
            label_font = self.previewExportFont(15)
            small_font = self.previewExportFont(11)
            resource_frames = [(role, self.previewExportSources(path)) for role, path in resources]
            frame_count = max((len(frames) for _role, frames in resource_frames), default=1)
            frame_count = max(1, min(36, frame_count))
            images = []
            for frame_index in range(frame_count):
                image = Image.new("RGBA", (width, height), (245, 250, 255, 255))
                draw = ImageDraw.Draw(image)
                draw.text((padding, padding), theme, fill=(15, 23, 42, 255), font=title_font)
                draw.text((padding, padding + 32), f"{len(resources)} 个鼠标状态", fill=(100, 116, 139, 255), font=small_font)
                for index, (role, frames) in enumerate(resource_frames):
                    if not frames:
                        continue
                    source = frames[frame_index % len(frames)]
                    row = index // columns
                    col = index % columns
                    x = padding + col * tile_w
                    y = padding + header_h + row * tile_h
                    card = (x + 8, y + 8, x + tile_w - 8, y + tile_h - 8)
                    draw.rounded_rectangle(card, radius=12, fill=(255, 255, 255, 235), outline=(219, 234, 254, 255), width=1)
                    preview = self.previewExportImage(source, (118, 104)).convert("RGBA")
                    image.alpha_composite(preview, (x + (tile_w - preview.width) // 2, y + 20))
                    label = role.label
                    bbox = draw.textbbox((0, 0), label, font=label_font)
                    label_x = x + max(10, (tile_w - (bbox[2] - bbox[0])) // 2)
                    draw.text((label_x, y + 128), label, fill=(30, 41, 59, 255), font=label_font)
                images.append(image.convert("P", palette=Image.Palette.ADAPTIVE))
            first, rest = images[0], images[1:]
            first.save(target, "GIF", save_all=True, append_images=rest, duration=90, loop=0, disposal=2)
            return target

        self.runTask("截图导出", work, lambda path: self.showInfo("导出完成", f"已导出：{path}"))

    def previewExportSources(self, path: Path) -> list[Path]:
        if path.suffix.lower() == ".ani":
            frames = self.backend.ani_frame_paths(path)[:36]
            if frames:
                return frames
        return [path]

    def previewExportImage(self, source: Path, box: tuple[int, int]) -> Image.Image:
        return self.backend.cursor_preview_image_sized(source, box, self.backend.size_level_to_pixels(self.sizeLevel))

    def previewExportFont(self, size: int, bold: bool = False):
        candidates = [
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / ("msyhbd.ttc" if bold else "msyh.ttc"),
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / ("seguisb.ttf" if bold else "segoeui.ttf"),
        ]
        for path in candidates:
            try:
                if path.exists():
                    return ImageFont.truetype(str(path), size)
            except Exception:
                pass
        return ImageFont.load_default()

    def buildInstaller(self):
        error = self.validate()
        if error:
            self.showWarn("还不能生成", error)
            return
        default_dir = self.backend.configured_output_root()
        default_dir.mkdir(parents=True, exist_ok=True)
        folder = QFileDialog.getExistingDirectory(self, "选择安装包保存位置", str(default_dir))
        if not folder:
            return
        output_dir = Path(folder)
        data = self.backend.load_settings()
        data["output_root"] = str(output_dir.resolve())
        self.backend.save_settings(data)
        theme = self.backend.sanitize_name(self.schemeBox.currentText() or "鼠标方案")
        pixels = self.backend.size_level_to_pixels(self.sizeLevel)
        installer_theme = self.backend.sanitize_name(f"{theme}_{pixels}px")

        def work():
            package_dir = self.backend.WORK_ROOT / "fluent_installer_package"
            package_dir.mkdir(parents=True, exist_ok=True)
            files = self.prepareAssets(package_dir)
            installer_py = package_dir / "install_cursor_theme.py"
            installer_py.write_text(self.backend.installer_source(installer_theme, files, pixels), encoding="utf-8")
            exe_name = f"{installer_theme}_鼠标样式安装器"
            icon_path = self.installerIcon(package_dir)
            python = self.backend.find_python_with_pyinstaller()
            command = [
                python,
                "-m",
                "PyInstaller",
                "--noconsole",
                "--windowed",
                "--onefile",
                "--clean",
                "--name",
                exe_name,
                "--distpath",
                str(output_dir),
                "--workpath",
                str(self.backend.WORK_ROOT / "pyinstaller"),
                "--specpath",
                str(self.backend.WORK_ROOT / "spec"),
                "--add-data",
                f"{package_dir / 'assets'};assets",
            ]
            if icon_path and icon_path.exists():
                command.extend(["--icon", str(icon_path)])
            command.append(str(installer_py))
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            result = subprocess.run(command, cwd=self.backend.APP_DIR, text=True, capture_output=True, check=False, creationflags=creationflags)
            if result.returncode != 0:
                log_path = self.backend.WORK_ROOT / "pyinstaller_error.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8", errors="replace")
                raise RuntimeError(f"PyInstaller 打包失败，日志：{log_path}")
            return output_dir / f"{exe_name}.exe"

        def done(path: Path):
            self.showInfo("生成完成", str(path))
            os.startfile(path.parent)

        self.runTask("正在生成安装包", work, done)

    def restoreCursor(self):
        self.runTask("正在恢复鼠标方案", self.backend.restore_cursor_backup, lambda _value: self.showInfo("已恢复", "已恢复应用前鼠标方案"))

    def installerIcon(self, package_dir: Path) -> Path | None:
        source = self.selected.get("Arrow") or next(iter(self.selected.values()), None)
        if not source:
            return None
        try:
            if source.suffix.lower() in {".cur", ".ani"}:
                frames = self.backend.ani_frame_paths(source) if source.suffix.lower() == ".ani" else []
                icon_source = frames[0] if frames else source
                try:
                    image = self.backend.centered_rgba(Image.open(icon_source).convert("RGBA"), 64)
                except Exception:
                    image = self.backend.render_cursor_with_windows(icon_source, 64)
                    if image is None:
                        image = self.backend.cursor_preview_image(icon_source, (64, 64)).convert("RGBA")
            else:
                image = self.backend.centered_rgba(self.backend.image_from_path(source), 64)
            icon_path = package_dir / "installer_icon.ico"
            image.save(icon_path, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
            return icon_path
        except Exception as exc:
            self.backend.log_error("Fluent 生成安装包图标失败", exc)
            return None

    def newScheme(self):
        base = "新方案"
        index = 1
        names = set(self.schemeNames())
        while f"{base}{index}" in names:
            index += 1
        name = f"{base}{index}"
        self.schemeBox.addItem(name)
        self.schemeBox.setCurrentText(name)
        self.clearSelection()

    def renameScheme(self):
        old = self.schemeBox.currentText()
        if not old:
            return
        new = f"{old}_重命名"
        old_dir = self.backend.SCHEME_LIBRARY / old
        new_dir = self.backend.SCHEME_LIBRARY / new
        try:
            if old_dir.exists() and not new_dir.exists():
                old_dir.rename(new_dir)
                manifest = new_dir / "scheme.json"
                if manifest.exists():
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    data["name"] = new
                    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.refreshSchemes()
            self.schemeBox.setCurrentText(new)
        except Exception as exc:
            self.showError("重命名失败", exc)

    def deleteScheme(self):
        name = self.schemeBox.currentText()
        if not name:
            return
        try:
            names = self.schemeNames()
            index = names.index(name) if name in names else -1
            shutil.rmtree(self.backend.SCHEME_LIBRARY / name, ignore_errors=True)
            self.refreshSchemes()
            names_after = self.schemeNames()
            if names_after:
                target_index = max(0, min(index - 1, len(names_after) - 1))
                self.schemeBox.setCurrentText(names_after[target_index])
                self.loadScheme(names_after[target_index])
            self.showInfo("删除完成", f"已删除：{name}")
        except Exception as exc:
            self.showError("删除失败", exc)

    def runTask(self, title: str, func, on_done):
        self.applyButton.setEnabled(False)
        self.status.setText(title)
        signal = TaskSignal(self)
        signal.finished.connect(lambda value: self.finishTask(value, on_done))
        signal.failed.connect(lambda msg: self.failTask(msg))

        def target():
            try:
                signal.finished.emit(func())
            except Exception as exc:
                self.backend.log_error(title, exc)
                signal.failed.emit(str(exc))

        threading.Thread(target=target, daemon=True).start()

    def finishTask(self, value, on_done):
        self.applyButton.setEnabled(True)
        self.status.setText("完成")
        on_done(value)
        self.refreshSchemes()
        self.updateRuntimeInfo()

    def failTask(self, message: str):
        self.applyButton.setEnabled(True)
        self.status.setText("失败")
        self.showWarn("操作失败", message)

    def showInfo(self, title: str, content: str):
        InfoBar.success(title=title, content=content, orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())

    def showWarn(self, title: str, content: str):
        InfoBar.warning(title=title, content=content, orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=4000, parent=self.window())

    def showError(self, title: str, exc):
        self.backend.log_error(title, exc)
        InfoBar.error(title=title, content=str(exc), orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=5500, parent=self.window())


class ResourcePage(QWidget):
    def __init__(self, backend, scheme_page: SchemePage, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.scheme_page = scheme_page
        self.gridMode = False
        self.deleted: dict[str, Path] = {}
        self.selectedName: str | None = None
        self.cardWidgets: dict[str, QWidget] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("资源库"))
        layout.addWidget(CaptionLabel("打开在线资源库下载文件，放入鼠标文件目录后点击刷新。"))
        row = QHBoxLayout()
        self.openWeb = PushButton("在线资源库")
        self.openWeb.setIcon(FIF.LINK)
        self.importButton = PushButton("导入资源")
        self.importButton.setIcon(FIF.DOWNLOAD)
        self.importFolderButton = PushButton("导入文件夹")
        self.importFolderButton.setIcon(FIF.FOLDER)
        self.refresh = PrimaryPushButton("刷新")
        self.refresh.setIcon(FIF.SYNC)
        self.restoreButton = PushButton("恢复上一份鼠标方案")
        self.restoreButton.setIcon(FIF.RETURN)
        self.gridButton = ToggleButton("九宫格")
        self.gridButton.setIcon(FIF.TILES)
        for button in [self.openWeb, self.importButton, self.importFolderButton, self.refresh, self.restoreButton, self.gridButton]:
            button.setMinimumWidth(104)
        row.addWidget(self.openWeb)
        row.addWidget(self.importButton)
        row.addWidget(self.importFolderButton)
        row.addWidget(self.refresh)
        row.addWidget(self.restoreButton)
        row.addWidget(self.gridButton)
        row.addStretch(1)
        layout.addLayout(row)
        self.dropArea = DropArea("拖入压缩包、安装器或文件夹添加到资源库")
        self.dropArea.dropped.connect(self.importDroppedResources)
        layout.addWidget(self.dropArea)
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.cards = QVBoxLayout(self.container)
        self.cards.setSpacing(10)
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 2, 0, 0)
        self.selectionStatus = CaptionLabel("未选择方案")
        self.selectionStatus.setTextColor("#64748b", "#94a3b8")
        self.applySelectedButton = PrimaryPushButton("应用")
        self.applySelectedButton.setIcon(FIF.ACCEPT)
        self.applySelectedButton.setMinimumWidth(112)
        self.deleteSelectedButton = PushButton("删除")
        self.deleteSelectedButton.setIcon(FIF.DELETE)
        self.deleteSelectedButton.setMinimumWidth(112)
        action_bar.addWidget(self.selectionStatus)
        action_bar.addStretch(1)
        action_bar.addWidget(self.applySelectedButton)
        action_bar.addWidget(self.deleteSelectedButton)
        layout.addLayout(action_bar)
        self.openWeb.clicked.connect(lambda: webbrowser.open(self.backend.RESOURCE_URL))
        self.importButton.clicked.connect(self.importResources)
        self.importFolderButton.clicked.connect(self.importResourceFolder)
        self.refresh.clicked.connect(self.render)
        self.restoreButton.clicked.connect(self.restoreCursor)
        self.gridButton.clicked.connect(self.toggleGrid)
        self.applySelectedButton.clicked.connect(self.applySelectedResource)
        self.deleteSelectedButton.clicked.connect(self.deleteSelectedResources)
        self.loadedOnce = False
        self.cards.addWidget(CaptionLabel("进入资源库页面后再加载资源预览。"))
        self.updateSelectionControls()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.loadedOnce:
            self.loadedOnce = True
            QTimer.singleShot(0, self.render)

    def toggleGrid(self):
        self.gridMode = self.gridButton.isChecked()
        self.render()

    def clearCards(self):
        layout = self.container.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(layout)

    def render(self):
        old = self.container.layout()
        if old:
            while old.count():
                item = old.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old)
        self.cards = QGridLayout(self.container) if self.gridMode else QVBoxLayout(self.container)
        self.cards.setSpacing(10)
        names = self.scheme_page.schemeNames()
        if self.selectedName not in names:
            self.selectedName = None
        self.cardWidgets = {}
        if not names:
            empty = BodyLabel("暂无资源")
            if self.gridMode:
                self.cards.addWidget(empty, 0, 0)
            else:
                self.cards.addWidget(empty)
            self.updateSelectionControls()
            return
        for index, name in enumerate(names):
            card = QWidget()
            card.setObjectName("resourceCard")
            card.setCursor(Qt.PointingHandCursor)
            if self.gridMode:
                card.setMinimumSize(320, 260)
            else:
                card.setMinimumHeight(92)
            self.cardWidgets[name] = card
            layout = QVBoxLayout(card) if self.gridMode else QHBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(10)
            text = QVBoxLayout()
            text.setSpacing(5)
            title_row = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)
            title_row.setSpacing(8)
            title_row.addWidget(StrongBodyLabel(name))
            scheme_dir, files = self.backend.scheme_manifest(name)
            summary = cursor_kind_summary_text(scheme_dir, files)
            summary_label = QLabel()
            style_summary_chip(summary_label, summary)
            title_row.addWidget(summary_label)
            title_row.addStretch(1)
            text.addLayout(title_row)
            count_text = f"{len(files)} 个鼠标状态"
            text.addWidget(CaptionLabel(count_text))
            layout.addLayout(text, 1 if not self.gridMode else 0)
            preview_grid = QGridLayout()
            preview_grid.setHorizontalSpacing(6)
            preview_grid.setVerticalSpacing(6)
            columns = 5 if self.gridMode else 9
            shown_index = 0
            for role in self.backend.CURSOR_ROLES:
                file_name = files.get(role.reg_name)
                if not file_name:
                    continue
                path = scheme_dir / file_name
                if not path.exists():
                    continue
                preview = CursorPreview(46 if self.gridMode else 38)
                preview.setPath(self.backend, path, 44 if self.gridMode else 34, role=role, showBadge=False)
                preview.setToolTip(role.label)
                preview_grid.addWidget(preview, shown_index // columns, shown_index % columns)
                shown_index += 1
            layout.addLayout(preview_grid, 1)
            card.mousePressEvent = self.resourceCardPressHandler(name)
            self.updateResourceCardStyle(name)
            if self.gridMode:
                self.cards.addWidget(card, index // 3, index % 3)
            else:
                self.cards.addWidget(card)
        if not self.gridMode:
            self.cards.addStretch(1)
        self.updateSelectionControls()

    def resourceCardPressHandler(self, name: str):
        def handler(event):
            if event.button() == Qt.LeftButton:
                self.toggleResourceSelection(name)
                event.accept()

        return handler

    def updateResourceCardStyle(self, name: str) -> None:
        card = self.cardWidgets.get(name)
        if not card:
            return
        if name == self.selectedName:
            card.setStyleSheet(
                "#resourceCard { background: #eef6ff; border: 1px solid #60a5fa; "
                "border-radius: 8px; } #resourceCard:hover { background: #e0f2fe; }"
            )
        else:
            card.setStyleSheet(
                "#resourceCard { background: #ffffff; border: 1px solid transparent; "
                "border-radius: 8px; } #resourceCard:hover { background: #f4fbff; }"
            )

    def setResourceSelected(self, name: str, selected: bool) -> None:
        if selected:
            previous = self.selectedName
            self.selectedName = name
            if previous and previous != name:
                self.updateResourceCardStyle(previous)
        else:
            if self.selectedName == name:
                self.selectedName = None
        self.updateResourceCardStyle(name)
        self.updateSelectionControls()

    def toggleResourceSelection(self, name: str) -> None:
        self.setResourceSelected(name, name != self.selectedName)

    def selectedResourceName(self) -> str | None:
        if self.selectedName in self.scheme_page.schemeNames():
            return self.selectedName
        self.selectedName = None
        return None

    def updateSelectionControls(self) -> None:
        if not self.selectedName:
            self.selectionStatus.setText("未选择方案")
        else:
            self.selectionStatus.setText(f"已选择：{self.selectedName}")
        self.applySelectedButton.setEnabled(bool(self.selectedName))
        self.deleteSelectedButton.setEnabled(bool(self.selectedName))

    def applySelectedResource(self):
        selected = self.selectedResourceName()
        if not selected:
            self.scheme_page.showWarn("请选择一个方案", "应用资源库方案前需要先选择一个方案。")
            return
        self.applyResource(selected)

    def deleteSelectedResources(self):
        selected = self.selectedResourceName()
        if not selected:
            return
        trash_root = self.backend.WORK_ROOT / "resource_trash"
        trash_root.mkdir(parents=True, exist_ok=True)
        stamp = int(time.time())
        source = self.backend.SCHEME_LIBRARY / selected
        if not source.exists():
            self.selectedName = None
            self.render()
            return
        target = trash_root / f"{selected}_{stamp}"
        suffix = 1
        while target.exists():
            target = trash_root / f"{selected}_{stamp}_{suffix}"
            suffix += 1
        try:
            source.rename(target)
            self.deleted[selected] = target
            self.selectedName = None
            self.scheme_page.refreshSchemes()
            self.render()
            InfoBar.success(
                title="删除完成",
                content=f"已移动到回收区：{selected}。误删可从 build/resource_trash 恢复。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000,
                parent=self.window(),
            )
        except Exception as exc:
            self.backend.log_error("删除资源库方案失败", exc)
            self.scheme_page.showWarn("删除失败", str(exc))

    def applyResource(self, name: str):
        self.scheme_page.schemeBox.setCurrentText(name)
        self.scheme_page.loadScheme(name)
        self.scheme_page.applyScheme()

    def deleteOrRestoreResource(self, name: str, button: PushButton):
        source = self.backend.SCHEME_LIBRARY / name
        if name in self.deleted:
            target = self.deleted.pop(name)
            if target.exists():
                if source.exists():
                    shutil.rmtree(source, ignore_errors=True)
                target.rename(source)
            button.setText("删除")
            button.setIcon(FIF.DELETE)
            self.scheme_page.refreshSchemes()
            return
        if not source.exists():
            return
        trash_root = self.backend.WORK_ROOT / "resource_trash"
        trash_root.mkdir(parents=True, exist_ok=True)
        target = trash_root / f"{name}_{int(self.backend.time.time())}"
        source.rename(target)
        self.deleted[name] = target
        button.setText("恢复")
        button.setIcon(FIF.RETURN)
        self.scheme_page.refreshSchemes()

    def restoreCursor(self):
        self.scheme_page.runTask("正在恢复鼠标方案", self.backend.restore_cursor_backup, lambda _value: InfoBar.success(title="已恢复", content="已恢复应用前鼠标方案", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window()))

    def importDroppedResources(self, paths: list[Path]):
        imported = []
        self.scheme_page.beginImportBatch()
        for path in paths:
            imported.extend([name for name in self.scheme_page.importPackagePath(path) if name])
        self.scheme_page.refreshSchemes()
        self.render()
        self.scheme_page.showImportSummary(imported)

    def importResources(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "导入资源包或安装器",
            str(self.backend.configured_storage_root()),
            "资源包 (*.zip *.rar *.7z *.exe);;所有文件 (*.*)",
        )
        if files:
            self.importDroppedResources([Path(file) for file in files])

    def importResourceFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "导入资源文件夹", str(self.backend.configured_storage_root()))
        if folder:
            self.importDroppedResources([Path(folder)])


class SchedulePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("时间切换"))
        layout.addWidget(CaptionLabel("点击时间框可选择时间，也可以手写具体时间。留空则不切换。"))
        self.lightTime = self.createTimeBox()
        self.lightScheme = ComboBox()
        self.darkTime = self.createTimeBox()
        self.darkScheme = ComboBox()
        for widget in [self.lightScheme, self.darkScheme]:
            widget.addItem("")
            widget.addItem("随机方案", self.backend.RANDOM_SCHEME_VALUE)
            widget.addItems(self.schemeNames())
        for title, time_edit, scheme in [("亮色模式", self.lightTime, self.lightScheme), ("暗色模式", self.darkTime, self.darkScheme)]:
            card = CardWidget()
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 14, 16, 14)
            row.addWidget(StrongBodyLabel(title))
            row.addWidget(time_edit)
            row.addWidget(scheme)
            layout.addWidget(card)
        save = PrimaryPushButton("应用时间切换")
        save.clicked.connect(self.save)
        layout.addWidget(save, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self.load()

    def schemeNames(self) -> list[str]:
        root = self.backend.SCHEME_LIBRARY
        return sorted([p.name for p in root.iterdir() if p.is_dir()], key=lambda name: self.backend.scheme_order_value(root / name)) if root.exists() else []

    def createTimeBox(self) -> EditableComboBox:
        box = EditableComboBox()
        box.setMinimumWidth(180)
        options = [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)]
        box.addItems(options)
        box.setText("")
        return box

    def currentSchemeValue(self, combo: ComboBox) -> str:
        data = combo.currentData()
        return str(data) if data else combo.currentText().strip()

    def setSchemeValue(self, combo: ComboBox, value: str):
        if value == self.backend.RANDOM_SCHEME_VALUE:
            combo.setCurrentText("随机方案")
        else:
            combo.setCurrentText(value)

    def load(self):
        try:
            items, _week = self.backend.load_schedule_state()
            by_mode = {item.get("mode"): item for item in items}
            for mode, time_edit, scheme in [("light", self.lightTime, self.lightScheme), ("dark", self.darkTime, self.darkScheme)]:
                item = by_mode.get(mode, {})
                time_edit.setText(item.get("time", ""))
                self.setSchemeValue(scheme, item.get("scheme", ""))
        except Exception:
            pass

    def save(self):
        try:
            items = []
            for mode, time_edit, scheme in [("light", self.lightTime, self.lightScheme), ("dark", self.darkTime, self.darkScheme)]:
                value = self.currentSchemeValue(scheme)
                at = time_edit.currentText().strip()
                if value:
                    self.backend.CursorThemeBuilder.validate_time(None, at)
                    items.append({"mode": mode, "time": at, "scheme": value})
            self.backend.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.SCHEDULE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(True)
            InfoBar.success(title="已应用", content="时间切换已保存并开启后台自启动", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("Fluent 时间切换保存失败", exc)
            InfoBar.error(title="保存失败", content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())


class TimerPage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("计时切换"))
        layout.addWidget(CaptionLabel("按固定间隔自动切换方案。选择“随机方案”时每次从方案库随机挑选。"))
        card = CardWidget()
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        self.enabled = SwitchButton("启用计时切换")
        self.interval = QSpinBox()
        self.interval.setRange(1, 86400)
        self.interval.setValue(5)
        self.unit = ComboBox()
        self.unit.addItems(["秒", "分钟"])
        self.scheme = ComboBox()
        self.scheme.addItem("")
        self.scheme.addItem("随机", self.backend.RANDOM_SCHEME_VALUE)
        self.scheme.addItem("顺序", "顺序")
        row.addWidget(self.enabled)
        row.addWidget(BodyLabel("每"))
        row.addWidget(self.interval)
        row.addWidget(self.unit)
        row.addWidget(self.scheme)
        layout.addWidget(card)
        save = PrimaryPushButton("应用计时切换")
        save.clicked.connect(self.save)
        layout.addWidget(save, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self.load()

    def schemeNames(self) -> list[str]:
        root = self.backend.SCHEME_LIBRARY
        return sorted([p.name for p in root.iterdir() if p.is_dir()], key=lambda name: self.backend.scheme_order_value(root / name)) if root.exists() else []

    def currentSchemeValue(self) -> str:
        data = self.scheme.currentData()
        return str(data) if data else self.scheme.currentText().strip()

    def load(self):
        try:
            items, _week = self.backend.load_schedule_state()
            timer = next((item for item in items if item.get("mode") == "timer"), {})
            self.enabled.setChecked(bool(timer.get("scheme")))
            seconds = int(timer.get("interval_seconds") or 300)
            if seconds % 60 == 0 and seconds >= 60:
                self.unit.setCurrentText("分钟")
                self.interval.setValue(max(1, seconds // 60))
            else:
                self.unit.setCurrentText("秒")
                self.interval.setValue(seconds)
            value = timer.get("scheme", "")
            if value == self.backend.RANDOM_SCHEME_VALUE:
                self.scheme.setCurrentText("随机")
            elif value == "顺序":
                self.scheme.setCurrentText("顺序")
            else:
                self.scheme.setCurrentText(value)
        except Exception:
            pass

    def save(self):
        try:
            items, week = self.backend.load_schedule_state()
            items = [item for item in items if item.get("mode") != "timer"]
            value = self.currentSchemeValue()
            if self.enabled.isChecked() and value:
                interval = int(self.interval.value()) * (60 if self.unit.currentText() == "分钟" else 1)
                items.append({"mode": "timer", "interval_seconds": interval, "scheme": value})
            self.backend.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.SCHEDULE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(True)
            InfoBar.success(title="已应用", content="计时切换已保存并开启后台自启动", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("Fluent 计时切换保存失败", exc)
            InfoBar.error(title="保存失败", content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())


class SwitchPage(QWidget):
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    def __init__(self, backend, scheme_page: SchemePage, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.scheme_page = scheme_page
        self.modeSwitches: dict[str, SwitchButton] = {}
        self.weekCombos: dict[str, ComboBox] = {}
        self.inputCombos: dict[str, ComboBox] = {}
        self.loading = False
        self.pendingApply = False
        self.saveTimer = QTimer(self)
        self.saveTimer.setSingleShot(True)
        self.saveTimer.timeout.connect(self.save)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("方案切换"))
        layout.addWidget(CaptionLabel("时间切换、计时切换、星期切换、中英文切换只能启用一种。开启或修改后会自动保存。"))

        self.timeCard = CardWidget()
        time_layout = QGridLayout(self.timeCard)
        time_layout.setContentsMargins(16, 14, 16, 14)
        time_title = QHBoxLayout()
        time_title.addWidget(StrongBodyLabel("时间切换"))
        self.timeSwitch = SwitchButton()
        self.modeSwitches["time"] = self.timeSwitch
        time_title.addWidget(self.timeSwitch)
        time_title.addStretch(1)
        time_layout.addLayout(time_title, 0, 0, 1, 4)
        self.lightTime = self.createTimeBox()
        self.lightScheme = self.createSchemeBox()
        self.darkTime = self.createTimeBox()
        self.darkScheme = self.createSchemeBox()
        time_layout.addWidget(BodyLabel("亮色模式"), 1, 0)
        time_layout.addWidget(self.lightTime, 1, 1)
        time_layout.addWidget(self.lightScheme, 1, 2)
        time_layout.addWidget(BodyLabel("暗色模式"), 2, 0)
        time_layout.addWidget(self.darkTime, 2, 1)
        time_layout.addWidget(self.darkScheme, 2, 2)
        layout.addWidget(self.timeCard)

        self.timerCard = CardWidget()
        timer_layout = QVBoxLayout(self.timerCard)
        timer_layout.setContentsMargins(16, 14, 16, 14)
        timer_layout.setSpacing(10)
        timer_header = QHBoxLayout()
        timer_header.addWidget(StrongBodyLabel("计时切换"))
        self.timerSwitch = SwitchButton()
        self.modeSwitches["timer"] = self.timerSwitch
        timer_header.addWidget(self.timerSwitch)
        timer_header.addWidget(BodyLabel("每"))
        self.timerInterval = QSpinBox()
        self.timerInterval.setRange(1, 86400)
        self.timerInterval.setValue(5)
        self.timerInterval.setFixedWidth(88)
        self.timerUnit = ComboBox()
        self.timerUnit.setFixedWidth(82)
        self.timerUnit.addItems(["秒", "分钟"])
        self.timerOrder = ComboBox()
        self.timerOrder.setFixedWidth(88)
        self.timerOrder.addItems(["顺序", "随机"])
        self.timerAllButton = ToggleButton("全选")
        self.timerSchemeButtons: dict[str, ToggleButton] = {}
        self.timerSchemeGrid = QGridLayout()
        self.timerSchemeGrid.setHorizontalSpacing(8)
        self.timerSchemeGrid.setVerticalSpacing(8)
        timer_header.addWidget(self.timerInterval)
        timer_header.addWidget(self.timerUnit)
        timer_header.addWidget(BodyLabel("模式"))
        timer_header.addWidget(self.timerOrder)
        timer_header.addWidget(self.timerAllButton)
        timer_header.addStretch(1)
        timer_layout.addLayout(timer_header)
        timer_tip = CaptionLabel("选择参与计时切换的方案；顺序模式按当前宫格顺序循环，随机模式只在勾选范围内抽取。")
        timer_tip.setWordWrap(True)
        timer_tip.setTextColor("#64748b", "#94a3b8")
        timer_layout.addWidget(timer_tip)
        timer_layout.addLayout(self.timerSchemeGrid)
        layout.addWidget(self.timerCard)

        self.weekCard = CardWidget()
        week_layout = QGridLayout(self.weekCard)
        week_layout.setContentsMargins(16, 14, 16, 14)
        week_title = QHBoxLayout()
        week_title.addWidget(StrongBodyLabel("星期切换"))
        self.weekSwitch = SwitchButton()
        self.modeSwitches["week"] = self.weekSwitch
        week_title.addWidget(self.weekSwitch)
        week_title.addStretch(1)
        week_layout.addLayout(week_title, 0, 0, 1, 4)
        for index, day in enumerate(self.weekdays):
            combo = self.createSchemeBox()
            self.weekCombos[str(index)] = combo
            row = index // 2 + 1
            col = (index % 2) * 2
            week_layout.addWidget(BodyLabel(day), row, col)
            week_layout.addWidget(combo, row, col + 1)
        layout.addWidget(self.weekCard)

        self.inputCard = CardWidget()
        input_layout = QGridLayout(self.inputCard)
        input_layout.setContentsMargins(16, 14, 16, 14)
        input_title = QHBoxLayout()
        input_title.addWidget(StrongBodyLabel("中英文切换"))
        self.inputSwitch = SwitchButton()
        self.modeSwitches["input"] = self.inputSwitch
        input_title.addWidget(self.inputSwitch)
        input_title.addStretch(1)
        input_layout.addLayout(input_title, 0, 0, 1, 4)
        for index, (key, label) in enumerate([("zh", "中文输入"), ("en", "英文输入"), ("upper", "大写锁定")]):
            combo = self.createSchemeBox(False)
            self.inputCombos[key] = combo
            input_layout.addWidget(BodyLabel(label), index + 1, 0)
            input_layout.addWidget(combo, index + 1, 1)
        input_tip = CaptionLabel("后台根据当前前台窗口输入状态切换；大写锁定优先。")
        input_tip.setWordWrap(True)
        input_tip.setTextColor("#64748b", "#94a3b8")
        input_layout.addWidget(input_tip, 4, 0, 1, 2)
        layout.addWidget(self.inputCard)

        layout.addStretch(1)

        for mode, switch in self.modeSwitches.items():
            switch.checkedChanged.connect(lambda checked, m=mode: self.onModeChanged(m, checked))
        for widget in [self.lightTime, self.darkTime, self.lightScheme, self.darkScheme, self.timerUnit, self.timerOrder, *self.weekCombos.values(), *self.inputCombos.values()]:
            try:
                widget.currentTextChanged.connect(self.scheduleSave)
            except Exception:
                pass
        self.timerInterval.valueChanged.connect(self.scheduleSave)
        self.timerAllButton.clicked.connect(self.onTimerAllChanged)
        self.load()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refreshSchemeBoxes()

    def createTimeBox(self) -> EditableComboBox:
        box = EditableComboBox()
        box.setMinimumWidth(180)
        box.addItems([f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)])
        box.setText("")
        return box

    def createSchemeBox(self, include_random: bool = True) -> ComboBox:
        box = ComboBox()
        box.setMinimumWidth(220)
        box.addItem("")
        if include_random:
            box.addItem("随机方案", self.backend.RANDOM_SCHEME_VALUE)
        for name in self.scheme_page.schemeNames():
            box.addItem(name)
        return box

    def allSchemeBoxes(self) -> list[ComboBox]:
        return [self.lightScheme, self.darkScheme, *self.weekCombos.values(), *self.inputCombos.values()]

    def refreshSchemeBoxes(self) -> None:
        if not hasattr(self, "timerSchemeGrid"):
            return
        old_loading = self.loading
        self.loading = True
        names = self.scheme_page.schemeNames()
        selected = self.timerSelectedSchemes()
        input_boxes = {id(box) for box in self.inputCombos.values()}
        for box in self.allSchemeBoxes():
            value = self.currentSchemeValue(box)
            box.clear()
            box.addItem("")
            if id(box) not in input_boxes:
                box.addItem("随机方案", self.backend.RANDOM_SCHEME_VALUE)
            for name in names:
                box.addItem(name)
            self.setSchemeValue(box, "" if id(box) in input_boxes and value == self.backend.RANDOM_SCHEME_VALUE else value)
        self.rebuildTimerSchemeGrid(names, selected)
        self.loading = old_loading

    def clearLayout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.deleteLater()
            elif child_layout:
                self.clearLayout(child_layout)

    def rebuildTimerSchemeGrid(self, names: list[str], selected: list[str] | None = None) -> None:
        selected_set = set(names if selected is None else selected)
        self.clearLayout(self.timerSchemeGrid)
        self.timerSchemeButtons = {}
        if not names:
            empty = CaptionLabel("暂无可选方案，请先在鼠标方案页导入或保存方案。")
            empty.setTextColor("#64748b", "#94a3b8")
            self.timerSchemeGrid.addWidget(empty, 0, 0)
            return
        for index, name in enumerate(names):
            button = ToggleButton(name)
            button.setCheckable(True)
            button.setChecked(name in selected_set)
            button.setMinimumWidth(132)
            button.clicked.connect(self.onTimerSchemeToggled)
            self.timerSchemeButtons[name] = button
            self.timerSchemeGrid.addWidget(button, index // 4, index % 4)
        self.syncTimerAllButton()

    def timerSelectedSchemes(self) -> list[str]:
        return [name for name, button in self.timerSchemeButtons.items() if button.isChecked()]

    def setTimerSelectedSchemes(self, names: list[str]) -> None:
        selected = set(names)
        for name, button in self.timerSchemeButtons.items():
            button.setChecked(name in selected)
        self.syncTimerAllButton()

    def syncTimerAllButton(self) -> None:
        if not hasattr(self, "timerAllButton"):
            return
        buttons = list(self.timerSchemeButtons.values())
        blocked = self.timerAllButton.blockSignals(True)
        self.timerAllButton.setChecked(bool(buttons) and all(button.isChecked() for button in buttons))
        self.timerAllButton.blockSignals(blocked)

    def onTimerAllChanged(self, checked: bool = False) -> None:
        if self.loading:
            return
        for button in self.timerSchemeButtons.values():
            button.setChecked(bool(checked))
        self.scheduleSave()

    def onTimerSchemeToggled(self, checked: bool = False) -> None:
        if self.loading:
            return
        self.syncTimerAllButton()
        self.scheduleSave()

    def currentSchemeValue(self, combo: ComboBox) -> str:
        data = combo.currentData()
        if data:
            text = str(data)
            return text
        text = combo.currentText().strip()
        return text

    def setSchemeValue(self, combo: ComboBox, value: str):
        combo.setCurrentText("随机方案" if value == self.backend.RANDOM_SCHEME_VALUE else value)

    def onModeChanged(self, mode: str, checked: bool):
        if checked:
            for key, switch in self.modeSwitches.items():
                if key != mode and switch.isChecked():
                    switch.setChecked(False)
            self.pendingApply = True
        self.scheduleSave()

    def scheduleSave(self, *args):
        if self.loading:
            return
        self.saveTimer.start(250)

    def activeMode(self) -> str:
        for mode, switch in self.modeSwitches.items():
            if switch.isChecked():
                return mode
        return ""

    def load(self):
        try:
            self.loading = True
            items, week_items = self.backend.load_schedule_state()
            by_mode = {item.get("mode"): item for item in items}
            light = by_mode.get("light", {})
            dark = by_mode.get("dark", {})
            self.lightTime.setText(light.get("time", ""))
            self.setSchemeValue(self.lightScheme, light.get("scheme", ""))
            self.darkTime.setText(dark.get("time", ""))
            self.setSchemeValue(self.darkScheme, dark.get("scheme", ""))
            timer = by_mode.get("timer", {})
            seconds = int(timer.get("interval_seconds") or 300)
            if seconds % 60 == 0 and seconds >= 60:
                self.timerUnit.setCurrentText("分钟")
                self.timerInterval.setValue(max(1, seconds // 60))
            else:
                self.timerUnit.setCurrentText("秒")
                self.timerInterval.setValue(seconds)
            order = timer.get("order") or ("随机" if timer.get("scheme") == self.backend.RANDOM_SCHEME_VALUE else "顺序")
            self.timerOrder.setCurrentText("随机" if order == "随机" else "顺序")
            names = self.scheme_page.schemeNames()
            selected = timer.get("selected_schemes")
            if not isinstance(selected, list):
                scheme = timer.get("scheme", "")
                if scheme in {self.backend.RANDOM_SCHEME_VALUE, "顺序"}:
                    selected = names
                elif scheme:
                    selected = [scheme]
                else:
                    selected = names
            self.rebuildTimerSchemeGrid(names, [name for name in selected if name in names])
            input_item = by_mode.get("input", {})
            for key, combo in self.inputCombos.items():
                self.setSchemeValue(combo, input_item.get(f"{key}_scheme", ""))
            for day, combo in self.weekCombos.items():
                self.setSchemeValue(combo, week_items.get(day, ""))
            if input_item:
                self.inputSwitch.setChecked(True)
            elif timer.get("scheme") or timer.get("selected_schemes"):
                self.timerSwitch.setChecked(True)
            elif week_items:
                self.weekSwitch.setChecked(True)
            elif light.get("scheme") or dark.get("scheme"):
                self.timeSwitch.setChecked(True)
        except Exception:
            pass
        finally:
            self.loading = False

    def save(self):
        if self.loading:
            return
        try:
            apply_now = self.pendingApply
            self.pendingApply = False
            mode = self.activeMode()
            items = []
            week_items = {}
            if mode == "time":
                for name, time_edit, scheme in [("light", self.lightTime, self.lightScheme), ("dark", self.darkTime, self.darkScheme)]:
                    value = self.currentSchemeValue(scheme)
                    at = time_edit.currentText().strip()
                    if value:
                        self.backend.CursorThemeBuilder.validate_time(None, at)
                        items.append({"mode": name, "time": at, "scheme": value})
            elif mode == "timer":
                selected = self.timerSelectedSchemes()
                if selected:
                    interval = int(self.timerInterval.value()) * (60 if self.timerUnit.currentText() == "分钟" else 1)
                    order = self.timerOrder.currentText().strip() or "顺序"
                    items.append({
                        "mode": "timer",
                        "interval_seconds": interval,
                        "scheme": self.backend.RANDOM_SCHEME_VALUE if order == "随机" else "顺序",
                        "selected_schemes": selected,
                        "order": order,
                    })
            elif mode == "week":
                for day, combo in self.weekCombos.items():
                    value = self.currentSchemeValue(combo)
                    if value:
                        week_items[day] = value
            elif mode == "input":
                item = {"mode": "input"}
                for key, combo in self.inputCombos.items():
                    value = self.currentSchemeValue(combo)
                    if value:
                        item[f"{key}_scheme"] = value
                if len(item) > 1:
                    items.append(item)
            self.backend.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.SCHEDULE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.WEEK_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.WEEK_SCHEDULE_FILE.write_text(json.dumps(week_items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(bool(mode))
            if apply_now and mode == "input":
                input_item = next((item for item in items if item.get("mode") == "input"), {})
                state = self.backend.current_input_state()
                scheme = input_item.get(f"{state}_scheme", "")
                if scheme:
                    picked = self.backend.pick_scheduled_scheme(scheme, "随机", 0)
                    if picked:
                        self.backend.apply_library_scheme(picked)
                        self.scheme_page.schemeBox.setCurrentText(picked)
                        self.scheme_page.loadScheme(picked)
            elif apply_now and mode == "week":
                today = str(datetime.now().weekday())
                scheme = week_items.get(today)
                if scheme == self.backend.RANDOM_SCHEME_VALUE:
                    scheme = self.backend.pick_scheduled_scheme(scheme, "随机", 0)
                if scheme:
                    self.backend.apply_library_scheme(scheme)
                    self.scheme_page.schemeBox.setCurrentText(scheme)
                    self.scheme_page.loadScheme(scheme)
            content = "切换设置已保存"
            if apply_now and mode:
                content = "切换设置已保存并按当前状态应用"
            InfoBar.success(title="已保存", content=content, orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("Fluent 切换设置保存失败", exc)
            InfoBar.error(title="保存失败", content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())


class WeekPage(QWidget):
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    def __init__(self, backend, scheme_page: SchemePage, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.scheme_page = scheme_page
        self.combos: dict[str, ComboBox] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("星期切换"))
        layout.addWidget(CaptionLabel("根据星期自动应用对应方案。留空则当天不切换。"))
        values = ["", "随机方案"] + self.scheme_page.schemeNames()
        for index, day in enumerate(self.weekdays):
            card = CardWidget()
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            row.addWidget(StrongBodyLabel(day))
            row.addStretch(1)
            combo = ComboBox()
            combo.setMinimumWidth(260)
            for value in values:
                combo.addItem(value, self.backend.RANDOM_SCHEME_VALUE if value == "随机方案" else None)
            row.addWidget(combo)
            layout.addWidget(card)
            self.combos[str(index)] = combo
        save = PrimaryPushButton("应用星期切换")
        save.clicked.connect(self.save)
        layout.addWidget(save, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self.load()

    def load(self):
        try:
            _items, week_items = self.backend.load_schedule_state()
            for day, combo in self.combos.items():
                value = week_items.get(day, "")
                combo.setCurrentText("随机方案" if value == self.backend.RANDOM_SCHEME_VALUE else value)
        except Exception:
            pass

    def refreshSchemes(self):
        values = ["", "随机方案"] + self.scheme_page.schemeNames()
        for combo in self.combos.values():
            current = combo.currentText()
            combo.clear()
            for value in values:
                combo.addItem(value, self.backend.RANDOM_SCHEME_VALUE if value == "随机方案" else None)
            if current in values:
                combo.setCurrentText(current)

    def save(self):
        try:
            week_items = {}
            for day, combo in self.combos.items():
                value = str(combo.currentData()) if combo.currentData() else combo.currentText().strip()
                if value:
                    week_items[day] = value
            self.backend.WEEK_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.WEEK_SCHEDULE_FILE.write_text(json.dumps(week_items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(True)
            today = str(__import__("datetime").datetime.now().weekday())
            scheme = week_items.get(today)
            if scheme == self.backend.RANDOM_SCHEME_VALUE:
                scheme = self.backend.pick_scheduled_scheme(scheme, "随机", 0)
            if scheme:
                self.backend.apply_library_scheme(scheme)
                self.scheme_page.schemeBox.setCurrentText(scheme)
                self.scheme_page.loadScheme(scheme)
            InfoBar.success(title="已应用", content="星期切换已保存并开启后台自启动", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("Fluent 星期切换保存失败", exc)
            InfoBar.error(title="保存失败", content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())


class SettingsPage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addWidget(SubtitleLabel("设置"))
        mission = CaptionLabel(self.backend.SOFTWARE_MISSION)
        mission.setTextColor("#64748b", "#94a3b8")
        layout.addWidget(mission)
        version = CaptionLabel(f"版本：{self.backend.APP_VERSION}    当前提交：{self.backend.current_build_commit()}")
        version.setTextColor("#64748b", "#94a3b8")
        layout.addWidget(version)

        self.storage = LineEdit()
        self.storage.setText(str(self.backend.configured_storage_root()))
        storage_card = CardWidget()
        row = QHBoxLayout(storage_card)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(10)
        row.addWidget(StrongBodyLabel("鼠标文件存放位置"))
        row.addWidget(self.storage, 1)
        pick = PushButton("选择")
        pick.clicked.connect(self.pickStorage)
        row.addWidget(pick)
        open_storage = PushButton("打开文件夹")
        open_storage.clicked.connect(self.openStorageFolder)
        row.addWidget(open_storage)
        layout.addWidget(storage_card)

        switch_card = CardWidget()
        switch_layout = QVBoxLayout(switch_card)
        switch_layout.setContentsMargins(16, 14, 16, 14)
        switch_layout.setSpacing(12)
        autostart_row = QHBoxLayout()
        autostart_row.addWidget(StrongBodyLabel("自启动后台"))
        self.autostart = SwitchButton()
        self.autostart.setChecked(self.backend.auto_start_enabled())
        autostart_row.addWidget(self.autostart)
        autostart_row.addStretch(1)
        self.repairStartupButton = PushButton("修复自启动")
        self.repairStartupButton.setIcon(FIF.SYNC)
        autostart_row.addWidget(self.repairStartupButton)
        self.autostartStatus = CaptionLabel("")
        self.autostartStatus.setWordWrap(True)
        self.autostartStatus.setTextColor("#64748b", "#94a3b8")
        hide_row = QHBoxLayout()
        hide_row.addWidget(StrongBodyLabel("隐藏任务栏"))
        self.hideTaskbarIcon = SwitchButton()
        self.hideTaskbarIcon.setChecked(self.backend.hide_taskbar_icon_enabled())
        hide_row.addWidget(self.hideTaskbarIcon)
        hide_row.addStretch(1)
        hide_tip = CaptionLabel("开启后开机只保留后台进程；关闭窗口也不会显示托盘图标。")
        hide_tip.setWordWrap(True)
        hide_tip.setTextColor("#64748b", "#94a3b8")

        assoc_row = QHBoxLayout()
        assoc_row.addWidget(StrongBodyLabel("关联 .cur / .ani 打开方式"))
        self.fileAssociation = SwitchButton()
        self.fileAssociation.setChecked(self.backend.file_association_enabled())
        assoc_row.addWidget(self.fileAssociation)
        assoc_row.addStretch(1)
        assoc_tip = CaptionLabel("开启后双击 .cur / .ani 会进入轻量预览窗口，而不是完整主界面。")
        assoc_tip.setWordWrap(True)
        assoc_tip.setTextColor("#64748b", "#94a3b8")

        english_row = QHBoxLayout()
        english_row.addWidget(StrongBodyLabel("语言：英文"))
        self.englishSwitch = SwitchButton()
        self.englishSwitch.setChecked(self.backend.load_settings().get("english_enabled", "false").lower() == "true")
        english_row.addWidget(self.englishSwitch)
        english_row.addStretch(1)
        switch_layout.addLayout(autostart_row)
        switch_layout.addWidget(self.autostartStatus)
        switch_layout.addLayout(hide_row)
        switch_layout.addWidget(hide_tip)
        switch_layout.addLayout(assoc_row)
        switch_layout.addWidget(assoc_tip)
        switch_layout.addLayout(english_row)

        save = PrimaryPushButton("保存设置")
        save.clicked.connect(self.save)
        tools = QHBoxLayout()
        tools.setSpacing(10)
        self.updateButton = PrimaryPushButton("检测更新")
        self.updateButton.setIcon(FIF.UPDATE)
        self.shortcutButton = PushButton("添加桌面快捷方式")
        self.shortcutButton.setIcon(FIF.LINK)
        for button in [save, self.updateButton, self.shortcutButton]:
            button.setMinimumWidth(120)
            tools.addWidget(button)
        tools.addStretch(1)
        link_row = QHBoxLayout()
        for item in [
            ("GitHub 源地址", self.backend.configured_github_url(), FIF.GITHUB),
        ]:
            text, url, icon = item
            btn = PushButton(text)
            btn.setIcon(icon)
            btn.clicked.connect(lambda _checked=False, u=url: webbrowser.open(u))
            link_row.addWidget(btn)
        link_row.addStretch(1)
        layout.addWidget(switch_card)
        layout.addLayout(tools)
        layout.addLayout(link_row)
        layout.addStretch(1)
        self.updateButton.clicked.connect(self.checkUpdates)
        self.shortcutButton.clicked.connect(self.createDesktopShortcut)
        self.repairStartupButton.clicked.connect(self.repairStartup)
        self.refreshStartupStatus()

    def showEvent(self, event):
        super().showEvent(event)
        self.refreshStartupStatus()

    def pickStorage(self):
        folder = QFileDialog.getExistingDirectory(self, "选择鼠标文件存放位置", self.storage.text())
        if folder:
            self.storage.setText(folder)

    def openStorageFolder(self):
        folder = Path(self.storage.text()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def createDesktopShortcut(self):
        english = ui_english_enabled(self.backend)
        title = tr_text("创建快捷方式", english)
        try:
            path = self.backend.create_desktop_app_shortcut()
            InfoBar.success(title=title, content=f"{tr_text('快捷方式已创建', english)}：{path}", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("创建桌面快捷方式失败", exc)
            InfoBar.error(title=title, content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())

    def refreshStartupStatus(self):
        try:
            self.autostartStatus.setText(tr_text(self.backend.startup_status_text(), ui_english_enabled(self.backend)))
        except Exception as exc:
            self.autostartStatus.setText(f"自启动状态：检测失败（{exc}）")

    def repairStartup(self):
        try:
            self.backend.set_auto_start(True)
            self.autostart.setChecked(True)
            self.refreshStartupStatus()
            InfoBar.success(title="自启动后台", content="已重新写入自启动配置", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("修复自启动失败", exc)
            self.refreshStartupStatus()
            InfoBar.error(title="修复自启动", content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())

    def save(self):
        try:
            self.backend.apply_storage_root(Path(self.storage.text()))
            data = self.backend.load_settings()
            data["storage_root"] = str(Path(self.storage.text()).resolve())
            data["hide_taskbar_icon"] = "1" if self.hideTaskbarIcon.isChecked() else "0"
            data["english_enabled"] = "true" if self.englishSwitch.isChecked() else "false"
            data[self.backend.CURSOR_FILE_ASSOCIATION_KEY] = "1" if self.fileAssociation.isChecked() else "0"
            data.pop("close_tip_enabled", None)
            self.backend.save_settings(data)
            self.backend.apply_cursor_file_association_setting(self.fileAssociation.isChecked())
            self.backend.set_auto_start(self.autostart.isChecked())
            if hasattr(self.window(), "applyLanguage"):
                self.window().applyLanguage()
            if hasattr(self.window(), "syncTrayIconVisibility"):
                self.window().syncTrayIconVisibility()
            self.refreshStartupStatus()
            InfoBar.success(title="已保存", content="设置已应用", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("Fluent 设置保存失败", exc)
            InfoBar.error(title="保存失败", content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())

    def runTask(self, title: str, func, done=None):
        signal = TaskSignal(self)
        signal.finished.connect(lambda value: self.finishTask(title, value, done))
        signal.failed.connect(lambda msg: InfoBar.error(title=title, content=msg, orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5500, parent=self.window()))

        def target():
            try:
                signal.finished.emit(func())
            except Exception as exc:
                self.backend.log_error(title, exc)
                signal.failed.emit(str(exc))

        threading.Thread(target=target, daemon=True).start()

    def finishTask(self, title: str, value, done):
        if done:
            done(value)
        else:
            InfoBar.success(title=title, content="完成", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())

    def checkUpdates(self):
        url = self.backend.configured_github_url()

        def work():
            try:
                release = self.backend.fetch_latest_release(url)
            except RuntimeError as exc:
                if "没有可用的 GitHub Release" in str(exc):
                    commit = self.backend.fetch_latest_github_commit(url)
                    return {"updated": False, "release_missing": True, "commit": commit}
                raise
            tag = str(release.get("tag_name", ""))
            if not self.backend.is_newer_version(tag, self.backend.APP_VERSION):
                return {"updated": False, "tag": tag}
            asset = self.backend.release_asset_for_current_app(release)
            downloaded = self.backend.download_release_asset(asset)
            return {"updated": True, "tag": tag, "path": downloaded}

        def done(info):
            if info.get("release_missing"):
                commit = info.get("commit", {})
                InfoBar.warning(
                    title="检测更新",
                    content=f"仓库暂无 Release，不能自动下载。最新提交：{commit.get('short', '未知')}",
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=6500,
                    parent=self.window(),
                )
                return
            if not info.get("updated"):
                InfoBar.success(title="检测更新", content=f"当前已是最新版本：{info.get('tag') or '未知'}", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=3500, parent=self.window())
                return
            if not self.backend.IS_FROZEN:
                InfoBar.warning(title="检测更新", content=f"已下载：{info['path']}。源码模式不会自动替换。", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self.window())
                return
            self.backend.launch_update_replacer(Path(info["path"]))
            QApplication.quit()

        self.runTask("检测更新", work, done)

    def restoreCursor(self):
        self.runTask("恢复鼠标方案", self.backend.restore_cursor_backup)

    def openErrorLog(self):
        self.backend.ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        self.backend.ERROR_LOG.touch(exist_ok=True)
        subprocess.Popen(["notepad.exe", str(self.backend.ERROR_LOG)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def copyDiagnostics(self):
        text = "\n".join([
            f"程序：{self.backend.APP_NAME}",
            f"版本：{self.backend.APP_VERSION}",
            f"当前提交：{self.backend.current_build_commit()}",
            f"程序目录：{self.backend.APP_DIR}",
            f"数据目录：{self.backend.APP_DATA}",
            f"鼠标文件目录：{self.backend.configured_storage_root()}",
            f"安装包目录：{self.backend.configured_output_root()}",
            f"GitHub：{self.backend.configured_github_url()}",
            f"自启动启用：{self.backend.auto_start_enabled()}",
            f"隐藏任务栏：{self.backend.hide_taskbar_icon_enabled()}",
            f"Run 项：{self.backend.run_auto_start_exists()}",
            f"启动快捷方式：{self.backend.startup_script_path()} / 存在={self.backend.startup_script_path().exists()}",
            f"任务计划：{self.backend.SCHEDULED_TASK_NAME} / 存在={self.backend.scheduled_task_exists()}",
        ])
        QApplication.clipboard().setText(text)
        InfoBar.success(title="已复制", content="诊断信息已复制到剪贴板", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())


class MousePointerFluentWindow(FluentWindow):
    def __init__(self, backend, start_hidden: bool = False):
        super().__init__()
        self.backend = backend
        self.exiting = False
        self.start_hidden = start_hidden
        self.trayIcon: QSystemTrayIcon | None = None
        self.commandSocket = None
        self.commandStop = threading.Event()
        self.lastScheduleKey = ""
        self.lastTimerAt = 0.0
        self.timerScheduleIndex = 0
        self.setWindowTitle(backend.APP_NAME)
        icon_path = backend.resource_path("icon终.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1440, 860)
        self.setMinimumSize(1260, 740)
        setTheme(Theme.LIGHT)
        setThemeColor("#4f8cff")
        app = QApplication.instance()
        if app:
            apply_popup_layer_style(app, force=True)
        try:
            self.setMicaEffectEnabled(True)
        except Exception:
            pass

        self.schemePage = SchemePage(backend, self)
        self.resourcePage = ResourcePage(backend, self.schemePage, self)
        self.switchPage = SwitchPage(backend, self.schemePage, self)
        self.settingsPage = SettingsPage(backend, self)

        self.schemePage.setObjectName("schemePage")
        self.resourcePage.setObjectName("resourcePage")
        self.switchPage.setObjectName("switchPage")
        self.settingsPage.setObjectName("settingsPage")

        english = ui_english_enabled(backend)
        self.addSubInterface(self.schemePage, FIF.BRUSH, tr_text("鼠标方案", english))
        self.addSubInterface(self.resourcePage, FIF.FOLDER, tr_text("资源库", english))
        self.addSubInterface(self.switchPage, FIF.DATE_TIME, tr_text("方案切换", english))
        self.addSubInterface(self.settingsPage, FIF.SETTING, tr_text("设置", english), NavigationItemPosition.BOTTOM)
        self.navigationInterface.setAcrylicEnabled(False)
        self.navigationInterface.setMinimumWidth(188)
        self.navigationInterface.setMaximumWidth(188)
        self.createTrayIcon()
        self.applyLanguage()
        self.scheduleTimer = QTimer(self)
        self.scheduleTimer.timeout.connect(self.checkScheduledSwitch)
        self.scheduleTimer.start(1000)
        self.startupLoaded = False

    def centerOnScreen(self):
        screen = QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        x = max(available.left(), min(frame.left(), available.right() - frame.width() + 1))
        y = max(available.top(), min(frame.top(), available.bottom() - frame.height() + 1))
        self.move(x, y)

    def finishStartupLoad(self):
        if self.startupLoaded:
            return
        self.startupLoaded = True
        self.backend.startup_timing_mark("startup.begin_deferred_load")
        self.schemePage.refreshSchemes()
        self.switchPage.refreshSchemeBoxes()
        self.settingsPage.refreshStartupStatus()
        self.backend.startup_timing_mark("startup.deferred_load_complete")
        self.backend.startup_timing_flush()

    def askDesktopShortcutOnFirstLaunch(self):
        data = self.backend.load_settings()
        if data.get("desktop_shortcut_prompted") == "1":
            return
        shortcut = self.backend.desktop_folder() / f"{self.backend.APP_NAME}.lnk"
        if shortcut.exists():
            data["desktop_shortcut_prompted"] = "1"
            self.backend.save_settings(data)
            return
        english = ui_english_enabled(self.backend)
        title = tr_text("创建快捷方式", english)
        text = f"{tr_text('是否在桌面添加快捷方式？', english)}\n\n{tr_text('后续也可以在设置里添加桌面快捷方式。', english)}"
        result = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        data["desktop_shortcut_prompted"] = "1"
        self.backend.save_settings(data)
        if result != QMessageBox.StandardButton.Yes:
            return
        try:
            path = self.backend.create_desktop_app_shortcut()
            InfoBar.success(title=title, content=f"{tr_text('快捷方式已创建', english)}：{path}", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)
        except Exception as exc:
            self.backend.log_error("创建桌面快捷方式失败", exc)
            InfoBar.error(title=title, content=str(exc), orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=5000, parent=self)

    def applyLanguage(self):
        english = ui_english_enabled(self.backend)
        self.setWindowTitle(tr_text(self.backend.APP_NAME, english))
        apply_widget_language(self, english)
        self.refreshNavigationText(english)
        self.schemePage.updateExtraBox()
        self.schemePage.updateLargePreview(self.schemePage.current_preview)
        self.settingsPage.refreshStartupStatus()
        self.schemePage.updateRuntimeInfo()
        self.refreshTrayMenu()

    def refreshNavigationText(self, english: bool):
        for route_key, text in [
            ("schemePage", "鼠标方案"),
            ("resourcePage", "资源库"),
            ("switchPage", "方案切换"),
            ("settingsPage", "设置"),
        ]:
            try:
                item = self.navigationInterface.widget(route_key)
                if item:
                    item.setText(tr_text(text, english))
            except Exception:
                pass

    def syncTrayIconVisibility(self):
        if not self.trayIcon:
            return
        if self.backend.hide_taskbar_icon_enabled():
            self.trayIcon.hide()
        else:
            self.trayIcon.show()

    def refreshRuntimeStatus(self):
        self.refreshTrayMenu()

    def applyScheduledScheme(self, scheme: str, *, last_key: str | None = None, timer_applied: bool = False):
        if not scheme:
            return
        self.backend.apply_library_scheme(scheme)
        self.schemePage.schemeBox.setCurrentText(scheme)
        self.schemePage.loadScheme(scheme)
        self.refreshRuntimeStatus()

    def createTrayIcon(self):
        icon = self.windowIcon()
        self.trayIcon = QSystemTrayIcon(icon, self)
        self.refreshTrayMenu()
        self.trayIcon.activated.connect(self.onTrayActivated)
        if not self.backend.hide_taskbar_icon_enabled():
            self.trayIcon.show()

    def refreshTrayMenu(self):
        if not self.trayIcon:
            return
        english = ui_english_enabled(self.backend)
        menu = style_popup_menu(QMenu())
        open_action = menu.addAction("打开")
        open_action.triggered.connect(self.openFromTray)
        menu.addSeparator()
        current_action = menu.addAction(f"当前配置：{self.backend.configured_current_scheme()}")
        current_action.setEnabled(False)
        next_text = self.backend.next_switch_text(*self.backend.load_schedule_state())
        next_action = menu.addAction(f"下次切换：{next_text}")
        next_action.setEnabled(False)
        menu.addSeparator()
        hide_action = menu.addAction("隐藏任务栏")
        hide_action.triggered.connect(self.hideTrayIconNow)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.exitFromTray)
        for action in menu.actions():
            action.setText(tr_text(action.text(), english))
        self.trayIcon.setContextMenu(menu)

    def onTrayActivated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.openFromTray()

    def openFromTray(self):
        self.centerOnScreen()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def startCommandServer(self, bridge: GuiCommandBridge):
        token = os.urandom(16).hex()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(5)
        listener.settimeout(0.5)
        self.commandSocket = listener
        self.commandStop.clear()
        self.backend.write_gui_command_state(listener.getsockname()[1], token)

        def loop():
            while not self.commandStop.is_set():
                try:
                    conn, _addr = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    try:
                        payload = json.loads(conn.recv(2048).decode("utf-8", "ignore"))
                    except Exception:
                        continue
                    if payload.get("token") == token and payload.get("command") == "show":
                        bridge.showRequested.emit()

        threading.Thread(target=loop, daemon=True).start()

    def stopCommandServer(self):
        self.commandStop.set()
        if self.commandSocket:
            try:
                self.commandSocket.close()
            except OSError:
                pass
            self.commandSocket = None
        self.backend.clear_gui_command_state()

    def hideTrayIconNow(self):
        self.backend.set_setting_enabled("hide_taskbar_icon", True)
        if self.trayIcon:
            self.trayIcon.hide()
        self.hide()

    def exitFromTray(self):
        self.exiting = True
        if self.trayIcon:
            self.trayIcon.hide()
        QApplication.quit()

    def checkScheduledSwitch(self):
        if not (self.settingsPage.autostart.isChecked() or self.backend.auto_start_enabled()):
            return
        try:
            schedule_items, week_items = self.backend.load_schedule_state()
            now = datetime.now()
            has_fast_mode = any(item.get("mode") in {"input", "timer"} for item in schedule_items)
            target_interval = 250 if any(item.get("mode") == "input" for item in schedule_items) else 1000 if has_fast_mode else 10000
            if self.scheduleTimer.interval() != target_interval:
                self.scheduleTimer.setInterval(target_interval)
            for item in schedule_items:
                if item.get("mode") == "input":
                    state = self.backend.current_input_state()
                    scheme = item.get(f"{state}_scheme", "")
                    key = f"input|{state}|{scheme}"
                    if scheme and key != self.lastScheduleKey:
                        picked = self.backend.pick_scheduled_scheme(scheme, "随机", 0)
                        if picked:
                            self.applyScheduledScheme(picked, last_key=key)
                        self.lastScheduleKey = key
                    continue
                if item.get("mode") == "timer":
                    interval = max(1, int(item.get("interval_seconds") or 0))
                    if __import__("time").time() - self.lastTimerAt >= interval:
                        scheme = self.backend.pick_scheduled_scheme(item.get("scheme", ""), item.get("order", "顺序"), self.timerScheduleIndex, item.get("selected_schemes"))
                        self.timerScheduleIndex += 1
                        self.lastTimerAt = __import__("time").time()
                        if scheme:
                            self.applyScheduledScheme(scheme, timer_applied=True)
                    continue
                scheme = item.get("scheme", "")
                key = f"{now:%Y-%m-%d}|{item.get('time')}|{scheme}"
                if scheme and item.get("time") == now.strftime("%H:%M") and key != self.lastScheduleKey:
                    picked = self.backend.pick_scheduled_scheme(scheme, item.get("order", "顺序"), 0)
                    if picked:
                        self.applyScheduledScheme(picked, last_key=key)
                    self.lastScheduleKey = key
                    return
            scheme = week_items.get(str(now.weekday()))
            key = f"{now:%Y-%m-%d}|week|{scheme}"
            if scheme and key != self.lastScheduleKey:
                picked = self.backend.pick_scheduled_scheme(scheme, "随机", 0) if scheme == self.backend.RANDOM_SCHEME_VALUE else scheme
                if picked:
                    self.applyScheduledScheme(picked, last_key=key)
                self.lastScheduleKey = key
        except Exception as exc:
            self.backend.log_error("Fluent 后台切换失败", exc)

    def closeEvent(self, event):
        if self.exiting:
            event.accept()
            return
        try:
            if self.settingsPage.autostart.isChecked() or self.backend.auto_start_enabled():
                self.backend.set_auto_start(True)
            if self.backend.hide_taskbar_icon_enabled():
                self.backend.start_background_process()
            else:
                self.backend.start_tray_process()
            if self.trayIcon:
                self.trayIcon.hide()
            self.exiting = True
            event.accept()
            QTimer.singleShot(0, QApplication.quit)
            return
        except Exception as exc:
            self.backend.log_error("Fluent 保留后台失败", exc)
        self.exiting = True
        event.accept()
        QTimer.singleShot(0, QApplication.quit)


class LightweightTrayApp(QObject):
    def __init__(self, backend, lock_fd, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.lock_fd = lock_fd
        self.lastScheduleKey = ""
        self.lastTimerAt = 0.0
        self.timerScheduleIndex = 0
        self.exiting = False
        icon_path = backend.resource_path("icon终.png")
        icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self.trayIcon = QSystemTrayIcon(icon, self)
        self.refreshMenu()
        self.trayIcon.activated.connect(self.onActivated)
        self.trayIcon.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkScheduledSwitch)
        self.timer.start(1000)

    def refreshMenu(self):
        english = ui_english_enabled(self.backend)
        menu = style_popup_menu(QMenu())
        open_action = menu.addAction("打开")
        open_action.triggered.connect(self.openMainWindow)
        menu.addSeparator()
        current_action = menu.addAction(f"当前配置：{self.backend.configured_current_scheme()}")
        current_action.setEnabled(False)
        next_text = self.backend.next_switch_text(*self.backend.load_schedule_state())
        next_action = menu.addAction(f"下次切换：{next_text}")
        next_action.setEnabled(False)
        menu.addSeparator()
        hide_action = menu.addAction("隐藏任务栏")
        hide_action.triggered.connect(self.hideTrayAndKeepBackground)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.quitTray)
        for action in menu.actions():
            action.setText(tr_text(action.text(), english))
        self.trayIcon.setContextMenu(menu)

    def onActivated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.openMainWindow()

    def openMainWindow(self):
        if self.exiting:
            return
        self.exiting = True
        self.backend.start_detached_process(self.backend.gui_command())
        self.cleanup()
        QApplication.quit()

    def hideTrayAndKeepBackground(self):
        self.backend.set_setting_enabled("hide_taskbar_icon", True)
        self.backend.start_background_process()
        self.quitTray()

    def quitTray(self):
        self.exiting = True
        self.cleanup()
        QApplication.quit()

    def cleanup(self):
        if self.trayIcon:
            self.trayIcon.hide()
        try:
            os.close(self.lock_fd)
        except Exception:
            pass
        self.backend.remove_pid_file(self.backend.APP_DATA / "tray.pid")

    def checkScheduledSwitch(self):
        try:
            schedule_items, week_items = self.backend.load_schedule_state()
            now = datetime.now()
            has_fast_mode = any(item.get("mode") in {"input", "timer"} for item in schedule_items)
            target_interval = 250 if any(item.get("mode") == "input" for item in schedule_items) else 1000 if has_fast_mode else 10000
            if self.timer.interval() != target_interval:
                self.timer.setInterval(target_interval)
            for item in schedule_items:
                if item.get("mode") == "input":
                    state = self.backend.current_input_state()
                    scheme = item.get(f"{state}_scheme", "")
                    key = f"input|{state}|{scheme}"
                    if scheme and key != self.lastScheduleKey:
                        picked = self.backend.pick_scheduled_scheme(scheme, "随机", 0)
                        if picked:
                            self.backend.apply_library_scheme(picked)
                            self.refreshMenu()
                        self.lastScheduleKey = key
                    continue
                if item.get("mode") == "timer":
                    interval = max(1, int(item.get("interval_seconds") or 0))
                    if time.time() - self.lastTimerAt >= interval:
                        scheme = self.backend.pick_scheduled_scheme(item.get("scheme", ""), item.get("order", "顺序"), self.timerScheduleIndex, item.get("selected_schemes"))
                        self.timerScheduleIndex += 1
                        self.lastTimerAt = time.time()
                        if scheme:
                            self.backend.apply_library_scheme(scheme)
                            self.refreshMenu()
                    continue
                scheme = item.get("scheme", "")
                key = f"{now:%Y-%m-%d}|{item.get('time')}|{scheme}"
                if scheme and item.get("time") == now.strftime("%H:%M") and key != self.lastScheduleKey:
                    picked = self.backend.pick_scheduled_scheme(scheme, item.get("order", "顺序"), 0)
                    if picked:
                        self.backend.apply_library_scheme(picked)
                        self.refreshMenu()
                    self.lastScheduleKey = key
                    return
            scheme = week_items.get(str(now.weekday()))
            key = f"{now:%Y-%m-%d}|week|{scheme}"
            if scheme and key != self.lastScheduleKey:
                picked = self.backend.pick_scheduled_scheme(scheme, "随机", 0) if scheme == self.backend.RANDOM_SCHEME_VALUE else scheme
                if picked:
                    self.backend.apply_library_scheme(picked)
                    self.refreshMenu()
                self.lastScheduleKey = key
        except Exception as exc:
            self.backend.log_error("Fluent 轻量托盘切换失败", exc)


def run_tray_app(backend) -> None:
    lock = backend.acquire_tray_lock()
    if lock is None:
        return
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    apply_popup_layer_style(app)
    app.setQuitOnLastWindowClosed(False)
    tray = LightweightTrayApp(backend, lock)
    app.aboutToQuit.connect(tray.cleanup)
    app.exec()


def run_cursor_preview_app(backend, path: Path) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    apply_popup_layer_style(app)
    backend.startup_timing_mark("startup.preview_qt_ready")
    window = CursorPreviewWindow(backend, path)
    window.show()
    backend.startup_timing_mark("startup.preview_first_window_visible")
    backend.startup_timing_flush()
    app.exec()


def run_app(backend, start_hidden: bool = False) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    backend.startup_timing_mark("startup.qt_ready")
    app = QApplication.instance() or QApplication(sys.argv)
    apply_popup_layer_style(app)
    app.setQuitOnLastWindowClosed(False)
    lock = backend.acquire_gui_lock()
    if lock is None:
        backend.notify_existing_gui("show")
        return
    window = MousePointerFluentWindow(backend, start_hidden=start_hidden)
    backend.startup_timing_mark("startup.build_ui")
    bridge = GuiCommandBridge()
    window.commandBridge = bridge
    bridge.showRequested.connect(window.openFromTray)
    window.startCommandServer(bridge)

    def cleanup():
        window.stopCommandServer()
        try:
            os.close(lock)
        except OSError:
            pass
        backend.remove_pid_file(backend.APP_DATA / "gui.pid")

    app.aboutToQuit.connect(cleanup)
    if start_hidden:
        if window.trayIcon and not backend.hide_taskbar_icon_enabled():
            window.trayIcon.show()
            window.trayIcon.showMessage(backend.APP_NAME, "已在后台运行。", QSystemTrayIcon.Information, 1800)
    else:
        window.centerOnScreen()
        window.show()
        backend.startup_timing_mark("startup.first_window_visible")
        backend.startup_timing_flush()
        QTimer.singleShot(0, window.finishStartupLoad)
        QTimer.singleShot(600, window.askDesktopShortcutOnFirstLaunch)
    app.exec()
