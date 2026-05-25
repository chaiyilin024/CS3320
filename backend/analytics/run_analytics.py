#!/usr/bin/env python3
"""分析流水线入口 — 单剧四任务（行当 / 网络 / 主题 / 叙事）。

多剧本对比交由前端在拿到各剧 JSON 后做。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.analytics.config import AnalyticsConfig
from backend.analytics.narrative.rhythm import analyze_play_narrative
from backend.analytics.network.build_graph import analyze_play_network
from backend.analytics.role.infer import analyze_play_role
from backend.analytics.theme.export import build_play_themes
from backend.analytics.theme.llm import build_play_themes_llm
from backend.analytics.theme.model import model_from_themes, train_theme_model
from backend.analytics.utils.io import iter_play_paths, load_play, save_json
from backend.analytics.utils.jieba_env import configure_jieba
from backend.analytics.utils.schema import validate_analytics

SCHEMA_MAP = {
    "role.json": "play_role.schema.json",
    "network.json": "network.schema.json",
    "themes.json": "theme.schema.json",
    "narrative.json": "narrative.schema.json",
}


def _build_themes(play: dict, cfg: AnalyticsConfig, theme_model):
    """返回 (themes.json 内容, 供叙事使用的 theme_model)。"""
    if cfg.llm_theme.enabled:
        try:
            themes = build_play_themes_llm(play, cfg.llm_theme)
            print(f"  主题: LLM ({cfg.llm_theme.model})", file=sys.stderr)
            return themes, model_from_themes(themes)
        except Exception as e:
            print(f"  WARN LLM 主题失败，回退 NMF/keyword: {e}", file=sys.stderr)
    themes = build_play_themes(play, theme_model)
    return themes, theme_model


def run_play_analytics(
    play: dict,
    cfg: AnalyticsConfig,
    theme_model,
    validate: bool,
) -> dict:
    role = analyze_play_role(play)
    network = analyze_play_network(play, role)
    themes, theme_model_play = _build_themes(play, cfg, theme_model)
    narrative = analyze_play_narrative(
        play, window=cfg.rhythm_window, theme_model=theme_model_play
    )

    sid = play["script_id"]
    out_dir = cfg.analytics_dir / "plays" / sid
    outputs = {
        "role.json": role,
        "network.json": network,
        "themes.json": themes,
        "narrative.json": narrative,
    }
    for name, doc in outputs.items():
        save_json(out_dir / name, doc)
        if validate:
            errs = validate_analytics(doc, SCHEMA_MAP[name], cfg.root)
            if errs:
                print(f"  WARN {sid}/{name}: {errs[0]}", file=sys.stderr)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="京剧剧本单剧分析流水线")
    parser.add_argument("--script-id", action="append", dest="script_ids")
    parser.add_argument("--all", action="store_true", help="处理 cleaned/plays 下全部剧本")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--num-topics", type=int, default=None)
    parser.add_argument(
        "--theme-llm",
        action="store_true",
        help="使用大模型 API 生成主题（需 OPENAI_API_KEY）",
    )
    args = parser.parse_args()

    cfg = AnalyticsConfig.load(ROOT)
    if args.num_topics:
        cfg.num_topics = args.num_topics
    if args.theme_llm and cfg.llm_theme.api_key:
        cfg.llm_theme.enabled = True
        cfg.num_topics = cfg.llm_theme.num_topics
    elif args.theme_llm:
        print("WARN: --theme-llm 已指定但未设置 OPENAI_API_KEY", file=sys.stderr)
    validate = not args.no_validate

    try:
        cache = configure_jieba(cfg.root)
        print(f"jieba 缓存: {cache}")
    except ImportError:
        pass

    if args.all:
        script_ids = [sid for sid, _ in iter_play_paths(cfg.cleaned_dir)]
    elif args.script_ids:
        script_ids = args.script_ids
    else:
        script_ids = ["01001012"]

    if not script_ids:
        print("未找到可分析的剧本，请先运行预处理。", file=sys.stderr)
        return 1

    plays: list[dict] = []
    for sid in script_ids:
        path = cfg.cleaned_dir / "plays" / f"{sid}.json"
        if not path.exists():
            print(f"跳过 {sid}：{path} 不存在", file=sys.stderr)
            continue
        plays.append(load_play(path))

    if not plays:
        return 1

    theme_model = None
    if cfg.llm_theme.enabled:
        print(f"主题分析: LLM 模式（{cfg.llm_theme.model}，K={cfg.llm_theme.num_topics}）")
    else:
        print(f"训练主题模型（K={cfg.num_topics}，文档块数基于 {len(plays)} 剧）…")
        theme_model = train_theme_model(plays, cfg.num_topics, cfg.random_seed)

    for play in plays:
        sid = play["script_id"]
        print(f"分析 {sid} 《{play.get('title', '')}》…")
        run_play_analytics(play, cfg, theme_model, validate)

    print(f"完成：{len(plays)} 剧 → {cfg.analytics_dir}/plays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
