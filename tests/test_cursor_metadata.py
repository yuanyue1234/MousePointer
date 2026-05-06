from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DEPENDENCY_SKIP_REASON = ""
try:
    from fluent_ui import cursor_kind_badge, cursor_kind_summary, cursor_kind_summary_text
except ModuleNotFoundError as exc:
    if exc.name not in {"PIL", "PySide6", "qfluentwidgets"}:
        raise
    DEPENDENCY_SKIP_REASON = f"应用 UI 依赖未安装：{exc.name}"
    cursor_kind_badge = cursor_kind_summary = cursor_kind_summary_text = None


@unittest.skipIf(bool(DEPENDENCY_SKIP_REASON), DEPENDENCY_SKIP_REASON)
class CursorMetadataTests(unittest.TestCase):
    def test_cursor_kind_badge_only_marks_cur_and_ani(self) -> None:
        self.assertEqual(cursor_kind_badge(Path("busy.ani")), "动")
        self.assertEqual(cursor_kind_badge(Path("arrow.cur")), "静")
        self.assertEqual(cursor_kind_badge(Path("preview.png")), "")
        self.assertEqual(cursor_kind_badge(None), "")

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


if __name__ == "__main__":
    unittest.main()
