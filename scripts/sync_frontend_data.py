#!/usr/bin/env python3
"""将 cleaned + analytics 产物复制到 frontend/public/data（Windows / macOS / Linux）。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "frontend" / "public" / "data"


def main() -> int:
    (DEST / "analytics" / "global").mkdir(parents=True, exist_ok=True)
    (DEST / "analytics" / "plays").mkdir(parents=True, exist_ok=True)
    (DEST / "plays").mkdir(parents=True, exist_ok=True)

    cleaned_plays = ROOT / "artifacts" / "cleaned" / "plays"
    if cleaned_plays.is_dir():
        for f in cleaned_plays.glob("*.json"):
            shutil.copy2(f, DEST / "plays" / f.name)
        print("OK plays (cleaned 正文)")

    catalog = ROOT / "artifacts" / "cleaned" / "catalog.json"
    if catalog.is_file():
        shutil.copy2(catalog, DEST / "catalog.json")
        print("OK catalog.json")
    else:
        print("WARN: artifacts/cleaned/catalog.json 不存在，请先运行预处理", file=sys.stderr)

    global_dir = ROOT / "artifacts" / "analytics" / "global"
    if global_dir.is_dir():
        dest_global = DEST / "analytics" / "global"
        for f in global_dir.iterdir():
            if f.is_file():
                shutil.copy2(f, dest_global / f.name)
        print("OK analytics/global")

    plays_dir = ROOT / "artifacts" / "analytics" / "plays"
    if plays_dir.is_dir():
        for d in sorted(plays_dir.iterdir()):
            if not d.is_dir():
                continue
            dest_play = DEST / "analytics" / "plays" / d.name
            dest_play.mkdir(parents=True, exist_ok=True)
            for f in d.glob("*.json"):
                shutil.copy2(f, dest_play / f.name)
        print("OK analytics/plays")

    print(f"数据已同步到 {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
