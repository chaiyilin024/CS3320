from __future__ import annotations

from pathlib import Path

_MARKERS = ("configs", "schemas", "backend")


def get_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "schemas").is_dir() and (parent / "configs").is_dir():
            return parent
    return here.parents[3]


def resolve_path(path: str | Path, root: Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    base = root or get_project_root()
    return (base / p).resolve()
