from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..utils.ids import PdfMeta, parse_pdf_filename
from .unzip import decode_zip_name


@dataclass
class PdfSource:
    pdf_path: Path | None
    zip_path: Path | None
    zip_member: str | None
    collection_id: str
    meta: PdfMeta


def list_single_pdf(
    pdf_path: Path,
    collection_id: str,
    *,
    title: str | None = None,
) -> PdfSource:
    meta = parse_pdf_filename(pdf_path.name)
    if not meta:
        raise ValueError(f"无法解析文件名: {pdf_path.name}")
    if title:
        meta = PdfMeta(
            script_id=meta.script_id,
            title=title,
            source_pdf=meta.source_pdf,
        )
    return PdfSource(
        pdf_path=pdf_path,
        zip_path=None,
        zip_member=None,
        collection_id=collection_id,
        meta=meta,
    )


def list_pdfs_in_zip(zip_path: Path, collection_id: str) -> list[PdfSource]:
    items: list[PdfSource] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if not member.lower().endswith(".pdf") or member.endswith("/"):
                continue
            decoded = decode_zip_name(member)
            meta = parse_pdf_filename(decoded)
            if not meta:
                continue
            items.append(
                PdfSource(
                    pdf_path=None,
                    zip_path=zip_path,
                    zip_member=member,
                    collection_id=collection_id,
                    meta=meta,
                )
            )
    items.sort(key=lambda x: x.meta.script_id)
    return items
