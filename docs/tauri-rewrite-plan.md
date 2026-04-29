# MousePointer Tauri 重写计划

> 状态: 计划阶段 / 未开工 · 创建于 2026-04-29 · 分支: `claudeCode`
> 当前 Python 版 bug 修复历史在 `codex/bugfix-stability-plan` 分支,本计划与之并存。

---

## 1. 背景与目标

Python + PySide6 + qfluentwidgets 的现版本累积了较多技术债务,具体表现:

- `main.py` 213 KB / `fluent_ui.py` 153 KB,单文件包揽全部职能,多轮 monkey patch
- PyInstaller 打包后 exe 约 60 MB,冷启动慢,常被杀软误报
- 第三方 qfluentwidgets 与原生 Fluent 始终存在 gap,upstream bug 多
- 启动后才显示主窗口、资源扫描阻塞 UI

**重写目标**

| 维度 | 现状 | 目标 |
|---|---|---|
| Portable EXE 体积 | ~60 MB | 5–10 MB |
| 冷启动至窗口可见 | > 2 s | ≤ 600 ms |
| 视觉 | 仿 Fluent | Animal Island 风(暖色系卡片、大圆角、动效) |
| 单文件最大体积 | > 150 KB | < 25 KB |
| 自动化测试 | 无 | Rust 单测 + 角色匹配回归 |
| Release 自动化 | 仅 portable | MSI + portable + 签名 update.json |

**不在范围**: macOS / Linux 移植、ARM64 架构、Python 版后续 bug 修复(冻结于 codex 分支)。

---

## 2. 技术栈

| 层 | 选型 | 版本 | 备注 |
|---|---|---|---|
| 桌面壳 | Tauri | 2.x | Webview2 内核,Rust 后端 |
| 前端框架 | React | 18.3 | 与 animal-island-ui peerDep 对齐 |
| 类型 | TypeScript | 5.7 | strict |
| 构建 | Vite | 7.x | animal-island-ui 同栈 |
| 样式 | Less | 4.x | animal-island-ui 同栈 |
| UI 库 | animal-island-ui | ^0.7 | 8 组件 + 自补 ~10 |
| 状态 | Zustand | ^4.5 | 轻量,免 Redux 模板 |
| i18n | react-i18next | ^14 | zh-CN / en |
| Win 系统 API | windows-rs | ^0.58 | 注册表 / SystemParametersInfo |
| ZIP | zip | ^2 | pure rust |
| 7Z | sevenz-rust | ^0.6 | pure rust |
| RAR | unrar | ^0.5 | 需 unrar.dll 或源 |
| INF | 自写 parser | — | 无现成 crate |
| 序列化 | serde / serde_json | ^1 | 与 Python settings.json 兼容 |
| 异步 | tokio | ^1 | rt-multi-thread,scheduler 用 |
| 错误 | thiserror / anyhow | ^1 | 库 / bin 分用 |

---

## 3. 目录结构

```
MousePointer/                   (仓库根,与 Python 版并存)
├─ main.py / fluent_ui.py        # 老 Python 版,只读冻结
├─ docs/tauri-rewrite-plan.md    # 本文档
└─ tauri/                        # 新版工程根
    ├─ src-tauri/                # Rust 后端
    │   ├─ src/
    │   │   ├─ commands/         # #[tauri::command] 暴露给 JS
    │   │   ├─ cursor/           # apply / preview / backup
    │   │   ├─ archive/          # zip / 7z / rar / exe / folder 解压
    │   │   ├─ inf/              # INF parser + alias map
    │   │   ├─ matching/         # role matching (复用 Python 11 例)
    │   │   ├─ scheduler/        # time / timer / weekday
    │   │   ├─ tray/             # 托盘菜单
    │   │   ├─ autostart/        # HKCU Run + 启动文件夹 + 任务计划
    │   │   ├─ data/             # 数据目录布局,迁移工具
    │   │   ├─ error.rs
    │   │   ├─ lib.rs
    │   │   └─ main.rs
    │   ├─ icons/                # app icon
    │   ├─ tauri.conf.json
    │   └─ Cargo.toml
    ├─ src/                      # 前端
    │   ├─ pages/                # SchemeListPage / ResourceLibraryPage / SwitchPage / SettingsPage / DiagnosticPage
    │   ├─ components/           # 自补的 List / Tab / Slider / Tooltip / Toast / DnDZone / Tree / Drawer / Segmented / ProgressRing
    │   ├─ hooks/
    │   ├─ stores/               # Zustand: schemes / settings / runtime
    │   ├─ api/                  # invoke 包装,1 文件 1 模块
    │   ├─ locales/              # zh-CN.json / en.json
    │   ├─ styles/               # design tokens, less mixins
    │   ├─ App.tsx
    │   └─ main.tsx
    ├─ index.html
    ├─ package.json
    ├─ tsconfig.json
    ├─ vite.config.ts
    └─ .gitignore
```

