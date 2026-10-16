"""
Ensamblado y postproceso de audio.

Une fragmentos de audio, inserta silencios entre secciones,
normaliza volumen y exporta a MP3.
"""

from __future__ import annotations

import os
from typing import Optional

from pydub import AudioSegment

from audiobook_gen.config import AudioConfig
from audiobook_gen.core.text_segmenter import TextChunk
from audiobook_gen.utils.logger import get_logger

log = get_logger("audio_assembler")


class AudioAssembler:
    """Ensambla fragmentos de audio en un audiolibro completo."""

    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or AudioConfig()

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
                combined += AudioSegment.from_file(audio_path)
            except Exception as e:
                raise RuntimeError(f"Could not read audio chunk {audio_path}: {e}") from e

            if i < len(audio_paths) - 1:
                if chunk.is_chapter_end:
                    combined += AudioSegment.silent(duration=self.config.silence_chapter_ms)
                    log.debug("Chapter pause inserted after chunk %d", chunk.index)
                elif self._chunk_ends_sentence(chunk.text):
                    combined += AudioSegment.silent(duration=self.config.silence_paragraph_ms)

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
