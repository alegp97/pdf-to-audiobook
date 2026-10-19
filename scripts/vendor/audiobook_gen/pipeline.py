"""
Pipeline principal de AudioBookGen.

Orquesta todo el flujo: PDF → Texto → Limpieza → Normalización
→ Segmentación → TTS → Ensamblado → MP3.

Emite señales de progreso para la GUI.
"""

from __future__ import annotations

import os
import time
import concurrent.futures
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from audiobook_gen.config import Settings
from audiobook_gen.core.audio_assembler import AudioAssembler
from audiobook_gen.core.pdf_extractor import PDFExtractor, ExtractionResult
from audiobook_gen.core.text_cleaner import TextCleaner, CleanedText
from audiobook_gen.core.text_normalizer import TextNormalizer
from audiobook_gen.core.text_segmenter import TextSegmenter, TextChunk
from audiobook_gen.core.tts_engine import create_tts_engine
from audiobook_gen.utils.logger import get_logger

log = get_logger("pipeline")


class PipelineState(str, Enum):
    """Pipeline execution states."""
    IDLE = "Ready"
    LOADING = "Loading PDF..."
    EXTRACTING = "Extracting text..."
    CLEANING = "Cleaning text..."
    NORMALIZING = "Normalising text..."
    SEGMENTING = "Segmenting text..."
    SYNTHESIZING = "Generating voice..."
    ASSEMBLING = "Assembling audio..."
    DONE = "Done!"
    ERROR = "Error"


@dataclass
class PipelineProgress:
    """Información de progreso del pipeline."""
    state: PipelineState
    progress: float  # 0.0 a 1.0
    message: str = ""
    detail: str = ""


@dataclass
class PipelineResult:
    """Resultado del pipeline."""
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
    duration_secs: float = 0.0
    total_chunks: int = 0
    total_chars: int = 0
    chapters_detected: int = 0


# Pesos relativos de cada fase para la barra de progreso
_PHASE_WEIGHTS = {
    PipelineState.LOADING: 0.02,
    PipelineState.EXTRACTING: 0.08,
    PipelineState.CLEANING: 0.05,
    PipelineState.NORMALIZING: 0.05,
    PipelineState.SEGMENTING: 0.05,
    PipelineState.SYNTHESIZING: 0.65,  # La fase más lenta
    PipelineState.ASSEMBLING: 0.10,
}


