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
