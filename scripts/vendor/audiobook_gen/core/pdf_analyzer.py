"""
PDF Analyzer for SimpleAudioBookGen.
Estimates document length, audio duration, and scanned-PDF likelihood.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pymupdf as fitz

@dataclass
class PdfAnalysis:
    path: str
    filename: str
    pages: int
    characters: int
    is_scanned_likelihood: float  # 0.0 to 1.0
    estimated_duration_minutes: float
    
    @property
    def requires_ocr(self) -> bool:
        return self.is_scanned_likelihood > 0.5

class PdfAnalyzer:
    """Analyzes PDF content to provide helpful user estimates."""
    
    # Average reading speed: ~150 words per minute
    # Average word length: ~5.2 characters
    CHARS_PER_MINUTE = 150 * 5.2

    def analyze(self, pdf_path: str | Path) -> PdfAnalysis:
        path = Path(pdf_path)
        doc = fitz.open(str(path))
        try:
            total_pages = len(doc)
            total_chars = 0
            text_samples = 0
            pages_with_text = 0

            # Sample pages (first, middle, last + others if doc is large)
            sample_indices = set([0, total_pages // 2, total_pages - 1])
            if total_pages > 10:
                sample_indices.update([1, 2, total_pages - 2])

            for i in range(total_pages):
                page = doc[i]
                text = page.get_text("text").strip()
                page_chars = len(text)

                # PyMuPDF is fast enough to scan all selectable text.
                total_chars += page_chars

                if i in sample_indices:
                    text_samples += 1
                    if page_chars > 50:
                        pages_with_text += 1
        finally:
            doc.close()
        
        # Likelihood calculation: if most samples have very little text, it's likely scanned.
        is_scanned_likelihood = 1.0 - (pages_with_text / text_samples) if text_samples > 0 else 1.0
        
        # Refine total chars for UI estimates. Scanned files are rejected in v1,
        # but an estimate still helps explain why the document was flagged.
        estimated_chars = total_chars
        if estimated_chars < 100 and is_scanned_likelihood > 0.5:
            estimated_chars = total_pages * 2000 

        duration = estimated_chars / self.CHARS_PER_MINUTE
        
        return PdfAnalysis(
            path=str(path),
            filename=path.name,
            pages=total_pages,
            characters=total_chars,
            is_scanned_likelihood=is_scanned_likelihood,
            estimated_duration_minutes=duration
        )
