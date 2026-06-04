"""主题质量评估单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analytics.theme.quality import (
    assess_play_themes,
    assess_topic,
    attach_quality,
)


def test_assess_fallback_topic():
    topic = {
        "topic_id": 0,
        "label": "其他情节",
        "weight": 0.4,
        "keywords": ["路径", "西门", "回营", "众将官", "得令"],
    }
    a = assess_topic(topic)
    assert a["tier"] in ("fallback", "noise")
    assert a["keyword_signal"] <= 1.0


def test_assess_labeled_topic():
    topic = {
        "topic_id": 1,
        "label": "守城攻防",
        "weight": 0.6,
        "keywords": ["守城", "攻城", "兵马", "西门", "敌兵", "复夺"],
    }
    a = assess_topic(topic)
    assert a["tier"] in ("strong", "weak")
    assert a["label_score"] > 0


def test_attach_quality_play_doc():
    doc = {
        "script_id": "01001001",
        "topics": [
            {
                "topic_id": 0,
                "label": "守城攻防",
                "weight": 0.8,
                "keywords": ["守城", "西城", "司马", "街亭"],
            },
            {
                "topic_id": 1,
                "label": "其他情节",
                "weight": 0.2,
                "keywords": ["正是", "只见", "怎么"],
            },
        ],
        "topic_composition": [0.8, 0.2],
    }
    attach_quality(doc)
    q = doc["quality"]
    assert 0 <= q["score"] <= 1
    assert q["fallback_weight"] == 0.2
    assert len(q["topic_assessments"]) == 2


def test_assess_real_themes_file():
    path = ROOT / "artifacts" / "analytics" / "plays" / "01001001" / "themes.json"
    if not path.exists():
        return
    import json

    doc = json.loads(path.read_text(encoding="utf-8"))
    q = assess_play_themes(doc)
    assert q["score"] > 0.5
