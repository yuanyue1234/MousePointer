from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DEPENDENCY_SKIP_REASON = ""
try:
    import main as backend
    from PySide6.QtWidgets import QApplication
    from fluent_ui import SchemePage, cursor_kind_badge, cursor_kind_summary, cursor_kind_summary_text, resource_filter_reason
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

    def test_inf_mapping_supports_scheme_list_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_dir = root / "Cursors"
            cursor_dir.mkdir()
            names = [
                "arrow.cur", "help.cur", "work.ani", "wait.ani", "cross.cur", "beam.cur",
                "pen.cur", "no.cur", "ns.cur", "we.cur", "nwse.cur", "nesw.cur",
                "all.cur", "up.cur", "hand.cur", "pin.cur", "person.cur",
            ]
            for name in names:
                (cursor_dir / name).write_bytes(b"")
            scheme_value = ",".join(f"%10%\\Cursors\\{name}" for name in names)
            (root / "theme.inf").write_text(
                f"""
[DefaultInstall]
AddReg = Scheme.Reg

[Scheme.Reg]
HKCU,"Control Panel\\Cursors\\Schemes","My Scheme",,"{scheme_value}"
""",
                encoding="utf-8",
            )

            mapping = backend.parse_inf_mapping(root, use_filename_fallback=False)
            self.assertEqual(mapping["Arrow"].name, "arrow.cur")
            self.assertEqual(mapping["NWPen"].name, "pen.cur")
            self.assertEqual(mapping["Pin"].name, "pin.cur")
            self.assertEqual(mapping["Person"].name, "person.cur")

    def test_inf_mapping_can_disable_filename_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "arrow.cur").write_bytes(b"")
            self.assertEqual(backend.parse_inf_mapping(root, use_filename_fallback=False), {})

    def test_resource_filter_excludes_documents_and_large_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "readme.pdf"
            png = root / "large.png"
            cur = root / "large.cur"
            pdf.write_bytes(b"%PDF")
            png.write_bytes(b"0" * (1024 * 1024 + 1))
            cur.write_bytes(b"0" * (1024 * 1024 + 1))

            self.assertIn("文档", resource_filter_reason(pdf))
            self.assertIn("1MB", resource_filter_reason(png))
            self.assertEqual(resource_filter_reason(cur), "")

    def test_no_inf_import_creates_resource_only_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _app = QApplication.instance() or QApplication([])
            old_root = backend.SCHEME_LIBRARY.parent
            storage = Path(tmp) / "storage"
            package = Path(tmp) / "package"
            package.mkdir()
            (package / "preview.png").write_bytes(b"png")
            (package / "arrow.cur").write_bytes(b"cur")
            (package / "manual.pdf").write_bytes(b"%PDF")
            backend.apply_storage_root(storage)
            page = SchemePage(backend)
            try:
                page.beginImportBatch()
                name = page.importRootAsScheme(package, "Loose Assets", package, duplicate_policy="copy")
                _scheme_dir, data = backend.scheme_manifest_data(name)
                self.assertTrue(data.get("resource_only"))
                self.assertEqual(data.get("files"), {})
                self.assertIn("extras/preview.png", data.get("extras", []))
                self.assertIn("extras/arrow.cur", data.get("extras", []))
                self.assertTrue(any("manual.pdf" in item for item in page.importFiltered))
            finally:
                page.deleteLater()
                backend.apply_storage_root(old_root)

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

    def test_archive_validation_rejects_unsafe_members(self) -> None:
        with self.assertRaises(RuntimeError):
            backend.validate_archive_members([("../evil.cur", 1, False)])
        with self.assertRaises(RuntimeError):
            backend.validate_archive_members([("secret.cur", 1, True)])

    def test_resource_only_schemes_are_visible_only_in_library_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _app = QApplication.instance() or QApplication([])
            old_root = backend.SCHEME_LIBRARY.parent
            storage = Path(tmp) / "storage"
            backend.apply_storage_root(storage)
            scheme = backend.SCHEME_LIBRARY / "Resource Only"
            extras = scheme / "extras"
            extras.mkdir(parents=True)
            (extras / "arrow.cur").write_bytes(b"cur")
            backend.write_json_atomic(scheme / "scheme.json", {
                "name": "Resource Only",
                "files": {},
                "extras": ["extras/arrow.cur"],
                "resource_only": True,
            })
            page = SchemePage(backend)
            try:
                self.assertNotIn("Resource Only", page.schemeNames())
                self.assertIn("Resource Only", page.schemeNames(include_resource_only=True))
            finally:
                page.deleteLater()
                backend.apply_storage_root(old_root)

    def test_frozen_pyinstaller_lookup_uses_extracted_runtime_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "python"
            runtime.mkdir()
            python = runtime / "python.exe"
            python.write_bytes(b"")
            old_frozen = backend.IS_FROZEN
            try:
                backend.IS_FROZEN = True
                completed = subprocess_result = type("Result", (), {"returncode": 0})()
                with mock.patch.object(backend, "ensure_python_runtime", return_value=runtime), \
                    mock.patch.object(backend.subprocess, "run", return_value=completed) as run:
                    self.assertEqual(backend.find_python_with_pyinstaller(), str(python))
                    self.assertEqual(Path(run.call_args.args[0][0]), python)
            finally:
                backend.IS_FROZEN = old_frozen


if __name__ == "__main__":
    unittest.main()
