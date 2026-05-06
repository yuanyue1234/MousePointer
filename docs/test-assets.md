# 测试素材台账

用于登记 bug 修复计划中要求的真实测试素材。没有素材时不要默认判定“已修复”，而是标记为“需要补素材”。

## 字段说明

- `素材类型`：用于哪一类回归测试。
- `建议文件名`：建议统一命名，方便团队复用。
- `来源`：素材来源或获取方式。
- `覆盖问题`：对应 `bug-fix-plan.md` 中的修复主题。
- `预期结果`：导入、预览、切换、打包时的预期表现。
- `状态`：`已准备` / `需要补素材` / `需要真机验证`。

## 素材清单

| 素材类型 | 建议文件名 | 来源 | 覆盖问题 | 预期结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 单个静态指针 | `single-arrow.cur` | 本地现有或从公开鼠标主题中提取 | 基础导入、单角色替换 | 可直接导入，角色预览正常，应用正常 | 需要补素材 |
| 普通动画指针 | `single-working.ani` | 公开鼠标主题包 | `.ani` 正常预览路径 | 可播放动画预览，应用正常 | 需要补素材 |
| 无法拆帧的纯 `.ani` | `fallback-only.ani` | 真实问题样本，需保留原文件 | `.ani` 预览兜底 | 至少显示首帧或占位图，不空白，不阻止应用 | 需要补素材 |
| 图片转指针样本 | `source-image.png` | 任意透明背景 PNG | 图片拖入角色行 | 可生成预览，应用时可转换为可用指针 | 需要补素材 |
| 普通 ZIP 鼠标包 | `theme-basic.zip` | 公开主题包 | `.zip` 导入、多文件匹配 | 导入成功，角色匹配正确 | 需要补素材 |
| 普通 RAR 鼠标包 | `theme-basic.rar` | 与 ZIP 同源，重新打包成 RAR | `.rar` 导入兼容 | 未安装 WinRAR 时也能导入 | 需要补素材 |
| 加密 RAR 鼠标包 | `theme-encrypted.rar` | 用普通主题包加密码重新打包 | 加密 RAR 错误提示 | 不闪退，提示暂不支持加密压缩包 | 需要补素材 |
| 7z 鼠标包 | `theme-basic.7z` | 与 ZIP 同源，重新打包成 7z | `.7z` 导入兼容 | 导入成功 | 需要补素材 |
| 自解压 EXE 鼠标包 | `theme-selfextract.exe` | 真实主题安装包或自制自解压包 | `.exe` 导入兼容 | 可识别并导入主题 | 需要补素材 |
| 多 INF 压缩包 | `theme-multi-inf.zip` | 真实多主题包 | 多 INF 批量导入 | 一次导入多个方案，结果统计正确 | 需要补素材 |
| 命名不规范主题包 | `theme-role-alias-mixed.zip` | 手工整理一组 `pen/cross/pin/person/hand/link` 文件 | 角色匹配修复 | `NWPen`、`Crosshair`、`Pin`、`Person`、`Hand` 落位正确 | 需要补素材 |
| 老主题包 | `theme-legacy-no-pin-person.zip` | 不包含 `Pin/Person` 的旧鼠标包 | 旧包兼容性 | 不报错，可正常导入已有角色 | 需要补素材 |
| 资源库多方案样本 | `library-selection-set/` | 至少 5 个已导入方案目录 | 资源库选择、应用、删除 | 列表/宫格视图选择一致，单选可应用和删除 | 需要补素材 |
| 动静混合方案 | `theme-ani-cur-mixed.zip` | 同时包含 `.ani` 和 `.cur` 的主题包 | 动静汇总标识 | 方案页和替换池显示标识，资源库只显示汇总 | 需要补素材 |
| 启动与托盘诊断样本 | `startup-diagnostics.txt` | 每次真机验证后记录 | 自启动、托盘、后台 | 能记录 Run、启动目录、任务计划、PID、进程路径 | 需要真机验证 |
| 干净系统打包环境记录 | `clean-win-build-notes.md` | Win10 / Win11 无 Python 环境实测 | 安装包运行时、黑框问题 | 能明确验证“可生成安装包”或“清晰降级提示” | 需要真机验证 |

## 最小手测素材组合

### 导入最小组合

- `single-arrow.cur`
- `single-working.ani`
- `fallback-only.ani`
- `theme-basic.zip`
- `theme-basic.rar`
- `theme-basic.7z`
- `theme-selfextract.exe`
- 1 个原始文件夹主题
- `theme-multi-inf.zip`

### 匹配最小组合

- `theme-role-alias-mixed.zip`
- `theme-legacy-no-pin-person.zip`

### 资源库交互最小组合

- `library-selection-set/`
- `theme-ani-cur-mixed.zip`
- 至少 1 个只含 `.cur` 的方案
- 至少 1 个只含 `.ani` 的方案
- 至少 1 个动静混合方案

### 打包与启动最小组合

- 1 台 Win10 x64 干净机器
- 1 台 Win11 x64 干净机器
- 记录启动耗时、托盘行为、自启动行为的诊断输出

## 采集要求

- 保留原始文件名和来源链接，避免后续无法复现。
- 同一素材如果做了二次打包，保留原包和再打包结果。
- 对“无法拆帧的 `.ani`”和“加密 `.rar`”必须保留真实问题样本，不能只用推测样本替代。
- 涉及系统鼠标、自启动、托盘、后台的验证结果，必须写明 Windows 版本、系统架构、是否管理员、是否安装安全软件。
