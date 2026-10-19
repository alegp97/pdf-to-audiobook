"""Offline behavioral checks. All fixtures are generated in temporary folders."""
from __future__ import annotations

import importlib.util
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave
import math
import struct

import pymupdf as fitz
from pydub import AudioSegment
from pydub.generators import Sine

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("adapter", ROOT / "scripts/pdf_to_mp3.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
from audiobook_gen.config import Settings
from audiobook_gen.core.audio_assembler import AudioAssembler
from audiobook_gen.core.pdf_extractor import PageContent
from audiobook_gen.core.text_segmenter import TextChunk, TextSegmenter
from audiobook_gen.core.tts_engine import (
    ElevenLabsEngine,
    create_tts_engine,
    load_elevenlabs_api_key,
)
from audiobook_gen.core.text_cleaner import TextCleaner
from audiobook_gen.core.text_normalizer import TextNormalizer
from audiobook_gen.paths import default_output_dir, default_output_path
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

    def test_desktop_is_the_default_output_but_home_is_a_safe_fallback(self):
        fake_home = self.base / "profile"
        fake_home.mkdir()
        desktop = fake_home / "Desktop"
        with patch("audiobook_gen.paths.Path.home", return_value=fake_home):
            self.assertEqual(default_output_dir(), fake_home)
            desktop.mkdir()
            self.assertEqual(default_output_dir(), desktop)
            self.assertEqual(default_output_path(self.pdf), desktop / "book.mp3")

    def test_voice_resolution(self):
        self.assertEqual(adapter.resolve_voice(None, None, "edge"), ("en-US-GuyNeural", "en"))
        self.assertEqual(adapter.resolve_voice(None, "es-ES-ElviraNeural", "edge"), ("es-ES-ElviraNeural", "es"))
        with self.assertRaisesRegex(ValueError, "do not match"):
            adapter.resolve_voice("en", "es-ES-ElviraNeural", "edge")
        with self.assertRaisesRegex(ValueError, "Select a voice"):
            adapter.resolve_voice("fr", None, "edge")
        self.assertEqual(
            adapter.resolve_voice("es", "voice-account-id", "elevenlabs"),
            ("voice-account-id", "es"),
        )
        with self.assertRaisesRegex(ValueError, "ElevenLabs voice ID"):
            adapter.resolve_voice("es", None, "elevenlabs")

    def test_elevenlabs_engine_writes_streamed_mp3(self):
        calls = []

        class FakeRawResponse:
            def __init__(self, data, request_id):
                self.data = data
                self.headers = {"request-id": request_id}

            def close(self):
                return None

        class FakeTextToSpeech:
            @property
            def with_raw_response(self):
                return self

            def convert_with_timestamps(self, **kwargs):
                calls.append(kwargs)
                alignment = types.SimpleNamespace(
                    characters=list("Hello ElevenLabs"),
                    character_start_times_seconds=[0.0] * len("Hello ElevenLabs"),
                    character_end_times_seconds=[0.1] * len("Hello ElevenLabs"),
                )
                payload = types.SimpleNamespace(
                    audio_base_64=base64.b64encode(b"firstsecond").decode("ascii"),
                    alignment=alignment,
                    normalized_alignment=None,
                )
                return FakeRawResponse(payload, f"request-{len(calls)}")

        class FakeClient:
            def __init__(self, api_key):
                self.api_key = api_key
                self.text_to_speech = FakeTextToSpeech()

        package = types.ModuleType("elevenlabs")
        client_module = types.ModuleType("elevenlabs.client")
        client_module.ElevenLabs = FakeClient
        destination = self.base / "elevenlabs.mp3"
        with patch.dict(sys.modules, {"elevenlabs": package, "elevenlabs.client": client_module}), \
             patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            self.settings.tts.engine = "elevenlabs"
            self.settings.tts.voice = "voice-account-id"
            engine = create_tts_engine(self.settings.tts)
            self.assertIsInstance(engine, ElevenLabsEngine)
            engine.synthesize(
                TextChunk(
                    index=0,
                    text="Hello ElevenLabs",
                    previous_text="x" * 600,
                    next_text="y" * 600,
                ),
                str(destination),
            )
            second_destination = self.base / "elevenlabs-2.mp3"
            engine.synthesize(
                TextChunk(index=1, text="Second request", next_text="future"),
                str(second_destination),
            )

        self.assertEqual(destination.read_bytes(), b"firstsecond")
        self.assertEqual(calls[0]["voice_id"], "voice-account-id")
        self.assertEqual(calls[0]["model_id"], "eleven_multilingual_v2")
        self.assertEqual(calls[0]["output_format"], "mp3_44100_128")
        self.assertEqual(calls[0]["previous_text"], "x" * 500)
        self.assertEqual(calls[0]["next_text"], "y" * 500)
        self.assertIsNone(calls[0]["previous_request_ids"])
        self.assertEqual(calls[1]["previous_request_ids"], ["request-1"])
        self.assertIsNone(calls[1]["previous_text"])

    def test_elevenlabs_chunks_receive_neighbor_context(self):
        self.settings.segmenter.max_chunk_chars = 55
        chunks = TextSegmenter(self.settings.segmenter).segment(
            "Primera oración suficientemente larga para separar. "
            "Segunda oración suficientemente larga para separar. "
            "Tercera oración suficientemente larga para separar."
        )
        self.assertGreaterEqual(len(chunks), 3)
        self.assertIsNone(chunks[0].previous_text)
        self.assertEqual(chunks[0].next_text, chunks[1].text)
        self.assertEqual(chunks[1].previous_text, chunks[0].text)
        self.assertIsNone(chunks[-1].next_text)

    def test_layout_paragraphs_are_coalesced_until_real_punctuation(self):
        self.settings.segmenter.max_chunk_chars = 500
        chunks = TextSegmenter(self.settings.segmenter).segment(
            "Esta frase continúa en el siguiente bloque\n\n"
            "sin coma ni punto y solo termina aquí. Otra oración completa."
        )
        self.assertEqual(len(chunks), 1)
        self.assertIn("bloque sin coma", chunks[0].text)

    def test_chunk_boundaries_prefer_punctuation(self):
        self.settings.segmenter.max_chunk_chars = 75
        chunks = TextSegmenter(self.settings.segmenter).segment(
            "Primera oración suficientemente extensa para ocupar espacio. "
            "Segunda oración suficientemente extensa para ocupar espacio. "
            "Tercera oración suficientemente extensa para ocupar espacio."
        )
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all(chunk.text.rstrip().endswith(".") for chunk in chunks))

    def test_meeting_timestamps_and_invisible_markers_are_not_narrated(self):
        normalized = TextNormalizer().normalize(
            "La estrategia continúa (00:03:57).\u200b Después termina."
        )
        self.assertNotIn("00:03:57", normalized)
        self.assertNotIn("\u200b", normalized)
        self.assertIn("Después termina.", normalized)

    def test_elevenlabs_chunk_trimming_keeps_a_short_sentence_edge(self):
        audio = (
            AudioSegment.silent(duration=300)
            + Sine(440).to_audio_segment(duration=300).apply_gain(-6)
            + AudioSegment.silent(duration=300)
        )
        trimmed = AudioAssembler._trim_edge_silence(audio, keep_ms=80)
        self.assertGreaterEqual(len(trimmed), 440)
        self.assertLessEqual(len(trimmed), 500)

    def test_elevenlabs_internal_pause_is_shorter_than_sentence_pause(self):
        tone = Sine(440).to_audio_segment(duration=300).apply_gain(-6)
        audio = tone + AudioSegment.silent(duration=600) + tone
        assembler = AudioAssembler(self.settings.audio, trim_chunk_edges=True)
        phrase = TextChunk(
            text="Una frase, continúa",
            index=0,
            alignment=[("e", 0.20, 0.28), (",", 0.28, 0.31), ("c", 0.90, 0.98)],
        )
        sentence = TextChunk(
            text="Una frase. Continúa",
            index=0,
            alignment=[("e", 0.20, 0.28), (".", 0.28, 0.31), ("C", 0.90, 0.98)],
        )
        phrase_audio = assembler._compress_internal_silence(audio, phrase)
        sentence_audio = assembler._compress_internal_silence(audio, sentence)
        self.assertLess(len(phrase_audio), len(sentence_audio))
        self.assertLess(len(phrase_audio), 850)
        self.assertGreater(len(sentence_audio), 850)

    def test_elevenlabs_boundary_pause_depends_on_punctuation(self):
        assembler = AudioAssembler(self.settings.audio, trim_chunk_edges=True)
        self.assertEqual(assembler._punctuation_pause_ms("continúa"), 0)
        self.assertEqual(
            assembler._punctuation_pause_ms("continúa,"),
            self.settings.audio.elevenlabs_phrase_pause_ms,
        )
        self.assertEqual(
            assembler._punctuation_pause_ms("termina."),
            self.settings.audio.elevenlabs_sentence_pause_ms,
        )

    def test_elevenlabs_unpunctuated_boundary_has_no_silence(self):
        assembler = AudioAssembler(self.settings.audio, trim_chunk_edges=True)
        tone = Sine(440).to_audio_segment(duration=300).apply_gain(-6)
        left = tone + AudioSegment.silent(duration=450)
        right = AudioSegment.silent(duration=450) + tone
        left = assembler._trim_edge_silence(
            left,
            leading_keep_ms=0,
            trailing_keep_ms=assembler._punctuation_pause_ms("la frase continúa"),
        )
        right = assembler._trim_edge_silence(
            right,
            leading_keep_ms=0,
            trailing_keep_ms=assembler._punctuation_pause_ms("sin detenerse"),
        )
        joined = left + right
        self.assertLessEqual(len(joined), 620)

    def test_elevenlabs_engine_requires_api_key(self):
        self.settings.tts.engine = "elevenlabs"
        self.settings.tts.voice = "voice-account-id"
        with patch.dict("os.environ", {}, clear=True), \
             self.assertRaisesRegex(RuntimeError, "ELEVENLABS_API_KEY"):
            create_tts_engine(self.settings.tts)

    def test_elevenlabs_key_loads_from_private_env_without_overriding_process(self):
        env_file = self.base / ".env"
        env_file.write_text("ELEVENLABS_API_KEY=file-key\n", encoding="utf-8")
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(load_elevenlabs_api_key(env_file), "file-key")
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "process-key"}, clear=True):
            self.assertEqual(load_elevenlabs_api_key(env_file), "process-key")

    def test_dry_run_and_batch_failure(self):
        output = self.base / "output"
        work = self.base / "work"
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/pdf_to_mp3.py"), str(self.pdf),
            str(self.base / "missing.pdf"), "--dry-run", "--output-dir", str(output),
            "--work-dir", str(work)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        entries = json.loads((work / "review" / "report.json").read_text(encoding="utf-8"))["results"]
        self.assertTrue(entries[0]["success"])
        self.assertFalse(entries[1]["success"])
        self.assertEqual(entries[0]["language"], "en")
        self.assertEqual(list(output.iterdir()), [])
        self.assertTrue((work / "review" / "book.txt").is_file())

    def test_cleanup_is_limited_to_a_direct_child_of_work(self):
        work = self.base / "work"
        review = work / "review"
        review.mkdir(parents=True)
        (review / "draft.txt").write_text("temporary", encoding="utf-8")
        adapter.remove_owned_directory(review, work)
        self.assertFalse(review.exists())
        outside = self.base / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(ValueError, "outside the work folder"):
            adapter.remove_owned_directory(outside, work)

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
