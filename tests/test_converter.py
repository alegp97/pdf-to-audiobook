"""Offline behavioral checks. All fixtures are generated in temporary folders."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import math
import struct

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("adapter", ROOT / "scripts/pdf_to_mp3.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
from audiobook_gen.config import Settings
from audiobook_gen.core.pdf_extractor import PageContent
from audiobook_gen.core.text_cleaner import TextCleaner
from audiobook_gen.pipeline import AudioBookPipeline


def make_pdf(path: Path, spanish=False):
    texts = (
        ["Este prefacio debe conservarse para que no falte el comienzo.\n\n"
         "CAPÍTULO I. El comienzo.\n\nUna viajera exploraba el bosque. "
         "Observaba el río y disfrutaba de la luz de la mañana.\n\nSí.",
         "CAPÍTULO II. El regreso.\n\nLa viajera regresó a casa con una historia. "
         "Este final debe escucharse completo y conservar sus últimas palabras."]
        if spanish else
        ["This preface must remain so the beginning of the book is preserved.\n\n"
         "CHAPTER I. The beginning.\n\nA traveler explored the forest. "
         "The map was marked in cm, and the appointment was with Dr. Smith.\n\nYes.",
         "CHAPTER II. The return.\n\nThe traveler returned home with a story. "
         "The final words must remain complete in the transcript."]
    )
    with fitz.open() as doc:
        for text in texts:
            doc.new_page().insert_textbox(fitz.Rect(50, 50, 540, 750), text, fontsize=12)
        doc.save(path)


def make_wave(path: Path):
    rate = 22050
    samples = b"".join(struct.pack("<h", int(5000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(rate // 5))
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(samples)


class SyntheticVoice:
    def get_voice_name(self):
        return "offline-test-tone"

    def preferred_extension(self):
        return ".wav"

    def synthesize(self, chunk, output_path):
        make_wave(Path(output_path))
        return output_path


class ConverterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = adapter.configure_ffmpeg()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.pdf = self.base / "book.pdf"
        make_pdf(self.pdf)
        self.settings = Settings(temp_dir=str(self.base / "chunks"))
        self.settings.tts.language = "Other"
        self.settings.segmenter.min_chunk_chars = 1
        self.settings.cleaner.min_line_length = 1

    def tearDown(self):
        self.temp.cleanup()

    def test_english_text_and_chapters_preserved(self):
        transcript = self.base / "text.txt"
        info = adapter.prepare(self.pdf, self.settings, transcript)
        text = transcript.read_text(encoding="utf-8")
        for passage in ("This preface", "CHAPTER I.", "CHAPTER II.", "Yes.", "final words", "cm", "Dr. Smith"):
            self.assertIn(passage, text)
        self.assertNotIn("centímetros", text)
        self.assertNotIn("[CAPÍTULO:", text)
        self.assertEqual(info["chapters"], 2)

    def test_spanish_text_preserved(self):
        path = self.base / "spanish.pdf"
        make_pdf(path, spanish=True)
        self.settings.tts.language = "Spanish"
        transcript = self.base / "spanish.txt"
        info = adapter.prepare(path, self.settings, transcript)
        text = transcript.read_text(encoding="utf-8")
        for passage in ("Este prefacio", "CAPÍTULO I.", "Sí.", "últimas palabras"):
            self.assertIn(passage, text)
        self.assertEqual(info["chapters"], 2)

    def test_mixed_image_only_page_is_rejected(self):
        path = self.base / "mixed.pdf"
        with fitz.open(self.pdf) as doc:
            pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
            pixmap.clear_with(140)
            doc.new_page().insert_image(fitz.Rect(50, 50, 300, 300), stream=pixmap.tobytes("png"))
            doc.save(path)
        with self.assertRaisesRegex(ValueError, "OCR"):
            adapter.prepare(path, self.settings, self.base / "mixed.txt")

    def test_header_count_is_per_page(self):
        pages = [PageContent(i, f"Header {i}\nUnique line {i}\nAnother line {i}") for i in range(3)]
        self.assertEqual(TextCleaner()._detect_repeated_lines(pages), [])

    def test_header_cleanup_does_not_remove_substrings(self):
        pages = [PageContent(i, "TITLE\nThe word TITLE remains in the body.\nClosing text.") for i in range(3)]
        cleaner = TextCleaner(self.settings.cleaner)
        with patch.object(cleaner, "_detect_repeated_lines", return_value=["TITLE"]):
            self.assertIn("word TITLE remains", cleaner.clean(pages).raw_text)

    def test_names_do_not_overwrite(self):
        original = self.base / "book.mp3"
        original.write_bytes(b"keep me")
        self.assertEqual(adapter.unique_stem(self.base, "book"), "book_2")
        self.assertEqual(original.read_bytes(), b"keep me")

    def test_voice_resolution(self):
        self.assertEqual(adapter.resolve_voice(None, None, "edge"), ("en-US-GuyNeural", "en"))
        self.assertEqual(adapter.resolve_voice(None, "es-ES-ElviraNeural", "edge"), ("es-ES-ElviraNeural", "es"))
        with self.assertRaisesRegex(ValueError, "do not match"):
            adapter.resolve_voice("en", "es-ES-ElviraNeural", "edge")
        with self.assertRaisesRegex(ValueError, "Select a voice"):
            adapter.resolve_voice("fr", None, "edge")

    def test_dry_run_and_batch_failure(self):
        output = self.base / "output"
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/pdf_to_mp3.py"), str(self.pdf),
            str(self.base / "missing.pdf"), "--dry-run", "--output-dir", str(output),
            "--work-dir", str(self.base / "work")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        entries = json.loads((output / "report.json").read_text(encoding="utf-8"))["results"]
        self.assertTrue(entries[0]["success"])
        self.assertFalse(entries[1]["success"])
        self.assertEqual(entries[0]["language"], "en")
        self.assertEqual(list(output.glob("*.mp3")), [])

    def test_pipeline_audio_assembly_without_network(self):
        destination = self.base / "book.mp3"
        with patch("audiobook_gen.pipeline.create_tts_engine", return_value=SyntheticVoice()):
            result = AudioBookPipeline(self.settings).run(str(self.pdf), str(destination))
        self.assertTrue(result.success, result.error)
        audio = adapter.validate_mp3(self.ffmpeg, destination)
        self.assertTrue(audio["audio_validated"])
        self.assertGreater(audio["audio_duration_seconds"], 0)
        self.assertEqual(list((self.base / "chunks").glob("*.wav")), [])

    def test_corrupt_mp3_is_rejected(self):
        bad = self.base / "broken.mp3"
        bad.write_bytes(b"this is not audio")
        with self.assertRaisesRegex(RuntimeError, "decoding failed"):
            adapter.validate_mp3(self.ffmpeg, bad)


if __name__ == "__main__":
    unittest.main()