class AudioBookPipeline:
    """Orquestador principal del pipeline PDF → MP3."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        progress_callback: Optional[Callable[[PipelineProgress], None]] = None,
    ) -> None:
        self.settings = settings or Settings()
        self._progress_callback = progress_callback
        self._cancelled = False

    def cancel(self) -> None:
        """Request pipeline cancellation."""
        self._cancelled = True
        log.info("Cancellation requested")

    def _emit_progress(
        self,
        state: PipelineState,
        progress: float,
        message: str = "",
        detail: str = "",
    ) -> None:
        """Emite progreso vía callback."""
        if self._progress_callback:
            self._progress_callback(PipelineProgress(
                state=state,
                progress=min(progress, 1.0),
                message=message or state.value,
                detail=detail,
            ))

    def _check_cancelled(self) -> None:
        """Raise an exception if cancellation has been requested."""
        if self._cancelled:
            raise InterruptedError("Pipeline cancelled by user")

    def run(self, pdf_path: str, output_path: str) -> PipelineResult:
        """
        Ejecuta el pipeline completo.

        Args:
            pdf_path: Ruta al PDF de entrada.
            output_path: Ruta para el MP3 de salida.

        Returns:
            PipelineResult con los datos del resultado.
        """
        self._cancelled = False
        start_time = time.time()
        temp_audio_files: list[str | None] = []

        try:
            # ── Phase 1: Load & validate ──
            self._emit_progress(PipelineState.LOADING, 0.0)
            pdf_path_obj = Path(pdf_path)
            if not pdf_path_obj.exists():
                raise FileNotFoundError(f"File not found: {pdf_path}")
            self._check_cancelled()

            # ── Phase 2: Text extraction ──
            base_progress = 0.02
            self._emit_progress(PipelineState.EXTRACTING, base_progress)
            extractor = PDFExtractor()
            extraction = extractor.extract(pdf_path)
            log.info("Extracted %d pages", extraction.metadata.total_pages)
            self._check_cancelled()

            # ── Phase 3: Text cleaning ──
            base_progress = 0.10
            self._emit_progress(PipelineState.CLEANING, base_progress)
            cleaner = TextCleaner(self.settings.cleaner)
            cleaned = cleaner.clean(extraction.pages)
            self._check_cancelled()

            # ── Phase 4: Linguistic normalisation ──
            base_progress = 0.15
            self._emit_progress(PipelineState.NORMALIZING, base_progress)
            normalizer = TextNormalizer(self.settings.normalization_rules_path)
            normalized_text = (normalizer.normalize(cleaned.full_text)
                               if self.settings.tts.language == "Spanish" else cleaned.full_text.strip())
            log.info("Normalised text: %d characters", len(normalized_text))
            self._check_cancelled()

            # ── Phase 5: Segmentation ──
            base_progress = 0.20
            self._emit_progress(PipelineState.SEGMENTING, base_progress)
            segmenter_config = replace(self.settings.segmenter)
            if self.settings.tts.engine == "elevenlabs":
                segmenter_config.max_chunk_chars = self.settings.tts.elevenlabs_chunk_chars
            segmenter = TextSegmenter(segmenter_config)
            chunks = segmenter.segment(normalized_text)
            log.info("Text segmented into %d chunks", len(chunks))
            if not chunks:
                raise RuntimeError("No narratable text was found after cleaning and segmentation.")
            self._check_cancelled()

            # ── Phase 6: Voice synthesis ──
            base_progress = 0.25
            self._emit_progress(
                PipelineState.SYNTHESIZING, base_progress,
                detail=f"0/{len(chunks)} chunks",
            )
            tts_engine = create_tts_engine(self.settings.tts)
            log.info("TTS engine: %s", tts_engine.get_voice_name())

            tts_progress_range = 0.65  # 65% of total
            temp_audio_files = [None] * len(chunks)
            completed_tasks = 0

            def _process_chunk(idx: int, chnk: TextChunk) -> str:
                self._check_cancelled()
                extension = tts_engine.preferred_extension()
                chunk_file = os.path.join(
                    self.settings.temp_dir,
                    f"chunk_{idx:05d}{extension}",
                )
                return tts_engine.synthesize(chnk, chunk_file)

            # Edge-TTS is online and can be heavily parallelized.
            # SAPI5 is a local COM object and usually doesn't like multi-threading.
            max_workers = 4 if self.settings.tts.engine == "edge" else 1
            log.info(f"Synthesizing {len(chunks)} chunks using {max_workers} threads...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_idx = {}
                for i, chunk in enumerate(chunks):
                    if self.settings.tts.engine == "edge":
                        future = executor.submit(_process_chunk, i, chunk)
                    else:
                        # SAPI COM objects must stay on the thread that created them.
                        future = concurrent.futures.Future()
                        try:
                            future.set_result(_process_chunk(i, chunk))
                        except Exception as exc:
                            future.set_exception(exc)
                    future_to_idx[future] = i

                # Process as they complete to update progress bar
                for future in concurrent.futures.as_completed(future_to_idx):
                    self._check_cancelled()
                    idx = future_to_idx[future]
                    try:
                        chunk_path = future.result()
                        temp_audio_files[idx] = chunk_path
                        completed_tasks += 1

                        chunk_progress = base_progress + (
                            tts_progress_range * completed_tasks / len(chunks)
                        )
                        self._emit_progress(
                            PipelineState.SYNTHESIZING,
                            chunk_progress,
                            detail=f"{completed_tasks}/{len(chunks)} chunks",
                        )
                    except InterruptedError:
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise
                    except Exception as e:
                        executor.shutdown(wait=False, cancel_futures=True)
                        log.error(f"Error generating chunk {idx}: {e}")
                        raise RuntimeError(f"Error generating voice for chunk {idx}: {e}") from e

            # Verify all chunks were processed
            if any(path is None for path in temp_audio_files):
                raise RuntimeError("Some audio chunks were not generated properly.")

            # ── Phase 7: Assembly ──
            base_progress = 0.90
            self._emit_progress(PipelineState.ASSEMBLING, base_progress)
            assembler = AudioAssembler(
                self.settings.audio,
                trim_chunk_edges=self.settings.tts.engine == "elevenlabs",
            )
            assembler.assemble([path for path in temp_audio_files if path], chunks, output_path)
            self._check_cancelled()

            # ── Completado ──
            duration = time.time() - start_time
            self._emit_progress(
                PipelineState.DONE, 1.0,
                detail=f"Duration: {duration:.0f}s",
            )

            result = PipelineResult(
                success=True,
                output_path=output_path,
                duration_secs=duration,
                total_chunks=len(chunks),
                total_chars=len(normalized_text),
                chapters_detected=len(cleaned.chapters),
            )
            log.info(
                "Pipeline completed in %.1f sec — %d chunks, %d chars, %d chapters",
                duration, result.total_chunks, result.total_chars,
                result.chapters_detected,
            )
            return result

        except InterruptedError:
            self._emit_progress(PipelineState.IDLE, 0.0, message="Cancelled")
            return PipelineResult(success=False, error="Cancelled by user")

        except Exception as e:
            log.error("Pipeline error: %s", e, exc_info=True)
            self._emit_progress(PipelineState.ERROR, 0.0, message=str(e))
            return PipelineResult(success=False, error=str(e))

        finally:
            # Limpiar archivos temporales
            assembler_cleanup = AudioAssembler(self.settings.audio)
            assembler_cleanup.cleanup_temp_files(temp_audio_files)
