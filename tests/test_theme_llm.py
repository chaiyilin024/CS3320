"""LLM theme module unit tests (no real API calls)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analytics.theme.llm import (
    LlmThemeConfig,
    normalize_llm_themes,
    sample_play_excerpt,
)
from backend.analytics.utils.io import load_play


def test_sample_play_excerpt():
    path = ROOT / "artifacts" / "cleaned" / "plays" / "01001012.json"
    if not path.exists():
        return
    play = load_play(path)
    cfg = LlmThemeConfig(enabled=False, num_topics=6, max_blocks=50)
    text, ids = sample_play_excerpt(play, cfg)
    assert "剧本ID: 01001012" in text
    assert "[b_" in text
    assert len(ids) > 10


def test_normalize_llm_themes():
    path = ROOT / "artifacts" / "cleaned" / "plays" / "01001012.json"
    if not path.exists():
        return
    play = load_play(path)
    cfg = LlmThemeConfig(num_topics=3)
    _, valid_ids = sample_play_excerpt(play, cfg)
    bid = next(iter(valid_ids))
    raw = {
        "topics": [
            {
                "topic_id": 0,
                "label": "谋略",
                "weight": 0.5,
                "keywords": ["周瑜", "计", "过江"],
                "representative_quotes": [
                    {"block_id": bid, "text_snippet": "测试片段", "score": 0.9}
                ],
            },
            {
                "topic_id": 1,
                "label": "忠义",
                "weight": 0.3,
                "keywords": ["刘备", "皇叔"],
            },
            {
                "topic_id": 2,
                "label": "宴饮",
                "weight": 0.2,
                "keywords": ["酒", "楼"],
            },
        ]
    }
    out = normalize_llm_themes(play, raw, cfg, valid_ids)
    assert out["model"]["method"] == "llm"
    assert len(out["topics"]) == 3
    assert abs(sum(out["topic_composition"]) - 1.0) < 0.02
    assert out["representative_blocks"]
