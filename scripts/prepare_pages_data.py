#!/usr/bin/env python3
"""从本地 frontend/public/data 抽取子集，供 GitHub Pages 演示部署（避免 400MB+ 全量进 Git）。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "public" / "data"
DEST = ROOT / "deploy" / "pages-data"


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 GitHub Pages 演示用数据子集")
    parser.add_argument(
        "--script-ids",
        nargs="*",
        help="保留的剧本 ID；留空则取 catalog 前 N 部",
    )
    parser.add_argument("--max-plays", type=int, default=24, help="未指定 ID 时最多保留部数")
    parser.add_argument("--src", type=Path, default=SRC, help="源数据目录")
    parser.add_argument("--dest", type=Path, default=DEST, help="输出目录")
    args = parser.parse_args()

    src = args.src
    catalog_path = src / "catalog.json"
    if not catalog_path.is_file():
        print(f"缺少 {catalog_path}，请先运行 python scripts/sync_frontend_data.py", file=sys.stderr)
        return 1

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    all_plays = catalog.get("plays") or []
    if args.script_ids:
        keep_ids = set(args.script_ids)
    else:
        keep_ids = {p["script_id"] for p in all_plays[: args.max_plays]}

    dest = args.dest
    (dest / "plays").mkdir(parents=True, exist_ok=True)
    (dest / "analytics" / "global").mkdir(parents=True, exist_ok=True)
    (dest / "analytics" / "plays").mkdir(parents=True, exist_ok=True)

    # catalog 子集
    subset_plays = [p for p in all_plays if p["script_id"] in keep_ids]
    subset_catalog = {**catalog, "plays": subset_plays}
    (dest / "catalog.json").write_text(
        json.dumps(subset_catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 单剧正文 + 分析
    for sid in sorted(keep_ids):
        play_src = src / "plays" / f"{sid}.json"
        if play_src.is_file():
            shutil.copy2(play_src, dest / "plays" / play_src.name)
        analytics_src = src / "analytics" / "plays" / sid
        if analytics_src.is_dir():
            _copy_tree(analytics_src, dest / "analytics" / "plays" / sid)

    # 全库 global（体积较小，热力图等需要）
    global_src = src / "analytics" / "global"
    if global_src.is_dir():
        for f in global_src.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / "analytics" / "global" / f.name)

    print(f"已生成演示数据：{len(subset_plays)} 部 → {dest}")
    print("提交 deploy/pages-data 后 push，GitHub Actions 会自动带上数据部署。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
