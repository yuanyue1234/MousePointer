# 第二批修复验收说明

本轮已经把“当前配置 / 下次切换”、拖入替换资源、动静标识、计时切换状态等能力推进到了可测试阶段，方向是对的。当前测试中出现了一个阻塞错误，并且动静标识的展示范围需要按产品预期收紧。下面是下一步给程序员的明确修改意见。

## 第一批返工复验补充

`first-batch-review-notes.md` 中的 3 个必修项目前基本已经收口：

- 角色匹配已按“精确 token 优先，长词拼接补充命中”调整，`hand/link/pointer_hand`、`pen/手写`、`cross/精确选择`、`pin/位置选择`、`person/个人选择` 的方向正确。
- `find_python_with_pyinstaller()` 已优先查找 `runtime/python/Scripts/python.exe` 和 `runtime/python/python.exe`，并且检测 `import PyInstaller` 时使用 `CREATE_NO_WINDOW`。
- `switch_state.json` 的半接入逻辑已经移除，当前 `main.py` 和 `fluent_ui.py` 没有残留引用。

还需要继续保留两个验收边界：

- 源码模式下 `find_python_with_pyinstaller()` 返回 `.venv\Scripts\python.exe` 是预期行为，不算问题；真正要验证的是打包后的 EXE 是否能在无系统 Python 或不依赖 `.venv` 的环境中使用 `runtime/python/Scripts/python.exe` 生成安装包。
- 角色匹配脚本要继续用 `\u` 形式覆盖中文文件名，避免 PowerShell 控制台编码把中文输入变成 `??` 后造成误判。

建议在下一轮补充这条打包后验证：

```text
从 dist/鼠标指针配置生成器_绿色程序.exe 启动程序，执行“生成安装包”，确认不会报找不到 PyInstaller，也不会弹黑色控制台窗口。
```

## 必须修复 1：先修复 `SchemePage` 崩溃

当前报错：

```text
'SchemePage' object has no attribute 'scheme_page'
```

问题位置在 `fluent_ui.py` 的 `SchemePage.loadScheme()` 附近。`SchemePage` 自己就是方案页对象，内部不应该调用 `self.scheme_page.updateRuntimeInfo()`。

请改成直接调用：

```python
self.updateRuntimeInfo()
```

并检查同类问题：只有资源库页、切换页、设置页这类“持有方案页引用”的页面才应该使用 `self.scheme_page`；`SchemePage` 类内部统一使用 `self`。

验收要求：

- 打开程序不再出现 `SchemePage object has no attribute scheme_page`。
- 在方案下拉框切换方案时不报错。
- 载入方案后右侧“当前配置 / 下次切换”区域正常显示。
- 手动应用方案后，状态栏和右侧运行状态都能刷新。

## 必须修复 2：动/静标识只按指定位置显示

当前实现把 `动 / 静` 放进了通用 `CursorPreview`，这会导致资源库里每一个图标都显示标识。这个不是目标效果。

目标效果如下：

- 鼠标方案界面：每个鼠标指针图标左上角可以显示 `动 / 静`。
- 替换鼠标指针资源池：每个资源图标左上角可以显示 `动 / 静`。
- 资源库界面：不要在每个鼠标图标上显示 `动 / 静`。
- 资源库界面：只在方案名称旁显示一次汇总标识。

资源库方案名称旁的显示规则：

- 如果该方案包含 `.ani`，显示 `动`。
- 如果该方案包含 `.cur`，显示 `静`。
- 如果两种都有，显示 `动` 和 `静` 两个小标识。
- 如果需要更清楚，可以显示数量，例如 `动 3`、`静 14`。
- 图片、未知格式、缺失文件暂不参与统计。

推荐实现方式：

- 不要让 `CursorPreview` 默认总是画 badge。
- 给 `CursorPreview` 增加参数，例如 `showBadge: bool = True`。
- 鼠标方案页和替换资源池调用 `setPath(..., showBadge=True)`。
- 资源库预览图调用 `setPath(..., showBadge=False)`。
- 在资源库卡片标题行单独计算并显示汇总 badge。

资源库汇总可以做一个小函数：

