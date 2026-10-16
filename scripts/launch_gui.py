"""Launch the bundled SimpleAudioBookGen-derived menu, independently of a checkout."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(description="Open the PDF to Audiobook desktop menu.")
    parser.add_argument("--pdf", type=Path, help="Preselect a PDF; never start narration automatically.")
    parser.add_argument("--state-dir", type=Path, help="Override the per-user settings/log directory.")
    parser.add_argument("--foreground", action="store_true", help="Run the GUI in this process.")
    parser.add_argument("--check", action="store_true", help="Check dependencies without opening the GUI.")
    parser.add_argument("--smoke-test", action="store_true", help="Construct and close the window offscreen, without speech requests.")
    return parser.parse_args()


def check_dependencies():
    modules = {"PySide6": "PySide6", "pymupdf": "PyMuPDF", "yaml": "PyYAML", "pydub": "pydub",
               "edge_tts": "edge-tts", "num2words": "num2words", "imageio_ffmpeg": "imageio-ffmpeg"}
    missing = [package for module, package in modules.items() if importlib.util.find_spec(module) is None]
    if missing:
        raise RuntimeError("Missing GUI dependencies: " + ", ".join(missing) +
                           ". Install them with this Python: -m pip install -r " + str(SCRIPT_DIR / "requirements-gui.txt"))


def show_window(args, state_dir: Path) -> int:
    if args.smoke_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # Import Qt only after selecting its platform; CLI users do not need Qt.
    from PySide6.QtWidgets import QApplication
    from audiobook_gen.config import Settings
    from audiobook_gen.gui.main_window import MainWindow
    from audiobook_gen.utils.logger import setup_logger
    from pdf_to_mp3 import configure_ffmpeg

    configure_ffmpeg()
    setup_logger(str(state_dir / "gui.log"))
    config = state_dir / "config.yaml"
    app = QApplication([sys.argv[0]])
    app.setApplicationName("PDF to Audiobook")
    app.setApplicationVersion("1.1.0")
    cache = state_dir / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gui-", dir=cache) as temp:
        if config.exists():
            settings = Settings.from_yaml(config)
            settings.temp_dir = temp
        else:
            settings = Settings(temp_dir=temp)
            settings.tts.language = "English"
            settings.tts.voice = "en-US-GuyNeural"
        settings.segmenter.min_chunk_chars = 1
        settings.cleaner.min_line_length = 1
        window = MainWindow(settings, config)
        window.show()
        if args.smoke_test:
            app.processEvents()
            assert window.isVisible(), "The menu did not become visible."
            assert window.combo_voice.count() > 0, "The voice menu is empty."
            # Verify a real saved choice and the Spanish voice the user uses.
            window.combo_lang.setCurrentText("Spanish")
            index = window.combo_voice.findData("es-ES-ElviraNeural")
            assert index >= 0, "Elvira is missing from the bundled menu."
            window.combo_voice.setCurrentIndex(index)
            assert Settings.from_yaml(config).tts.voice == "es-ES-ElviraNeural"
            window.close()
            app.processEvents()
            print("GUI smoke test passed: window, voice choices, and saved preferences.")
            return 0
        if args.pdf:
            window._load_pdf(str(args.pdf.resolve()))
        return app.exec()


def main() -> int:
    args = parse_args()
    check_dependencies()
    sys.path.insert(0, str(SCRIPT_DIR / "vendor"))
    from audiobook_gen.paths import user_data_dir
    if args.pdf and not args.pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {args.pdf}")
    if args.check:
        print("Bundled GUI and dependencies are ready.")
        return 0
    if args.smoke_test and not args.state_dir:
        with tempfile.TemporaryDirectory(prefix="audiobook-gui-check-") as temp:
            try:
                return show_window(args, Path(temp))
            finally:
                # Windows cannot remove a temporary directory with an open log.
                import logging
                logging.shutdown()
    state = (args.state_dir or user_data_dir()).resolve()
    state.mkdir(parents=True, exist_ok=True)
    if args.foreground or args.smoke_test:
        return show_window(args, state)

    python = Path(sys.executable)
    if os.name == "nt" and python.with_name("pythonw.exe").is_file():
        python = python.with_name("pythonw.exe")
    command = [str(python), str(Path(__file__).resolve()), "--foreground", "--state-dir", str(state)]
    if args.pdf:
        command.extend(["--pdf", str(args.pdf.resolve())])
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    log_path = state / "gui-launch.log"
    with log_path.open("a", encoding="utf-8") as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment, **options)
    try:
        code = child.wait(timeout=4)
    except subprocess.TimeoutExpired:
        print(f"GUI started (PID {child.pid}). Startup log: {log_path}")
        return 0
    raise RuntimeError(f"GUI exited during startup (code {code}). Read {log_path}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
