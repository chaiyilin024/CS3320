from __future__ import annotations

import json
import math
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
        json.dump(_json_safe(data), f, ensure_ascii=False, indent=indent, allow_nan=False)
        f.write("\n")


def _json_safe(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