---

## 4. 基础部分 (MVP)

预计 2–3 周。每步一个独立 commit。

| # | 步骤 | 要做 | 验收 |
|---|---|---|---|
| B1 | bootstrap | `npm create tauri-app@latest`,选 React + TS;安装 animal-island-ui;改 vite.config 兼容 less | `npm run tauri dev` 能开窗口,Button 组件可渲染 |
| B2 | data 兼容 | 在 Rust 写 `data::paths`,读取 `%APPDATA%\MouseCursorThemeBuilder\` 下旧目录,settings.json 反序列化为新 struct | 单测: 用现成 settings.json 解析无报错 |
| B3 | scheme list page | 调用 `list_schemes` command,前端用 animal-island-ui Card + 自补 List 渲染卡片网格 | 看到老 Python 版同样的方案集合 |
| B4 | apply scheme | Rust `cursor::apply` 写 `HKCU\Control Panel\Cursors` 各角色,调 `SystemParametersInfoW(SPI_SETCURSORS)` | 点击应用,Windows 鼠标指针真切变化;再切回老方案 OK |
| B5 | static .cur 预览 | Rust 用 `LoadImageW + DrawIconEx` 渲染到 PNG 字节流,前端 `<img>` 展示 | 每个角色看到清晰预览图,不模糊 |
| B6 | tray | Tauri 2 tray API: 左键显示 / 右键菜单(打开 / 退出) | 关窗口后留托盘;右键退出后进程消失 |
| B7 | autostart | `tauri-plugin-autostart`,只用 HKCU Run | 设置页开关切换后,重启 Win 验证生效 |
| B8 | CI 打包 | `.github/workflows/release.yml` 用 `tauri-action`,Win Latest,artifacts: MSI + portable EXE | tag `v0.1.0-tauri` push 后 Release 自动出现两份产物 |
| B9 | 基础 settings | 仅含: 自启动开关、显示语言占位、版本号、当前 commit | 设置项保存到 settings.json,重启保留 |

**MVP 完成判定**: 一个不熟悉项目的用户在 Win10 上下载 MSI,安装运行,能看到老 Python 版的方案,点击一个方案后系统鼠标即变化;关闭窗口后保留托盘。

---

## 5. 完整部分

预计 2–3 周。在 MVP 基础上扩展。每步一个独立 commit。

| # | 步骤 | 要做 | 验收 |
|---|---|---|---|
| F01 | 导入: .cur/.ani/单图片 | 文件选择 + 拖拽,文件级落地到 SCHEME_LIBRARY 子目录 | 拖入单文件可建方案 |
| F02 | 导入: .zip | `zip` crate 解压到临时目录,扫 .cur/.ani | zip 主题包成功导入 |
| F03 | 导入: .7z | `sevenz-rust` 解压 | 7z 主题包成功导入 |
| F04 | 导入: .rar | `unrar` crate(若不可用回退捆绑 7-Zip CLI) | rar 主题包成功导入,加密包提示 "暂不支持加密压缩包" |
| F05 | 导入: 自解压 .exe | 检测 PyInstaller CArchive / 普通自解压头,抽 .cur/.ani | 老 Python 版生成的安装器可被识别导入 |
| F06 | 导入: 文件夹 | 递归扫 .cur/.ani/.inf | 直接拖文件夹生效 |
| F07 | INF 解析 | 自写 parser:section + alias_to_reg + 多方案 INF 拆分 | 多 INF 压缩包一次导入产出多个方案 |
| F08 | 角色匹配规则迁移 | 复用 Python `map_files_to_roles` 11 例(`hand/link/手写/精确选择/位置选择/个人选择`等)并写 Rust 单测 | `cargo test` 11 例全过 |
| F09 | .ani 动画 | RIFF 解析帧,Tauri command 推送帧 PNG;Win32 兜底首帧 | 动态指针在预览区动起来;无法解析时显示首帧 |
| F10 | 资源库页 | 卡片网格 + 删除/恢复 + 拖拽导入 + 列表/宫格切换 + 汇总徽章 | 完整对齐 Python 版资源库 |
| F11 | 替换资源池 | DnD 区,白名单 .cur/.ani/png/jpg/jpeg/bmp/gif/webp/ico,拒绝压缩包并提示去资源库 | 拖入压缩包不进池且 Toast 提示 |
| F12 | 切换调度: 时间 | 后端 tokio 任务,到点应用 | 设两个时间点验证切换 |
| F13 | 切换调度: 计时 | 间隔 + 顺序/随机,4×4 宫格 + 多选 + 全选 + 拖动排序 | 对齐 Python bug-fix-plan Step 9 |
| F14 | 切换调度: 星期 | 七天独立配置 | 周一/周二切换正确 |
| F15 | 三模式互斥 | 单页面 + 标题旁 SwitchButton 互斥 + 一个应用按钮 | 启用一种自动关闭其他两种 |
| F16 | 当前/下次切换状态 | `status.json` 写入,前端订阅文件变更 | 自动切换后,UI、托盘、注册表三者一致 |
| F17 | 备份恢复 | 应用前快照 `cursor_backup.json`,设置页 + 资源库均有恢复入口 | 应用后能一键回滚 |
| F18 | 隐藏任务栏双模式 | `--tray` (托盘) / `--background` (纯后台),设置页开关切换 | 开关切换后重启自启动验证 |
| F19 | .inf 安装包生成 | 不再用 PyInstaller;输出 Windows 原生 `.inf`,右键安装即可 | 生成的 .inf 在干净 Win 上右键 → 安装可用 |
| F20 | 自动更新 | `tauri-plugin-updater` + GitHub Release 的 `latest.json`(由 CI 生成签名) | 旧版本启动时检测到新版,提示更新 |
| F21 | i18n | react-i18next,zh-CN / en,所有文案外置 | 切换语言无残留中文/英文 |
| F22 | 诊断页 | Run 项 / 启动文件夹 / 任务计划 / 托盘 PID / 当前 Cursors 注册表 / 数据目录大小 | 复制按钮,粘贴到 issue 即可 |
| F23 | 视觉打磨 | Animal Island 调色,卡片悬停轻动,输入聚焦呼吸光,Toast 入场缓动 | 一致性 visual review 通过 |

**完整版完成判定**: Python 版 [发布测试清单.md](../发布测试清单.md) 全部 90+ 项可勾选通过。

---

## 5b. Tauri Commands 表面 (前后端 API 契约)

下表是前端通过 `@tauri-apps/api/core` 的 `invoke()` 调用的 Rust 命令清单,**作为重写时第一个落地的接口契约**。基础部分(B 阶段)实现前 8 个,完整部分(F 阶段)逐步补齐其余。

| 命令 | 阶段 | 入参 | 返回 | 用途 |
|---|---|---|---|---|
| `list_schemes` | B3 | — | `Vec<SchemeMeta>` | 列出全部方案 |
| `load_scheme` | B3 | `name: String` | `Scheme` (含每角色文件路径) | 详情 |
| `apply_scheme` | B4 | `name: String` | `()` | 写注册表并刷新系统 |
| `preview_cursor` | B5 | `path: String, size: u32` | `Vec<u8>` PNG bytes | 静态预览 |
| `set_autostart` | B7 | `enabled: bool, mode: TrayMode` | `()` | HKCU Run 写入/删除 |
| `read_settings` | B9 | — | `Settings` | 读全局配置 |
| `write_settings` | B9 | `settings: Settings` | `()` | 持久化 |
| `import_files` | F01–F06 | `paths: Vec<String>` | `ImportSummary` | 通用导入入口 |
| `parse_inf` | F07 | `path: String` | `Vec<InfScheme>` | INF 拆方案 |
| `match_roles` | F08 | `files: Vec<String>` | `HashMap<RegName, FilePath>` | 角色匹配 |
| `preview_ani` | F09 | `path: String, size: u32` | `Vec<Vec<u8>>` 帧序列 | 动态预览 |
| `delete_scheme` | F10 | `name: String, soft: bool` | `()` | 删除/软删 |
| `restore_scheme` | F10 | `name: String` | `()` | 软删恢复 |
| `set_schedule` | F12–F15 | `schedule: ScheduleConfig` | `()` | 三模式互斥写入 |
| `read_runtime_status` | F16 | — | `RuntimeStatus` (current_scheme + next_at + mode) | 状态轮询 |
| `backup_cursor` / `restore_cursor` | F17 | — / — | `()` / `()` | 应用前备份 / 恢复 |
| `generate_inf` | F19 | `name: String, dest: String` | `String` 输出路径 | .inf 安装包 |
| `check_update` | F20 | — | `Option<UpdateInfo>` | 主动查更 |
| `collect_diagnostics` | F22 | — | `DiagnosticBundle` (autostart 状态/PID/数据目录) | 一键诊断 |

**事件(Rust → JS 推送)**: `runtime-status-changed`、`import-progress`、`update-available`、`error-occurred`。

---

## 6. 数据兼容

新版**直接读老 Python 版数据目录**,不做迁移:

| 路径 | 用途 | 兼容策略 |
|---|---|---|
| `%APPDATA%\MouseCursorThemeBuilder\settings.json` | 全局设置 | 反序列化为 Rust struct,未知字段忽略;新字段如 `ui_theme`/`updater_check_at` 写回不破坏旧字段 |
| `mouse_files\schemes\` | 方案库 | 按目录名直接读 |
| `mouse_files\resources\` | 资源池 | 按目录名直接读 |
| `mouse_files\installed\` | 已安装索引 | 直接读 |
| `cursor_backup.json` | 应用前备份 | 字段结构保持 |
| `schedule.json` / `week_schedule.json` | 切换配置 | 字段结构保持,新增字段附加 |

设置页**移除存储路径开关**(老版有 BUG 经验),固定使用 `%APPDATA%`。

---

## 7. UI 设计指南

### 7.1 animal-island-ui 组件覆盖

| 项目 UI 需求 | animal-island-ui 直接用 | 自补 |
|---|---|---|
| 主按钮 / 次按钮 | `Button` | — |
| 文本输入 | `Input` | — |
| 开关 | `Switch` | — |
| 弹窗 | `Modal` | — |
| 卡片容器 | `Card` | — |
| 折叠区 | `Collapse` | — |
| 自定义鼠标特效 | `Cursor` | 装饰用,可选 |
| 分割线 | `Divider` | — |
| 列表行 / 虚拟滚动 | × | `VList`(react-virtual 或 react-window) |
| 标签页 | × | `Tab`(受控按钮组) |
| 滑条 | × | `Slider`(自绘 + range input) |
| Tooltip | × | `Tooltip`(@floating-ui/react) |
| 提示条 | × | `Toast`(自实现,3 类型) |
| 拖拽区 | × | `DnDZone`(HTML5 native) |
| 树 | × | `Tree`(资源浏览用) |
| 抽屉 | × | `Drawer`(详情面板) |
| 分段控件 | × | `Segmented`(三模式切换用) |
| 进度环 | × | `ProgressRing`(导入进度) |

### 7.2 风格守则

| 维度 | 规范 |
|---|---|
| 主色板 | Primary `#7BB7E0`,Accent `#F4C95D`,Success `#7DCE82`,Danger `#E58D8D`,Background `#FBF7EE` |
| 字体 | 标题 Zen Maru Gothic;正文 Nunito;中文 Noto Sans SC |
| 圆角 | 卡片 16 px,按钮 12 px,输入 10 px |
| 阴影 | `0 6px 20px rgba(0,0,0,0.06)`,悬停时 `0 10px 24px rgba(0,0,0,0.10)` |
| 动画 | 入场 220 ms `cubic-bezier(0.22, 1, 0.36, 1)`;悬停 120 ms ease-out |
| 间距网格 | 4 / 8 / 12 / 16 / 24 / 32 px |
| 图标 | Lucide React (轻量,svg) + animal-island 内置 |

