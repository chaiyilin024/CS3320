from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class AnalyticsConfig:
    root: Path
    cleaned_dir: Path
    analytics_dir: Path
    catalog_path: Path
    num_topics: int = 8
    random_seed: int = 42
    rhythm_window: int = 20

    @classmethod
    def load(cls, root: Path | None = None) -> AnalyticsConfig:
        root = (root or ROOT).resolve()
        pipeline_path = root / "configs" / "pipeline.yaml"
        num_topics, rhythm_window = 8, 20
        cleaned = root / "artifacts" / "cleaned"
        if pipeline_path.exists():
            with pipeline_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            paths = cfg.get("paths") or {}
            if paths.get("output_cleaned"):
                cleaned = root / paths["output_cleaned"]
            analytics = cfg.get("analytics") or {}
            num_topics = int(analytics.get("num_topics", num_topics))
            rhythm_window = int(analytics.get("rhythm_window", rhythm_window))
        return cls(
            root=root,
            cleaned_dir=cleaned,
            analytics_dir=root / "artifacts" / "analytics",
            catalog_path=cleaned / "catalog.json",
            num_topics=num_topics,
            rhythm_window=rhythm_window,
        )
