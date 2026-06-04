"""分析流水线单元测试（依赖 cleaned 金样例）。"""
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
    """同一 label 的多个 NMF 子主题应合并为一条。"""
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
