"""
Voice Synthesis Engine (TTS).
Abstractions with implementations:
- EdgeTTSEngine:  Online neural voices through Edge-TTS (primary)
- KokoroEngine:   Lightweight ONNX model (offline)
- PiperEngine:    Ultra-fast synthesis (offline)
- SAPIEngine:     Local fallback using Windows SAPI5 COM
"""

from __future__ import annotations

import asyncio
import wave
from abc import ABC, abstractmethod
from typing import Optional

from pydub import AudioSegment

from audiobook_gen.config import TTSConfig
from audiobook_gen.core.text_segmenter import TextChunk
from audiobook_gen.utils.logger import get_logger

log = get_logger("tts_engine")

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
    if "edge" in engine_type:
        return EdgeTTSEngine(config, voice_id)
    elif "kokoro" in engine_type:
        return KokoroEngine(config, voice_id)
    elif "piper" in engine_type:
        return PiperEngine(config, voice_id)
    else:
        return SAPIEngine(config, voice_id)
