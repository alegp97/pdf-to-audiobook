"""Portable menu checks; speech synthesis is never requested."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "launch_gui.py"
spec = importlib.util.spec_from_file_location("portable_gui_launcher", LAUNCHER)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class GuiDependencyTests(unittest.TestCase):
    def test_missing_dependency_is_actionable(self):
        with patch.object(launcher.importlib.util, "find_spec", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "requirements-gui.txt"):
                launcher.check_dependencies()


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Optional GUI dependencies are not installed")
class GuiWindowTests(unittest.TestCase):
    def test_menu_from_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = subprocess.run([sys.executable, "-X", "utf8", str(LAUNCHER), "--smoke-test"],
                                  cwd=temp, capture_output=True, text=True, encoding="utf-8", timeout=90)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("GUI smoke test passed", proc.stdout)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_dependency_check_does_not_create_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "not-created"
            proc = subprocess.run([sys.executable, str(LAUNCHER), "--check", "--state-dir", str(state)],
                                  cwd=temp, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
