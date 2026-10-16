"""
Segmentación inteligente de texto para TTS.

Divide el texto en chunks apropiados para síntesis de voz,
respetando límites de oración, párrafos y capítulos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from audiobook_gen.config import SegmenterConfig
from audiobook_gen.utils.logger import get_logger

log = get_logger("text_segmenter")


@dataclass
class TextChunk:
    """Un fragmento de texto listo para TTS."""
    text: str
    index: int
    chapter: Optional[str] = None
    is_chapter_start: bool = False
    is_chapter_end: bool = False

    @property
    def char_count(self) -> int:
        return len(self.text)


# Patrón para dividir en oraciones (español)
SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\"])"
)

# Marcador de capítulo insertado por TextCleaner
CHAPTER_MARKER = re.compile(r"\[CAPÍTULO:\s*(.+?)\]")


class TextSegmenter:
    """Divide texto normalizado en chunks para TTS."""

    def __init__(self, config: Optional[SegmenterConfig] = None) -> None:
        self.config = config or SegmenterConfig()

    def segment(self, text: str) -> list[TextChunk]:
        """
        Segmenta el texto en chunks para TTS.

        Estrategia:
        1. Dividir por marcadores de capítulo
        2. Dividir párrafos largos por oraciones
        3. Respetar límite máximo de caracteres por chunk
        4. No cortar oraciones a la mitad
        """
        chunks: list[TextChunk] = []
        chunk_index = 0

        # Dividir por capítulos si los hay
        sections = self._split_by_chapters(text)

        for section_chapter, section_text in sections:
            paragraphs = self._split_paragraphs(section_text)

            first_in_chapter = True
            for para_idx, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue

                if len(paragraph) <= self.config.max_chunk_chars:
                    chunks.append(TextChunk(
                        text=paragraph,
                        index=chunk_index,
                        chapter=section_chapter,
                        is_chapter_start=first_in_chapter,
                    ))
                    chunk_index += 1
                    first_in_chapter = False
                else:
                    # Párrafo largo → dividir por oraciones
                    sub_chunks = self._split_long_paragraph(paragraph)
                    for sub in sub_chunks:
                        chunks.append(TextChunk(
                            text=sub,
                            index=chunk_index,
                            chapter=section_chapter,
                            is_chapter_start=first_in_chapter,
                        ))
                        chunk_index += 1
                        first_in_chapter = False

            # Marcar el último chunk del capítulo
            if chunks and section_chapter:
                chunks[-1].is_chapter_end = True

        # Filtrar chunks vacíos o demasiado cortos
        chunks = [
            ch for ch in chunks
            if len(ch.text.strip()) >= self.config.min_chunk_chars
        ]

        # Re-indexar
        for i, ch in enumerate(chunks):
            ch.index = i

        log.info(
            "Segmentation complete — %d chunks, average %d characters",
            len(chunks),
            sum(ch.char_count for ch in chunks) // max(len(chunks), 1),
        )

        return chunks

    def _split_by_chapters(self, text: str) -> list[tuple[Optional[str], str]]:
        """Divide texto por marcadores de capítulo."""
        parts = CHAPTER_MARKER.split(text)

        if len(parts) == 1:
            # No hay capítulos
            return [(None, text)]

        sections: list[tuple[Optional[str], str]] = []

        # El primer elemento es texto antes del primer capítulo
        if parts[0].strip():
            sections.append((None, parts[0]))

        # Los siguientes son pares (título_capítulo, contenido)
        for i in range(1, len(parts), 2):
            chapter_title = parts[i].strip() if i < len(parts) else None
            content = parts[i + 1] if i + 1 < len(parts) else ""
            if chapter_title:
                sections.append((chapter_title, content))

        return sections

    def _split_paragraphs(self, text: str) -> list[str]:
        """Divide texto en párrafos."""
        # Doble newline = párrafo
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        """Divide un párrafo largo respetando límites de oración."""
        if not self.config.respect_sentence_boundaries:
            # División simple por longitud
            return self._split_by_length(paragraph)

        sentences = SENTENCE_SPLIT.split(paragraph)
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if current_len + len(sentence) + 1 > self.config.max_chunk_chars and current:
                chunks.append(" ".join(current))
                current = [sentence]
                current_len = len(sentence)
            else:
                current.append(sentence)
                current_len += len(sentence) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _split_by_length(self, text: str) -> list[str]:
        """División simple por longitud máxima (fallback)."""
        words = text.split()
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 > self.config.max_chunk_chars and current:
                chunks.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks
