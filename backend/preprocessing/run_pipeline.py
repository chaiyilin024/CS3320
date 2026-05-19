#!/usr/bin/env python3
"""预处理流水线入口。

示例:
  python backend/preprocessing/run_pipeline.py --pdf example/01001012_黄鹤楼.pdf
  python backend/preprocessing/run_pipeline.py --zip data/京剧剧本/01000000.zip --limit 5
  python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许直接运行: python backend/preprocessing/run_pipeline.py
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.preprocessing.config import PipelineConfig, load_collections
from backend.preprocessing.clean.pipeline import (
    process_extract_result_to_play,
    process_text_to_play,
)
from backend.preprocessing.export.write_json import PlayWriter, build_catalog_entry
from backend.preprocessing.extract.pdf_text import extract_pdf_pages
from backend.preprocessing.ingest.index import PdfSource, list_pdfs_in_zip, list_single_pdf
from backend.preprocessing.ingest.unzip import extract_zip_member
from backend.preprocessing.utils.paths import get_project_root


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


def process_source(
    source: PdfSource,
    *,
    cfg: PipelineConfig,
    collections: dict,
    writer: PlayWriter,
    cache_dir: Path,
) -> bool:
    try:
        pdf_path = _resolve_pdf_path(source, cache_dir)
        extracted = extract_pdf_pages(pdf_path)
        play = process_extract_result_to_play(
            extracted,
            script_id=source.meta.script_id,
            title=source.meta.title,
            collection_id=source.collection_id,
            collection_name=_collection_name(collections, source.collection_id),
            source_pdf=source.meta.source_pdf,
            parse_version=cfg.parse_version,
        )
        writer.write_play(play)
        print(f"  OK {source.meta.script_id} {source.meta.title} "
              f"(blocks={len(play['blocks'])}, quality={play['metadata']['parse_quality']})")
        return True
    except Exception as exc:
        writer.failed.append(
            {
                "script_id": source.meta.script_id,
                "source_pdf": source.meta.source_pdf,
                "reason": str(exc),
            }
        )
        print(f"  FAIL {source.meta.script_id}: {exc}")
        return False


def run_from_config(cfg: PipelineConfig, *, catalog_only: bool = False) -> None:
    root = get_project_root()
    collections = load_collections(cfg.collections_config)
    writer = PlayWriter(cfg.output_cleaned, validate=True)

    if catalog_only:
        for path in sorted((cfg.output_cleaned / "plays").glob("*.json")):
            import json

            with path.open(encoding="utf-8") as f:
                play = json.load(f)
            writer.entries.append(build_catalog_entry(play))
        writer.write_catalog(
            schema_version=cfg.schema_version,
            parse_version=cfg.parse_version,
        )
        print(f"catalog 已更新: {cfg.output_cleaned / 'catalog.json'}")
        return

    sources: list[PdfSource] = []

    if cfg.zip_files:
        zip_names = cfg.zip_files
    else:
        zip_names = sorted(p.name for p in cfg.data_root.glob("*.zip"))

    for zname in zip_names:
        zip_path = cfg.data_root / zname
        if not zip_path.exists():
            print(f"跳过不存在的 zip: {zip_path}")
            continue
        cid = zip_path.stem
        sources.extend(list_pdfs_in_zip(zip_path, cid))

    if cfg.script_ids:
        allow = set(cfg.script_ids)
        sources = [s for s in sources if s.meta.script_id in allow]

    if cfg.limit_per_zip > 0:
        by_zip: dict[str, list[PdfSource]] = {}
        for s in sources:
            by_zip.setdefault(s.collection_id, []).append(s)
        trimmed: list[PdfSource] = []
        for cid in sorted(by_zip):
            trimmed.extend(by_zip[cid][: cfg.limit_per_zip])
        sources = trimmed

    print(f"待处理 {len(sources)} 个剧本 → {cfg.output_cleaned}")
    ok = 0
    for source in sources:
        if process_source(source, cfg=cfg, collections=collections, writer=writer, cache_dir=cfg.pdf_cache):
            ok += 1

    writer.write_catalog(
        schema_version=cfg.schema_version,
        parse_version=cfg.parse_version,
        pipeline_meta={
            "source_root": str(cfg.data_root),
            "play_count_total": len(sources),
        },
    )
    print(f"完成: 成功 {ok}/{len(sources)}, catalog → {cfg.output_cleaned / 'catalog.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="京剧剧本预处理流水线")
    parser.add_argument("--config", type=Path, default=None, help="pipeline.yaml 路径")
    parser.add_argument("--pdf", type=Path, default=None, help="单份 PDF")
    parser.add_argument("--zip", type=Path, default=None, help="zip 集合路径")
    parser.add_argument("--collection-id", type=str, default="01000000")
    parser.add_argument("--limit", type=int, default=0, help="限制处理数量")
    parser.add_argument("--catalog-only", action="store_true", help="仅从已有 plays 重建 catalog")
    parser.add_argument("--no-validate", action="store_true", help="跳过 jsonschema 校验")
    args = parser.parse_args()

    cfg = PipelineConfig.load(args.config)
    if args.limit:
        cfg.limit_per_zip = args.limit

    collections = load_collections(cfg.collections_config)
    writer = PlayWriter(cfg.output_cleaned, validate=not args.no_validate)
    cfg.pdf_cache.mkdir(parents=True, exist_ok=True)

    if args.catalog_only:
        run_from_config(cfg, catalog_only=True)
        return

    if args.pdf:
        pdf_path = args.pdf if args.pdf.is_absolute() else _ROOT / args.pdf
        source = list_single_pdf(pdf_path.resolve(), args.collection_id)
        process_source(source, cfg=cfg, collections=collections, writer=writer, cache_dir=cfg.pdf_cache)
        writer.write_catalog(
            schema_version=cfg.schema_version,
            parse_version=cfg.parse_version,
            pipeline_meta={"source_root": str(pdf_path.parent)},
        )
        return

    if args.zip:
        zip_path = args.zip if args.zip.is_absolute() else _ROOT / args.zip
        cid = zip_path.stem
        sources = list_pdfs_in_zip(zip_path.resolve(), cid)
        if cfg.limit_per_zip or args.limit:
            limit = args.limit or cfg.limit_per_zip
            sources = sources[:limit]
        for source in sources:
            process_source(source, cfg=cfg, collections=collections, writer=writer, cache_dir=cfg.pdf_cache)
        writer.write_catalog(
            schema_version=cfg.schema_version,
            parse_version=cfg.parse_version,
            pipeline_meta={"source_root": str(zip_path)},
        )
        return

    run_from_config(cfg)


if __name__ == "__main__":
    main()
