"""预处理单剧本 worker — 供进程池调用。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.preprocessing.clean.pipeline import process_extract_result_to_play
from backend.preprocessing.export.write_json import PlayWriter, build_catalog_entry
from backend.preprocessing.extract.pdf_text import extract_pdf_pages
from backend.preprocessing.ingest.index import PdfSource
from backend.preprocessing.ingest.unzip import extract_zip_member
from backend.preprocessing.utils.ids import PdfMeta


def _collection_name(collections: dict, collection_id: str) -> str:
    info = collections.get(collection_id) or {}
    return info.get("name") or collection_id


def _resolve_pdf_path(source: PdfSource, cache_dir: Path) -> Path:
    if source.pdf_path and source.pdf_path.exists():
        return source.pdf_path
    if source.zip_path and source.zip_member:
        return extract_zip_member(
            source.zip_path,
            source.zip_member,
            cache_dir / source.collection_id,
            decoded_name=source.meta.source_pdf,
        )
    raise FileNotFoundError(f"无法定位 PDF: {source.meta.source_pdf}")


def source_to_payload(source: PdfSource) -> dict[str, Any]:
    return {
        "pdf_path": str(source.pdf_path) if source.pdf_path else None,
        "zip_path": str(source.zip_path) if source.zip_path else None,
        "zip_member": source.zip_member,
        "collection_id": source.collection_id,
        "meta": {
            "script_id": source.meta.script_id,
            "title": source.meta.title,
            "source_pdf": source.meta.source_pdf,
        },
    }


def source_from_payload(payload: dict[str, Any]) -> PdfSource:
    meta = payload["meta"]
    return PdfSource(
        pdf_path=Path(payload["pdf_path"]) if payload.get("pdf_path") else None,
        zip_path=Path(payload["zip_path"]) if payload.get("zip_path") else None,
        zip_member=payload.get("zip_member"),
        collection_id=payload["collection_id"],
        meta=PdfMeta(
            script_id=meta["script_id"],
            title=meta["title"],
            source_pdf=meta["source_pdf"],
        ),
    )


def preprocess_source_task(task: dict[str, Any]) -> dict[str, Any]:
    """处理单个 PDF 源，写入 play JSON。返回汇总信息供主进程合并 catalog。"""
    source = source_from_payload(task["source"])
    sid = source.meta.script_id
    title = source.meta.title
    cfg = task["cfg"]
    collections = task["collections"]
    cache_dir = Path(cfg["pdf_cache"])
    output_cleaned = Path(cfg["output_cleaned"])
    validate = bool(cfg.get("validate", True))

    try:
        pdf_path = _resolve_pdf_path(source, cache_dir)
        extracted = extract_pdf_pages(pdf_path)
        play = process_extract_result_to_play(
            extracted,
            script_id=sid,
            title=title,
            collection_id=source.collection_id,
            collection_name=_collection_name(collections, source.collection_id),
            source_pdf=source.meta.source_pdf,
            parse_version=cfg["parse_version"],
        )
        writer = PlayWriter(output_cleaned, validate=validate)
        writer.write_play(play)
        failed = writer.failed[-1] if writer.failed else None
        entry = writer.entries[-1] if writer.entries else build_catalog_entry(play)
        blocks = len(play.get("blocks") or [])
        quality = play.get("metadata", {}).get("parse_quality", 0)
        return {
            "ok": failed is None,
            "script_id": sid,
            "title": title,
            "catalog_entry": entry,
            "failed": failed,
            "log": f"  OK {sid} {title} (blocks={blocks}, quality={quality})",
        }
    except Exception as exc:
        failed = {
            "script_id": sid,
            "source_pdf": source.meta.source_pdf,
            "reason": str(exc),
        }
        return {
            "ok": False,
            "script_id": sid,
            "title": title,
            "catalog_entry": None,
            "failed": failed,
            "log": f"  FAIL {sid}: {exc}",
        }
