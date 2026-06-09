from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractResult:
    pages: list[str] = field(default_factory=list)
    page_count: int = 0
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(self.pages)


def extract_pdf_pages(pdf_path: Path) -> ExtractResult:
    warnings: list[str] = []
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "Install pdfplumber: pip install -r backend/requirements.txt"
        ) from exc

    pages: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            if not text.strip():
                warnings.append(f"page_{i + 1}_empty")
            pages.append(text)

    if not any(p.strip() for p in pages):
        warnings.append("document_empty")

    return ExtractResult(
        pages=pages,
        page_count=len(pages),
        ocr_used=False,
        warnings=warnings,
    )
