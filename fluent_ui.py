from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
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
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
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
        self.setStyleSheet("border-radius: 8px; background: rgba(246, 250, 255, 0.9);")

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
        self.setMinimumSize(300, 300)
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


class CursorRow(CardWidget):
    hovered = Signal(str)
    picked = Signal(str)

    def __init__(self, backend, role, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.role = role
        self.path: Path | None = None
        self.setMinimumHeight(70)

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


class SchemePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.rows: dict[str, CursorRow] = {}
        self.selected: dict[str, Path] = {}
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
        self.saveButton = PushButton("保存")
        self.saveButton.setIcon(FIF.SAVE)
        for button in [self.newButton, self.renameButton, self.deleteButton, self.importButton, self.saveButton]:
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        left_layout.addLayout(toolbar)

        self.dropArea = DropArea("拖入文件即可导入或替换当前选中项")
        self.dropArea.dropped.connect(self.handleDropped)
        left_layout.addWidget(self.dropArea)

        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rowWidget = QWidget()
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

        right = CardWidget()
        right.setFixedWidth(360)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        right_layout.addWidget(SubtitleLabel("实时预览"))
        right_layout.addWidget(CaptionLabel("鼠标移入左侧配置行时同步切换"))

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
        self.sizeTip.setTextColor("#64748b", "#ef4444")
        right_layout.addWidget(self.sizeTip)

        self.largePreview = PreviewPane()
        right_layout.addWidget(self.largePreview, 1)
        self.previewName = StrongBodyLabel("正常选择")
        self.previewFile = CaptionLabel("")
        self.previewFile.setTextColor("#64748b", "#94a3b8")
        right_layout.addWidget(self.previewName)
        right_layout.addWidget(self.previewFile)

        action_row = QHBoxLayout()
        self.sizeSettingsButton = PushButton("鼠标大小设置")
        self.sizeSettingsButton.setIcon(FIF.SETTING)
        self.applyButton = PrimaryPushButton("应用")
        self.applyButton.setIcon(FIF.ACCEPT)
        self.buildButton = PushButton("生成安装包")
        self.buildButton.setIcon(FIF.APPLICATION)
        action_row.addWidget(self.sizeSettingsButton)
        action_row.addWidget(self.applyButton)
        action_row.addWidget(self.buildButton)
        right_layout.addLayout(action_row)
        self.status = CaptionLabel("更改鼠标至对应大小后应用方案")
        self.status.setTextColor("#64748b", "#94a3b8")
        right_layout.addWidget(self.status)

        root.addWidget(left, 1)
        root.addWidget(right, 0)

        self.importButton.clicked.connect(self.importPackage)
        self.saveButton.clicked.connect(self.saveScheme)
        self.newButton.clicked.connect(self.newScheme)
        self.deleteButton.clicked.connect(self.deleteScheme)
        self.renameButton.clicked.connect(self.renameScheme)
        self.applyButton.clicked.connect(self.applyScheme)
        self.buildButton.clicked.connect(self.buildInstaller)
        self.sizeSettingsButton.clicked.connect(self.openPointerSettings)
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
        return sorted(names)

    def refreshSchemes(self):
        current = self.schemeBox.currentText()
        self.schemeBox.clear()
        names = self.schemeNames()
        self.schemeBox.addItems(names)
        if current in names:
            self.schemeBox.setCurrentText(current)
        elif names:
            self.schemeBox.setCurrentIndex(0)
            self.loadScheme(names[0])
        else:
            self.clearSelection()

    def clearSelection(self):
        self.selected.clear()
        for row in self.rows.values():
            row.setPath(None)
        self.updateLargePreview("Arrow")

    def loadScheme(self, name: str):
        if not name:
            return
        try:
            scheme_dir, files = self.backend.scheme_manifest(name)
            self.selected = {reg: scheme_dir / file_name for reg, file_name in files.items() if (scheme_dir / file_name).exists()}
            for reg, row in self.rows.items():
                row.setPath(self.selected.get(reg))
            self.updateLargePreview(self.current_preview)
            self.status.setText(f"已载入：{name}")
        except Exception as exc:
            self.showError("载入失败", exc)

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
        archives = [p for p in paths if p.suffix.lower() in {".zip", ".rar", ".7z", ".exe"}]
        if archives:
            for archive in archives:
                self.importArchiveAsScheme(archive)
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
            "导入安装包或压缩包",
            str(self.backend.configured_storage_root()),
            "资源包 (*.zip *.rar *.7z *.exe);;所有文件 (*.*)",
        )
        for file_name in files:
            self.importArchiveAsScheme(Path(file_name))
        if files:
            self.refreshSchemes()

    def importArchiveAsScheme(self, archive: Path):
        try:
            name = self.backend.sanitize_name(archive.stem)
            if name in self.backend.DEFAULT_SCHEME_NAMES:
                name = f"{name}_资源"
            scheme_dir = self.backend.SCHEME_LIBRARY / name
            if (scheme_dir / "scheme.json").exists():
                base = name
                index = 2
                while (self.backend.SCHEME_LIBRARY / f"{base}_{index}" / "scheme.json").exists():
                    index += 1
                name = f"{base}_{index}"
                scheme_dir = self.backend.SCHEME_LIBRARY / name
            extracted = self.backend.extract_import_package(archive)
            mapping = self.backend.parse_inf_mapping(extracted)
            if not mapping:
                raise RuntimeError(f"{archive.name} 没有识别到鼠标方案。")
            scheme_dir.mkdir(parents=True, exist_ok=True)
            files = {}
            for reg_name, source in mapping.items():
                role = self.backend.ROLE_BY_REG.get(reg_name)
                if not role:
                    continue
                output_name = f"{role.file_stem}{source.suffix.lower()}"
                shutil.copy2(source, scheme_dir / output_name)
                files[reg_name] = output_name
            self.writeManifest(name, files, scheme_dir)
            self.showInfo("导入完成", f"已添加：{name}")
        except Exception as exc:
            self.showError("导入失败", exc)

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

    def writeManifest(self, theme: str, files: dict[str, str], folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {"name": theme, "files": files}
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
            if scheme_dir.exists():
                shutil.rmtree(scheme_dir)
            shutil.copytree(package_dir / "assets", scheme_dir)
            self.writeManifest(theme, files, scheme_dir)
            self.refreshSchemes()
            self.schemeBox.setCurrentText(theme)
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
            shutil.rmtree(self.backend.SCHEME_LIBRARY / name, ignore_errors=True)
            self.refreshSchemes()
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("资源库"))
        layout.addWidget(CaptionLabel("打开在线资源库下载文件，放入鼠标文件目录后点击刷新。"))
        row = QHBoxLayout()
        self.openWeb = PushButton("在线资源库")
        self.openWeb.setIcon(FIF.LINK)
        self.openFolder = PushButton("打开存放位置")
        self.openFolder.setIcon(FIF.FOLDER)
        self.refresh = PrimaryPushButton("刷新")
        self.refresh.setIcon(FIF.SYNC)
        self.gridButton = ToggleButton("九宫格")
        self.gridButton.setIcon(FIF.TILES)
        row.addWidget(self.openWeb)
        row.addWidget(self.openFolder)
        row.addWidget(self.refresh)
        row.addWidget(self.gridButton)
        row.addStretch(1)
        layout.addLayout(row)
        self.container = QWidget()
        self.cards = QVBoxLayout(self.container)
        self.cards.setSpacing(10)
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)
        self.openWeb.clicked.connect(lambda: webbrowser.open(self.backend.RESOURCE_URL))
        self.openFolder.clicked.connect(lambda: os.startfile(self.backend.configured_storage_root()))
        self.refresh.clicked.connect(self.render)
        self.gridButton.clicked.connect(self.toggleGrid)
        self.render()

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
        if not names:
            self.cards.addWidget(BodyLabel("暂无资源"))
            return
        for index, name in enumerate(names):
            card = CardWidget()
            layout = QVBoxLayout(card) if self.gridMode else QHBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            text = QVBoxLayout()
            text.addWidget(StrongBodyLabel(name))
            scheme_dir, files = self.backend.scheme_manifest(name)
            text.addWidget(CaptionLabel(f"{len(files)} 个鼠标状态"))
            layout.addLayout(text, 1 if not self.gridMode else 0)
            preview_row = QHBoxLayout()
            for file_name in list(files.values())[:9]:
                preview = CursorPreview(54 if self.gridMode else 42)
                preview.setPath(self.backend, scheme_dir / file_name, 48 if self.gridMode else 38)
                preview_row.addWidget(preview)
            layout.addLayout(preview_row)
            apply_btn = PrimaryPushButton("应用")
            apply_btn.clicked.connect(lambda _checked=False, n=name: self.applyResource(n))
            layout.addWidget(apply_btn)
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


class SchedulePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(SubtitleLabel("时间切换"))
        layout.addWidget(CaptionLabel("亮色模式与暗色模式各选择一个时间和方案。留空则不切换。"))
        self.lightTime = LineEdit()
        self.lightTime.setPlaceholderText("亮色时间，例如 08:00")
        self.lightScheme = ComboBox()
        self.darkTime = LineEdit()
        self.darkTime.setPlaceholderText("暗色时间，例如 20:00")
        self.darkScheme = ComboBox()
        for widget in [self.lightScheme, self.darkScheme]:
            widget.addItem("")
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
        return sorted([p.name for p in root.iterdir() if p.is_dir()]) if root.exists() else []

    def load(self):
        try:
            items, _week = self.backend.load_schedule_state()
            by_mode = {item.get("mode"): item for item in items}
            self.lightTime.setText(by_mode.get("light", {}).get("time", ""))
            self.lightScheme.setCurrentText(by_mode.get("light", {}).get("scheme", ""))
            self.darkTime.setText(by_mode.get("dark", {}).get("time", ""))
            self.darkScheme.setCurrentText(by_mode.get("dark", {}).get("scheme", ""))
        except Exception:
            pass

    def save(self):
        try:
            items = []
            for mode, time_edit, scheme in [("light", self.lightTime, self.lightScheme), ("dark", self.darkTime, self.darkScheme)]:
                if scheme.currentText().strip():
                    self.backend.CursorThemeBuilder.validate_time(None, time_edit.text().strip())
                    items.append({"mode": mode, "time": time_edit.text().strip(), "scheme": scheme.currentText().strip()})
            self.backend.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.SCHEDULE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(True)
            InfoBar.success(title="已应用", content="时间切换已保存并开启后台自启动", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())
        except Exception as exc:
            self.backend.log_error("Fluent 时间切换保存失败", exc)
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
        values = [""] + self.scheme_page.schemeNames()
        for index, day in enumerate(self.weekdays):
            card = CardWidget()
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            row.addWidget(StrongBodyLabel(day))
            row.addStretch(1)
            combo = ComboBox()
            combo.setMinimumWidth(260)
            combo.addItems(values)
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
                combo.setCurrentText(week_items.get(day, ""))
        except Exception:
            pass

    def refreshSchemes(self):
        values = [""] + self.scheme_page.schemeNames()
        for combo in self.combos.values():
            current = combo.currentText()
            combo.clear()
            combo.addItems(values)
            if current in values:
                combo.setCurrentText(current)

    def save(self):
        try:
            week_items = {day: combo.currentText().strip() for day, combo in self.combos.items() if combo.currentText().strip()}
            self.backend.WEEK_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.backend.WEEK_SCHEDULE_FILE.write_text(json.dumps(week_items, ensure_ascii=False, indent=2), encoding="utf-8")
            self.backend.set_auto_start(True)
            today = str(__import__("datetime").datetime.now().weekday())
            scheme = week_items.get(today)
            if scheme:
                self.scheme_page.schemeBox.setCurrentText(scheme)
                self.scheme_page.loadScheme(scheme)
                self.scheme_page.applyScheme()
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
        layout.addWidget(CaptionLabel("工具制作 BY ASUNNY"))

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
        layout.addWidget(storage_card)

        self.autostart = SwitchButton("自启动后台")
        self.autostart.setChecked(self.backend.scheduled_task_exists() or self.backend.startup_script_path().exists())
        save = PrimaryPushButton("保存设置")
        save.clicked.connect(self.save)
        tools = QHBoxLayout()
        self.updateButton = PrimaryPushButton("检测更新")
        self.updateButton.setIcon(FIF.UPDATE)
        self.restoreButton = PushButton("恢复应用前鼠标方案")
        self.restoreButton.setIcon(FIF.RETURN)
        self.errorButton = PushButton("打开错误记录")
        self.errorButton.setIcon(FIF.DOCUMENT)
        self.copyDiagButton = PushButton("复制诊断信息")
        self.copyDiagButton.setIcon(FIF.COPY)
        for button in [self.updateButton, self.restoreButton, self.errorButton, self.copyDiagButton]:
            tools.addWidget(button)
        tools.addStretch(1)
        link_row = QHBoxLayout()
        for text, url in [
            ("像素指针指南文章", self.backend.PIXEL_GUIDE_URL),
            ("工具制作 BY ASUNNY", self.backend.ASUNNY_URL),
            ("GitHub 源地址", self.backend.configured_github_url()),
        ]:
            btn = PushButton(text)
            btn.clicked.connect(lambda _checked=False, u=url: webbrowser.open(u))
            link_row.addWidget(btn)
        link_row.addStretch(1)
        layout.addWidget(self.autostart)
        layout.addWidget(save, alignment=Qt.AlignLeft)
        layout.addLayout(tools)
        layout.addLayout(link_row)
        layout.addStretch(1)
        self.updateButton.clicked.connect(self.checkUpdates)
        self.restoreButton.clicked.connect(self.restoreCursor)
        self.errorButton.clicked.connect(self.openErrorLog)
        self.copyDiagButton.clicked.connect(self.copyDiagnostics)

    def pickStorage(self):
        folder = QFileDialog.getExistingDirectory(self, "选择鼠标文件存放位置", self.storage.text())
        if folder:
            self.storage.setText(folder)

    def save(self):
        try:
            self.backend.apply_storage_root(Path(self.storage.text()))
            data = self.backend.load_settings()
            data["storage_root"] = str(Path(self.storage.text()).resolve())
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
        os.startfile(self.backend.ERROR_LOG)

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
            f"启动快捷方式：{self.backend.startup_script_path()} / 存在={self.backend.startup_script_path().exists()}",
            f"任务计划：{self.backend.SCHEDULED_TASK_NAME} / 存在={self.backend.scheduled_task_exists()}",
        ])
        QApplication.clipboard().setText(text)
        InfoBar.success(title="已复制", content="诊断信息已复制到剪贴板", orient=Qt.Horizontal, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self.window())


class MousePointerFluentWindow(FluentWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.exiting = False
        self.trayIcon: QSystemTrayIcon | None = None
        self.setWindowTitle(backend.APP_NAME)
        icon_path = backend.resource_path("icon终.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1360, 820)
        self.setMinimumSize(1180, 720)
        setTheme(Theme.LIGHT)
        setThemeColor("#4f8cff")
        try:
            self.setMicaEffectEnabled(True)
        except Exception:
            pass

        self.schemePage = SchemePage(backend, self)
        self.resourcePage = ResourcePage(backend, self.schemePage, self)
        self.schedulePage = SchedulePage(backend, self)
        self.weekPage = WeekPage(backend, self.schemePage, self)
        self.settingsPage = SettingsPage(backend, self)

        self.schemePage.setObjectName("schemePage")
        self.resourcePage.setObjectName("resourcePage")
        self.schedulePage.setObjectName("schedulePage")
        self.weekPage.setObjectName("weekPage")
        self.settingsPage.setObjectName("settingsPage")

        self.addSubInterface(self.schemePage, FIF.BRUSH, "鼠标方案")
        self.addSubInterface(self.resourcePage, FIF.FOLDER, "资源库")
        self.addSubInterface(self.schedulePage, FIF.DATE_TIME, "时间切换")
        self.addSubInterface(self.weekPage, FIF.CALENDAR, "星期切换")
        self.addSubInterface(self.settingsPage, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM)
        self.navigationInterface.setAcrylicEnabled(True)
        self.navigationInterface.setMinimumWidth(188)
        self.navigationInterface.setMaximumWidth(188)
        self.createTrayIcon()

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
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.exitFromTray)
        self.trayIcon.setContextMenu(menu)
        self.trayIcon.activated.connect(self.onTrayActivated)

    def onTrayActivated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.openFromTray()

    def openFromTray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def exitFromTray(self):
        self.exiting = True
        if self.trayIcon:
            self.trayIcon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if self.exiting:
            event.accept()
            return
        if self.settingsPage.autostart.isChecked():
            try:
                self.backend.set_auto_start(True)
                self.backend.start_background_process()
                if self.trayIcon:
                    self.trayIcon.show()
                    self.trayIcon.showMessage(self.backend.APP_NAME, "已保留后台运行。", QSystemTrayIcon.Information, 1800)
                self.hide()
                event.ignore()
                return
            except Exception as exc:
                self.backend.log_error("Fluent 保留后台失败", exc)
        event.accept()


def run_app(backend) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MousePointerFluentWindow(backend)
    window.show()
    app.exec()
