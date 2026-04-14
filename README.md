# 鼠标指针配置生成器

Windows 鼠标指针方案图形化工具。支持导入鼠标资源包、编辑每个鼠标状态对应的文件、实时预览、应用当前方案，并生成不显示命令行窗口的独立安装包。

## 当前功能

- 鼠标方案页支持新建、重命名、删除、导入、保存、应用和生成安装包。
- 每行支持拖入图片、`.cur`、`.ani`、`zip`、`rar`、`7z`、`exe`；拖入资源包会识别并添加为新方案。
- 右侧实时预览支持 `.cur`、`.ani` 和普通图片；动态指针会循环播放，鼠标移入预览区后会跟随移动，移出后回到中间。
- 保留“鼠标大小设置”按钮，点击后跳转 Windows 鼠标指针大小设置；提示为“更改鼠标至对应大小后应用方案”。
- 应用方案前会刷新鼠标参数并写入指针方案，不再直接写入 Windows 指针大小。
- 生成安装包时先选择保存位置，完成后自动打开对应文件夹；安装包不携带鼠标大小配置。
- 生成的安装包优先使用“正常选择”指针图像作为 EXE 图标，并使用 PyInstaller `--noconsole`。
- 应用方案和生成安装包会显示居中等待窗口，耗时任务在后台线程执行。
- 勾选“自启动并保留后台”后，关闭窗口会保留托盘后台；托盘左键打开窗口，右键菜单提供“打开”和“退出”。
- 时间切换和星期切换默认不预填方案，应用时同样走等待窗口。
- 设置页可修改鼠标文件存放位置，默认位于 `%APPDATA%\MouseCursorThemeBuilder\mouse_files`；也可设置安装包默认保存位置。
- 资源库页可打开在线资源库、打开鼠标文件存放位置、刷新本地资源。
- 资源库已有资源会随整页滚动；每个方案内部图标条支持鼠标拖动或 `Shift + 滚轮` 横向查看，不显示横向滚动条。
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
