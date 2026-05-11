from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DEPENDENCY_SKIP_REASON = ""
try:
    import main as backend
    from fluent_ui import cursor_kind_badge, cursor_kind_summary, cursor_kind_summary_text
    from cursor_preview_light import cursor_kind as light_cursor_kind
    from cursor_preview_light import file_cache_key
except ModuleNotFoundError as exc:
    if exc.name not in {"PIL", "PySide6", "qfluentwidgets"}:
        raise
    DEPENDENCY_SKIP_REASON = f"应用 UI 依赖未安装：{exc.name}"
    cursor_kind_badge = cursor_kind_summary = cursor_kind_summary_text = light_cursor_kind = file_cache_key = None


@unittest.skipIf(bool(DEPENDENCY_SKIP_REASON), DEPENDENCY_SKIP_REASON)
class CursorMetadataTests(unittest.TestCase):
    def test_cursor_kind_badge_only_marks_cur_and_ani(self) -> None:
        self.assertEqual(cursor_kind_badge(Path("busy.ani")), "动")
        self.assertEqual(cursor_kind_badge(Path("arrow.cur")), "静")
        self.assertEqual(cursor_kind_badge(Path("preview.png")), "")
        self.assertEqual(cursor_kind_badge(None), "")
        self.assertEqual(light_cursor_kind(Path("busy.ani")), "动")
        self.assertEqual(light_cursor_kind(Path("arrow.cur")), "静")

    def test_cursor_kind_summary_counts_scheme_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "Arrow": "arrow.cur",
                "Wait": "busy.ani",
                "Help": "help.cur",
                "Preview": "preview.png",
            }
            for file_name in files.values():
                (root / file_name).write_bytes(b"")

            self.assertEqual(cursor_kind_summary(root, files), (1, 2))
            self.assertEqual(cursor_kind_summary_text(root, files), "动 1  静 2")

    def test_preview_cache_key_changes_when_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arrow.cur"
            path.write_bytes(b"one")
            first = file_cache_key(path, 200)
            path.write_bytes(b"three")
            second = file_cache_key(path, 200)
            self.assertNotEqual(first, second)

    def test_inf_mapping_uses_installer_role_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_dir = root / "Cursors"
            cursor_dir.mkdir()
            for name in ["normal.cur", "write.ani", "place.cur"]:
                (cursor_dir / name).write_bytes(b"")
            (root / "theme.inf").write_text(
                """
[Strings]
NormalCursor = "normal.cur"
PenCursor = "write.ani"

[Install]
HKCU,"Control Panel\\Cursors",Arrow,0x00020000,"%10%\\Cursors\\%NormalCursor%"
HKCU,"Control Panel\\Cursors",NWPen,0x00020000,"%10%\\Cursors\\%PenCursor%"
""",
                encoding="utf-8",
            )
            (root / "extra.inf").write_text(
                """
[Install]
location = "Cursors\\place.cur"
""",
                encoding="utf-8",
            )

            mapping = backend.parse_inf_mapping(root)
            self.assertEqual(mapping["Arrow"].name, "normal.cur")
            self.assertEqual(mapping["NWPen"].name, "write.ani")
            self.assertEqual(mapping["Pin"].name, "place.cur")

    def test_input_switch_only_resolves_configured_existing_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_library = backend.SCHEME_LIBRARY
            backend.SCHEME_LIBRARY = Path(tmp)
            for name in ["Mouse Scheme 1", "Mouse Scheme 2"]:
                scheme_dir = backend.SCHEME_LIBRARY / name
                scheme_dir.mkdir(parents=True)
                (scheme_dir / "scheme.json").write_text("{}", encoding="utf-8")
            try:
                item = {
                    "mode": "input",
                    "zh_scheme": "Mouse Scheme 1",
                    "en_scheme": "Not Existing",
                    "upper_scheme": backend.RANDOM_SCHEME_VALUE,
                }
                self.assertEqual(backend.resolve_input_switch_scheme(item, "zh"), "Mouse Scheme 1")
                self.assertEqual(backend.resolve_input_switch_scheme(item, "en"), "")
                self.assertEqual(backend.resolve_input_switch_scheme(item, "upper"), "")
            finally:
                backend.SCHEME_LIBRARY = old_library


if __name__ == "__main__":
    unittest.main()
