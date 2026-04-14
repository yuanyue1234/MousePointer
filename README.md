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
- 勾选“自启动并保留后台”后点击应用，开机可进入后台；手动关闭窗口时会隐藏到托盘并继续执行时间/星期切换。
- 托盘图标左键可打开窗口，右键菜单提供“打开”和“退出”。
- 开启自启动后会通过系统托盘通知提示启动选项已更改。
- 定时切换在标题右侧按钮里配置：
  - 亮色模式：时间 + 方案
  - 暗色模式：时间 + 方案
  - 每行有小 `x` 可清除
- 星期切换在标题右侧按钮里配置，每天可选择一个方案。
- 切换方案时，下方每个鼠标状态的文件配置和右侧实时预览会同步更新。
- 鼠标方案表格使用整行宽度，滚轮滚动，不显示右侧滚动条。
- 设置页可以修改鼠标文件存放位置，默认位于 Roaming：`%APPDATA%\MouseCursorThemeBuilder\mouse_files`。
- 设置页可以修改安装包默认保存位置，默认位于 Roaming：`%APPDATA%\MouseCursorThemeBuilder\installers`。
- 资源库页面会打开在线资源库，并优先使用 Edge App 模式把下载目录指向鼠标文件存放位置。
- 鼠标悬停到下方配置行时，右侧预览会立即切换到该行；动态 `.ani` 会循环播放预览。
- 鼠标方案页支持新建方案、删除自定义方案。
- 时间切换和星期切换在左侧导航中进入，不再弹出新窗口。
- 右侧预览区支持鼠标移入后跟随鼠标移动，移出后回到中间。
- UI 图标统一为 Google Material 3 / Material Symbols 的圆角线性风格。Material Symbols 参考：https://github.com/google/material-design-icons
- 生成安装包时会先选择保存位置，只使用 Python/PyInstaller 生成独立 EXE，完成后自动打开对应文件夹。
- 生成的安装包会优先使用“正常选择”鼠标指针图像作为 EXE 图标，并且不显示 Python 命令行窗口。
- 应用方案和生成安装包会显示等待窗口，耗时任务在后台执行。
- 时间切换和星期切换应用时同样显示等待窗口。
- 资源库页支持拖入 `zip/rar/7z/exe` 并自动添加为新方案，下方会显示已有资源的图标预览。
- 资源库已有资源区支持纵向滚动；每个方案的图标条支持 `Shift + 滚轮` 或鼠标拖拽横向查看。
- 实时预览上方可调整鼠标大小，范围 `1-15`，对应 `32px-256px`；应用时始终按滑条值先刷新鼠标参数，写入 Windows `CursorBaseSize`，再应用指针方案。
- “清除”用于恢复 Windows 默认鼠标指针，不会清空当前方案配置。
- 时间切换和星期切换的方案下拉默认为空。
- 支持拖入由本工具生成的 PyInstaller 单文件 EXE，会从内置素材中读取鼠标文件并添加为新方案。
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
