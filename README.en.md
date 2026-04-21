<br />
<div align="center">
  <a href="https://github.com/yuanyue1234/MousePointer">
    <img src="icon.png" alt="Logo" width="128" height="128">
  </a>

  <h1 align="center" style="margin-top: 0.2em;">Mouse Pointer Manager</h1>

  [![Python][python-badge]][python-url]
  [![PySide6][pyside-badge]][pyside-url]
  [![Fluent Widgets][fluent-badge]][fluent-url]
  [![Windows][windows-badge]][windows-url]

  <p align="center">
    <h3>A graphical cursor manager for beginners and cursor creators</h3>
    <br />
    <a href="https://github.com/yuanyue1234/MousePointer/releases/download/v2.0.0/MousePointer_Portable.exe"><strong>Download &raquo;</strong></a>
    <br />
    <br />
    <a href="README.en.md">English</a>
    &middot;
    <a href="README.md">简体中文</a>
    &middot;
    <a href="https://github.com/yuanyue1234/MousePointer/issues/new?labels=bug">Report Bug</a>
    &middot;
    <a href="https://github.com/yuanyue1234/MousePointer/issues/new?labels=enhancement">Request Feature</a>
  </p>
</div>

<details>
  <summary>Contents</summary>
  <ol>
    <li><a href="#features">Features</a></li>
    <li><a href="#screenshots">Screenshots</a></li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li><a href="#run-from-source">Run From Source</a></li>
    <li><a href="#build">Build</a></li>
    <li><a href="#references">References</a></li>
  </ol>
</details>

## Features

- **Scheme management**: create, rename, delete, import, and auto-save cursor schemes.
- **Multi-format import**: supports `.cur`, `.ani`, common images, `.zip`, `.rar`, `.7z`, `.exe`, and folders.
- **INF parsing**: reads `.inf` files and imports multiple cursor schemes from a single package.
- **Partial replacement**: apply a scheme even when only some cursor roles are configured.
- **Live preview**: preview static and animated cursors in real time, including `.ani`.
- **Size control**: uses `- / +` controls and a segmented progress bar instead of an easy-to-misfire slider.
- **Screenshot export**: exports scheme previews as `.gif`, preserving animated frames when available.
- **Background mode**: supports background startup, tray persistence, taskbar hiding, and startup repair.
- **Beginner friendly**: edit, apply, and package cursor themes without using the command line.

## Screenshots

<p align="center">
  <img src="docs/screenshots/screenshot-1.png" alt="Scheme manager" width="300">
  <img src="docs/screenshots/screenshot-2.png" alt="Resource library" width="300">
  <img src="docs/screenshots/screenshot-3.png" alt="Settings" width="300">
</p>

## Quick Start

### Step 1: Download

- GitHub Releases:  
  [Download latest build](https://github.com/yuanyue1234/MousePointer/releases/download/v2.0.0/MousePointer_Portable.exe)

### Step 2: Import a scheme

- Drag in `.cur`, `.ani`, images, archives, `exe`, or folders.
- If the package contains `.inf`, the app builds schemes automatically.

### Step 3: Edit and apply

- Assign resources to each cursor role on the scheme page.
- Use the live preview on the right side to check the result.
- Click apply to write the cursor configuration into Windows.

### Step 4: Build an installer

- Click the build button on the scheme page.
- The portable build is distributed through the Release link above.

## Run From Source

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Build

```powershell
.\.venv\Scripts\python.exe -m PyInstaller -y --clean "鼠标指针配置生成器_绿色程序.spec"
```

Output:

```text
dist\鼠标指针配置生成器_绿色程序.exe
release-assets\鼠标指针配置生成器_绿色程序.exe
```

## References

- The Chinese/English input switching logic references InputTip:  
  https://inputtip.abgox.com/zh-CN/
- Extra cursor resources for InputTip:  
  https://inputtip.abgox.com/zh-CN/download/extra
- The UI framework style references PyQt-Fluent-Widgets:  
  https://github.com/zhiyiYo/PyQt-Fluent-Widgets
- Pixel cursor guide:  
  https://mp.weixin.qq.com/s/DyO-dBMKf7RrMetCqji4jg
- Made by ASUNNY:  
  https://asunny.top/

[python-badge]: https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[pyside-badge]: https://img.shields.io/badge/PySide6-Qt-41CD52?style=for-the-badge&logo=qt&logoColor=white
[pyside-url]: https://doc.qt.io/qtforpython-6/
[fluent-badge]: https://img.shields.io/badge/PyQt--Fluent--Widgets-UI-009688?style=for-the-badge
[fluent-url]: https://github.com/zhiyiYo/PyQt-Fluent-Widgets
[windows-badge]: https://img.shields.io/badge/Windows-10%2B-0078D6?style=for-the-badge&logo=windows&logoColor=white
[windows-url]: https://www.microsoft.com/windows/
