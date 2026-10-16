"""
Limpieza de texto extraído de PDF.

Elimina artefactos visuales del PDF: cabeceras/pies repetidos, números de página,
caracteres basura, y repara cortes de palabra por salto de línea.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from audiobook_gen.config import CleanerConfig
from audiobook_gen.core.pdf_extractor import PageContent
from audiobook_gen.utils.logger import get_logger

log = get_logger("text_cleaner")


@dataclass
class Chapter:
    """Un capítulo detectado en el texto."""
    title: str
    content: str
    page_start: int


@dataclass
class CleanedText:
    """Resultado de la limpieza de texto."""
    chapters: list[Chapter] = field(default_factory=list)
    raw_text: str = ""
    preamble: str = ""

    @property
    def full_text(self) -> str:
        if self.chapters:
            parts = [self.preamble] if self.preamble else []
            for ch in self.chapters:
                parts.append(f"\n\n[CAPÍTULO: {ch.title}]\n\n{ch.title}\n\n{ch.content}")
            return "\n".join(parts)
        return self.raw_text


# Patrones de detección de capítulos
CHAPTER_PATTERNS = [
    re.compile(r"^((?:chapter|part|section)\s+(?:\d+|[IVXLCDM]+)\b[.:)—\-\s]*.*)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(cap[íi]tulo\s+[\dIVXLCDM]+[.:)—\-\s]*.*)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(CAPÍTULO\s+[\dIVXLCDM]+[.:)—\-\s]*.*)$", re.MULTILINE),
    re.compile(r"^(PARTE\s+[\dIVXLCDM]+[.:)—\-\s]*.*)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(\d+\.\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{5,})$", re.MULTILINE),
]

# Patrón para números de página sueltos
PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE),
    re.compile(r"^\s*[-—]\s*\d{1,4}\s*[-—]\s*$", re.MULTILINE),
    re.compile(r"^\s*[Pp]ágina\s+\d+\s*$", re.MULTILINE),
    re.compile(r"^\s*[Pp]age\s+\d+\s*$", re.MULTILINE),
]


class TextCleaner:
    """Limpia texto extraído de PDF para producción de audiolibro."""

    def __init__(self, config: Optional[CleanerConfig] = None) -> None:
        self.config = config or CleanerConfig()

    def clean(self, pages: list[PageContent]) -> CleanedText:
        """
        Limpia la lista de páginas extraídas.

        Pipeline de limpieza:
        1. Detectar y eliminar cabeceras/pies repetidos
        2. Eliminar números de página
        3. Reparar cortes de palabra por guión + salto de línea
        4. Normalizar espacios y caracteres
        5. Eliminar líneas basura
        6. Detectar capítulos
        """
        log.info("Cleaning %d pages", len(pages))

        # Paso 1: Detectar líneas repetidas (cabeceras/pies)
        repeated = self._detect_repeated_lines(pages)
        if repeated:
            log.info("Detected repeated header/footer lines: %d", len(repeated))

        # Procesar cada página
        cleaned_parts: list[str] = []
        for page in pages:
            text = page.text

            # Eliminar cabeceras/pies repetidos
            text = "\n".join(line for line in text.split("\n") if line.strip() not in repeated)

            # Eliminar números de página
            if self.config.remove_page_numbers:
                text = self._remove_page_numbers(text)

            # Reparar cortes de palabra por guión antes de unir líneas
            text = self._fix_hyphenated_words(text)

            # Normalizar espacios y caracteres
            text = self._normalize_whitespace(text)
            text = self._remove_junk_characters(text)

            # Eliminar líneas demasiado cortas (probablemente basura)
            lines = text.split("\n")
            lines = [
                ln for ln in lines
                if len(ln.strip()) >= self.config.min_line_length
                or ln.strip() == ""  # preservar párrafos vacíos
            ]
            text = "\n".join(lines)

            if text.strip():
                cleaned_parts.append(text.strip())

        full_text = "\n\n".join(cleaned_parts)

        # Unir líneas de continuidad DESPUÉS de ensamblar todas las páginas.
        # Esto resuelve el problema de pausas entre líneas del PDF que
        # pertenecen al mismo párrafo/frase narrativa.
        full_text = self._join_continuation_lines(full_text)

        # Detectar capítulos
        chapters = self._detect_chapters(full_text, pages)

        result = CleanedText(
            chapters=chapters,
            raw_text=full_text,
            preamble=(full_text[:min(
                match.start() for pattern in CHAPTER_PATTERNS
                for match in pattern.finditer(full_text)
            )].strip() if chapters else ""),
        )

        log.info(
            "Cleanup complete — %d chapters detected, %d characters",
            len(chapters),
            len(full_text),
        )
        return result

    def _detect_repeated_lines(self, pages: list[PageContent]) -> list[str]:
        """Detecta líneas que se repiten en muchas páginas (cabeceras/pies)."""
        if len(pages) < 3:
            return []

        # Contar primeras y últimas líneas de cada página
        line_counter: Counter[str] = Counter()
        for page in pages:
            lines = [ln.strip() for ln in page.text.strip().split("\n") if ln.strip()]
            if not lines:
                continue
            # Verificar las primeras 3 y últimas 3 líneas
            candidates = lines[:3] + lines[-3:]
            for ln in set(candidates):
                if len(ln) > 2:  # Evitar contar líneas vacías o muy cortas
                    if any(pattern.match(ln) for pattern in CHAPTER_PATTERNS):
                        continue
                    line_counter[ln] += 1

        threshold = len(pages) * self.config.header_footer_threshold
        return [ln for ln, count in line_counter.items() if count >= threshold]

    def _remove_page_numbers(self, text: str) -> str:
        """Elimina números de página."""
        for pattern in PAGE_NUMBER_PATTERNS:
            text = pattern.sub("", text)
        return text

    def _fix_hyphenated_words(self, text: str) -> str:
        """Repara palabras cortadas por guión al final de línea."""
        # "pala-\nbra" → "palabra"
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
        # "pala-  bra" within the same line after imperfect extraction
        text = re.sub(r"(\w)-\s{2,}(\w)", r"\1\2", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normaliza espacios: múltiples → uno, elimina tabs."""
        text = text.replace("\t", " ")
        text = re.sub(r"[^\S\n]+", " ", text)  # Múltiples espacios → uno (preservar newlines)
        text = re.sub(r"\n{4,}", "\n\n\n", text)  # Max 3 newlines seguidos
        return text

    def _join_continuation_lines(self, text: str) -> str:
        """
        Une líneas de continuidad: un \\n simple entre dos líneas de texto
        que NO terminan en puntuación fuerte (.!?…) se convierte en espacio.

        Esto evita que cada línea del PDF genere un chunk TTS independiente
        con silencio artificial entre ellos.

        Regla:
        - Si la línea anterior termina en [a-záéíóúñA-Z0-9,;:"] → unir con espacio
        - Si termina en [.!?…] → preservar el párrafo (doble newline)
        - Doble newline siempre separa párrafos reales → no tocar
        """
        # Primero proteger los dobles newlines reemplazándolos temporalmente
        PLACEHOLDER = "\x00PARRAFO\x00"
        text = re.sub(r"\n{2,}", PLACEHOLDER, text)

        # Unir líneas que continúan: línea no terminada en puntuación fuerte
        # seguida de un \n simple y otra línea con texto
        text = re.sub(
            r"([^.!?…\n])\n([^\n])",
            r"\1 \2",
            text,
        )

        # Restaurar párrafos reales
        text = text.replace(PLACEHOLDER, "\n\n")
        return text

    def _remove_junk_characters(self, text: str) -> str:
        """Elimina caracteres basura no imprimibles."""
        # Mantener letras, números, puntuación estándar, y caracteres acentuados
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Eliminar secuencias de caracteres especiales extraños
        text = re.sub(r"[□■●◆▪▫▶►◀◄★☆♦♣♠♥]+", "", text)
        # Eliminar bullets sueltos
        text = re.sub(r"^[•·–]\s*", "", text, flags=re.MULTILINE)
        return text

    def _detect_chapters(
        self, text: str, pages: list[PageContent]
    ) -> list[Chapter]:
        """Detecta capítulos en el texto limpio."""
        chapter_positions: list[tuple[int, str]] = []

        for pattern in CHAPTER_PATTERNS:
            for match in pattern.finditer(text):
                title = match.group(1).strip()
                pos = match.start()
                # Evitar duplicados cercanos
                if not any(abs(pos - p) < 50 for p, _ in chapter_positions):
                    chapter_positions.append((pos, title))

        if not chapter_positions:
            return []

        # Ordenar por posición
        chapter_positions.sort(key=lambda x: x[0])

        chapters: list[Chapter] = []
        for i, (pos, title) in enumerate(chapter_positions):
            # Contenido hasta el siguiente capítulo o fin
            end = (
                chapter_positions[i + 1][0]
                if i + 1 < len(chapter_positions)
                else len(text)
            )
            content = text[pos + len(title):end].strip()

            # Estimar página de inicio
            chars_before = pos
            page_start = 1
            chars_acc = 0
            for page in pages:
                chars_acc += len(page.text)
                if chars_acc >= chars_before:
                    page_start = page.page_number
                    break

            chapters.append(Chapter(title=title, content=content, page_start=page_start))

        log.debug("Detected chapters: %s", [ch.title for ch in chapters])
        return chapters
