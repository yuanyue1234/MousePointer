# 鼠标指针配置生成器

Windows 图形化鼠标指针方案工具。可以导入鼠标压缩包或安装包，预览鼠标指针，应用到当前电脑，并生成独立安装器。

## 当前功能

- 左侧是从 `1439978017.svg` 裁切出的参考图标。
- 右侧是实时大预览，支持普通图片、`.cur`、`.ani`。
- 支持拖入文件到对应鼠标状态行。
- 支持导入 `zip/rar/7z/exe`，优先解压并读取 `.inf`，再匹配 `.cur/.ani`。EXE 需要是自解压压缩包才能直接读取。
- 项目内置两套默认鼠标指针 zip，启动时自动导入到方案库。
- 保留 Windows 鼠标大小设置跳转按钮，并提示“建议调整大小后再应用。”
- 定时切换在标题右侧按钮里配置：
  - 亮色模式：时间 + 方案
  - 暗色模式：时间 + 方案
  - 每行有小 `x` 可清除
- 星期切换在标题右侧按钮里配置，每天可选择一个方案。
- 保存定时或星期切换后，会写入当前用户自启动；自启动时使用 `--background`，不显示界面。
- 生成安装包时优先生成独立 PyInstaller EXE；检测到 WinRAR 后会再封装 WinRAR 自解压包。
- 错误会追加到 `错误记录.md`。

## 运行

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 打包主程序

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --onefile --clean --name 鼠标配置生成器 --add-data "assets;assets" --add-data "1439978017.svg;." --add-data "小垚_鼠标指针_ByAsunny.zip;." --add-data "鼠鼠_动态鼠标指针(右击解压).zip;." main.py
```

输出位置：

```text
dist\鼠标配置生成器.exe
```
