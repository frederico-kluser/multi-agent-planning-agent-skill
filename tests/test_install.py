"""Offline installer regression tests; all writes stay in owned temp directories."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("skill_install", SCRIPT)
assert SPEC and SPEC.loader
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wave-skill-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        for name in INSTALLER.ROOT_FILES:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"public resource: {name}\n", encoding="utf-8")
        for name in INSTALLER.RESOURCE_DIRS:
            directory = self.source / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "sample.md").write_text("public sample\n", encoding="utf-8")
        self.root = self.base / "skills with spaces"
        self.destination = self.root / INSTALLER.NAME

    def test_dry_run_never_creates_root(self):
        result = INSTALLER.install(self.source, self.root, dry_run=True)
        self.assertEqual(result["state"], "would_install")
        self.assertFalse(self.root.exists())

    def test_install_and_identical_repeat(self):
        first = INSTALLER.install(self.source, self.root)
        self.assertEqual(first["state"], "installed")
        self.assertFalse(first["configuration_changed"])
        self.assertTrue((self.destination / "SKILL.md").is_file())
        again = INSTALLER.install(self.source, self.root)
        self.assertEqual(again["state"], "unchanged")
        self.assertEqual(first["files"], again["files"])

    def test_modified_file_is_preserved(self):
        INSTALLER.install(self.source, self.root)
        target = self.destination / "SKILL.md"
        target.write_text("user changes\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "alterada"):
            INSTALLER.install(self.source, self.root)
        self.assertEqual(target.read_text(encoding="utf-8"), "user changes\n")

    def test_extra_file_is_preserved(self):
        INSTALLER.install(self.source, self.root)
        target = self.destination / "user-note.md"
        target.write_text("personal note\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "diferente"):
            INSTALLER.install(self.source, self.root)
        self.assertEqual(target.read_text(encoding="utf-8"), "personal note\n")

    def test_dry_run_rejects_drift_without_writing(self):
        INSTALLER.install(self.source, self.root)
        target = self.destination / "README.md"
        target.write_text("changed\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            INSTALLER.install(self.source, self.root, dry_run=True)
        self.assertEqual(target.read_text(encoding="utf-8"), "changed\n")

    def test_private_and_generated_files_are_not_exported(self):
        (self.source / ".env").write_text("SECRET=not-a-real-token\n", encoding="utf-8")
        (self.source / ".git").mkdir()
        (self.source / ".git" / "config").write_text("local metadata\n", encoding="utf-8")
        (self.source / "scripts" / "__pycache__").mkdir()
        (self.source / "scripts" / "__pycache__" / "cache.py").write_text("pass\n")
        (self.source / "references" / "media.mp4").write_bytes(b"not video")
        result = INSTALLER.install(self.source, self.root)
        self.assertFalse((self.destination / ".env").exists())
        self.assertFalse((self.destination / ".git").exists())
        self.assertNotIn("references/media.mp4", result["files"])
        self.assertFalse(any("__pycache__" in path for path in result["files"]))

    def test_existing_file_destination_is_not_overwritten(self):
        self.root.mkdir()
        self.destination.write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "não é um diretório"):
            INSTALLER.install(self.source, self.root)
        self.assertEqual(self.destination.read_text(encoding="utf-8"), "keep me")

    def test_source_tree_destination_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fora da árvore"):
            INSTALLER.install(self.source, self.source / "skills")
        self.assertFalse((self.source / "skills").exists())

    def test_missing_resource_is_rejected_before_writes(self):
        incomplete = self.base / "incomplete"
        incomplete.mkdir()
        with self.assertRaisesRegex(ValueError, "obrigatório"):
            INSTALLER.install(incomplete, self.root)
        self.assertFalse(self.root.exists())

    def test_resource_symlink_is_rejected(self):
        target = self.base / "outside.md"
        target.write_text("outside", encoding="utf-8")
        link = self.source / "references" / "link.md"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("host does not permit creating symlinks")
        with self.assertRaisesRegex(ValueError, "links"):
            INSTALLER.install(self.source, self.root)
        self.assertFalse(self.root.exists())

    def test_destination_symlink_is_rejected(self):
        self.root.mkdir()
        outside = self.base / "outside-directory"
        outside.mkdir()
        try:
            self.destination.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("host does not permit creating symlinks")
        with self.assertRaisesRegex(ValueError, "link/junction"):
            INSTALLER.install(self.source, self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_windows_reparse_attribute_is_rejected_conservatively(self):
        info = SimpleNamespace(st_file_attributes=0x400)
        with patch.object(Path, "is_symlink", return_value=False), patch.object(Path, "lstat", return_value=info):
            self.assertTrue(INSTALLER.is_link(self.source))
        info.st_file_attributes = 0
        with patch.object(Path, "is_symlink", return_value=False), patch.object(Path, "lstat", return_value=info):
            self.assertFalse(INSTALLER.is_link(self.source))

    def test_nested_root_resource_checks_its_linked_parent(self):
        linked_parent = self.source / ".github"
        with patch.object(INSTALLER, "is_link", side_effect=lambda path: path == linked_parent):
            with self.assertRaisesRegex(ValueError, "links"):
                INSTALLER.install(self.source, self.root)
        self.assertFalse(self.root.exists())

    def test_cli_dry_run_is_json_and_creates_nothing(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), "--dry-run"],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["state"], "would_install")
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
