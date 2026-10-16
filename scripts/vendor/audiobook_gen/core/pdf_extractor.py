"""Extract selectable text from text-based PDF files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pymupdf as fitz

from audiobook_gen.utils.logger import get_logger

log = get_logger("pdf_extractor")

SCANNED_PDF_MESSAGE = (
    "Scanned PDF detected. This PDF does not seem to contain selectable text. "
    "SimpleAudioBookGen currently works with text-based PDFs. Please convert "
    "this file to a searchable PDF using an OCR tool, then try again."
)


class ScannedPdfError(ValueError):
    """Raised when a PDF has too little selectable text for v1 processing."""


@dataclass
class PageContent:
    """Text content extracted from one PDF page."""

    page_number: int
    text: str
    is_ocr: bool = False


@dataclass
class PDFMetadata:
    """PDF metadata used by the pipeline."""

    title: Optional[str] = None
    author: Optional[str] = None
    total_pages: int = 0
    is_scanned: bool = False


@dataclass
class ExtractionResult:
    """Complete text extraction result."""

    metadata: PDFMetadata = field(default_factory=PDFMetadata)
    pages: list[PageContent] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text.strip())


class PDFExtractor:
    """Extract text from PDFs that already contain selectable text."""

    SCANNED_THRESHOLD = 50

    def extract(self, pdf_path: str | Path) -> ExtractionResult:
        """Extract text from a text-based PDF."""
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"File not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"The file is not a PDF: {pdf_path}")

        log.info("Opening PDF: %s", pdf_path.name)

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            raise ValueError(f"Could not open PDF: {exc}") from exc

        try:
            metadata = PDFMetadata(
                title=doc.metadata.get("title") or None,
                author=doc.metadata.get("author") or None,
                total_pages=len(doc),
            )
            pages = self._extract_text(doc)

            avg_chars = sum(len(page.text) for page in pages) / max(len(pages), 1)
            if avg_chars < self.SCANNED_THRESHOLD:
                metadata.is_scanned = True
                log.warning(
                    "Scanned or low-text PDF detected: %.0f average chars/page",
                    avg_chars,
                )
                raise ScannedPdfError(SCANNED_PDF_MESSAGE)

            result = ExtractionResult(metadata=metadata, pages=pages)
            total_chars = sum(len(page.text) for page in pages)
            log.info(
                "Extraction completed: %d pages, %d characters",
                len(result.pages),
                total_chars,
            )
            return result
        finally:
            doc.close()

    def _extract_text(self, doc: fitz.Document) -> list[PageContent]:
        pages: list[PageContent] = []
        for index, page in enumerate(doc):
            pages.append(PageContent(page_number=index + 1, text=page.get_text("text")))
        return pages
