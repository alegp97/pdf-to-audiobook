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
    def test_elevenlabs_account_voices_are_listed_and_saved(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict("os.environ", {"QT_QPA_PLATFORM": "offscreen"}), \
             patch("audiobook_gen.gui.main_window.list_elevenlabs_voices", return_value=[
                 {"id": "voice-alice", "name": "Alice - Clear Educator", "category": "premade"},
                 {"id": "voice-sarah", "name": "Sarah - Reassuring", "category": "premade"},
             ]):
            from PySide6.QtWidgets import QApplication
            from audiobook_gen.config import Settings
            from audiobook_gen.gui.main_window import MainWindow

            app = QApplication.instance() or QApplication([])
            settings = Settings(temp_dir=str(Path(temp) / "chunks"))
            window = MainWindow(settings, config_path=Path(temp) / "settings.yaml")
            window.combo_engine.setCurrentIndex(window.ENGINE_IDS.index("elevenlabs"))
            self.assertTrue(window.combo_voice.isEditable())
            self.assertEqual(window.combo_voice.count(), 2)
            self.assertGreaterEqual(window.combo_voice.findData("voice-sarah"), 0)
            window.combo_voice.setCurrentIndex(window.combo_voice.findData("voice-sarah"))
            window._save_preferences()
            self.assertEqual(settings.tts.voice, "voice-sarah")
            self.assertNotIn("ELEVENLABS_API_KEY", (Path(temp) / "settings.yaml").read_text(encoding="utf-8"))
            window.close()
            app.processEvents()

    def test_elevenlabs_voice_id_remains_editable_if_catalog_fails(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict("os.environ", {"QT_QPA_PLATFORM": "offscreen"}), \
             patch("audiobook_gen.gui.main_window.list_elevenlabs_voices", side_effect=RuntimeError("catalog offline")):
            from PySide6.QtWidgets import QApplication
            from audiobook_gen.config import Settings
            from audiobook_gen.gui.main_window import MainWindow

            app = QApplication.instance() or QApplication([])
            settings = Settings(temp_dir=str(Path(temp) / "chunks"))
            window = MainWindow(settings, config_path=Path(temp) / "settings.yaml")
            window.combo_engine.setCurrentIndex(window.ENGINE_IDS.index("elevenlabs"))
            self.assertTrue(window.combo_voice.isEditable())
            window.combo_voice.setEditText("manual-voice-id")
            self.assertEqual(window._selected_voice_id(), "manual-voice-id")
            self.assertIn("catalog offline", window.lbl_manual_models.text())
            window.close()
            app.processEvents()

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
