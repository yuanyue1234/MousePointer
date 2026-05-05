# 测试说明

## 自动化测试

```powershell
dotnet test .\tests\MousePointer.Core.Tests\MousePointer.Core.Tests.csproj -c Debug
```

当前自动化覆盖：

- `Hand` 和 `NWPen` 不互相误判。
- `Pin`、`Person` 参与完整 17 角色编号兜底。
- INF alias 和注册表写法可解析到对应文件。

## 构建验证

```powershell
dotnet build .\MousePointer.WinUI.sln -c Debug
dotnet build .\src\MousePointer.App\MousePointer.App.csproj -c Debug -p:Platform=x64
```

## 真机手测

- 应用鼠标方案前，确认能恢复备份。
- 在普通用户权限下验证 HKCU 写入。
- Win10 / Win11 分别验证系统鼠标刷新。
- 100%、125%、150% DPI 验证 WinUI 布局。
- 验证 `--tray` 托盘右键打开/退出。
- 验证 Run 自启动项是否按设置写入。
- 验证 `.cur` / `.ani` 文件关联能恢复原关联。

