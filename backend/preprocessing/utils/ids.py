from __future__ import annotations

import re
from dataclasses import dataclass

SCRIPT_FILE_RE = re.compile(r"^(\d{8})_(.+)\.pdf$", re.IGNORECASE)


@dataclass
class PdfMeta:
    script_id: str
    title: str
    source_pdf: str


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name.strip())


def character_id(name: str) -> str:
    return f"c_{normalize_name(name)}"


def parse_pdf_filename(filename: str) -> PdfMeta | None:
    base = filename.replace("\\", "/").split("/")[-1]
    m = SCRIPT_FILE_RE.match(base)
    if not m:
        return None
    script_id, title = m.group(1), m.group(2).strip()
    return PdfMeta(script_id=script_id, title=title, source_pdf=base)
