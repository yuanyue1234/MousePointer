# UI 小窗口闪烁排查经验总结

日期：2026-05-10

## 背景

这次“点击按钮、切换方案时闪出小窗口”的问题被反复检查了 5 次以上。前几轮修复没有真正解决问题，主要原因不是技术能力不够，而是排查方法失控：在没有把触发源缩小到最小范围前，就开始改全局弹窗、下拉框、窗口图标、打包方式和 UI 控件。

这类问题以后必须按证据推进，不能靠猜。

## 最终确定的关键错误

最终最有价值的定位是：可疑窗口并不是 Python 解释器窗口，也不是普通业务弹窗，而是 Qt 内部创建的临时顶层窗口。

日志里出现过：

```text
Qt6110QWindowPopupSaveBits
Qt6110QWindowIcon
```

更关键的是，`ui_debug.log` 里同时反复出现了无父窗口的顶层 `QLabel`：

```text
class=QLabel title='' size=12x16 parent='' text='动'
```

这说明某些小标签在还没有被加入布局、还没有父控件时就被 `setVisible(True)` 显示了。Qt 会把这种没有父控件的可见 QWidget 当成临时顶层窗口处理，于是用户看到类似空白小窗的一闪。

也就是说，真正应该优先检查的是：

```python
label = QLabel()
style_kind_chip(label, text)  # 这里如果直接 setVisible(True)，但 label 还没 addWidget，就有风险
layout.addWidget(label)
```

而不是一上来重写 ComboBox、全局隐藏窗口、改所有弹窗样式。

## 为什么前面多次没修好

1. 把日志里的 `Qt6110QWindowIcon` 误判成窗口图标或解释器问题，忽略了同一时间出现的顶层 `QLabel`。

2. 先做“大范围修复”，后做“最小复现验证”，顺序反了。

3. 用全局 suppress/hide 去压窗口，结果可能误伤 tooltip、InfoBar、小标签、菜单等 Qt 辅助控件。

4. 看到 ComboBox popup 有问题后，把所有下拉控件当成主因，后来证明“方案切换闪窗”不是单纯 ComboBox。

5. 打包路径和测试对象一度混乱，`dist`、`release-assets`、目录版、单文件版没有严格区分，导致验证结论不稳。

6. 回退时没有先列清“保留项”和“撤回项”，误把不该回退的功能改动也回退了。

## 正确排查方法

以后遇到 UI 闪窗，必须按下面顺序做：

1. 先保留用户可复现动作，只做诊断，不改 UI 行为。

2. 同时记录 Qt 层事件和 Win32 层窗口事件：

```text
Qt show event: class / title / size / parent / text / objectName
WinEvent show: hwnd / pid / class / title / size / process path
```

3. 用 master 或上一个稳定提交做同样动作对照，确认问题是哪个改动之后出现的。

4. 对可疑点做最小开关实验，一次只关一个因素：

```text
只关 ComboBox popup
只关窗口 setWindowIcon
只关某个 QLabel chip
只关某个 InfoBar
```

5. 如果关掉某个点后日志归零，再做最小代码修复。

6. 修复后必须用同一个脚本验证源码版和打包版，不能换测试对象。

## 以后禁止的做法

不要再做这些：

- 不要全局隐藏所有小窗口。
- 不要为了一个闪窗问题替换整页控件。
- 不要在没确认根因前改打包形态。
- 不要把 `QLabel`、tooltip、InfoBar、菜单这类 Qt 辅助控件当成“垃圾窗口”直接 suppress。
- 不要在没有清单的情况下回退文件。

## 修复原则

如果根因是父控件为空的 QLabel/小 chip，修复应当很小：

```python
def set_label_visible_after_parent(label, visible):
    if visible and label.parentWidget() is None:
        label.hide()
        QTimer.singleShot(0, lambda: label.setVisible(label.parentWidget() is not None and bool(label.text())))
        return
    label.setVisible(visible)
```

或者更稳妥：

```python
label = QLabel(parent_widget)
layout.addWidget(label)
style_kind_chip(label, text)
```

核心原则：控件先挂到父控件和布局，再显示。

## 验收标准

一次修复不能只靠肉眼说“好像没了”，必须满足：

- 用户动作：从“鼠标方案 1”切到“鼠标方案 2”。
- 重复 10 次。
- Win32 采样里没有同进程的小尺寸 `Qt*QWindow*` 可疑窗口。
- Qt 日志里没有无父窗口、无标题、小尺寸、文本为 `动/静` 的顶层 `QLabel`。
- 源码版和实际交付的打包版都通过。

## 最重要的经验

这次最大的教训是：复杂 UI bug 不能靠“感觉像什么”来修。日志里每一个字段都要解释清楚，尤其是 `class`、`parent`、`text` 和 `process path`。

当一个 bug 修了 2 次还没好，就必须停止扩大改动，回到最小复现、最小开关、最小补丁。否则越修越乱。