---

## 8. GitHub Actions 打包

`.github/workflows/release.yml` 大纲:

| 项 | 配置 |
|---|---|
| 触发 | `push` tag `v*-tauri` |
| 平台 | `windows-latest` |
| Action | `tauri-apps/tauri-action@v0` |
| 输入 | `tagName=${{ github.ref_name }}`,`releaseName=MousePointer ${{ github.ref_name }}`,`includeUpdaterJson=true` |
| 产物 | `MousePointer_${version}_x64_en-US.msi` + `MousePointer_${version}_x64-setup.exe` + `latest.json` |
| 签名 | Tauri Updater 私钥 / 公钥(私钥放 GitHub Secrets,公钥进 `tauri.conf.json`) |
| 主分支 push | 跑 `tauri build --debug` smoke,不发 release |

**与 Python 版老 release 区分**: tag 后缀 `-tauri`(待决,详见第 11 节)。资产命名继续用英文,避免老版中文 normalize 问题。

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| Tauri 2 中文资料少 | 实现速度受限 | 直接读 `https://v2.tauri.app` 英文官方;遇 API 不清打印 issue |
| .ani RIFF 无 Rust crate | 动画预览不可用 | 阶段一: Win32 LoadImage 取首帧;阶段二: 自写 RIFF chunk 解析 |
| RAR unrar.dll 分发许可 | 法律风险 | 优先 `unrar` 源(BSD-like);加密包不支持继续保留 |
| 重写期老版 bug | 用户反馈双轨 | 老版冻结 codex 分支,只接关键安全补丁 |
| animal-island-ui 不够用 | 自补成本 | 按 7.2 风格守则统一;每个自补组件独立 commit + storybook 例 |
| Win API 异常 | 系统鼠标卡死 | 所有 Win 调用包 Result + thiserror,catch panic 写 `error.log`,UI 显示 Toast |
| Tauri 2 自更 Webview2 不存在 | 旧 Win10 启动失败 | bootstrapper 检测 + 引导用户安装 |
| GitHub Actions 限免额度 | CI 排队 | 仅 tag push 触发完整打包,主分支 push 仅 smoke |

---

## 10. 进度追踪

| 阶段 | 任务 | 预估工时 | 状态 | 完成日期 |
|---|---|---|---|---|
| Bootstrap (B1–B2) | 工程脚手架 + 数据兼容 | 0.4 周 | ⬜ | — |
| MVP 主体 (B3–B7) | 列表/应用/预览/托盘/自启动 | 1.2 周 | ⬜ | — |
| MVP 收尾 (B8–B9) | CI + 设置 | 0.4 周 | ⬜ | — |
| 完整 - 导入 (F01–F08) | 6 路导入 + INF + 角色匹配 | 1.0 周 | ⬜ | — |
| 完整 - 切换 (F09–F18) | .ani 动画 + 资源库 + 三模式调度 + 后台 | 1.5 周 | ⬜ | — |
| 完整 - 收尾 (F19–F23) | .inf 生成 + 自更 + i18n + 视觉 | 0.8 周 | ⬜ | — |
| 真机回归 + 发布 | Win10 + Win11 全清单 | 0.5 周 | ⬜ | — |

合计 ~5.8 周(单人全职)。

---

## 11. 待决问题

| # | 问题 | 决策点 |
|---|---|---|
| Q1 | 双轨合并策略 | 默认: Python 版彻底冻结于 codex 分支,master 在 MVP 完成后切到 Tauri 版;待用户确认 |
| Q2 | release tag 后缀 | `-tauri` vs 单独 prerelease channel,用户选 |
| Q3 | 老用户数据迁移文案 | 首次启动检测旧路径,InfoBar 提示"已沿用现有数据"还是要明确 onboarding 引导 |
| Q4 | 仓库 LICENSE | 当前仓库无 LICENSE 文件,Tauri 重写前应先 PR 加 MIT |
| Q5 | animal-island-ui 道德条款致谢 | README 致谢段写明"非商业用途,符合 animal-island-ui 作者预期" |

---

## 12. 不在范围

- 不做 macOS / Linux 移植
- 不做 ARM64 (与 Python 版 bug-fix-plan 一致)
- 不重写 Python 版 bug fix(冻结 codex 分支即可)
- 不做付费版 / 商业版分发
- 不做云同步、账号体系、多设备
- 不做 Windows 鼠标主题之外的桌面美化(壁纸 / 主题色等)

---

## 13. 参考链接

- Tauri v2 官方文档: https://v2.tauri.app
- tauri-action: https://github.com/tauri-apps/tauri-action
- windows-rs: https://github.com/microsoft/windows-rs
- animal-island-ui: https://github.com/guokaigdg/animal-island-ui
- 现有 Python 版 bug-fix-plan: `codex/bugfix-stability-plan` 分支 `docs/bug-fix-plan.md`
- 现有 Python 版回归清单: `发布测试清单.md`
- 现有 Python 版错误日志: `错误记录.txt`
