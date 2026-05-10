# 第一批修复验收说明

本轮修改方向是正确的，语法检查已通过，资源库地址、`.ani` 预览兜底、RAR 多后端导入路径都已经进入正确方向。当前还需要补齐 3 个明确点，补完后再进入下一轮验收会更稳。

## 必须修复 1：角色匹配继续收紧

当前 `map_files_to_roles()` 的匹配规则还需要再调整：

- `link.cur` 需要稳定匹配到 `Hand`，不能匹配到 `NWPen`。
- `hand.cur` 需要匹配到 `Hand`。
- `pointer_hand.cur` 需要匹配到 `Hand`，不能被 `pointer` 提前匹配到 `Arrow`。
- 中文文件名如 `手写.cur`、`精确选择.cur`、`位置选择.cur`、`个人选择.cur` 需要命中对应角色。

请把匹配逻辑改成“精确别名优先、短词避免子串误伤、中文关键词补齐”的方式。`hand/link` 归到 `Hand`，`pen/nwpen/手写` 归到 `NWPen`，`cross/精确选择` 归到 `Crosshair`，`pin/位置选择` 归到 `Pin`，`person/个人选择` 归到 `Person`。

建议至少用下面的脚本验证：

```powershell
@'
from pathlib import Path
import main

cases = [
    "hand.cur",
    "link.cur",
    "pointer_hand.cur",
    "pen.cur",
    "手写.cur",
    "cross.cur",
    "精确选择.cur",
    "pin.cur",
    "位置选择.cur",
    "person.cur",
    "个人选择.cur",
]

for name in cases:
    print(name, "=>", {k: v.name for k, v in main.map_files_to_roles([Path(name)]).items()})
'@ | .\.venv\Scripts\python.exe -
```

## 必须修复 2：内置 PyInstaller 运行时需要真正接入

当前 spec 已准备把 `runtime` 带入包体，但 `find_python_with_pyinstaller()` 仍然只查 `.venv` 和系统 PATH。这样在干净机器上仍可能报“找不到包含 PyInstaller 的 Python”。

请让 `find_python_with_pyinstaller()` 优先查找：

```text
resource_path("runtime/python/Scripts/python.exe")
resource_path("runtime/python/python.exe")
```

同时，检测 `import PyInstaller` 的子进程也需要使用 `CREATE_NO_WINDOW`，避免生成安装包或检测运行时时弹黑框。

## 必须修复 3：切换状态文件不要半接入

当前新增了 `switch_state.json` 相关函数，但调度循环没有写入它，`next_switch_text()` 却开始读取它。这会造成“下次切换”显示不准确。

这一轮建议二选一：

- 方案 A：完整接入，在时间、星期、计时切换成功应用后写入状态。
- 方案 B：先移除本轮新增的 `switch_state.json` 逻辑，等计时切换重做时再统一实现。

为了保持这批修复低耦合，建议先采用方案 B。

## 可以保留的改动

以下改动可以保留，并在修复上述问题后继续验收：

- 在线资源库地址改为 `http://8.135.33.2:5002/`。
- `.ani` 预览失败时显示占位图。
- Fluent UI 统一走后端预览链路。
- RAR 导入改为 7-Zip、WinRAR、rarfile 多后端尝试。
- `发布测试清单.md` 和 `docs/test-assets.md` 的回归记录。

## 重新验收要求

修复后请重新运行：

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py fluent_ui.py
```

同时附上角色匹配脚本输出。角色匹配和内置 PyInstaller 查找路径通过后，这一批修复可以进入真实素材回归。

