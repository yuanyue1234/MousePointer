# Current Progress

Updated: 2026-05-10

## Keep

- Python mainline remains the active product path.
- Current product version is `2.1.0`.
- WinUI work stays out of Python bug-fix commits unless explicitly requested.
- `assets/role_icons/*.png` deletion state is not part of Python commits.
- Legacy Tk runtime UI code has been removed from `main.py`; the active UI is PySide6/qfluentwidgets only.
- Portable/frozen runtime data should live under `%APPDATA%\MouseCursorThemeBuilder`, not next to the exe.
- Cursor preview file association command must quote `"%1"` so paths with spaces or Chinese characters are passed correctly.
- `--preview-cursor` should tolerate a path split across argv pieces and join it back when possible.
- Folder portable packaging is preferred for local checking because it starts faster than onefile.

## Reverted / Do Not Reapply

- Do not add global Qt window suppress/hide filters.
- Do not replace normal ComboBox controls with page-level custom selectors just to hide popup windows.
- Do not disable `setWindowIcon()` as a blanket fix.
- Do not monkey patch qfluentwidgets popup internals unless a minimal, reproducible bug proves it is required.
- Do not make file dialogs globally non-native as a window-flash workaround.

## Commands

```powershell
.\.venv\Scripts\python.exe -m compileall main.py fluent_ui.py cursor_preview_light.py tests
.\.venv\Scripts\python.exe -m unittest tests.test_cursor_metadata
.\scripts\build_portable.ps1 -PackageMode Both
.\scripts\measure_preview_startup.ps1 -Mode OneDir
```

## Packaging Notes

`scripts/build_portable.ps1` restores tracked `assets/role_icons/*.png` into a temporary payload using `git checkout-index`, so the current working-tree deletion state is not packaged by mistake.

The script cleans managed old outputs before each build, excludes `tkinter`, `_tkinter`, and `tkinterdnd2`, and writes:

- `release-assets\鼠标指针配置生成器_绿色程序.exe`
- `release-assets\MousePointer_Portable_Directory\`
- `release-assets\MousePointer_Portable_Directory.zip`
- `release-assets\SHA256SUMS.txt`

Generated release artifacts are local outputs. The GitHub Release workflow rebuilds them from source when tag `v2.1.0` is pushed.

## 2026-05-11 Fix Plan In Progress

Scope stays on the Python mainline. Do not stage `MousePointer.WinUI/`, and do not stage deleted `assets/role_icons/*.png`.

Current fixes applied:

- INF mapping now parses every `.inf` under an imported folder, reads `[Strings]`, expands `%Name%` values, and honors `HKCU,"Control Panel\Cursors",Role,...` mappings before falling back to filename matching.
- `正常选择` / `手写` / `位置选择` are covered by role aliases and by real INF registry role names: `Arrow`, `NWPen`, `Pin`.
- `.cur` / `.ani` file association no longer writes the app exe as `DefaultIcon`; it preserves the previous or system cursor icon where available.
- Input-language switching now refuses random or missing schemes, so Chinese/English toggles cannot apply a scheme outside the saved configuration.
- qfluent ComboBox popup creation is patched centrally to force a solid white popup, no translucent background, no drop shadow, and stable viewport styling.
- Timer SpinBox controls are styled with dark foreground text on a white field.
- Resource library remains single-select; grid cards use fixed size and top-left layout instead of stretching across the page.
- Resource library no longer shows per-thumbnail dynamic/static chips; only the scheme title row keeps the summary line.
- Import buttons and resource-drop imports now run through background tasks; duplicate schemes imported in background auto-create a suffixed copy instead of showing a QMessageBox from a worker thread.
- Automatic first-launch desktop-shortcut prompt is disabled; the Settings page button remains the manual path.
- Cursor preview text is reduced: normal preview shows only metadata/actions; failure shows a short error.

Validation already run:

```powershell
.\.venv\Scripts\python.exe -m compileall main.py fluent_ui.py cursor_preview_light.py tests
.\.venv\Scripts\python.exe -m unittest tests.test_cursor_metadata
```
