from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    Theme,
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


class CursorPreview(QLabel):
    def __init__(self, size: int = 46, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border-radius: 8px; background: rgba(246, 250, 255, 0.9);")

    def setPath(self, backend, path: Path | None, size: int = 42) -> None:
        if not path or not path.exists():
            self.clear()
            return
        try:
            image = backend.cursor_preview_image(path, (size, size)).convert("RGBA")
            qimage = ImageQt(image)
            pixmap = QPixmap.fromImage(qimage)
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.setText("...")


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
        self.pickButton = PushButton("选择")
        self.pickButton.setIcon(FIF.FOLDER)
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
        self.preview.setPath(self.backend, path)


class SchemePage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.rows: dict[str, CursorRow] = {}
        self.selected: dict[str, Path] = {}
        self.current_preview = "Arrow"
        self.sizeLevel = 3

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(18)

        left = QWidget()
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
        right.setMinimumWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        right_layout.addWidget(SubtitleLabel("实时预览"))
        right_layout.addWidget(CaptionLabel("鼠标移入左侧配置行时同步切换"))

        size_row = QHBoxLayout()
        size_row.addWidget(BodyLabel("预览大小"))
        self.sizeBox = ComboBox()
        for value in range(1, 16):
            self.sizeBox.addItem(str(value))
        self.sizeBox.setCurrentText("3")
        self.sizeBox.currentTextChanged.connect(self.onSizeChanged)
        size_row.addWidget(self.sizeBox)
        size_row.addStretch(1)
        right_layout.addLayout(size_row)

        self.largePreview = QLabel()
        self.largePreview.setMinimumSize(300, 300)
        self.largePreview.setAlignment(Qt.AlignCenter)
        self.largePreview.setStyleSheet("border-radius: 12px; background: #f8fbff; border: 1px solid #dbeafe;")
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
        root.addWidget(right)

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
        role = self.backend.ROLE_BY_REG.get(reg_name)
        path = self.selected.get(reg_name)
        if role:
            self.previewName.setText(role.label)
        self.previewFile.setText(str(path) if path else "未选择")
        if not path or not path.exists():
            self.largePreview.clear()
            return
        try:
            size = max(32, min(256, self.sizeLevel * 16 + 16))
            image = self.backend.cursor_preview_image(path, (size, size)).convert("RGBA")
            pixmap = QPixmap.fromImage(ImageQt(image))
            self.largePreview.setPixmap(pixmap.scaled(self.largePreview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as exc:
            self.largePreview.setText("预览失败")
            self.backend.log_error("Fluent 预览失败", exc)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateLargePreview(self.current_preview)

    def onSizeChanged(self, text: str):
        self.sizeLevel = int(text) if text.isdigit() else 3
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
        self.showWarn("暂未迁移", "安装包生成仍可使用旧界面 --tk，本界面先完成 Fluent 主体验。")

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
        row.addWidget(self.openWeb)
        row.addWidget(self.openFolder)
        row.addWidget(self.refresh)
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
        self.render()

    def render(self):
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        names = self.scheme_page.schemeNames()
        if not names:
            self.cards.addWidget(BodyLabel("暂无资源"))
            return
        for name in names:
            card = CardWidget()
            layout = QHBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            text = QVBoxLayout()
            text.addWidget(StrongBodyLabel(name))
            scheme_dir, files = self.backend.scheme_manifest(name)
            text.addWidget(CaptionLabel(f"{len(files)} 个鼠标状态"))
            layout.addLayout(text, 1)
            preview_row = QHBoxLayout()
            for file_name in list(files.values())[:8]:
                preview = CursorPreview(38)
                preview.setPath(self.backend, scheme_dir / file_name, 34)
                preview_row.addWidget(preview)
            layout.addLayout(preview_row)
            apply_btn = PrimaryPushButton("应用")
            apply_btn.clicked.connect(lambda _checked=False, n=name: self.applyResource(n))
            layout.addWidget(apply_btn)
            self.cards.addWidget(card)
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
        layout.addLayout(link_row)
        layout.addStretch(1)

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


class MousePointerFluentWindow(FluentWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.setWindowTitle(backend.APP_NAME)
        icon_path = backend.resource_path("icon终.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1280, 820)
        self.setMinimumSize(1060, 720)
        setTheme(Theme.LIGHT)
        setThemeColor("#4f8cff")
        try:
            self.setMicaEffectEnabled(True)
        except Exception:
            pass

        self.schemePage = SchemePage(backend, self)
        self.resourcePage = ResourcePage(backend, self.schemePage, self)
        self.schedulePage = SchedulePage(backend, self)
        self.settingsPage = SettingsPage(backend, self)

        self.schemePage.setObjectName("schemePage")
        self.resourcePage.setObjectName("resourcePage")
        self.schedulePage.setObjectName("schedulePage")
        self.settingsPage.setObjectName("settingsPage")

        self.addSubInterface(self.schemePage, FIF.BRUSH, "鼠标方案")
        self.addSubInterface(self.resourcePage, FIF.FOLDER, "资源库")
        self.addSubInterface(self.schedulePage, FIF.DATE_TIME, "时间切换")
        self.addSubInterface(self.settingsPage, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM)
        self.navigationInterface.setAcrylicEnabled(True)


def run_app(backend) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    window = MousePointerFluentWindow(backend)
    window.show()
    app.exec()