```python
def cursor_kind_summary(scheme_dir: Path, files: dict[str, str]) -> tuple[int, int]:
    ani_count = 0
    cur_count = 0
    for file_name in files.values():
        suffix = (scheme_dir / file_name).suffix.lower()
        if suffix == ".ani":
            ani_count += 1
        elif suffix == ".cur":
            cur_count += 1
    return ani_count, cur_count
```

验收要求：

- 鼠标方案页 `.ani` 图标左上角显示 `动`。
- 鼠标方案页 `.cur` 图标左上角显示 `静`。
- 替换鼠标指针资源池中的 `.ani / .cur` 显示对应标识。
- 资源库每个方案卡片的预览小图不再显示 `动 / 静`。
- 资源库只在方案名称旁显示一次汇总标识。

## 必须修复 3：拖入替换资源只接收资源文件

替换鼠标指针资源池现在支持拖入文件，这是正确方向。这里需要明确边界，避免后续和资源库导入逻辑混在一起。

替换资源池只接收：

```text
.cur
.ani
.png
.jpg
.jpeg
.bmp
.gif
.webp
.ico
```

如果拖入 `.zip / .rar / .7z / .exe / 文件夹`，不要加入替换资源池，应该提示用户去资源库导入区操作。

验收要求：

- 拖入 `.cur` 后资源池新增该资源。
- 拖入 `.ani` 后资源池新增该资源。
- 拖入图片后资源池新增该资源。
- 拖入压缩包不会进入替换资源池，界面给出清晰提示。

## 继续观察：当前配置和下次切换

本轮新增“当前配置 / 下次切换”是对的，但要在修复崩溃后重新测试。

重新验收时请覆盖：

- 手动应用方案后，“当前配置”刷新为实际方案名。
- 保存时间切换设置后，“下次切换”刷新。
- 保存计时切换设置后，“下次切换”显示计时结果。
- 保存星期切换设置后，“下次切换”显示最近一次星期切换。
- 自动切换真正触发后，系统鼠标、方案页下拉框、右侧“当前配置”三者一致。

注意：如果 `switch_state.json` 已经正式接入，就必须保证每次自动切换成功后都写入状态。不要只在 UI 保存时写，也不要在应用失败时写。

## 可以保留的改动

以下改动可以保留，修完上面问题后继续测试：

- 右侧新增“当前配置 / 下次切换”状态显示。
- 自动切换后同步方案页 UI。
- 计时切换状态文件用于计算下次切换。
- 替换资源区支持拖入单个资源文件。
- `.ani / .cur` 标识能力本身保留，但展示位置按本说明收紧。
- 绿色版 spec 使用 `Tree` 或等效方式带入 `runtime`。

## 本轮不建议继续扩大的范围

下面这些仍按原计划放到后续批次，不要混进这次返工：

- 计时切换 UI 重做。
- 方案列表 hover、小 X、移回素材池。
- 托盘和自启动真机验证。
- 补齐 `runtime/7zip` 实体并做 RAR 真机回归。
- README 和网页下载链接同步。

## 重新验收命令

修复后请先运行：

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py fluent_ui.py
```

继续保留第一批角色匹配回归：

```powershell
@'
from pathlib import Path
import main

cases = [
    "hand.cur",
    "link.cur",
    "pointer_hand.cur",
    "pen.cur",
    "\u624b\u5199.cur",
    "cross.cur",
    "\u7cbe\u786e\u9009\u62e9.cur",
    "pin.cur",
    "\u4f4d\u7f6e\u9009\u62e9.cur",
    "person.cur",
    "\u4e2a\u4eba\u9009\u62e9.cur",
]

for name in cases:
    print(name.encode("unicode_escape").decode(), "=>", {k: v.name.encode("unicode_escape").decode() for k, v in main.map_files_to_roles([Path(name)]).items()})
'@ | .\.venv\Scripts\python.exe -
```

然后用当前打包产物重新测试：

```text
dist/鼠标指针配置生成器_绿色程序.exe
```

这轮验收通过标准很明确：程序不再崩溃；动/静标识只出现在方案页图标、替换资源池图标、资源库方案名旁；资源库预览小图不再逐个显示动静标识。
