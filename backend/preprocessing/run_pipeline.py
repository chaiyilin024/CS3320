#!/usr/bin/env python3
"""Preprocessing pipeline entry point.

Examples:
  python backend/preprocessing/run_pipeline.py --pdf example/01001012_黄鹤楼.pdf
  python backend/preprocessing/run_pipeline.py --zip data/京剧剧本/01000000.zip --limit 5
  python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml
  python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml --workers 4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow direct run: python backend/preprocessing/run_pipeline.py
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.preprocessing.config import PipelineConfig, load_collections
from backend.preprocessing.export.write_json import PlayWriter, build_catalog_entry
from backend.preprocessing.ingest.index import PdfSource, list_pdfs_in_zip, list_single_pdf
from backend.preprocessing.workers import preprocess_source_task, source_to_payload
from backend.utils.parallel import resolve_workers, run_parallel


def _cfg_payload(cfg: PipelineConfig, *, validate: bool) -> dict:
    return {
        "parse_version": cfg.parse_version,
        "output_cleaned": str(cfg.output_cleaned),
        "pdf_cache": str(cfg.pdf_cache),
        "validate": validate,
    }


def _run_sources(
    sources: list[PdfSource],
    *,
    cfg: PipelineConfig,
    collections: dict,
    writer: PlayWriter,
    validate: bool,
    workers: int,
) -> int:
    if not sources:
        return 0
    w = resolve_workers(workers)
    print(f"Workers: {w}, processing {len(sources)} plays → {cfg.output_cleaned}")
    payload = _cfg_payload(cfg, validate=validate)
    tasks = [
        {"source": source_to_payload(s), "cfg": payload, "collections": collections}
        for s in sources
    ]

    def _progress(done: int, total: int, _result: dict) -> None:
        if done % 100 == 0 or done == total:
            print(f"  … done {done}/{total}")

    results = run_parallel(preprocess_source_task, tasks, workers, progress=_progress)
    ok = 0
    for r in results:
        print(r.get("log", ""))
        if r.get("catalog_entry"):
            writer.entries.append(r["catalog_entry"])
        if r.get("failed"):
            writer.failed.append(r["failed"])
        if r.get("ok"):
            ok += 1
    return ok


def run_from_config(cfg: PipelineConfig, *, catalog_only: bool = False, workers: int | None = None) -> None:
    collections = load_collections(cfg.collections_config)
    writer = PlayWriter(cfg.output_cleaned, validate=True)
    w = workers if workers is not None else cfg.workers

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
        print(f"Catalog updated: {cfg.output_cleaned / 'catalog.json'}")
        return

    sources: list[PdfSource] = []

    if cfg.zip_files:
        zip_names = cfg.zip_files
    else:
        zip_names = sorted(p.name for p in cfg.data_root.glob("*.zip"))

    for zname in zip_names:
        zip_path = cfg.data_root / zname
        if not zip_path.exists():
            print(f"Skipping missing zip: {zip_path}")
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

    ok = _run_sources(
        sources,
        cfg=cfg,
        collections=collections,
        writer=writer,
        validate=True,
        workers=w,
    )

    writer.write_catalog(
        schema_version=cfg.schema_version,
        parse_version=cfg.parse_version,
        pipeline_meta={
            "source_root": str(cfg.data_root),
            "play_count_total": len(sources),
        },
    )
    print(f"Done: {ok}/{len(sources)} succeeded, catalog → {cfg.output_cleaned / 'catalog.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Peking opera script preprocessing pipeline")
    parser.add_argument("--config", type=Path, default=None, help="path to pipeline.yaml")
    parser.add_argument("--pdf", type=Path, default=None, help="single PDF file")
    parser.add_argument("--zip", type=Path, default=None, help="path to zip collection")
    parser.add_argument("--collection-id", type=str, default="01000000")
    parser.add_argument("--limit", type=int, default=0, help="limit number of plays to process")
    parser.add_argument("--catalog-only", action="store_true", help="rebuild catalog from existing plays only")
    parser.add_argument("--no-validate", action="store_true", help="skip jsonschema validation")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="parallel worker count (0=auto min(CPU,8), 1=serial)",
    )
    args = parser.parse_args()

    cfg = PipelineConfig.load(args.config)
    if args.limit:
        cfg.limit_per_zip = args.limit

    collections = load_collections(cfg.collections_config)
    writer = PlayWriter(cfg.output_cleaned, validate=not args.no_validate)
    cfg.pdf_cache.mkdir(parents=True, exist_ok=True)
    workers = args.workers if args.workers is not None else cfg.workers

    if args.catalog_only:
        run_from_config(cfg, catalog_only=True, workers=workers)
        return

    if args.pdf:
        pdf_path = args.pdf if args.pdf.is_absolute() else _ROOT / args.pdf
        source = list_single_pdf(pdf_path.resolve(), args.collection_id)
        _run_sources(
            [source],
            cfg=cfg,
            collections=collections,
            writer=writer,
            validate=not args.no_validate,
            workers=workers,
        )
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
        _run_sources(
            sources,
            cfg=cfg,
            collections=collections,
            writer=writer,
            validate=not args.no_validate,
            workers=workers,
        )
        writer.write_catalog(
            schema_version=cfg.schema_version,
            parse_version=cfg.parse_version,
            pipeline_meta={"source_root": str(zip_path)},
        )
        return

    run_from_config(cfg, workers=workers)


if __name__ == "__main__":
    main()
