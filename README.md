<br />
<div align="center">
  <a href="https://github.com/yuanyue1234/MousePointer">
    <img src="icon.png" alt="Logo" width="128" height="128">
  </a>

  <h1 align="center" style="margin-top: 0.2em;">鼠标指针配置管理器</h1>

  [![Python][python-badge]][python-url]
  [![PySide6][pyside-badge]][pyside-url]
  [![Fluent Widgets][fluent-badge]][fluent-url]
  [![Windows][windows-badge]][windows-url]

  <p align="center">
    <h3>给新手用户和鼠标指针制作者的图形化管理工具</h3>
    <br />
    <a href="https://github.com/yuanyue1234/MousePointer/releases/download/v2.0.0/MousePointer_Portable.exe"><strong>下载软件 &raquo;</strong></a>
    <br />
    <br />
    <a href="README.en.md">English</a>
    &middot;
    <a href="README.md">简体中文</a>
    &middot;
    <a href="https://github.com/yuanyue1234/MousePointer/issues/new?labels=bug">报告 Bug</a>
    &middot;
    <a href="https://github.com/yuanyue1234/MousePointer/issues/new?labels=enhancement">功能建议</a>
  </p>
</div>

<details>
  <summary>目录</summary>
  <ol>
    <li><a href="#功能特性">功能特性</a></li>
    <li><a href="#软件截图">软件截图</a></li>
    <li><a href="#快速开始">快速开始</a></li>
    <li><a href="#运行源码">运行源码</a></li>
    <li><a href="#打包">打包</a></li>
    <li><a href="#参考">参考</a></li>
  </ol>
</details>

## 功能特性

- **方案管理**：新建、重命名、删除、导入和自动保存鼠标指针方案。
- **多格式导入**：支持 `.cur`、`.ani`、常见图片、`.zip`、`.rar`、`.7z`、`.exe` 和文件夹导入。
- **INF 识别**：导入资源包时自动识别 `.inf`，支持一个压缩包内包含多份鼠标指针方案。
- **局部替换**：只配置部分鼠标状态时，也可以直接应用，不会被未配置项阻断。
- **动态预览**：右侧实时预览支持静态和动态鼠标指针，`.ani` 会直接播放。
- **大小调节**：鼠标大小使用 `- / +` 和分段进度条调整，避免滑块误触。
- **截图导出**：方案截图导出为 `.gif`，动态指针会保留动画帧。
- **后台驻留**：支持自启动后台、隐藏任务栏、托盘保留和启动修复。
- **面向小白**：用图形界面完成导入、编辑、应用和打包，不依赖命令行。

## 软件截图

<p align="center">
  <img src="docs/screenshots/screenshot-1.png" alt="鼠标方案管理" width="300">
  <img src="docs/screenshots/screenshot-2.png" alt="资源库" width="300">
  <img src="docs/screenshots/screenshot-3.png" alt="设置页面" width="300">
</p>

## 快速开始

### Step 1：下载安装

- GitHub Releases：
  [下载最新版本](https://github.com/yuanyue1234/MousePointer/releases/download/v2.0.0/MousePointer_Portable.exe)
- 在线资源库：
  [打开鼠标指针资源库](http://8.135.33.2:5002/)

### Step 2：导入方案

- 支持拖入 `.cur`、`.ani`、图片、压缩包、`exe` 或文件夹。
- 资源包内如果存在 `.inf`，程序会自动识别并建立方案。
- 也可以在应用的资源库页面打开在线资源库下载资源包。

### Step 3：编辑与应用

- 在鼠标方案页为各个状态选择资源。
- 右侧实时预览会显示当前方案效果。
- 点击应用后写入系统鼠标指针配置。

### Step 4：生成安装包

- 在方案页点击生成安装包。
- 当前绿色版下载地址固定为上面的 Release 链接。

## 运行源码

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 打包

```powershell
.\.venv\Scripts\python.exe -m PyInstaller -y --clean "鼠标指针配置生成器_绿色程序.spec"
```

输出位置：

```text
dist\鼠标指针配置生成器_绿色程序.exe
release-assets\鼠标指针配置生成器_绿色程序.exe
```

## 参考

- 中英文切换逻辑参考了 InputTip 的实现思路：  
  https://inputtip.abgox.com/zh-CN/
- InputTip 扩展鼠标指针资源：  
  https://inputtip.abgox.com/zh-CN/download/extra
- 界面框架风格参考了 PyQt-Fluent-Widgets：  
  https://github.com/zhiyiYo/PyQt-Fluent-Widgets
- 像素指针指南文章：  
  https://mp.weixin.qq.com/s/DyO-dBMKf7RrMetCqji4jg
- 工具制作 BY ASUNNY：  
  https://asunny.top/

[python-badge]: https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[pyside-badge]: https://img.shields.io/badge/PySide6-Qt-41CD52?style=for-the-badge&logo=qt&logoColor=white
[pyside-url]: https://doc.qt.io/qtforpython-6/
[fluent-badge]: https://img.shields.io/badge/PyQt--Fluent--Widgets-UI-009688?style=for-the-badge
[fluent-url]: https://github.com/zhiyiYo/PyQt-Fluent-Widgets
[windows-badge]: https://img.shields.io/badge/Windows-10%2B-0078D6?style=for-the-badge&logo=windows&logoColor=white
[windows-url]: https://www.microsoft.com/windows/
