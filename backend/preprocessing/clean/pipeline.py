from __future__ import annotations

from datetime import datetime, timezone

from ..extract.pdf_text import ExtractResult
from ..utils.quality import compute_parse_quality
from .characters import attach_speakers_to_blocks, build_characters
from .edges import build_cooccurrence_edges
from .normalize import normalize_full_text
from .scenes import build_scenes
from .segment import segment_lines
from .tags import infer_tags


def process_text_to_play(
    *,
    full_text: str,
    script_id: str,
    title: str,
    collection_id: str,
    collection_name: str,
    source_pdf: str,
    parse_version: str = "1.0",
    page_count: int = 0,
    ocr_used: bool = False,
    warnings: list[str] | None = None,
    page_line_boundaries: list[int] | None = None,
) -> dict:
    warnings = list(warnings or [])
    lines = normalize_full_text(full_text)
    if not lines:
        warnings.append("no_lines_after_normalize")
        lines = ["[empty document]"]

    segment = segment_lines(lines, page_line_boundaries)
    characters = build_characters(segment, [])
    blocks = attach_speakers_to_blocks(segment, characters)
    scenes = build_scenes(blocks, segment.blocks)
    edges = build_cooccurrence_edges(blocks, scenes)

    char_count = sum(len(b["text"]) for b in blocks)
    if page_count == 0 and page_line_boundaries:
        page_count = len(page_line_boundaries)
    elif page_count == 0:
        page_count = max(1, char_count // 800)

    quality = compute_parse_quality(blocks, char_count, page_count, warnings)
    tags = infer_tags(title, full_text)

    for c in characters:
        if c.get("traits") is None:
            c.pop("traits", None)

    play = {
        "script_id": script_id,
        "title": title,
        "collection_id": collection_id,
        "collection_name": collection_name,
        "metadata": {
            "source_pdf": source_pdf,
            "parse_version": parse_version,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "page_count": page_count,
            "char_count": char_count,
            "parse_quality": quality,
            "ocr_used": ocr_used,
            "warnings": warnings,
        },
        "characters": characters,
        "scenes": scenes,
        "blocks": blocks,
        "cooccurrence_edges_raw": edges,
    }
    if tags:
        play["tags"] = tags
    return play


def process_extract_result_to_play(
    extracted: ExtractResult,
    *,
    script_id: str,
    title: str,
    collection_id: str,
    collection_name: str,
    source_pdf: str,
    parse_version: str = "1.0",
) -> dict:
    boundaries: list[int] = []
    line_offset = 0
    for page_text in extracted.pages:
        boundaries.append(line_offset)
        line_offset += len([ln for ln in page_text.split("\n") if ln.strip()])

    return process_text_to_play(
        full_text=extracted.full_text,
        script_id=script_id,
        title=title,
        collection_id=collection_id,
        collection_name=collection_name,
        source_pdf=source_pdf,
        parse_version=parse_version,
        page_count=extracted.page_count,
        ocr_used=extracted.ocr_used,
        warnings=extracted.warnings,
        page_line_boundaries=boundaries if boundaries else None,
    )
