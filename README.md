# 鼠标指针配置生成器

Windows 图形化鼠标指针方案工具。可以把不同鼠标状态绑定到自定义图片，生成独立安装器，也可以在本机保存方案并按时间自动切换。

## 功能

- 单窗口界面，左侧是从 `1439978017.svg` 裁切出的参考图标，右侧是自定义素材预览。
- 支持拖入文件到任意鼠标状态行，也支持点击选择文件。
- 支持 `PNG/JPG/BMP/GIF/WEBP/ICO/CUR/ANI`。
- 鼠标大小滑块会影响预览和生成的 `.cur` 光标尺寸。
- 提供按钮跳转 Windows 鼠标指针大小设置。
- 方案名称使用下拉框，可继续手动输入新名称。
- 可保存方案到本机方案库，并添加 `HH:MM -> 方案` 的定时切换规则。
- 生成安装包时优先生成独立 PyInstaller EXE；检测到 WinRAR 后会再封装 WinRAR 自解压包。
- 错误会写入 `错误记录.md`。

## 安装依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 运行

```powershell
.\.venv\Scripts\python.exe main.py
```

## 打包主程序

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --onefile --clean --name 鼠标配置生成器 --add-data "assets;assets" --add-data "1439978017.svg;." main.py
```

输出位置：

```text
dist\鼠标配置生成器.exe
```

## 注意

- 生成的鼠标样式安装器是独立 EXE，目标电脑不需要 Python。
- 拖拽支持依赖 `tkinterdnd2`，已经写入 `requirements.txt` 并会被 PyInstaller 一起打包。
- 定时切换需要程序保持运行。方案要先点击 `保存到方案库`，再添加到定时列表。
