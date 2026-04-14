# 鼠标指针配置管理器

Windows 鼠标指针方案图形化工具。支持导入鼠标资源包、编辑每个鼠标状态对应的文件、实时预览、应用当前方案，并生成不显示命令行窗口的独立安装包。

## 当前功能

- 鼠标方案页支持新建、重命名、删除、导入、保存、应用和生成安装包。
- 每行支持拖入图片、`.cur`、`.ani`、`zip`、`rar`、`7z`、`exe`；拖入资源包会识别并添加为新方案。
- 右侧实时预览支持 `.cur`、`.ani` 和普通图片；动态指针会循环播放，鼠标移入预览区后会跟随移动，移出后回到中间。
- 实时预览上方保留大小滑条，范围 `1-15`，只用于判断预览大小，不会写入系统，也不会写入安装包。
- 保留“鼠标大小设置”按钮，点击后跳转 Windows 鼠标指针大小设置；提示为“更改鼠标至对应大小后应用方案”。
- 应用方案只写入鼠标指针方案，不再直接写入 Windows 指针大小。
- 生成安装包时先选择保存位置；点击“生成完成”提示后才打开对应文件夹；安装包不携带鼠标大小配置。
- 生成的安装包优先使用“正常选择”指针图像作为 EXE 图标；`.cur/.ani` 会先转换为 `.ico`，并使用 PyInstaller `--noconsole --windowed`。
- 应用方案和生成安装包会显示居中等待窗口，耗时任务在后台线程执行。
- 勾选“自启动并保留后台”后，会写入 HKCU Run 项、启动文件夹快捷方式，并创建任务计划程序登录触发项；关闭窗口会保留托盘后台，托盘左键打开窗口，右键菜单提供“打开”和“退出”。
- 时间切换和星期切换默认不预填方案，应用时同样走等待窗口。
- 设置页可修改鼠标文件存放位置，默认位于 `%APPDATA%\MouseCursorThemeBuilder\mouse_files`；也可设置安装包默认保存位置，并提供“像素指针指南文章”和“工具制作 BY ASUNNY”跳转。
- 资源库页可打开在线资源库、打开鼠标文件存放位置、刷新本地资源。
- 资源库已有资源会随整页滚动，支持切换宫格显示；每个方案提供应用、编辑、打开文件夹、删除快捷按钮；每个方案内部图标条支持 `Shift + 滚轮` 横向查看。
- 设置页提供 GitHub 源地址、检测更新并自动替换程序、检测自启动状态、测试后台启动、恢复应用前鼠标方案、打开错误记录、复制诊断信息。
- 安装模式支持生成安装版：把 EXE 命名为 `安装鼠标指针配置管理器.exe` 后运行，会安装到 `%LOCALAPPDATA%\Programs\MouseCursorPointerManager`，并在安装目录放置 `卸载鼠标指针配置管理器.exe`。
- 卸载程序会询问是否保留鼠标指针文件；选择保留并打开后，会打开鼠标文件夹并创建桌面快捷方式。
- 错误会追加到 `错误记录.md`。

## 运行

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 打包主程序

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --windowed --onefile --clean --name 鼠标指针配置管理器 --icon "assets\app.ico" --add-data "assets;assets" --add-data "icon终.png;." --add-data "icon.png;." --add-data "1439978017.svg;." --add-data "小垚_鼠标指针_ByAsunny.zip;." --add-data "鼠鼠_动态鼠标指针(右击解压).zip;." --add-data "DangoDaikazoku_团子大家族v1.0.zip;." --add-data "win11cus-gnb-jj_syb_109345.zip;." main.py
```

输出位置：

```text
dist\鼠标指针配置管理器.exe
dist\安装鼠标指针配置管理器.exe
```

## GitHub Release

推送 `v*` 标签时，GitHub Actions 会把 `release-assets/*.exe` 上传到 Releases。
