from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPoint, Qt, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QMessageBox,
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
    Slider,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    Theme,
    ToggleButton,
    setTheme,
    setThemeColor,
)


class TaskSignal(QObject):
    finished = Signal(object)
    failed = Signal(str)


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


def role_icon_path(backend, role) -> Path:
    return backend.resource_path(f"assets/role_icons/{role.file_stem}.png")


EXTRA_RESOURCE_EXTS = {".cur", ".ani", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"}


def pixmap_from_image(image: Image.Image, target_size: int | None = None) -> QPixmap:
    qimage = ImageQt(image.convert("RGBA"))
    pixmap = QPixmap.fromImage(qimage)
    if target_size:
        return pixmap.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pixmap


class CursorPreview(QLabel):
    def __init__(self, size: int = 46, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border-radius: 8px; background: #f8fbff;")

    def setPath(self, backend, path: Path | None, size: int = 42, role=None) -> None:
        if not path or not path.exists():
            self.setRoleIcon(backend, role, size)
            return
        try:
            image = backend.cursor_preview_image_sized(path, (size * 3, size * 3), min(size * 2, 128)).convert("RGBA")
            pixmap = pixmap_from_image(image)
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.setText("...")

    def setRoleIcon(self, backend, role, size: int = 42) -> None:
        if not role:
            self.clear()
            return
        icon = role_icon_path(backend, role)
        if not icon.exists():
            self.clear()
            return
        try:
            pixmap = QPixmap(str(icon))
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.clear()


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


class CursorRow(QWidget):
    hovered = Signal(str)
    picked = Signal(str)

    def __init__(self, backend, role, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.role = role
        self.path: Path | None = None
        self.setMinimumHeight(70)
        self.setObjectName("cursorRow")
        self.setStyleSheet("#cursorRow { background: #ffffff; border: none; border-radius: 8px; } #cursorRow:hover { background: #f6fbff; }")

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(12)
        layout.setColumnStretch(2, 1)

        self.preview = CursorPreview(48)
        self.name = StrongBodyLabel(role.label)
        self.tip = CaptionLabel(role.tip)
        self.tip.setTextColor("#64748b", "#94a3b8")
        self.file = BodyLabel("未选择")
        self.file.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.file.setMinimumWidth(80)
        self.file.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.pickButton = PushButton("选择")
        self.pickButton.setIcon(FIF.FOLDER)
        self.pickButton.setFixedWidth(84)
        self.pickButton.clicked.connect(lambda: self.picked.emit(self.role.reg_name))

        text_box = QWidget()
        text_layout = QVBoxLayout(text_box)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.name)
        text_layout.addWidget(self.tip)

        layout.addWidget(self.preview, 0, 0, 2, 1)
        layout.addWidget(text_box, 0, 1, 2, 1)
        layout.addWidget(self.file, 0, 2, 2, 1)
        layout.addWidget(self.pickButton, 0, 3, 2, 1)

    def enterEvent(self, event) -> None:
        self.hovered.emit(self.role.reg_name)
        super().enterEvent(event)

    def setPath(self, path: Path | None) -> None:
        self.path = path
        if path:
            self.file.setText(path.name)
            self.file.setToolTip(str(path))
        else:
            self.file.setText("未选择")
            self.file.setToolTip("")
        self.preview.setPath(self.backend, path, role=self.role)


class ExtraResourceItem(QWidget):
    def __init__(self, backend, path: Path, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 58)
        self.setToolTip(path.name)
        self.setObjectName("extraResourceItem")
        self.setStyleSheet("#extraResourceItem { background: #ffffff; border: none; border-radius: 8px; } #extraResourceItem:hover { background: #eef7ff; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        preview = CursorPreview(48)
        preview.setPath(backend, path, 42)
        layout.addWidget(preview, alignment=Qt.AlignCenter)


class SchemePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.rows: dict[str, CursorRow] = {}
        self.selected: dict[str, Path] = {}
        self.extraFiles: list[Path] = []
        self.current_preview = "Arrow"
        self.sizeLevel = 3
        self.animationFrames: list[QPixmap] = []
        self.animationIndex = 0
        self.animationTimer = QTimer(self)
        self.animationTimer.timeout.connect(self.nextAnimationFrame)

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
        self.saveButton = PushButton("保存")
        self.saveButton.setIcon(FIF.SAVE)
        for button in [self.newButton, self.renameButton, self.deleteButton, self.importButton, self.importFolderButton, self.saveButton]:
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
        self.rowLayout = QVBoxLayout(self.rowWidget)
        self.rowLayout.setContentsMargins(2, 2, 8, 2)
        self.rowLayout.setSpacing(8)
        for role in self.backend.CURSOR_ROLES:
            row = CursorRow(backend, role)
            row.hovered.connect(self.updateLargePreview)
            row.picked.connect(self.pickFileForRole)
            self.rows[role.reg_name] = row
            self.rowLayout.addWidget(row)
        self.rowLayout.addStretch(1)
        self.scroll.setWidget(self.rowWidget)
        left_layout.addWidget(self.scroll, 1)

        self.extraBox = QWidget()
        self.extraBox.setObjectName("extraBox")
        self.extraBox.setMinimumHeight(170)
        self.extraBox.setMaximumHeight(210)
        self.extraBox.setStyleSheet("#extraBox { background: rgba(255, 255, 255, 0.82); border: none; border-radius: 8px; }")
        extra_layout = QVBoxLayout(self.extraBox)
        extra_layout.setContentsMargins(12, 10, 12, 10)
        extra_layout.setSpacing(8)
        extra_header = QHBoxLayout()
        self.extraTitle = StrongBodyLabel("资源盒子")
        self.extraAddButton = PushButton("添加资源")
        self.extraAddButton.setIcon(FIF.ADD)
        self.extraAddButton.setFixedWidth(102)
        extra_header.addWidget(self.extraTitle)
        extra_header.addStretch(1)
        extra_header.addWidget(self.extraAddButton)
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
        size_row.addWidget(BodyLabel("预览大小"))
        self.sizeText = CaptionLabel("3 / 64px")
        self.sizeText.setTextColor("#64748b", "#94a3b8")
        size_row.addStretch(1)
        size_row.addWidget(self.sizeText)
        right_layout.addLayout(size_row)
        self.sizeSlider = Slider(Qt.Horizontal)
        self.sizeSlider.setRange(1, 15)
        self.sizeSlider.setValue(3)
        self.sizeSlider.valueChanged.connect(self.onSizeChanged)
        right_layout.addWidget(self.sizeSlider)
        self.sizeTip = CaptionLabel("推荐范围：2-7，仅用于预览判断，不会写入系统或安装包")
        self.sizeTip.setWordWrap(True)
        self.sizeTip.setTextColor("#64748b", "#ef4444")
        right_layout.addWidget(self.sizeTip)

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
        self.status = CaptionLabel("更改鼠标至对应大小后应用方案")
        self.status.setWordWrap(True)
        self.status.setTextColor("#64748b", "#94a3b8")
        right_layout.addWidget(self.status)

        root.addWidget(left, 1)
        root.addWidget(right, 0)

        self.importButton.clicked.connect(self.importPackage)
        self.importFolderButton.clicked.connect(self.importFolder)
        self.saveButton.clicked.connect(self.saveScheme)
        self.newButton.clicked.connect(self.newScheme)
        self.deleteButton.clicked.connect(self.deleteScheme)
        self.renameButton.clicked.connect(self.renameScheme)
        self.applyButton.clicked.connect(self.applyScheme)
        self.buildButton.clicked.connect(self.buildInstaller)
        self.restoreButton.clicked.connect(self.restoreCursor)
        self.sizeSettingsButton.clicked.connect(self.openPointerSettings)
        self.extraAddButton.clicked.connect(self.importExtraResources)
        self.refreshSchemes()

    def openPointerSettings(self):
        try:
            os.startfile("ms-settings:easeofaccess-mousepointer")
        except Exception:
            os.startfile("control.exe")

    def schemeNames(self) -> list[str]:
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
        return sorted(names, key=lambda name: self.backend.scheme_order_value(root / name))

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

    def clearSelection(self):
        self.selected.clear()
        self.extraFiles = []
        for row in self.rows.values():
            row.setPath(None)
        self.updateLargePreview("Arrow")
        self.updateExtraBox()

    def loadScheme(self, name: str):
        if not name:
            return
        try:
            scheme_dir, files = self.backend.scheme_manifest(name)
            _manifest_dir, manifest = self.readManifest(name)
            self.selected = {reg: scheme_dir / file_name for reg, file_name in files.items() if (scheme_dir / file_name).exists()}
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
        except Exception as exc:
            self.showError("载入失败", exc)

    def clearGrid(self, layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def updateExtraBox(self) -> None:
        name = self.schemeBox.currentText().strip()
        self.extraTitle.setText(f"资源盒子[{name}]" if name else "资源盒子")
        self.clearGrid(self.extraGrid)
        if not self.extraFiles:
            empty = CaptionLabel("无文件")
            empty.setTextColor("#64748b", "#94a3b8")
            self.extraGrid.addWidget(empty, 0, 0)
            return
        for index, path in enumerate(self.extraFiles):
            row = index // 3
            col = index % 3
            self.extraGrid.addWidget(ExtraResourceItem(self.backend, path), row, col)
        self.extraGrid.setRowStretch(max(3, (len(self.extraFiles) + 2) // 3), 1)

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

    def persistExtraFiles(self) -> None:
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
        self.updateExtraBox()

    def importExtraResources(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "添加可替换指针资源",
            str(self.backend.configured_storage_root()),
            "可替换资源 (*.cur *.ani *.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico);;所有文件 (*.*)",
        )
        if not files:
            return
        self.extraFiles.extend([Path(file) for file in files if Path(file).suffix.lower() in EXTRA_RESOURCE_EXTS])
        self.persistExtraFiles()
        self.updateExtraBox()

    def updateLargePreview(self, reg_name: str):
        self.current_preview = reg_name
        self.animationTimer.stop()
        self.animationFrames = []
        self.animationIndex = 0
        role = self.backend.ROLE_BY_REG.get(reg_name)
        path = self.selected.get(reg_name)
        if role:
            self.previewName.setText(role.label)
        self.previewFile.setText(str(path) if path else "未选择")
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
        image = None
        if path.suffix.lower() in {".cur", ".ani"}:
            image = self.backend.render_cursor_with_windows(path, cursor_size)
        if image is None:
            image = self.backend.centered_rgba(self.backend.image_from_path(path), cursor_size)
        return pixmap_from_image(image)

    def renderRoleIconPixmap(self, role) -> QPixmap:
        if not role:
            return QPixmap()
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
        if 2 <= self.sizeLevel <= 7:
            self.sizeTip.setText("推荐范围：2-7，仅用于预览判断，不会写入系统或安装包")
            self.sizeTip.setTextColor("#64748b", "#94a3b8")
        else:
            self.sizeTip.setText("推荐范围：2-7，当前大小可能过大或过小")
            self.sizeTip.setTextColor("#ef4444", "#ef4444")
        self.updateLargePreview(self.current_preview)

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

    def handleDropped(self, paths: list[Path]):
        packages = [p for p in paths if p.is_dir() or p.suffix.lower() in {".zip", ".rar", ".7z", ".exe"}]
        if packages:
            for package in packages:
                self.importPackagePath(package)
            self.refreshSchemes()
            return
        files = [p for p in paths if p.suffix.lower() in {".cur", ".ani", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"}]
        for path in files:
            self.selected[self.current_preview] = path
            self.rows[self.current_preview].setPath(path)
        self.updateLargePreview(self.current_preview)

    def importPackage(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "导入安装包、压缩包或光标文件",
            str(self.backend.configured_storage_root()),
            "资源包和光标 (*.zip *.rar *.7z *.exe *.cur *.ani);;所有文件 (*.*)",
        )
        for file_name in files:
            path = Path(file_name)
            if path.suffix.lower() in {".cur", ".ani"}:
                self.selected[self.current_preview] = path
                self.rows[self.current_preview].setPath(path)
            else:
                self.importPackagePath(path)
        if files:
            self.refreshSchemes()

    def importFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "导入鼠标指针文件夹", str(self.backend.configured_storage_root()))
        if folder:
            self.importPackagePath(Path(folder))
            self.refreshSchemes()

    def importPackagePath(self, package: Path) -> list[str]:
        imported = []
        try:
            extracted = self.backend.extract_import_package(package)
            roots = self.detectSchemeRoots(extracted)
            if len(roots) > 1:
                self.showInfo("批量导入", f"识别到 {len(roots)} 份鼠标指针，正在批量添加。")
            for root in roots:
                name = package.stem if len(roots) == 1 else root.name
                imported.append(self.importRootAsScheme(root, name))
            return imported
        except Exception as exc:
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

    def extraResourcesFromRoot(self, root: Path, mapping: dict[str, Path]) -> list[Path]:
        mapped = {path.resolve() for path in mapping.values() if path.exists()}
        extras = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTRA_RESOURCE_EXTS:
                continue
            try:
                if path.resolve() in mapped:
                    continue
            except Exception:
                pass
            extras.append(path)
        return extras

    def importRootAsScheme(self, root: Path, raw_name: str) -> str:
        try:
            name = self.backend.sanitize_name(raw_name)
            if name in self.backend.DEFAULT_SCHEME_NAMES:
                name = f"{name}_资源"
            scheme_dir = self.backend.SCHEME_LIBRARY / name
            if (scheme_dir / "scheme.json").exists():
                result = QMessageBox.question(self, "发现重复方案", f"{name} 已存在，是否继续导入为新副本？\n选择“否”将跳过该方案。")
                if result != QMessageBox.Yes:
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
            extra_names = self.copyExtraFilesToScheme(scheme_dir, self.extraResourcesFromRoot(root, mapping))
            self.writeManifest(name, files, scheme_dir, extra_names)
            self.showInfo("导入完成", f"已添加：{name}")
            return name
        except Exception as exc:
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
        for reg_name, source in self.selected.items():
            role = self.backend.ROLE_BY_REG[reg_name]
            suffix = source.suffix.lower()
            output_name = f"{role.file_stem}{suffix if suffix in {'.cur', '.ani'} else '.cur'}"
            output = assets_dir / output_name
            self.backend.convert_to_cursor(source, output.with_suffix(".cur") if suffix not in {".cur", ".ani"} else output, role, self.backend.DEFAULT_CURSOR_SIZE)
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

    def writeManifest(self, theme: str, files: dict[str, str], folder: Path, extras: list[str] | None = None):
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {"name": theme, "files": files, "order": self.backend.time.time(), "saved_at": datetime.now().isoformat()}
        if extras:
            manifest["extras"] = extras
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

        def work():
            package_dir = self.backend.WORK_ROOT / "fluent_current_theme"
            files = self.prepareAssets(package_dir)
            target_dir = self.installAssetsToScheme(theme, files, package_dir / "assets")
            self.backend.apply_refreshed_cursor_scheme(theme, {reg: str(target_dir / name) for reg, name in files.items()})
            self.writeManifest(theme, files, target_dir)
            return theme

        self.runTask("正在应用鼠标方案", work, lambda name: self.showInfo("应用完成", f"已应用：{name}"))

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

        def work():
            package_dir = self.backend.WORK_ROOT / "fluent_installer_package"
            package_dir.mkdir(parents=True, exist_ok=True)
            files = self.prepareAssets(package_dir)
            installer_py = package_dir / "install_cursor_theme.py"
            installer_py.write_text(self.backend.installer_source(theme, files), encoding="utf-8")
            exe_name = f"{theme}_鼠标样式安装器"
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
        self.openWeb.clicked.connect(lambda: webbrowser.open(self.backend.RESOURCE_URL))
        self.importButton.clicked.connect(self.importResources)
        self.importFolderButton.clicked.connect(self.importResourceFolder)
        self.refresh.clicked.connect(self.render)
        self.restoreButton.clicked.connect(self.restoreCursor)
        self.gridButton.clicked.connect(self.toggleGrid)
        self.render()

    def toggleGrid(self):
        self.gridMode = self.gridButton.isChecked()
        self.deleted.clear()
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
        if not names:
            self.cards.addWidget(BodyLabel("暂无资源"))
            return
        for index, name in enumerate(names):
            card = QWidget()
            card.setObjectName("resourceCard")
            card.setStyleSheet("#resourceCard { background: #ffffff; border: none; border-radius: 8px; }")
            if self.gridMode:
                card.setMinimumSize(320, 260)
            layout = QVBoxLayout(card) if self.gridMode else QHBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(10)
            text = QVBoxLayout()
            text.addWidget(StrongBodyLabel(name))
            scheme_dir, files = self.backend.scheme_manifest(name)
            text.addWidget(CaptionLabel(f"{len(files)} 个鼠标状态"))
            layout.addLayout(text, 1 if not self.gridMode else 0)
            preview_grid = QGridLayout()
            preview_grid.setHorizontalSpacing(6)
            preview_grid.setVerticalSpacing(6)
            columns = 5 if self.gridMode else 9
            for role_index, role in enumerate(self.backend.CURSOR_ROLES):
                preview = CursorPreview(46 if self.gridMode else 38)
                file_name = files.get(role.reg_name)
                path = scheme_dir / file_name if file_name else None
                preview.setPath(self.backend, path, 44 if self.gridMode else 34, role=role)
                preview.setToolTip(role.label)
                preview_grid.addWidget(preview, role_index // columns, role_index % columns)
            layout.addLayout(preview_grid, 1)
            action_row = QHBoxLayout()
            delete_btn = PushButton("删除")
            delete_btn.setIcon(FIF.DELETE)
            delete_btn.clicked.connect(lambda _checked=False, n=name, b=delete_btn: self.deleteOrRestoreResource(n, b))
            apply_btn = PrimaryPushButton("应用")
            apply_btn.clicked.connect(lambda _checked=False, n=name: self.applyResource(n))
            action_row.addWidget(delete_btn)
            action_row.addWidget(apply_btn)
            if self.gridMode:
                layout.addLayout(action_row)
            else:
                layout.addLayout(action_row)
            if self.gridMode:
                self.cards.addWidget(card, index // 3, index % 3)
            else:
                self.cards.addWidget(card)
        if not self.gridMode:
            self.cards.addStretch(1)

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
        for path in paths:
            imported.extend([name for name in self.scheme_page.importPackagePath(path) if name])
        self.scheme_page.refreshSchemes()
        self.render()
        if imported:
            InfoBar.success(title="资源已添加", content=f"已导入 {len(imported)} 个方案", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self.window())

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
        self.scheme.addItem("随机方案", self.backend.RANDOM_SCHEME_VALUE)
        self.scheme.addItems(self.schemeNames())
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
            self.scheme.setCurrentText("随机方案" if value == self.backend.RANDOM_SCHEME_VALUE else value)
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("方案切换"))
        layout.addWidget(CaptionLabel("时间切换、计时切换、星期切换只能启用一种。"))

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
        timer_layout = QHBoxLayout(self.timerCard)
        timer_layout.setContentsMargins(16, 14, 16, 14)
        timer_layout.addWidget(StrongBodyLabel("计时切换"))
        self.timerSwitch = SwitchButton()
        self.modeSwitches["timer"] = self.timerSwitch
        timer_layout.addWidget(self.timerSwitch)
        timer_layout.addWidget(BodyLabel("每"))
        self.timerInterval = QSpinBox()
        self.timerInterval.setRange(1, 86400)
        self.timerInterval.setValue(5)
        self.timerUnit = ComboBox()
        self.timerUnit.addItems(["秒", "分钟"])
        self.timerScheme = self.createSchemeBox()
        timer_layout.addWidget(self.timerInterval)
        timer_layout.addWidget(self.timerUnit)
        timer_layout.addWidget(self.timerScheme)
        timer_layout.addStretch(1)
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

        layout.addStretch(1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.applyButton = PrimaryPushButton("应用")
        self.applyButton.setIcon(FIF.ACCEPT)
        bottom.addWidget(self.applyButton)
        layout.addLayout(bottom)

        for mode, switch in self.modeSwitches.items():
            switch.checkedChanged.connect(lambda checked, m=mode: self.onModeChanged(m, checked))
        self.applyButton.clicked.connect(self.save)
        self.load()

    def createTimeBox(self) -> EditableComboBox:
        box = EditableComboBox()
        box.setMinimumWidth(180)
        box.addItems([f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)])
        box.setText("")
        return box

    def createSchemeBox(self) -> ComboBox:
        box = ComboBox()
        box.setMinimumWidth(220)
        box.addItem("")
        box.addItem("随机方案", self.backend.RANDOM_SCHEME_VALUE)
        box.addItems(self.scheme_page.schemeNames())
        return box

    def currentSchemeValue(self, combo: ComboBox) -> str:
        data = combo.currentData()
        return str(data) if data else combo.currentText().strip()

    def setSchemeValue(self, combo: ComboBox, value: str):
        combo.setCurrentText("随机方案" if value == self.backend.RANDOM_SCHEME_VALUE else value)

    def onModeChanged(self, mode: str, checked: bool):
        if not checked:
            return
        for key, switch in self.modeSwitches.items():
            if key != mode and switch.isChecked():
                switch.setChecked(False)

    def activeMode(self) -> str:
        for mode, switch in self.modeSwitches.items():
            if switch.isChecked():
                return mode
        return ""

    def load(self):
        try:
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
            self.setSchemeValue(self.timerScheme, timer.get("scheme", ""))
            for day, combo in self.weekCombos.items():
                self.setSchemeValue(combo, week_items.get(day, ""))
            if timer.get("scheme"):
                self.timerSwitch.setChecked(True)
            elif week_items:
                self.weekSwitch.setChecked(True)
            elif light.get("scheme") or dark.get("scheme"):
                self.timeSwitch.setChecked(True)
        except Exception:
            pass

    def save(self):
        try:
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
                value = self.currentSchemeValue(self.timerScheme)
                if value:
                    interval = int(self.timerInterval.value()) * (60 if self.timerUnit.currentText() == "分钟" else 1)
                    items.append({"mode": "timer", "interval_seconds": interval, "scheme": value})
            elif mode == "week":
                for day, combo in self.weekCombos.items():
                    value = self.currentSchemeValue(combo)
                    if value:
                        week_items[day] = value
            self.backend.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.SCHEDULE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.WEEK_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.WEEK_SCHEDULE_FILE.write_text(json.dumps(week_items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(bool(mode))
            if mode == "week":
                today = str(datetime.now().weekday())
                scheme = week_items.get(today)
                if scheme == self.backend.RANDOM_SCHEME_VALUE:
                    scheme = self.backend.pick_scheduled_scheme(scheme, "随机", 0)
                if scheme:
                    self.backend.apply_library_scheme(scheme)
                    self.scheme_page.schemeBox.setCurrentText(scheme)
                    self.scheme_page.loadScheme(scheme)
            InfoBar.success(title="已应用", content="切换设置已保存", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
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
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("设置"))

        self.storage = LineEdit()
        self.storage.setText(str(self.backend.configured_storage_root()))
        storage_card = CardWidget()
        row = QHBoxLayout(storage_card)
        row.setContentsMargins(16, 14, 16, 14)
        row.addWidget(StrongBodyLabel("鼠标文件存放位置"))
        row.addWidget(self.storage, 1)
        pick = PushButton("选择")
        pick.clicked.connect(self.pickStorage)
        row.addWidget(pick)
        open_storage = PushButton("打开文件夹")
        open_storage.clicked.connect(self.openStorageFolder)
        row.addWidget(open_storage)
        layout.addWidget(storage_card)

        autostart_row = QHBoxLayout()
        autostart_row.addWidget(StrongBodyLabel("自启动后台"))
        self.autostart = SwitchButton()
        self.autostart.setChecked(self.backend.auto_start_enabled())
        autostart_row.addWidget(self.autostart)
        autostart_row.addStretch(1)
        hide_row = QHBoxLayout()
        hide_row.addWidget(StrongBodyLabel("隐藏任务栏图标"))
        self.hideTaskbarIcon = SwitchButton()
        self.hideTaskbarIcon.setChecked(self.backend.hide_taskbar_icon_enabled())
        hide_row.addWidget(self.hideTaskbarIcon)
        hide_row.addStretch(1)
        hide_tip = CaptionLabel("开启后开机只保留后台进程；关闭窗口也不会显示托盘图标。")
        hide_tip.setWordWrap(True)
        hide_tip.setTextColor("#64748b", "#94a3b8")
        save = PrimaryPushButton("保存设置")
        save.clicked.connect(self.save)
        tools = QHBoxLayout()
        self.updateButton = PrimaryPushButton("检测更新")
        self.updateButton.setIcon(FIF.UPDATE)
        self.errorButton = PushButton("打开错误记录")
        self.errorButton.setIcon(FIF.DOCUMENT)
        self.copyDiagButton = PushButton("复制诊断信息")
        self.copyDiagButton.setIcon(FIF.COPY)
        for button in [self.updateButton, self.errorButton, self.copyDiagButton]:
            tools.addWidget(button)
        tools.addStretch(1)
        link_row = QHBoxLayout()
        for item in [
            ("像素指针指南文章", self.backend.PIXEL_GUIDE_URL, FIF.LINK),
            ("工具制作 BY ASUNNY", self.backend.ASUNNY_URL, FIF.LINK),
            ("GitHub 源地址", self.backend.configured_github_url(), FIF.GITHUB),
        ]:
            text, url, icon = item
            btn = PushButton(text)
            btn.setIcon(icon)
            btn.clicked.connect(lambda _checked=False, u=url: webbrowser.open(u))
            link_row.addWidget(btn)
        link_row.addStretch(1)
        layout.addLayout(autostart_row)
        layout.addLayout(hide_row)
        layout.addWidget(hide_tip)
        layout.addWidget(save, alignment=Qt.AlignLeft)
        layout.addLayout(tools)
        layout.addLayout(link_row)
        layout.addStretch(1)
        self.updateButton.clicked.connect(self.checkUpdates)
        self.errorButton.clicked.connect(self.openErrorLog)
        self.copyDiagButton.clicked.connect(self.copyDiagnostics)

    def pickStorage(self):
        folder = QFileDialog.getExistingDirectory(self, "选择鼠标文件存放位置", self.storage.text())
        if folder:
            self.storage.setText(folder)

    def openStorageFolder(self):
        folder = Path(self.storage.text()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def save(self):
        try:
            self.backend.apply_storage_root(Path(self.storage.text()))
            data = self.backend.load_settings()
            data["storage_root"] = str(Path(self.storage.text()).resolve())
            data["hide_taskbar_icon"] = "1" if self.hideTaskbarIcon.isChecked() else "0"
            self.backend.save_settings(data)
            self.backend.set_auto_start(self.autostart.isChecked())
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
            f"隐藏任务栏图标：{self.backend.hide_taskbar_icon_enabled()}",
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

        self.addSubInterface(self.schemePage, FIF.BRUSH, "鼠标方案")
        self.addSubInterface(self.resourcePage, FIF.FOLDER, "资源库")
        self.addSubInterface(self.switchPage, FIF.DATE_TIME, "方案切换")
        self.addSubInterface(self.settingsPage, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM)
        self.navigationInterface.setAcrylicEnabled(True)
        self.navigationInterface.setMinimumWidth(188)
        self.navigationInterface.setMaximumWidth(188)
        self.createTrayIcon()
        self.scheduleTimer = QTimer(self)
        self.scheduleTimer.timeout.connect(self.checkScheduledSwitch)
        self.scheduleTimer.start(30_000)

    def createTrayIcon(self):
        icon = self.windowIcon()
        self.trayIcon = QSystemTrayIcon(icon, self)
        menu = QMenu()
        open_action = menu.addAction("打开")
        open_action.triggered.connect(self.openFromTray)
        menu.addSeparator()
        current_action = menu.addAction(f"当前配置：{self.backend.configured_current_scheme()}")
        current_action.setEnabled(False)
        next_text = self.backend.next_switch_text(*self.backend.load_schedule_state())
        next_action = menu.addAction(f"下次切换：{next_text}")
        next_action.setEnabled(False)
        menu.addSeparator()
        hide_action = menu.addAction("隐藏任务栏图标")
        hide_action.triggered.connect(self.hideTrayIconNow)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.exitFromTray)
        self.trayIcon.setContextMenu(menu)
        self.trayIcon.activated.connect(self.onTrayActivated)
        if not self.backend.hide_taskbar_icon_enabled():
            self.trayIcon.show()

    def onTrayActivated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.openFromTray()

    def openFromTray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

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
            for item in schedule_items:
                if item.get("mode") == "timer":
                    interval = max(1, int(item.get("interval_seconds") or 0))
                    if __import__("time").time() - self.lastTimerAt >= interval:
                        scheme = self.backend.pick_scheduled_scheme(item.get("scheme", ""), item.get("order", "顺序"), self.timerScheduleIndex)
                        self.timerScheduleIndex += 1
                        self.lastTimerAt = __import__("time").time()
                        if scheme:
                            self.backend.apply_library_scheme(scheme)
                    continue
                scheme = item.get("scheme", "")
                key = f"{now:%Y-%m-%d}|{item.get('time')}|{scheme}"
                if scheme and item.get("time") == now.strftime("%H:%M") and key != self.lastScheduleKey:
                    picked = self.backend.pick_scheduled_scheme(scheme, item.get("order", "顺序"), 0)
                    if picked:
                        self.backend.apply_library_scheme(picked)
                    self.lastScheduleKey = key
                    return
            scheme = week_items.get(str(now.weekday()))
            key = f"{now:%Y-%m-%d}|week|{scheme}"
            if scheme and key != self.lastScheduleKey:
                picked = self.backend.pick_scheduled_scheme(scheme, "随机", 0) if scheme == self.backend.RANDOM_SCHEME_VALUE else scheme
                if picked:
                    self.backend.apply_library_scheme(picked)
                self.lastScheduleKey = key
        except Exception as exc:
            self.backend.log_error("Fluent 后台切换失败", exc)

    def closeEvent(self, event):
        if self.exiting:
            event.accept()
            return
        if self.settingsPage.autostart.isChecked() or self.backend.auto_start_enabled():
            try:
                self.backend.set_auto_start(True)
                if self.backend.hide_taskbar_icon_enabled():
                    self.backend.start_background_process()
                    event.accept()
                    return
                if self.trayIcon:
                    self.trayIcon.show()
                    self.trayIcon.showMessage(self.backend.APP_NAME, "已保留后台运行。", QSystemTrayIcon.Information, 1800)
                self.hide()
                event.ignore()
                return
            except Exception as exc:
                self.backend.log_error("Fluent 保留后台失败", exc)
        event.accept()


def run_app(backend, start_hidden: bool = False) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MousePointerFluentWindow(backend, start_hidden=start_hidden)
    if start_hidden:
        if window.trayIcon and not backend.hide_taskbar_icon_enabled():
            window.trayIcon.show()
            window.trayIcon.showMessage(backend.APP_NAME, "已在后台运行。", QSystemTrayIcon.Information, 1800)
    else:
        window.show()
    app.exec()
