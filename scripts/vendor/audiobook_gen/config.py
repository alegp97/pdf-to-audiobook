"""
Configuración global de AudioBookGen.

Centraliza todos los parámetros editables del sistema.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class TTSConfig:
    """Configuración del motor de síntesis de voz."""

    engine: str = "edge"  # "edge" | "sapi"
    language: str = "Spanish"
    voice: str = "es-ES-AlvaroNeural"
    rate: str = "+0%"      # p.ej. "+10%", "-5%"
    pitch: str = "+0Hz"    # p.ej. "+5Hz", "-2Hz"
    volume: str = "+0%"


@dataclass
class AudioConfig:
    """Configuración de audio de salida."""

    mp3_bitrate: str = "192k"
    sample_rate: int = 24000
    silence_paragraph_ms: int = 200   # pausa tras punto/oración completa
    silence_chapter_ms: int = 1800
    normalize_target_dbfs: float = -20.0
    save_intermediate_wav: bool = False


@dataclass
class CleanerConfig:
    """Configuración del limpiador de texto."""

    header_footer_threshold: float = 0.5  # % de páginas donde una línea se considera repetida
    min_line_length: int = 3               # Líneas más cortas que esto se descartan
    remove_page_numbers: bool = True


@dataclass
class SegmenterConfig:
    """Configuración del segmentador de texto."""

    max_chunk_chars: int = 500
    min_chunk_chars: int = 50
    respect_sentence_boundaries: bool = True


@dataclass
class Settings:
    """Configuración global del sistema."""

    tts: TTSConfig = field(default_factory=TTSConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    cleaner: CleanerConfig = field(default_factory=CleanerConfig)
    segmenter: SegmenterConfig = field(default_factory=SegmenterConfig)

    temp_dir: str = field(default_factory=lambda: os.path.join(tempfile.gettempdir(), "audiobook_gen"))
    log_file: str = "audiobook_gen.log"
    debug: bool = False

    # Ruta a las reglas de normalización
    normalization_rules_path: Optional[str] = None

    def __post_init__(self) -> None:
        os.makedirs(self.temp_dir, exist_ok=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        """Carga configuración desde un archivo YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        settings = cls()

        if "tts" in data:
            for k, v in data["tts"].items():
                if hasattr(settings.tts, k):
                    setattr(settings.tts, k, v)

        if "audio" in data:
            for k, v in data["audio"].items():
                if hasattr(settings.audio, k):
                    setattr(settings.audio, k, v)

        if "cleaner" in data:
            for k, v in data["cleaner"].items():
                if hasattr(settings.cleaner, k):
                    setattr(settings.cleaner, k, v)

        if "segmenter" in data:
            for k, v in data["segmenter"].items():
                if hasattr(settings.segmenter, k):
                    setattr(settings.segmenter, k, v)

        for key in ("temp_dir", "log_file", "debug", "normalization_rules_path"):
            if key in data:
                setattr(settings, key, data[key])

        settings.__post_init__()
        return settings

    def save_yaml(self, path: str | Path) -> None:
        """Guarda la configuración actual en YAML."""
        data = {
            "tts": {
                "engine": self.tts.engine,
                "language": self.tts.language,
                "voice": self.tts.voice,
                "rate": self.tts.rate,
                "pitch": self.tts.pitch,
                "volume": self.tts.volume,
            },
            "audio": {
                "mp3_bitrate": self.audio.mp3_bitrate,
                "sample_rate": self.audio.sample_rate,
                "silence_paragraph_ms": self.audio.silence_paragraph_ms,
                "silence_chapter_ms": self.audio.silence_chapter_ms,
                "normalize_target_dbfs": self.audio.normalize_target_dbfs,
                "save_intermediate_wav": self.audio.save_intermediate_wav,
            },
            "cleaner": {
                "header_footer_threshold": self.cleaner.header_footer_threshold,
                "min_line_length": self.cleaner.min_line_length,
                "remove_page_numbers": self.cleaner.remove_page_numbers,
            },
            "segmenter": {
                "max_chunk_chars": self.segmenter.max_chunk_chars,
                "min_chunk_chars": self.segmenter.min_chunk_chars,
                "respect_sentence_boundaries": self.segmenter.respect_sentence_boundaries,
            },
            "temp_dir": self.temp_dir,
            "log_file": self.log_file,
            "debug": self.debug,
            "normalization_rules_path": self.normalization_rules_path,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
