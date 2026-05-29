from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .utils.paths import get_project_root, resolve_path


@dataclass
class PipelineConfig:
    parse_version: str = "1.0"
    schema_version: str = "1.0"
    data_root: Path = field(default_factory=Path)
    pdf_cache: Path = field(default_factory=Path)
    output_cleaned: Path = field(default_factory=Path)
    collections_config: Path = field(default_factory=Path)
    script_ids: list[str] = field(default_factory=list)
    limit_per_zip: int = 0
    zip_files: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, config_path: Path | None = None) -> PipelineConfig:
        root = get_project_root()
        path = config_path or (root / "configs" / "pipeline.yaml")
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        paths = raw.get("paths") or {}
        return cls(
            parse_version=str(raw.get("parse_version", "1.0")),
            schema_version=str(raw.get("schema_version", "1.0")),
            data_root=resolve_path(paths.get("data_root", "data/京剧剧本"), root),
            pdf_cache=resolve_path(paths.get("pdf_cache", "artifacts/cache/pdf"), root),
            output_cleaned=resolve_path(
                paths.get("output_cleaned", "artifacts/cleaned"), root
            ),
            collections_config=resolve_path(
                paths.get("collections_config", "configs/collections.yaml"), root
            ),
            script_ids=list(raw.get("script_ids") or []),
            limit_per_zip=int(raw.get("limit_per_zip") or 0),
            zip_files=list(raw.get("zip_files") or []),
        )


def load_collections(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
