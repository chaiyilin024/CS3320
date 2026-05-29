from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def load_play(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_catalog(path: Path) -> dict:
    if not path.exists():
        return {"plays": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_play_paths(cleaned_dir: Path) -> Iterator[tuple[str, Path]]:
    plays_dir = cleaned_dir / "plays"
    if not plays_dir.exists():
        return
    for path in sorted(plays_dir.glob("*.json")):
        yield path.stem, path


def save_json(path: Path, data: dict, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
