"""
Voice Synthesis Engine (TTS).
Abstractions with implementations:
- EdgeTTSEngine:  Online neural voices through Edge-TTS (primary)
- ElevenLabsEngine: Premium online voices through the ElevenLabs API
- KokoroEngine:   Lightweight ONNX model (offline)
- PiperEngine:    Ultra-fast synthesis (offline)
- SAPIEngine:     Local fallback using Windows SAPI5 COM
"""

from __future__ import annotations

import asyncio
import base64
import os
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydub import AudioSegment

from audiobook_gen.config import TTSConfig
from audiobook_gen.core.text_segmenter import TextChunk
from audiobook_gen.utils.logger import get_logger

log = get_logger("tts_engine")


def skill_env_path() -> Path:
    """Return the private .env file at the root of this skill/repository."""
    return Path(__file__).resolve().parents[4] / ".env"


def load_elevenlabs_api_key(env_path: Optional[Path] = None) -> str:
    """Load the ElevenLabs key without overriding an existing process value."""
    load_dotenv(dotenv_path=env_path or skill_env_path(), override=False)
    return os.environ.get("ELEVENLABS_API_KEY", "").strip()


def _elevenlabs_error_message(exc: Exception) -> str:
    """Return the actionable API message without dumping response headers."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        detail = body.get("detail", body)
        if isinstance(detail, dict) and detail.get("message"):
            return str(detail["message"])
    return str(exc)

class TTSEngine(ABC):
    def __init__(self, config: TTSConfig, voice_id: str) -> None:
        self.config = config
        self.voice_id = voice_id

    def get_voice_name(self) -> str:
        return self.voice_id or "System Default"

    def preferred_extension(self) -> str:
        return ".mp3"

    def _synthesize_empty(self, output_path: str) -> str:
        AudioSegment.silent(duration=500).export(
            output_path,
            format=self.preferred_extension().lstrip("."),
        )
        return output_path

    @abstractmethod
    def synthesize(self, chunk: TextChunk, output_path: str) -> str:
        pass

class EdgeTTSEngine(TTSEngine):
    def __init__(self, config: TTSConfig, voice_id: str):
        super().__init__(config, voice_id)

    def synthesize(self, chunk: TextChunk, output_path: str) -> str:
        if not chunk.text.strip():
            return self._synthesize_empty(output_path)

        import edge_tts
        from edge_tts.exceptions import NoAudioReceived

        async def _run():
            communicate = edge_tts.Communicate(
                chunk.text,
                voice=self.voice_id,
                rate=self.config.rate,
                pitch=self.config.pitch,
                volume=self.config.volume,
            )
            await communicate.save(output_path)
        try:
            asyncio.run(_run())
        except NoAudioReceived as exc:
            raise RuntimeError(
                "No audio was received from Edge-TTS online voice synthesis. This usually means the "
                f"selected voice ({self.voice_id}) is listed in the repository but it is not currently available for synthesis. Try selecting a different voice."
            ) from exc
        return output_path


class ElevenLabsEngine(TTSEngine):
    """Synthesize MP3 chunks with the official ElevenLabs Python SDK."""

    def __init__(self, config: TTSConfig, voice_id: str):
        api_key = load_elevenlabs_api_key()
        if not api_key:
            raise RuntimeError(
                "ElevenLabs requires ELEVENLABS_API_KEY. Set the environment variable "
                "or add it to the private .env file at the skill root."
            )
        if not voice_id:
            raise ValueError("ElevenLabs requires a voice ID.")
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as exc:
            raise RuntimeError(
                "ElevenLabs support requires the optional package 'elevenlabs'. "
                "Install scripts/requirements.txt."
            ) from exc
        super().__init__(config, voice_id)
        self.client = ElevenLabs(api_key=api_key)
        self._request_ids: list[str] = []

    def synthesize(self, chunk: TextChunk, output_path: str) -> str:
        if not chunk.text.strip():
            return self._synthesize_empty(output_path)
        try:
            context_chars = max(0, self.config.elevenlabs_context_chars)
            previous_text = (
                chunk.previous_text[-context_chars:]
                if chunk.previous_text and context_chars
                else None
            )
            next_text = (
                chunk.next_text[:context_chars]
                if chunk.next_text and context_chars
                else None
            )
            supports_request_stitching = not self.config.elevenlabs_model.startswith("eleven_v3")
            previous_request_ids = self._request_ids[-3:] if supports_request_stitching else []
            previous_request_ids = previous_request_ids or None
            raw_response = self.client.text_to_speech.with_raw_response.convert_with_timestamps(
                voice_id=self.voice_id,
                text=chunk.text,
                model_id=self.config.elevenlabs_model,
                output_format=self.config.elevenlabs_output_format,
                previous_text=None if previous_request_ids else previous_text,
                next_text=next_text,
                previous_request_ids=previous_request_ids,
            )
            try:
                response = raw_response.data
                request_id = raw_response.headers.get("request-id")
                if request_id:
                    self._request_ids.append(request_id)
                alignment = response.alignment or response.normalized_alignment
                if alignment:
                    chunk.alignment = list(zip(
                        alignment.characters,
                        alignment.character_start_times_seconds,
                        alignment.character_end_times_seconds,
                    ))
                with open(output_path, "wb") as stream:
                    stream.write(base64.b64decode(response.audio_base_64))
            finally:
                raw_response.close()
        except Exception as exc:
            raise RuntimeError(
                f"ElevenLabs synthesis failed for voice '{self.voice_id}': "
                f"{_elevenlabs_error_message(exc)}"
            ) from exc
        return output_path


def list_elevenlabs_voices() -> list[dict[str, str]]:
    """Return every voice visible to the configured ElevenLabs account."""
    api_key = load_elevenlabs_api_key()
    if not api_key:
        raise RuntimeError(
            "ElevenLabs requires ELEVENLABS_API_KEY in the environment or skill .env file."
        )
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as exc:
        raise RuntimeError(
            "ElevenLabs support requires the optional package 'elevenlabs'."
        ) from exc

    client = ElevenLabs(api_key=api_key)
    voices: list[dict[str, str]] = []
    next_page_token = None
    while True:
        page = client.voices.search(
            page_size=100,
            next_page_token=next_page_token,
            sort="name",
            sort_direction="asc",
            include_total_count=False,
        )
        voices.extend(
            {
                "id": voice.voice_id,
                "name": voice.name,
                "category": getattr(voice, "category", None) or "",
            }
            for voice in page.voices
        )
        if not page.has_more or not page.next_page_token:
            break
        next_page_token = page.next_page_token
    return voices

class KokoroEngine(TTSEngine):
    def __init__(self, config: TTSConfig, voice_id: str):
        from audiobook_gen.voices import kokoro_model_dir
        model_path = kokoro_model_dir() / "kokoro-v1.0.onnx"
        voices_path = kokoro_model_dir() / "voices-v1.0.bin"
        if not model_path.exists() or not voices_path.exists():
            raise RuntimeError(
                "Kokoro offline model is not installed. Place kokoro-v1.0.onnx "
                f"and voices-v1.0.bin in {kokoro_model_dir()}."
            )
        try:
            import kokoro_onnx
        except ImportError as exc:
            raise RuntimeError(
                "Kokoro support requires the optional package 'kokoro-onnx'."
            ) from exc
        super().__init__(config, voice_id)
        self.kokoro = kokoro_onnx.KokoroONNX(str(model_path), str(voices_path))

    def preferred_extension(self) -> str:
        return ".wav"

    def synthesize(self, chunk: TextChunk, output_path: str) -> str:
        if not chunk.text.strip():
            return self._synthesize_empty(output_path)
        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError(
                "Kokoro support requires the optional package 'soundfile'."
            ) from exc
        samples, rate = self.kokoro.create(chunk.text, voice=self.voice_id, speed=1.0)
        sf.write(output_path, samples, rate)
        return output_path

class PiperEngine(TTSEngine):
    def __init__(self, config: TTSConfig, voice_id: str):
        from audiobook_gen.voices import piper_model_dir
        model_path = piper_model_dir() / f"{voice_id}.onnx"
        if not model_path.exists():
            raise RuntimeError(
                f"Piper voice '{voice_id}' is not installed. Place {voice_id}.onnx "
                f"and {voice_id}.onnx.json in {piper_model_dir()}."
            )
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise RuntimeError(
                "Piper support requires the optional package 'piper-tts'."
            ) from exc
        super().__init__(config, voice_id)
        self.voice = PiperVoice.load(str(model_path))

    def preferred_extension(self) -> str:
        return ".wav"

    def synthesize(self, chunk: TextChunk, output_path: str) -> str:
        if not chunk.text.strip():
            return self._synthesize_empty(output_path)
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.voice.config.sample_rate)
            self.voice.synthesize(chunk.text, wav_file)
        return output_path

class SAPIEngine(TTSEngine):
    def __init__(self, config: TTSConfig, voice_id: str):
        try:
            import win32com.client
        except ImportError as exc:
            raise RuntimeError("SAPI support requires the package 'pywin32'.") from exc
        super().__init__(config, voice_id)
        self.engine = win32com.client.Dispatch("SAPI.SpVoice")
        if voice_id and voice_id != "System Default":
            matches = [v for v in self.engine.GetVoices() if v.Id == voice_id]
            if not matches:
                raise ValueError(f"SAPI voice not installed: {voice_id}")
            self.engine.Voice = matches[0]

    def preferred_extension(self) -> str:
        return ".wav"

    def synthesize(self, chunk: TextChunk, output_path: str) -> str:
        if not chunk.text.strip():
            return self._synthesize_empty(output_path)
        import win32com.client
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        previous = self.engine.AudioOutputStream
        stream.Open(output_path, 3, False)
        try:
            self.engine.AudioOutputStream = stream
            self.engine.Speak(chunk.text, 0)
        finally:
            self.engine.AudioOutputStream = previous
            stream.Close()
        return output_path

def create_tts_engine(config: TTSConfig, voice_id: Optional[str] = None) -> TTSEngine:
    voice_id = voice_id or config.voice
    engine_type = config.engine.lower()
    if engine_type == "edge":
        return EdgeTTSEngine(config, voice_id)
    if engine_type == "elevenlabs":
        return ElevenLabsEngine(config, voice_id)
    if engine_type == "kokoro":
        return KokoroEngine(config, voice_id)
    if engine_type == "piper":
        return PiperEngine(config, voice_id)
    if engine_type == "sapi":
        return SAPIEngine(config, voice_id)
    raise ValueError(f"Unsupported TTS engine: {config.engine}")
