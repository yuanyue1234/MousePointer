from __future__ import annotations

import hashlib
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


PREVIEW_QSS = """
QWidget {
    background: #f8fafc;
    color: #0f172a;
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 13px;
}
QLabel#previewCanvas {
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-radius: 12px;
}
QLabel#kindChip {
    background: #eef6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#mutedText {
    color: #64748b;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 8px;
    padding: 7px 12px;
}
QPushButton:hover {
    background: #f1f7ff;
    border-color: #93c5fd;
}
QPushButton#primaryButton {
    background: #2563eb;
    border-color: #2563eb;
    color: white;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #1d4ed8;
}
QMenu, QListView {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 8px;
    padding: 4px;
    color: #0f172a;
    selection-background-color: #eef6ff;
    selection-color: #0f172a;
}
"""


def cursor_kind(path: Path | None) -> str:
    if not path:
        return ""
    suffix = path.suffix.lower()
    if suffix == ".ani":
        return "动"
    if suffix == ".cur":
        return "静"
    return ""


def pixmap_from_image(image, target_size: int | None = None) -> QPixmap:
    pixmap = QPixmap.fromImage(ImageQt(image.convert("RGBA")))
    if target_size:
        return pixmap.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pixmap


def file_cache_key(path: Path, size: int) -> str:
    stat = path.stat()
    payload = f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{size}".encode("utf-8", "ignore")
    return hashlib.sha1(payload).hexdigest()


@dataclass
class PreviewResult:
    frames: list[object]
    message: str
    failed: bool = False


class PreviewSignal(QObject):
    loaded = Signal(object)


class CursorPreviewWindow(QWidget):
    def __init__(self, backend, path: Path):
        super().__init__()
        self.backend = backend
        self.path = path
        self.frames: list[QPixmap] = []
        self.frameIndex = 0
        self.signal = PreviewSignal(self)
        self.signal.loaded.connect(self.finishLoad)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.nextFrame)
        self.setWindowTitle(f"{backend.APP_NAME} - 光标预览")
        self.setMinimumSize(520, 420)
        icon_path = backend.resource_path("icon终.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self.title = QLabel(path.name if path and path.name else "未选择文件")
        self.title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.subtitle = QLabel(str(path) if path else "")
        self.subtitle.setObjectName("mutedText")
        self.subtitle.setWordWrap(True)
        self.kind = QLabel("")
        self.kind.setObjectName("kindChip")
        self.kind.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.preview = QLabel("正在加载预览...")
        self.preview.setObjectName("previewCanvas")
        self.preview.setFixedHeight(220)
        self.preview.setAlignment(Qt.AlignCenter)
        self.message = QLabel("轻量预览窗口会先显示首帧，再补齐动画帧。")
        self.message.setObjectName("mutedText")
        self.message.setWordWrap(True)

        actions = QHBoxLayout()
        open_main = QPushButton("打开完整软件")
        open_main.setObjectName("primaryButton")
        open_main.clicked.connect(self.openMainApp)
        open_folder = QPushButton("打开位置")
        open_folder.clicked.connect(self.openFolder)
        copy_path = QPushButton("复制路径")
        copy_path.clicked.connect(lambda: QApplication.clipboard().setText(str(path)))
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        actions.addWidget(open_main)
        actions.addWidget(open_folder)
        actions.addWidget(copy_path)
        actions.addStretch(1)
        actions.addWidget(close_button)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.kind)
        layout.addWidget(self.preview)
        layout.addWidget(self.message)
        layout.addLayout(actions)
        self.prepareMetadata()
        QTimer.singleShot(0, self.loadPreviewAsync)

    def prepareMetadata(self) -> None:
        path = self.path
        if not path or not path.exists():
            self.kind.setText("文件不存在")
            return
        kind = cursor_kind(path)
        parts = [path.suffix.lower() or "未知格式"]
        if kind:
            parts.append("动画指针" if kind == "动" else "静态指针")
        try:
            parts.append(f"{path.stat().st_size / 1024:.1f} KB")
        except OSError:
            pass
        self.kind.setText("  ".join(parts))

    def openMainApp(self) -> None:
        command = [str(Path(sys.executable).resolve())]
        if not self.backend.IS_FROZEN:
            command.append(str(self.backend.APP_DIR / "main.py"))
        self.backend.start_detached_process(command)

    def openFolder(self) -> None:
        if self.path and self.path.exists():
            subprocess.Popen(["explorer.exe", "/select,", str(self.path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def loadPreviewAsync(self) -> None:
        threading.Thread(target=self.loadPreview, daemon=True).start()

    def loadPreview(self) -> None:
        path = self.path
        if not path or not path.exists():
            self.signal.loaded.emit(PreviewResult([], "指定的鼠标文件不存在，无法预览。", True))
            return
        try:
            frames = self.previewFrames(path)
            if not frames:
                raise RuntimeError("没有生成可用预览。")
            message = "预览已就绪。"
            if len(frames) > 1:
                message = "动画预览已就绪，已限制帧数以保持启动速度。"
            self.signal.loaded.emit(PreviewResult(frames, message, False))
        except Exception as exc:
            try:
                self.backend.log_error("光标轻量预览失败", exc)
            except Exception:
                pass
            fallback = self.fallbackImage(path)
            self.signal.loaded.emit(PreviewResult([fallback], f"无法完整预览该文件：{exc}", True))

    def previewFrames(self, path: Path) -> list[object]:
        if path.suffix.lower() == ".ani":
            frame_paths = self.backend.ani_frame_paths(path)[:12]
            if frame_paths:
                return [self.previewImage(frame, 200) for frame in frame_paths]
        return [self.previewImage(path, 200)]

    def previewImage(self, path: Path, size: int):
        cache_root = self.backend.WORK_ROOT / "preview_cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_path = cache_root / f"{file_cache_key(path, size)}.png"
        if cache_path.exists():
            try:
                return self.backend.Image.open(cache_path).convert("RGBA")
            except Exception:
                pass
        image = self.backend.cursor_preview_image_sized(path, (size, size), 128).convert("RGBA")
        try:
            image.save(cache_path)
        except Exception:
            pass
        return image

    def fallbackImage(self, path: Path):
        image = self.backend.Image.new("RGBA", (200, 200), (248, 251, 255, 255))
        draw = self.backend.ImageDraw.Draw(image)
        text = path.suffix.lower() or "?"
        draw.rounded_rectangle((24, 52, 176, 148), radius=18, outline=(147, 197, 253, 255), width=2, fill=(239, 246, 255, 255))
        draw.text((78, 86), text, fill=(30, 64, 175, 255))
        return image

    def finishLoad(self, result: PreviewResult) -> None:
        self.frames = [pixmap_from_image(image, 200) for image in result.frames]
        self.frameIndex = 0
        if self.frames:
            self.preview.setPixmap(self.frames[0])
        else:
            self.preview.setText("预览不可用")
        self.message.setText(result.message)
        if len(self.frames) > 1 and not result.failed:
            self.timer.start(100)

    def nextFrame(self) -> None:
        if not self.frames:
            return
        self.preview.setPixmap(self.frames[self.frameIndex % len(self.frames)])
        self.frameIndex += 1


def run_cursor_preview_app(backend, path: Path) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet((app.styleSheet() or "") + PREVIEW_QSS)
    backend.startup_timing_mark("startup.preview_qt_ready")
    window = CursorPreviewWindow(backend, path)
    window.show()
    backend.startup_timing_mark("startup.preview_first_window_visible")
    backend.startup_timing_flush()
    app.exec()
