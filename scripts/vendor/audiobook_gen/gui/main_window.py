"""
Ventana principal de AudioBookGen (Versión 14:15 + Menús Detallados).
Diseño moderno, premium y en español.
"""

from __future__ import annotations

import os
import logging
import copy
import hashlib
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QFont, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout, QWidget, QComboBox, QGroupBox, QLineEdit,
    QGridLayout, QSpacerItem, QSizePolicy
)

from audiobook_gen.config import Settings
from audiobook_gen.paths import default_output_path
from audiobook_gen.pipeline import AudioBookPipeline, PipelineProgress, PipelineResult, PipelineState
from audiobook_gen.utils.logger import get_logger
from audiobook_gen.voices import (
    EDGE_VOICES, KOKORO_VOICES, PIPER_VOICES, LANGUAGE_ORDER,
    is_kokoro_installed, is_piper_voice_installed, kokoro_model_dir,
    piper_model_dir, SAMPLE_TEXTS
)
from audiobook_gen.core.pdf_analyzer import PdfAnalyzer, PdfAnalysis
from audiobook_gen.core.pdf_extractor import SCANNED_PDF_MESSAGE
from audiobook_gen.core.tts_engine import list_elevenlabs_voices, load_elevenlabs_api_key

log = get_logger("main_window")

class PdfAnalysisWorker(QThread):
    finished = Signal(object)
    def __init__(self, pdf_path: str):
        super().__init__()
        self.pdf_path = pdf_path
    def run(self):
        try:
            analyzer = PdfAnalyzer()
            result = analyzer.analyze(self.pdf_path)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(str(e))

# Estilos Modernos Premium
MODERN_STYLESHEET = """
QMainWindow { background-color: #0f0f12; }
QWidget { color: #f0f0f5; font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }
QGroupBox {
    background-color: #1a1a24;
    border: 1px solid #2d2d3d;
    border-radius: 12px;
    margin-top: 25px;
    padding-top: 20px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 15px;
    color: #4d7cff;
    font-size: 14px;
}
QPushButton {
    background-color: #3d5afe;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 15px;
    font-weight: bold;
}
QPushButton:hover { background-color: #536dfe; }
QPushButton#secondaryBtn { background-color: #2d2d3d; color: #b0b0c8; }
QPushButton#secondaryBtn:hover { background-color: #3d3d4d; color: white; }
QPushButton#accentBtn { background-color: #00c853; }
QPushButton#dangerBtn { background-color: #ff5252; }
QLineEdit, QComboBox {
    background-color: #12121a;
    border: 1px solid #2d2d3d;
    border-radius: 6px;
    padding: 8px;
    color: #e0e0e0;
}
QProgressBar {
    background-color: #12121a;
    border: 1px solid #2d2d3d;
    border-radius: 10px;
    text-align: center;
    color: white;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d5afe, stop:1 #8c9eff);
    border-radius: 9px;
}
QMessageBox {
    background-color: #1a1a24;
}
QMessageBox QLabel {
    color: #f0f0f5;
}
QMessageBox QPushButton {
    min-width: 80px;
    background-color: #3d5afe;
}
QLabel#headerTitle { font-size: 26px; font-weight: bold; color: white; }
QLabel#headerSubtitle { color: #707085; font-size: 14px; }
QLabel#statusText { color: #8c9eff; font-weight: bold; }
"""

class PipelineWorker(QThread):
    progress = Signal(object)
    finished = Signal(object)
    def __init__(self, pipeline: AudioBookPipeline, pdf_path: str, output_path: str):
        super().__init__()
        self.pipeline, self.pdf_path, self.output_path = pipeline, pdf_path, output_path
    def run(self):
        if os.name == "nt":
            import pythoncom
            pythoncom.CoInitialize()
        try:
            self.pipeline._progress_callback = lambda p: self.progress.emit(p)
            self.finished.emit(self.pipeline.run(self.pdf_path, self.output_path))
        finally:
            if os.name == "nt":
                pythoncom.CoUninitialize()

