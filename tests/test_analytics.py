"""分析流水线单元测试（依赖 cleaned 金样例）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analytics.config import AnalyticsConfig
from backend.analytics.integrated.correlate import analyze_integrated
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
    integrated = analyze_integrated(play, role, network, themes, narrative)

    assert role["script_id"] == "01001012"
    assert role["hangdang_distribution"]
    assert network["metrics"]["node_count"] >= 2
    assert len(themes["topics"]) >= 3
    assert abs(sum(themes["topic_composition"]) - 1.0) < 0.05
    assert narrative["plot_stages"]
    assert integrated["summary_insights"]

    errs = validate_analytics(themes, "theme.schema.json", ROOT)
    assert not errs, errs[:3]


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
