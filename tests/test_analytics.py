"""Analytics pipeline unit tests (depends on cleaned golden samples)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analytics.narrative.rhythm import analyze_play_narrative
from backend.analytics.network.build_graph import analyze_play_network
from backend.analytics.role.infer import analyze_play_role
from backend.analytics.theme.export import build_play_themes
from backend.analytics.theme.model import train_theme_model
from backend.analytics.utils.io import load_play
from backend.analytics.utils.schema import validate_analytics


def test_analyze_huanghelou():
    play_path = ROOT / "artifacts" / "cleaned" / "plays" / "01001012.json"
    if not play_path.exists():
        return
    play = load_play(play_path)
    model = train_theme_model([play], num_topics=6, random_seed=42)
    role = analyze_play_role(play)
    network = analyze_play_network(play, role)
    themes = build_play_themes(play, model)
    narrative = analyze_play_narrative(play, theme_model=model)

    assert role["script_id"] == "01001012"
    assert role["hangdang_distribution"]
    assert network["metrics"]["node_count"] >= 2
    assert len(themes["topics"]) >= 2
    assert abs(sum(themes["topic_composition"]) - 1.0) < 0.05
    assert narrative["plot_stages"]
    assert narrative.get("performance_mark_distribution") is not None

    for doc, schema in (
        (role, "play_role.schema.json"),
        (network, "network.schema.json"),
        (themes, "theme.schema.json"),
        (narrative, "narrative.schema.json"),
    ):
        errs = validate_analytics(doc, schema, ROOT)
        assert not errs, errs[:3]


def test_merge_topics_with_same_label():
    """Multiple NMF subtopics with the same label should merge into one entry."""
    from backend.analytics.theme.export import _merge_topics_by_label

    merged, mapping = _merge_topics_by_label(
        [
            {
                "topic_id": 0,
                "label": "家训教子",
                "weight": 0.4,
                "keywords": ["老奴", "教道"],
                "keyword_weights": [1.0, 0.5],
            },
            {
                "topic_id": 1,
                "label": "家训教子",
                "weight": 0.5,
                "keywords": ["机房", "老奴"],
                "keyword_weights": [0.9, 0.3],
            },
            {
                "topic_id": 2,
                "label": "冲突怒斥",
                "weight": 0.1,
                "keywords": ["怒斥"],
                "keyword_weights": [1.2],
            },
        ]
    )
    assert len(merged) == 2
    labels = {t["label"] for t in merged}
    assert labels == {"家训教子", "冲突怒斥"}
    jiaxun = next(t for t in merged if t["label"] == "家训教子")
    assert jiaxun["topic_id"] == 0
    assert abs(jiaxun["weight"] - 0.9) < 1e-4
    assert "老奴" in jiaxun["keywords"]
    assert "机房" in jiaxun["keywords"]
    assert mapping[0] == mapping[1] == 0
    assert mapping[2] == 1


def test_theme_keywords_not_empty():
    play_path = ROOT / "artifacts" / "cleaned" / "plays" / "01001012.json"
    if not play_path.exists():
        return
    play = load_play(play_path)
    model = train_theme_model([play], num_topics=5)
    themes = build_play_themes(play, model)
    for t in themes["topics"]:
        assert t["keywords"]
        assert t["label"]


def test_aggregate_theme_patterns_by_label():
    """Cross-play heatmap columns should align by semantic label, not T0/T1 slots."""
    from backend.analytics.integrated.aggregate import aggregate_theme_patterns
    from backend.analytics.theme.model import global_topic_label_entries

    play_a = {
        "script_id": "a",
        "title": "甲",
        "topics": [
            {"topic_id": 0, "label": "朝堂奏对", "weight": 0.6, "keywords": ["领旨"]},
            {"topic_id": 1, "label": "战争征伐", "weight": 0.4, "keywords": ["厮杀"]},
        ],
    }
    play_b = {
        "script_id": "b",
        "title": "乙",
        "topics": [
            {"topic_id": 0, "label": "朝堂奏对", "weight": 0.3, "keywords": ["见驾"]},
            {"topic_id": 1, "label": "行军调度", "weight": 0.7, "keywords": ["众将官"]},
        ],
    }

    class _FakeModel:
        num_topics = 3
        pinned_labels = {}

        def topic_label(self, tid: int) -> str:
            return ["朝堂奏对", "战争征伐", "行军调度"][tid]

        topic_words = {
            0: [("领旨", 1.0), ("见驾", 0.9)],
            1: [("厮杀", 1.0)],
            2: [("众将官", 1.0)],
        }

        _label_cache = {"朝堂奏对": 0, "战争征伐": 1, "行军调度": 2}

    fake = _FakeModel()
    fake._label_cache = {0: "朝堂奏对", 1: "战争征伐", 2: "行军调度"}

    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for doc in (play_a, play_b):
            d = root / doc["script_id"]
            d.mkdir()
            (d / "themes.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        out = aggregate_theme_patterns(root, {}, theme_model=fake)
    labels = [x["label"] for x in out["topic_labels"]]
    assert labels == [e["label"] for e in global_topic_label_entries(fake)]
    assert "朝堂奏对" in labels
    row_a = next(r for r in out["play_topic_matrix"] if r["script_id"] == "a")
    idx_chao = labels.index("朝堂奏对")
    idx_war = labels.index("战争征伐")
    assert row_a["weights"][idx_chao] == 0.6
    assert row_a["weights"][idx_war] == 0.4


def test_theme_model_save_load():
    play_path = ROOT / "artifacts" / "cleaned" / "plays" / "01001012.json"
    if not play_path.exists():
        return
    from backend.analytics.theme.model import load_theme_model, save_theme_model

    play = load_play(play_path)
    model = train_theme_model([play], num_topics=4, random_seed=42)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "theme_model.pkl"
        save_theme_model(model, path)
        loaded = load_theme_model(path)
    assert loaded.num_topics == model.num_topics
    assert loaded.topic_label(0) == model.topic_label(0)
