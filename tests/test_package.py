"""Package, documentation and real installed-copy smoke tests (no plan execution)."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


CHECKER = module("package_checker", "scripts/check_skill.py")
INSTALLER = module("package_installer", "scripts/install.py")
WAVEPLAN = module("package_waveplan", "scripts/waveplan.py")


class PackageTests(unittest.TestCase):
    def test_package_contract_and_links(self):
        self.assertEqual(CHECKER.check(ROOT), [])

    def test_json_examples_in_documentation_are_valid_plans(self):
        text = (ROOT / "references" / "plan-format.md").read_text(encoding="utf-8")
        blocks = re.findall(r"^```json\n(.*?)\n```", text, flags=re.M | re.S)
        self.assertGreater(len(blocks), 0)
        for block in blocks:
            plan = json.loads(block)
            WAVEPLAN.validate_plan(plan)
            self.assertTrue(WAVEPLAN.schedule_plan(plan)["ok"])

    def test_skill_has_one_entrypoint_and_explicit_modes(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for heading in ("## Modo plan", "## Modo execute", "## Modo review"):
            self.assertIn(heading, text)
        entrypoints = [path for path in ROOT.rglob("SKILL.md") if ".git" not in path.parts]
        self.assertEqual(entrypoints, [ROOT / "SKILL.md"])
        self.assertIn("não executam comandos do plano", text)

    def test_install_real_copy_and_validate_offline(self):
        with tempfile.TemporaryDirectory(prefix="wave-installed-") as directory:
            root = Path(directory) / "skills"
            result = INSTALLER.install(ROOT, root)
            destination = root / INSTALLER.NAME
            self.assertEqual(result["state"], "installed")
            self.assertEqual(CHECKER.check(destination), [])
            self.assertFalse((destination / ".git").exists())
            self.assertFalse((destination / "tests").exists())
            process = subprocess.run(
                [sys.executable, str(destination / "scripts" / "waveplan.py"),
                 "validate", str(destination / "examples" / "plan.json"), "--json"],
                capture_output=True, text=True, encoding="utf-8", timeout=15,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertTrue(json.loads(process.stdout)["ok"])
            self.assertEqual(INSTALLER.install(ROOT, root)["state"], "unchanged")

    def test_installer_cli_supports_unicode_destination_without_encoding_failure(self):
        with tempfile.TemporaryDirectory(prefix="wave-unicode-") as directory:
            root = Path(directory) / "instalação"
            process = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "install.py"),
                 "--root", str(root), "--dry-run"],
                capture_output=True, text=True, encoding="utf-8", timeout=15,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            result = json.loads(process.stdout)
            self.assertIn("instalação", result["destination"])
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