class AudioPreviewWorker(QThread):
    finished = Signal(bool, str)
    def __init__(self, settings, voice_id, engine, lang):
        super().__init__()
        self.settings, self.voice_id, self.engine, self.lang = settings, voice_id, engine, lang
    def run(self):
        from audiobook_gen.core.tts_engine import create_tts_engine
        from audiobook_gen.core.text_segmenter import TextChunk
        if os.name == "nt":
            import pythoncom
            pythoncom.CoInitialize()
        try:
            config = copy.deepcopy(self.settings.tts)
            config.engine, config.voice = self.engine, self.voice_id
            tts = create_tts_engine(config, voice_id=self.voice_id)
            sample = SAMPLE_TEXTS.get(self.lang, SAMPLE_TEXTS["Spanish"])
            temp_path = os.path.join(
                self.settings.temp_dir,
                f"preview_{hashlib.sha256(self.voice_id.encode()).hexdigest()[:16]}{tts.preferred_extension()}",
            )
            tts.synthesize(TextChunk(index=0, text=sample), temp_path)
            self.finished.emit(True, temp_path)
        except Exception as e:
            self.finished.emit(False, str(e))
        finally:
            if os.name == "nt":
                pythoncom.CoUninitialize()

class MainWindow(QMainWindow):
    ENGINE_IDS = ["edge", "elevenlabs", "kokoro", "piper", "sapi"]

    def __init__(self, settings: Optional[Settings] = None, config_path: Optional[str | Path] = None) -> None:
        super().__init__()
        self.settings = settings or Settings()
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parents[2] / "config.yaml"
        self._restoring_preferences = False
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.setAcceptDrops(True)
        self._pdf_path = None
        self._pdf_analysis: Optional[PdfAnalysis] = None
        self._elevenlabs_voice_cache: Optional[list[dict[str, str]]] = None
        self._elevenlabs_voice_error = ""
        self._init_ui()
        self._restore_tts_preferences()
        self._connect_signals()

    def _init_ui(self) -> None:
        self.setWindowTitle("PDF to Audiobook — Desktop Menu")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(MODERN_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header Section
        header = QVBoxLayout()
        title = QLabel("PDF to Audiobook")
        title.setObjectName("headerTitle")
        subtitle = QLabel("Turn PDFs into high-quality audiobooks using AI neural voices")
        subtitle.setObjectName("headerSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        main_layout.addLayout(header)

        # Main Content: Two Columns
        content_row = QHBoxLayout()
        content_row.setSpacing(25)

        # Left Column: Input and Output
        left_col = QVBoxLayout()
        
        # Step 1: File Selection
        input_group = QGroupBox("📥 1. SELECT SOURCE")
        input_group.setToolTip("Choose the PDF file you want to convert to speech")
        input_layout = QVBoxLayout(input_group)
        self.btn_select_pdf = QPushButton("Choose PDF Document")
        self.btn_select_pdf.setMinimumHeight(45)
        self.lbl_pdf_path = QLabel("Drop your PDF here or click above")
        self.lbl_pdf_path.setAlignment(Qt.AlignCenter)
        self.lbl_pdf_path.setStyleSheet("color: #707085; border: 2px dashed #2d2d3d; border-radius: 10px; padding: 20px;")
        input_layout.addWidget(self.btn_select_pdf)
        input_layout.addWidget(self.lbl_pdf_path)
        left_col.addWidget(input_group)

        # Step 2: Output and Quality
        output_group = QGroupBox("📤 2. OUTPUT SETTINGS")
        output_group.setToolTip("Configure where to save the audio and its quality")
        output_layout = QGridLayout(output_group)
        output_layout.addWidget(QLabel("Save audiobook as:"), 0, 0)
        self.edit_output = QLineEdit()
        self.edit_output.setPlaceholderText("Select destination path...")
        self.btn_browse_output = QPushButton("...")
        self.btn_browse_output.setFixedWidth(40)
        self.btn_browse_output.setObjectName("secondaryBtn")
        output_layout.addWidget(self.edit_output, 0, 1)
        output_layout.addWidget(self.btn_browse_output, 0, 2)
        
        output_layout.addWidget(QLabel("Audio quality (kbps):"), 1, 0)
        self.combo_bitrate = QComboBox()
        self.combo_bitrate.addItems(["64k", "128k", "192k", "256k", "320k"])
        self.combo_bitrate.setCurrentText(self.settings.audio.mp3_bitrate)
        output_layout.addWidget(self.combo_bitrate, 1, 1, 1, 2)
        left_col.addWidget(output_group)
        left_col.addStretch()
        content_row.addLayout(left_col, 1)

        # Right Column: Voice Settings
        right_col = QVBoxLayout()
        tts_group = QGroupBox("🎙️ 3. VOICE SETTINGS")
        tts_group.setToolTip("Select the engine, language, and voice that suits your book")
        tts_layout = QVBoxLayout(tts_group)
        
        tts_layout.addWidget(QLabel("Voice Mode:"))
        self.combo_engine = QComboBox()
        self.combo_engine.addItems([
            "Natural Online Voice (Highest Quality)",
            "ElevenLabs Voice (API Key)",
            "Offline Neural Voice (High Quality)",
            "Fast Offline Voice (Lightweight)",
            "Basic System Voice (Windows Default)"
        ])
        if os.name != "nt":
            self.combo_engine.model().item(4).setEnabled(False)
        tts_layout.addWidget(self.combo_engine)

        self.lbl_engine_desc = QLabel("")
        self.lbl_engine_desc.setWordWrap(True)
        self.lbl_engine_desc.setStyleSheet("color: #8c9eff; font-size: 11px; font-style: italic; margin-bottom: 10px;")
        tts_layout.addWidget(self.lbl_engine_desc)
        
        tts_layout.addWidget(QLabel("Document Language:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(LANGUAGE_ORDER)
        tts_layout.addWidget(self.combo_lang)
        
        tts_layout.addWidget(QLabel("Select Voice:"))
        voice_row = QHBoxLayout()
        self.combo_voice = QComboBox()
        self.btn_preview = QPushButton("▶ Preview")
        self.btn_preview.setObjectName("secondaryBtn")
        self.btn_preview.setToolTip("Play a sample of the selected voice")
        voice_row.addWidget(self.combo_voice, 1)
        voice_row.addWidget(self.btn_preview)
        tts_layout.addLayout(voice_row)
        
        self.lbl_manual_models = QLabel("")
        self.lbl_manual_models.setWordWrap(True)
        self.lbl_manual_models.setStyleSheet("color: #707085; font-size: 11px;")
        tts_layout.addWidget(self.lbl_manual_models)
        tts_layout.addStretch()
        
        # Main Action Button
        self.btn_generate = QPushButton("CREATE AUDIOBOOK")
        self.btn_generate.setObjectName("accentBtn")
        self.btn_generate.setMinimumHeight(60)
        self.btn_generate.setEnabled(False)
        tts_layout.addWidget(self.btn_generate)
        
        self.btn_cancel = QPushButton("CANCEL PROCESS")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setMinimumHeight(50)
        self.btn_cancel.setVisible(False)
        tts_layout.addWidget(self.btn_cancel)
        right_col.addWidget(tts_group)
        content_row.addLayout(right_col, 1)
        main_layout.addLayout(content_row)

        # Bottom Section: Estimates and Progress
        bottom_row = QHBoxLayout()

        # Document Estimate Panel
        estimate_group = QGroupBox("📄 DOCUMENT ESTIMATE")
        estimate_layout = QVBoxLayout(estimate_group)
        self.lbl_no_pdf = QLabel("No document loaded")
        self.lbl_no_pdf.setAlignment(Qt.AlignCenter)
        self.lbl_no_pdf.setStyleSheet("color: #707085;")

        self.analysis_frame = QFrame()
        af_layout = QGridLayout(self.analysis_frame)
        self.lbl_pages = QLabel("Pages: -")
        self.lbl_chars = QLabel("Characters: -")
        self.lbl_duration = QLabel("Est. Duration: -")
        self.lbl_ocr_warning = QLabel(SCANNED_PDF_MESSAGE)
        self.lbl_ocr_warning.setStyleSheet("color: #ffb74d; font-weight: bold;")
        self.lbl_ocr_warning.setVisible(False)

        af_layout.addWidget(self.lbl_pages, 0, 0)
        af_layout.addWidget(self.lbl_chars, 0, 1)
        af_layout.addWidget(self.lbl_duration, 1, 0)
        af_layout.addWidget(self.lbl_ocr_warning, 1, 1)
        self.analysis_frame.setVisible(False)

        estimate_layout.addWidget(self.lbl_no_pdf)
        estimate_layout.addWidget(self.analysis_frame)
        bottom_row.addWidget(estimate_group, 1)

        # Progress Panel
        progress_group = QGroupBox("📊 PROGRESS")
        progress_layout = QVBoxLayout(progress_group)
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("statusText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.lbl_detail = QLabel("Choose a PDF to get started.")
        progress_layout.addWidget(self.lbl_status)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_detail)
        bottom_row.addWidget(progress_group, 1)

        main_layout.addLayout(bottom_row)

    def _connect_signals(self) -> None:
        self.btn_select_pdf.clicked.connect(self._on_select_pdf)
        self.btn_browse_output.clicked.connect(self._on_browse_output)
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)
        self.combo_engine.currentIndexChanged.connect(self._on_engine_changed)
        self.combo_voice.currentIndexChanged.connect(self._save_preferences)
        self.combo_voice.currentTextChanged.connect(self._save_preferences)
        self.combo_bitrate.currentIndexChanged.connect(self._save_preferences)
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_cancel.clicked.connect(self._on_cancel)

    def _restore_tts_preferences(self) -> None:
        self._restoring_preferences = True
        try:
            engine_idx = self._engine_index(self.settings.tts.engine)
            self.combo_engine.setCurrentIndex(engine_idx)

            language = self.settings.tts.language
            inferred_language = self._language_for_voice(self.settings.tts.voice, engine_idx)
            if language not in LANGUAGE_ORDER or (inferred_language and inferred_language != language):
                language = inferred_language or "Spanish"
            self._set_combo_text(self.combo_lang, language)

            self._on_engine_changed()
            self._set_combo_data(self.combo_voice, self.settings.tts.voice)
        finally:
            self._restoring_preferences = False

    def _engine_index(self, engine: str) -> int:
        try:
            return self.ENGINE_IDS.index(engine)
        except ValueError:
            return 0

    def _language_for_voice(self, voice_id: str, engine_idx: int) -> Optional[str]:
        voice_groups = [EDGE_VOICES, {}, KOKORO_VOICES, PIPER_VOICES, {}]
        for language, voices in voice_groups[engine_idx].items():
            if any(v.id == voice_id for v in voices):
                return language
        return None

    def _set_combo_text(self, combo: QComboBox, text: str) -> None:
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _on_language_changed(self) -> None:
        self._populate_voices()
        self._save_preferences()

    def _save_preferences(self) -> None:
        if self._restoring_preferences:
            return

        self.settings.tts.engine = self.ENGINE_IDS[self.combo_engine.currentIndex()]
        self.settings.tts.language = self.combo_lang.currentText()
        voice_id = self._selected_voice_id()
        if voice_id:
            self.settings.tts.voice = voice_id
        self.settings.audio.mp3_bitrate = self.combo_bitrate.currentText()

        try:
            self.settings.save_yaml(self.config_path)
        except Exception:
            log.exception("Could not save user preferences to %s", self.config_path)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(".pdf"): self._load_pdf(path)

    def _on_select_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if path: self._load_pdf(path)

    def _load_pdf(self, path):
        self._pdf_path = path
        self._pdf_analysis = None
        self.lbl_pdf_path.setText(Path(path).name)
        self.lbl_pdf_path.setStyleSheet("color: #00c853; border: 2px solid #00c853; border-radius: 10px; padding: 20px; font-weight: bold;")

        # Propose a convenient Desktop destination; the user can choose another.
        if not self.edit_output.text() or self.edit_output.text().endswith(".mp3"):
            self.edit_output.setText(str(default_output_path(path)))

        self.lbl_status.setText("Analyzing document...")
        self.analysis_frame.setVisible(False)
        self.lbl_no_pdf.setVisible(True)

        self.analysis_worker = PdfAnalysisWorker(path)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.start()

    def _on_browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save audiobook as", self.edit_output.text(), "MP3 Audio (*.mp3)")
        if path: self.edit_output.setText(path)

    def _on_analysis_finished(self, result):
        if isinstance(result, str):
            self.lbl_status.setText(f"Analysis failed: {result}")
            return

        self._pdf_analysis = result
        self.lbl_pages.setText(f"Pages: {result.pages}")
        self.lbl_chars.setText(f"Characters: {result.characters:,}")
        self.lbl_duration.setText(f"Est. Duration: {result.estimated_duration_minutes:.0f} min")
        self.lbl_ocr_warning.setText(SCANNED_PDF_MESSAGE)
        self.lbl_ocr_warning.setVisible(result.requires_ocr)

        self.lbl_no_pdf.setVisible(False)
        self.analysis_frame.setVisible(True)
        if result.requires_ocr:
            self.lbl_status.setText("Scanned PDF detected")
            self.lbl_detail.setText(SCANNED_PDF_MESSAGE)
            self.btn_generate.setEnabled(False)
        else:
            self.lbl_status.setText("Ready to convert")
            self.btn_generate.setEnabled(True)

    def _on_engine_changed(self):
        idx = self.combo_engine.currentIndex()
        descs = [
            "Best quality. Requires internet and sends text fragments to an external TTS service.",
            "Premium online voice. Requires ELEVENLABS_API_KEY and may use paid API credits.",
            "High-quality offline voice. Place Kokoro files manually in the models folder.",
            "Lightweight local voice. Place Piper files manually in the models folder.",
            "Windows fallback voice. Works offline but may sound robotic."
        ]
        self.lbl_engine_desc.setText(descs[idx])
        self._populate_voices()
        self._update_manual_model_hint()
        self._save_preferences()

    def _populate_voices(self):
        configured_engine = self.settings.tts.engine
        configured_voice = self.settings.tts.voice
        self.combo_voice.clear()
        lang, eng_idx = self.combo_lang.currentText(), self.combo_engine.currentIndex()
        self.combo_voice.setEditable(eng_idx == 1)
        if eng_idx == 0:
            voices = EDGE_VOICES.get(lang, [])
        elif eng_idx == 1:
            self.combo_voice.setPlaceholderText("Loading ElevenLabs voices...")
            if self._elevenlabs_voice_cache is None and not self._elevenlabs_voice_error:
                try:
                    self._elevenlabs_voice_cache = list_elevenlabs_voices()
                except Exception as exc:
                    self._elevenlabs_voice_error = str(exc)

            if self._elevenlabs_voice_cache:
                for voice in self._elevenlabs_voice_cache:
                    label = voice["name"]
                    if voice.get("category"):
                        label += f" — {voice['category']}"
                    self.combo_voice.addItem(label, voice["id"])
                if configured_engine == "elevenlabs":
                    self._set_combo_data(self.combo_voice, configured_voice)
                self.combo_voice.setPlaceholderText("Select an ElevenLabs voice")
            else:
                self.combo_voice.setPlaceholderText("Enter an ElevenLabs voice ID")
                if configured_engine == "elevenlabs":
                    self.combo_voice.setEditText(configured_voice)
            return
        elif eng_idx == 2:
            voices = KOKORO_VOICES.get(lang, [])
        elif eng_idx == 3:
            voices = PIPER_VOICES.get(lang, [])
        else:
            self.combo_voice.addItem("System Default Voice", "System Default")
            return
        
        for v in voices:
            label = v.display_name
            if eng_idx == 2 and not is_kokoro_installed():
                label += " [Missing local model]"
            elif eng_idx == 3 and not is_piper_voice_installed(v.id):
                label += " [Missing local voice]"
            self.combo_voice.addItem(label, v.id)

    def _selected_voice_id(self) -> str:
        return str(self.combo_voice.currentData() or self.combo_voice.currentText()).strip()

    def _validate_voice_available(self, engine: str, voice_id: str) -> bool:
        if engine == "elevenlabs" and not load_elevenlabs_api_key():
            QMessageBox.warning(
                self,
                "ElevenLabs API key required",
                "Set ELEVENLABS_API_KEY before opening the desktop menu.",
            )
            return False
        if engine == "kokoro" and not is_kokoro_installed():
            QMessageBox.warning(
                self,
                "Local model required",
                f"Place kokoro-v1.0.onnx and voices-v1.0.bin in:\n{kokoro_model_dir()}",
            )
            return False
        if engine == "piper" and not is_piper_voice_installed(voice_id):
            QMessageBox.warning(
                self,
                "Local voice required",
                f"Place {voice_id}.onnx and {voice_id}.onnx.json in:\n{piper_model_dir()}",
            )
            return False
        return True

    def _update_manual_model_hint(self):
        idx = self.combo_engine.currentIndex()
        if idx == 1:
            if self._elevenlabs_voice_cache:
                self.lbl_manual_models.setText(
                    f"{len(self._elevenlabs_voice_cache)} account voices loaded from ElevenLabs. "
                    "The API key is never saved in the menu settings."
                )
            elif self._elevenlabs_voice_error:
                self.lbl_manual_models.setText(
                    "Could not load the ElevenLabs voice list. You can still enter a voice ID manually. "
                    f"{self._elevenlabs_voice_error}"
                )
            else:
                self.lbl_manual_models.setText(
                    "Choose a voice from your ElevenLabs account. "
                    "The API key is read privately and is never saved here."
                )
        elif idx == 2:
            self.lbl_manual_models.setText(
                f"Kokoro folder: {kokoro_model_dir()} "
                "(requires kokoro-v1.0.onnx and voices-v1.0.bin)"
            )
        elif idx == 3:
            self.lbl_manual_models.setText(
                f"Piper folder: {piper_model_dir()} "
                "(requires <voice>.onnx and <voice>.onnx.json)"
            )
        else:
            self.lbl_manual_models.setText("")

    def _on_preview(self):
        v_id, eng_idx = self._selected_voice_id(), self.combo_engine.currentIndex()
        engine = self.ENGINE_IDS[eng_idx]
        if not v_id:
            QMessageBox.warning(self, "Voice required", "Please select a voice first.")
            return
        if not self._validate_voice_available(engine, v_id):
            return
        self.btn_preview.setEnabled(False)
        self.btn_preview.setText("⌛ Generating...")
        self.preview_worker = AudioPreviewWorker(self.settings, v_id, engine, self.combo_lang.currentText())
        self.preview_worker.finished.connect(self._on_preview_done)
        self.preview_worker.start()

    def _on_preview_done(self, ok, res):
        self.btn_preview.setEnabled(True)
        self.btn_preview.setText("▶ Preview")
        if ok: self.player.stop(); self.player.setSource(QUrl.fromLocalFile(os.path.abspath(res))); self.player.play()
        else: QMessageBox.critical(self, "Error", f"Preview failed: {res}")

    def _on_generate(self):
        if not self._pdf_path:
            QMessageBox.warning(self, "PDF required", "Please choose a PDF document first.")
            return
        output_path = self.edit_output.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Output required", "Please choose where to save the MP3 file.")
            return
        if Path(output_path).suffix.lower() != ".mp3":
            output_path = str(Path(output_path).with_suffix(".mp3"))
            self.edit_output.setText(output_path)
        output_dir = Path(output_path).parent
        if Path(output_path).exists():
            answer = QMessageBox.question(self, "Replace existing audio?", f"This file already exists:\n{output_path}\n\nReplace it?",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        if not output_dir.exists():
            QMessageBox.warning(self, "Invalid output", f"The output folder does not exist:\n{output_dir}")
            return

        engine = self.ENGINE_IDS[self.combo_engine.currentIndex()]
        voice_id = self._selected_voice_id()
        if not voice_id:
            QMessageBox.warning(self, "Voice required", "Please select a voice first.")
            return
        if not self._validate_voice_available(engine, voice_id):
            return
        if self._pdf_analysis and self._pdf_analysis.requires_ocr:
            QMessageBox.warning(
                self,
                "Scanned PDF detected",
                SCANNED_PDF_MESSAGE,
            )
            return

        self.settings.tts.engine = engine
        self.settings.tts.language = self.combo_lang.currentText()
        self.settings.tts.voice = voice_id
        self.settings.audio.mp3_bitrate = self.combo_bitrate.currentText()
        self._save_preferences()
        self.btn_generate.setVisible(False); self.btn_cancel.setVisible(True)
        self.pipeline = AudioBookPipeline(self.settings)
        self.worker = PipelineWorker(self.pipeline, self._pdf_path, output_path)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, p):
        self.progress_bar.setValue(int(p.progress * 1000))
        self.lbl_status.setText(p.message); self.lbl_detail.setText(p.detail)

    def _on_finished(self, res):
        self.btn_generate.setVisible(True); self.btn_cancel.setVisible(False)
        if res.success: QMessageBox.information(self, "Success", f"Audiobook created successfully at:\n{res.output_path}")
        else: QMessageBox.critical(self, "Error", f"An error occurred: {res.error}")

    def _on_cancel(self):
        if self.pipeline: self.pipeline.cancel()
        self.lbl_status.setText("Cancelling process...")

    def closeEvent(self, event):
        for name in ("worker", "preview_worker", "analysis_worker"):
            worker = getattr(self, name, None)
            if worker is not None and worker.isRunning():
                QMessageBox.information(self, "Still working", "Please wait for the current task to finish, or cancel the conversion before closing.")
                event.ignore()
                return
        self.player.stop()
        self.player.setSource(QUrl())
        super().closeEvent(event)
