# 鼠标指针配置生成器

Windows 图形化鼠标指针方案工具。可以导入鼠标压缩包或安装包，预览鼠标指针，应用到当前电脑，并生成独立安装器。

## 当前功能

- 左侧是从 `1439978017.svg` 裁切出的参考图标。
- 右侧是实时大预览，支持普通图片、`.cur`、`.ani`。
- 支持拖入文件到对应鼠标状态行。
- 支持导入 `zip/rar/7z/exe`，优先解压并读取 `.inf`，再匹配 `.cur/.ani`。EXE 需要是自解压压缩包才能直接读取。
- 项目内置鼠标指针 zip，启动时自动导入为 `01方案`、`02方案`。
- 其他内置 zip 作为资源库方案，进入资源库页面点击刷新后会自动解压并添加。
- 保留 Windows 鼠标大小设置跳转按钮，并提示“建议调整大小后再应用。”
- 勾选“自启动后台”后点击应用，后台启动不会显示界面，手动打开仍显示界面。
- 定时切换在标题右侧按钮里配置：
  - 亮色模式：时间 + 方案
  - 暗色模式：时间 + 方案
  - 每行有小 `x` 可清除
- 星期切换在标题右侧按钮里配置，每天可选择一个方案。
- 切换方案时，下方每个鼠标状态的文件配置和右侧实时预览会同步更新。
- 鼠标方案表格使用整行宽度，滚轮滚动，不显示右侧滚动条。
- 设置页可以修改鼠标文件存放位置，默认位于 Roaming：`%APPDATA%\MouseCursorThemeBuilder\mouse_files`。
- 资源库页面会打开在线资源库，并优先使用 Edge App 模式把下载目录指向鼠标文件存放位置。
- 鼠标悬停到下方配置行时，右侧预览会立即切换到该行；动态 `.ani` 会循环播放预览。
- 鼠标方案页支持新建方案、删除自定义方案。
- 时间切换和星期切换在左侧导航中进入，不再弹出新窗口。
- 右侧预览区支持鼠标移入后跟随鼠标移动，移出后回到中间。
- UI 图标统一为 Google Material 3 / Material Symbols 的圆角线性风格。Material Symbols 参考：https://github.com/google/material-design-icons
- 生成安装包时优先生成独立 PyInstaller EXE；检测到 WinRAR 后会再封装 WinRAR 自解压包。
- 错误会追加到 `错误记录.md`。

## 运行

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 打包主程序

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --onefile --clean --name 鼠标配置生成器 --icon "assets\app.ico" --add-data "assets;assets" --add-data "icon.png;." --add-data "1439978017.svg;." --add-data "小垚_鼠标指针_ByAsunny.zip;." --add-data "鼠鼠_动态鼠标指针(右击解压).zip;." --add-data "DangoDaikazoku_团子大家族v1.0.zip;." --add-data "win11cus-gnb-jj_syb_109345.zip;." main.py
```

输出位置：

```text
dist\鼠标配置生成器.exe
```
