#!/usr/bin/env python3
"""将 demo-data/ 复制到 frontend/public/data（本地开发与 Pages 构建）。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "demo-data"
DEST = ROOT / "frontend" / "public" / "data"


def main() -> int:
    if not SRC.is_dir():
        print(f"ERROR: {SRC} 不存在，请先运行 python scripts/build_demo_data.py", file=sys.stderr)
        return 1
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST)
    n = sum(1 for _ in DEST.rglob("*") if _.is_file())
    print(f"OK {SRC} → {DEST} ({n} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
