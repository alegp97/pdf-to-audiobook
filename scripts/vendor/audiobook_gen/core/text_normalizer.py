"""
Normalización lingüística del texto para TTS.

Convierte abreviaturas, números, siglas y símbolos a formas pronunciables.
Carga reglas editables desde YAML.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

from audiobook_gen.utils.logger import get_logger

log = get_logger("text_normalizer")

# Ruta por defecto a las reglas de normalización
_DEFAULT_RULES_PATH = Path(__file__).parent.parent / "rules" / "normalization.yaml"


def _number_to_words_es(n: int) -> str:
    """Convierte un entero a palabras en español usando num2words."""
    try:
        from num2words import num2words
        return num2words(n, lang="es")
    except ImportError:
        log.warning("num2words is unavailable; numbers will remain as digits.")
        return str(n)
    except Exception:
        return str(n)


class TextNormalizer:
    """Normaliza texto para que suene natural al ser leído por TTS."""

    def __init__(self, rules_path: Optional[str | Path] = None) -> None:
        self.rules_path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
        self.abbreviations: dict[str, str] = {}
        self.symbols: dict[str, str] = {}
        self.spell_acronyms: list[str] = []
        self.artifact_patterns: list[re.Pattern[str]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Carga reglas de normalización desde YAML."""
        if not self.rules_path.exists():
            log.warning("Normalization rules not found: %s", self.rules_path)
            return

        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.abbreviations = data.get("abbreviations", {})
        self.symbols = data.get("symbols", {})
        self.spell_acronyms = data.get("spell_acronyms", [])
        self.artifact_patterns = [
            re.compile(p, re.MULTILINE)
            for p in data.get("artifacts_patterns", [])
        ]

        log.info(
            "Rules loaded — %d abbreviations, %d symbols, %d acronyms, %d patterns",
            len(self.abbreviations),
            len(self.symbols),
            len(self.spell_acronyms),
            len(self.artifact_patterns),
        )

    def normalize(self, text: str) -> str:
        """
        Normaliza texto para TTS.

        Pipeline:
        1. Eliminar artefactos residuales
        2. Expandir abreviaturas
        3. Convertir números a palabras
        4. Deletrear siglas
        5. Reemplazar símbolos
        6. Normalizar puntuación para prosodia
        """
        text = self._remove_artifacts(text)
        text = self._expand_abbreviations(text)
        text = self._convert_numbers(text)
        text = self._spell_acronyms(text)
        text = self._replace_symbols(text)
        text = self._normalize_punctuation_for_prosody(text)
        text = self._final_cleanup(text)

        return text

    def _remove_artifacts(self, text: str) -> str:
        """Elimina artefactos residuales usando patrones regex."""
        for pattern in self.artifact_patterns:
            text = pattern.sub("", text)
        return text

    def _expand_abbreviations(self, text: str) -> str:
        """Expande abreviaturas a su forma completa."""
        for abbr, expansion in self.abbreviations.items():
            # Usar word boundary para evitar reemplazos parciales
            # re.escape para manejar puntos en las abreviaturas
            pattern = re.compile(re.escape(abbr), re.IGNORECASE)
            text = pattern.sub(expansion, text)
        return text

    def _convert_numbers(self, text: str) -> str:
        """Convierte números a palabras en español."""

        # Números con separador de miles: 1.500 → mil quinientos
        def _replace_thousands(m: re.Match) -> str:
            num_str = m.group(0).replace(".", "")
            try:
                return _number_to_words_es(int(num_str))
            except ValueError:
                return m.group(0)

        text = re.sub(r"\b\d{1,3}(?:\.\d{3})+\b", _replace_thousands, text)

        # Números decimales con coma: 3,14 → "tres coma catorce"
        def _replace_decimal(m: re.Match) -> str:
            integer_part = m.group(1)
            decimal_part = m.group(2)
            int_words = _number_to_words_es(int(integer_part))
            dec_words = _number_to_words_es(int(decimal_part))
            return f"{int_words} coma {dec_words}"

        text = re.sub(r"\b(\d+),(\d+)\b", _replace_decimal, text)

        # Números simples (no precedidos de "Capítulo" u otros contextos)
        def _replace_simple_number(m: re.Match) -> str:
            num = int(m.group(0))
            if num > 9999:
                return m.group(0)  # Dejar años y números muy grandes
            return _number_to_words_es(num)

        # Solo convertir números que están en contexto narrativo (rodeados de texto)
        text = re.sub(r"(?<=[a-záéíóúñ]\s)\d{1,4}(?=\s[a-záéíóúñ])", _replace_simple_number, text)

        # Años comunes (1900-2099) se dejan como están para que TTS los lea bien
        # Los motores TTS neuronales suelen manejar años correctamente

        return text

    def _spell_acronyms(self, text: str) -> str:
        """Deletrea siglas: ONU → O-N-U."""
        for acronym in self.spell_acronyms:
            spelled = "-".join(acronym)
            # Solo reemplazar si es palabra completa
            text = re.sub(
                rf"\b{re.escape(acronym)}\b",
                spelled,
                text,
            )
        return text

    def _replace_symbols(self, text: str) -> str:
        """Reemplaza símbolos por su equivalente pronunciable."""
        # Ordenar por longitud descendente para reemplazar "°C" antes que "°"
        sorted_symbols = sorted(self.symbols.keys(), key=len, reverse=True)
        for symbol in sorted_symbols:
            replacement = self.symbols[symbol]
            text = text.replace(symbol, replacement)
        return text

    def _normalize_punctuation_for_prosody(self, text: str) -> str:
        """Normaliza puntuación para mejorar la prosodia del TTS."""
        # Puntos suspensivos → pausa (TTS los interpreta mejor normalizados)
        text = re.sub(r"\.{2,}", "...", text)

        # Guión largo como pausa narrativa
        text = text.replace("—", ", ")
        text = text.replace("–", ", ")

        # Comillas tipográficas → comillas simples (menos confuso para TTS)
        text = text.replace("«", '"').replace("»", '"')
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")

        # Múltiples signos de exclamación/interrogación
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[?]{2,}", "?", text)

        return text

    def _final_cleanup(self, text: str) -> str:
        """Limpieza final del texto normalizado."""
        # Eliminar espacios extra que se hayan generado
        text = re.sub(r"  +", " ", text)
        # Eliminar espacios antes de puntuación
        text = re.sub(r"\s+([.,;:!?])", r"\1", text)
        # Asegurar espacio después de puntuación
        text = re.sub(r"([.,;:!?])([A-ZÁÉÍÓÚÑa-záéíóúñ])", r"\1 \2", text)
        return text.strip()
