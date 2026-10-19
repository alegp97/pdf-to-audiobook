"""
Ensamblado y postproceso de audio.

Une fragmentos de audio, inserta silencios entre secciones,
normaliza volumen y exporta a MP3.
"""

from __future__ import annotations

import os
from typing import Optional

from pydub import AudioSegment
from pydub.silence import detect_leading_silence, detect_silence

from audiobook_gen.config import AudioConfig
from audiobook_gen.core.text_segmenter import TextChunk
from audiobook_gen.utils.logger import get_logger

log = get_logger("audio_assembler")


class AudioAssembler:
    """Ensambla fragmentos de audio en un audiolibro completo."""

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        trim_chunk_edges: bool = False,
    ) -> None:
        self.config = config or AudioConfig()
        self.trim_chunk_edges = trim_chunk_edges

    def assemble(
        self,
        audio_paths: list[str],
        chunks: list[TextChunk],
        output_path: str,
    ) -> str:
        """
        Ensambla fragmentos MP3/WAV mixtos y exporta un MP3 final.

        Reencodear al final es mas robusto que concatenar con stream copy:
        Edge puede generar MP3, mientras que motores locales suelen producir WAV.
        """
        if not audio_paths:
            raise ValueError("There are no audio chunks to assemble.")

        log.info("Assembling %d audio chunks...", len(audio_paths))
        combined = AudioSegment.empty()

        for i, (audio_path, chunk) in enumerate(zip(audio_paths, chunks)):
            try:
                segment = AudioSegment.from_file(audio_path)
                if self.trim_chunk_edges:
                    segment = self._compress_internal_silence(segment, chunk)
                    segment = self._trim_edge_silence(
                        segment,
                        leading_keep_ms=0,
                        trailing_keep_ms=self._punctuation_pause_ms(chunk.text),
                    )
                combined += segment
            except Exception as e:
                raise RuntimeError(f"Could not read audio chunk {audio_path}: {e}") from e

            if i < len(audio_paths) - 1:
                if chunk.is_chapter_end:
                    combined += AudioSegment.silent(duration=self.config.silence_chapter_ms)
                    log.debug("Chapter pause inserted after chunk %d", chunk.index)
                elif not self.trim_chunk_edges and self._chunk_ends_sentence(chunk.text):
                    pause_ms = (
                        self.config.silence_paragraph_ms
                    )
                    combined += AudioSegment.silent(duration=pause_ms)

        combined = self._normalize_volume(combined)

        try:
            with combined.export(output_path, format="mp3", bitrate=self.config.mp3_bitrate):
                pass
        except Exception as e:
            raise RuntimeError(f"Final MP3 export failed: {e}") from e

        duration_secs = len(combined) / 1000.0
        file_size_mb = 0.0
        if os.path.exists(output_path):
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        log.info(
            "MP3 exported: %s - Duration: %.1f min, Size: %.1f MB",
            output_path,
            duration_secs / 60,
            file_size_mb,
        )

        return output_path

    def _normalize_volume(self, audio: AudioSegment) -> AudioSegment:
        """Normaliza volumen al objetivo configurado si hay nivel medible."""
        if audio.dBFS == float("-inf"):
            return audio
        return audio.apply_gain(self.config.normalize_target_dbfs - audio.dBFS)

    @staticmethod
    def _trim_edge_silence(
        audio: AudioSegment,
        keep_ms: int = 80,
        leading_keep_ms: int | None = None,
        trailing_keep_ms: int | None = None,
        silence_threshold_dbfs: float = -42.0,
    ) -> AudioSegment:
        """Trim API chunk edges, preserving only punctuation-driven trailing time."""
        if not audio or audio.dBFS == float("-inf"):
            return audio
        leading_keep_ms = keep_ms if leading_keep_ms is None else max(0, leading_keep_ms)
        trailing_keep_ms = keep_ms if trailing_keep_ms is None else max(0, trailing_keep_ms)
        leading = detect_leading_silence(
            audio,
            silence_threshold=silence_threshold_dbfs,
            chunk_size=10,
        )
        trailing = detect_leading_silence(
            audio.reverse(),
            silence_threshold=silence_threshold_dbfs,
            chunk_size=10,
        )
        start = max(0, leading - leading_keep_ms)
        end = min(len(audio), len(audio) - trailing + trailing_keep_ms)
        return audio[start:end] if end > start else audio

    def _compress_internal_silence(
        self,
        audio: AudioSegment,
        chunk: TextChunk,
        silence_threshold_dbfs: float = -38.0,
        minimum_silence_ms: int = 350,
    ) -> AudioSegment:
        """Shorten phrase pauses while retaining longer pauses after full stops."""
        if not chunk.alignment or len(audio) < minimum_silence_ms:
            return audio
        spans = detect_silence(
            audio,
            min_silence_len=minimum_silence_ms,
            silence_thresh=silence_threshold_dbfs,
            seek_step=10,
        )
        internal = [
            (start, end)
            for start, end in spans
            if start > 50 and end < len(audio) - 50
        ]
        if not internal:
            return audio

        result = AudioSegment.empty()
        cursor = 0
        for start, end in internal:
            punctuation = self._punctuation_before_silence(chunk, start, end)
            if punctuation in ".!?…":
                keep_ms = self.config.elevenlabs_sentence_pause_ms
            elif punctuation in ",;:":
                keep_ms = self.config.elevenlabs_phrase_pause_ms
            else:
                keep_ms = 0
            duration = end - start
            if duration <= keep_ms:
                continue
            left_keep = keep_ms // 2
            right_keep = keep_ms - left_keep
            result += audio[cursor:start + left_keep]
            cursor = end - right_keep
        result += audio[cursor:]
        return result

    @staticmethod
    def _silence_follows_sentence(chunk: TextChunk, start_ms: int, end_ms: int) -> bool:
        """Use ElevenLabs character timing to identify a sentence-ending pause."""
        return AudioAssembler._punctuation_before_silence(chunk, start_ms, end_ms) in ".!?…"

    @staticmethod
    def _punctuation_before_silence(chunk: TextChunk, start_ms: int, end_ms: int) -> str:
        """Return punctuation responsible for an aligned silence, if present."""
        nearby = [
            character
            for character, char_start, char_end in chunk.alignment
            if char_start * 1000 <= end_ms + 80 and char_end * 1000 >= start_ms - 120
        ]
        for character in reversed(nearby):
            if character in ".!?…,;:":
                return character
        preceding = [
            character
            for character, _char_start, char_end in chunk.alignment
            if char_end * 1000 <= end_ms + 80 and not character.isspace()
        ]
        return preceding[-1] if preceding and preceding[-1] in ".!?…,;:" else ""

    def _punctuation_pause_ms(self, text: str) -> int:
        """Keep a boundary pause only when the spoken text contains punctuation."""
        stripped = text.rstrip().rstrip('"\'’”»)]}')
        if not stripped:
            return 0
        if stripped[-1] in ".!?…":
            return self.config.elevenlabs_sentence_pause_ms
        if stripped[-1] in ",;:":
            return self.config.elevenlabs_phrase_pause_ms
        return 0

    @staticmethod
    def _chunk_ends_sentence(text: str) -> bool:
        """Determina si corresponde insertar pausa tras el chunk."""
        stripped = text.rstrip()
        if not stripped:
            return True
        return stripped[-1] in '.!?\u2026"\u2019\u201d\u00bb)'

    def cleanup_temp_files(self, audio_paths: list[str | None]) -> None:
        """Elimina archivos temporales de audio y la lista concat heredada."""
        for path in audio_paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                log.warning("Could not remove temporary audio %s: %s", path, e)

        if audio_paths:
            first = next((path for path in audio_paths if path), None)
            if first:
                concat_path = os.path.join(os.path.dirname(first), "concat.txt")
                if os.path.exists(concat_path):
                    try:
                        os.remove(concat_path)
                    except OSError:
                        pass
