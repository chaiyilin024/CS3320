#!/usr/bin/env python3
"""从全库产物裁剪约 10 部示例剧本，生成 demo-data/ 供 GitHub Pages 部署。"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.analytics.integrated.aggregate import (  # noqa: E402
    aggregate_narrative_templates,
    aggregate_network_compare,
    aggregate_role_analysis,
    aggregate_theme_patterns,
    aggregate_theme_quality_report,
)

CONFIG = ROOT / "configs" / "demo_plays.json"
SRC_CLEANED = ROOT / "artifacts" / "cleaned"
SRC_ANALYTICS = ROOT / "artifacts" / "analytics"
DEST = ROOT / "demo-data"

PLAY_FILES = ("role.json", "network.json", "themes.json", "narrative.json")


def load_play_ids() -> list[str]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    ids = cfg.get("play_ids") or []
    if not ids:
        raise SystemExit(f"{CONFIG} 中 play_ids 为空")
    return [str(x) for x in ids]


def main() -> int:
    play_ids = load_play_ids()
    catalog_path = SRC_CLEANED / "catalog.json"
    if not catalog_path.is_file():
        print("ERROR: 请先运行预处理生成 artifacts/cleaned/catalog.json", file=sys.stderr)
        return 1

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    idx = {p["script_id"]: p for p in catalog.get("plays") or []}
    missing = [pid for pid in play_ids if pid not in idx]
    if missing:
        print(f"ERROR: catalog 中缺少剧本: {missing}", file=sys.stderr)
        return 1

    if DEST.exists():
        shutil.rmtree(DEST)
    (DEST / "plays").mkdir(parents=True)
    (DEST / "analytics" / "plays").mkdir(parents=True)
    (DEST / "analytics" / "global").mkdir(parents=True)

    demo_plays = [idx[pid] for pid in play_ids]
    demo_catalog = {
        "version": catalog.get("version", "1.0"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo": True,
        "demo_note": f"在线演示样本，共 {len(demo_plays)} 部（全库 1473 部）",
        "plays": demo_plays,
    }
    (DEST / "catalog.json").write_text(
        json.dumps(demo_catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for pid in play_ids:
        cleaned = SRC_CLEANED / "plays" / f"{pid}.json"
        if not cleaned.is_file():
            print(f"WARN: 缺少正文 {cleaned.name}", file=sys.stderr)
            continue
        shutil.copy2(cleaned, DEST / "plays" / cleaned.name)

        src_play_dir = SRC_ANALYTICS / "plays" / pid
        if not src_play_dir.is_dir():
            print(f"WARN: 缺少分析 {pid}", file=sys.stderr)
            continue
        dest_play_dir = DEST / "analytics" / "plays" / pid
        dest_play_dir.mkdir(parents=True, exist_ok=True)
        for name in PLAY_FILES:
            src = src_play_dir / name
            if src.is_file():
                shutil.copy2(src, dest_play_dir / name)

    catalog_idx = {p["script_id"]: p for p in demo_plays}
    plays_dir = DEST / "analytics" / "plays"
    global_outputs = {
        "role_analysis.json": aggregate_role_analysis(plays_dir, catalog_idx),
        "network_compare.json": aggregate_network_compare(plays_dir, catalog_idx),
        "theme_patterns.json": aggregate_theme_patterns(plays_dir, catalog_idx),
        "theme_quality.json": aggregate_theme_quality_report(plays_dir, catalog_idx),
        "narrative_templates.json": aggregate_narrative_templates(plays_dir, catalog_idx),
    }
    for name, doc in global_outputs.items():
        (DEST / "analytics" / "global" / name).write_text(
            json.dumps(doc, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    total_bytes = sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file())
    print(f"OK demo-data: {len(demo_plays)} 部剧本, {total_bytes / 1024 / 1024:.2f} MB")
    print(f"   → {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
