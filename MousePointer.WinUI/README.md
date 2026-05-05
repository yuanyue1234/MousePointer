# 鼠标指针配置管理器 WinUI

这是现有 Python 版鼠标指针配置管理器的 C# + WinUI 3 迁移工程。新工程保留原项目功能边界，并把领域逻辑、Windows 系统接口和 WinUI 界面拆开维护。

## 项目结构

```text
MousePointer.WinUI/
  src/
    MousePointer.Core/        # 领域模型、导入、INF 解析、注册表、调度、安装包生成
    MousePointer.App/         # WinUI 3 界面、后台/托盘入口、页面交互
  tests/
    MousePointer.Core.Tests/  # 角色匹配和 INF 解析回归测试
  docs/
    specification.md
    architecture.md
    migration-plan.md
    testing.md
```

## 当前能力

- 鼠标角色模型：覆盖 17 个 Windows 鼠标状态，包含 `Pin` 和 `Person`。
- 方案管理：新建、重命名、删除、载入、保存、资源库列表。
- 导入：文件夹、`.zip`、`.rar`、`.7z`、自解压 `.exe`；RAR 优先使用 `runtime\7zip\7z.exe`、系统 7-Zip、WinRAR，再尝试 `tar`。
- 匹配：INF alias、注册表写法和文件名关键词匹配，保留编号兜底。
- 应用：写入 `HKCU\Control Panel\Cursors`，备份/恢复上一份鼠标方案，刷新系统鼠标。
- 大小：1-15 级映射到 32-256px，支持实时写入。
- 素材：`.cur`、`.ani` 原样保存，常见图片可转换为 `.cur`。
- 自动切换：固定时间、星期、计时顺序/随机；`--background` 后台执行，`--tray` 使用 Win32 托盘图标。
- 设置：存储目录、输出目录、自启动、文件关联、GitHub 更新检查、诊断信息。
- 生成安装包：为当前方案生成一个单文件安装器工程并发布为 x64 exe。

## 构建

```powershell
dotnet restore .\MousePointer.WinUI.sln
dotnet build .\MousePointer.WinUI.sln -c Debug
dotnet test .\tests\MousePointer.Core.Tests\MousePointer.Core.Tests.csproj -c Debug
```

WinUI App 目标平台为 Windows x64，最低系统版本 Windows 10 2004 (`10.0.19041.0`)。

## 运行

开发期可从项目目录运行：

```powershell
dotnet run --project .\src\MousePointer.App\MousePointer.App.csproj -c Debug -p:Platform=x64
```

后台模式：

```powershell
dotnet run --project .\src\MousePointer.App\MousePointer.App.csproj -c Debug -p:Platform=x64 -- --background
dotnet run --project .\src\MousePointer.App\MousePointer.App.csproj -c Debug -p:Platform=x64 -- --tray
```

涉及注册表、系统鼠标、自启动和文件关联的功能需要在真实 Windows 环境手测。

