#!/usr/bin/env python3
"""分析流水线入口：单剧 / 批量 / 仅全局聚合。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.analytics.config import AnalyticsConfig
from backend.analytics.utils.jieba_env import configure_jieba
from backend.analytics.integrated.correlate import analyze_integrated
from backend.analytics.narrative.rhythm import analyze_play_narrative
from backend.analytics.narrative.templates import aggregate_narrative_templates
from backend.analytics.network.build_graph import analyze_play_network
from backend.analytics.network.compare import aggregate_network_compare
from backend.analytics.role.aggregate import aggregate_role_analysis
from backend.analytics.role.infer import analyze_play_role
from backend.analytics.theme.export import aggregate_theme_patterns, build_play_themes
from backend.analytics.theme.llm import build_play_themes_llm
from backend.analytics.theme.model import model_from_themes, train_theme_model
from backend.analytics.utils.io import (
    iter_play_paths,
    load_catalog,
    load_play,
    save_json,
)
from backend.analytics.utils.schema import validate_analytics


def _plays_meta(catalog: dict, script_ids: list[str]) -> list[dict]:
    by_id = {p["script_id"]: p for p in catalog.get("plays") or []}
    meta = []
    for sid in script_ids:
        if sid in by_id:
            meta.append(by_id[sid])
        else:
            meta.append({"script_id": sid, "title": sid})
    return meta


def _build_themes(play: dict, cfg: AnalyticsConfig, theme_model) -> tuple[dict, object]:
    """返回 (themes.json 内容, 供叙事/综合使用的 theme_model)。"""
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
    integrated = analyze_integrated(play, role, network, themes, narrative)

    sid = play["script_id"]
    out_dir = cfg.analytics_dir / "plays" / sid
    outputs = {
        "role.json": role,
        "network.json": network,
        "themes.json": themes,
        "narrative.json": narrative,
        "integrated.json": integrated,
    }
    schemas = {
        "role.json": "play_role.schema.json",
        "network.json": "network.schema.json",
        "themes.json": "theme.schema.json",
        "narrative.json": "narrative.schema.json",
        "integrated.json": "integrated.schema.json",
    }
    for name, doc in outputs.items():
        path = out_dir / name
        save_json(path, doc)
        if validate:
            errs = validate_analytics(doc, schemas[name], cfg.root)
            if errs:
                print(f"  WARN {sid}/{name}: {errs[0]}", file=sys.stderr)
    return {
        "role": role,
        "network": network,
        "themes": themes,
        "narrative": narrative,
        "integrated": integrated,
    }


def run_global(
    cfg: AnalyticsConfig,
    plays_meta: list[dict],
    results: dict[str, dict],
    theme_model,
    validate: bool,
) -> None:
    global_dir = cfg.analytics_dir / "global"
    role_agg = aggregate_role_analysis(
        plays_meta, {sid: results[sid]["role"] for sid in results}
    )
    net_cmp = aggregate_network_compare(
        plays_meta, {sid: results[sid]["network"] for sid in results}
    )
    theme_pat = aggregate_theme_patterns(
        plays_meta,
        {sid: results[sid]["themes"] for sid in results},
        theme_model,
    )
    narr_tpl = aggregate_narrative_templates(
        plays_meta, {sid: results[sid]["narrative"] for sid in results}
    )
    globals_out = {
        "role_analysis.json": (role_agg, "role_analysis.schema.json"),
        "network_compare.json": (net_cmp, "network_compare.schema.json"),
        "theme_patterns.json": (theme_pat, "theme_patterns.schema.json"),
        "narrative_templates.json": (narr_tpl, "narrative_templates.schema.json"),
    }
    for fname, (doc, schema) in globals_out.items():
        path = global_dir / fname
        save_json(path, doc)
        if validate:
            errs = validate_analytics(doc, schema, cfg.root)
            if errs:
                print(f"  WARN global/{fname}: {errs[0]}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="京剧剧本分析流水线")
    parser.add_argument("--script-id", action="append", dest="script_ids")
    parser.add_argument("--all", action="store_true", help="处理 cleaned/plays 下全部剧本")
    parser.add_argument("--global-only", action="store_true", help="仅重算 global 聚合")
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

    catalog = load_catalog(cfg.catalog_path)
    if args.all:
        script_ids = [sid for sid, _ in iter_play_paths(cfg.cleaned_dir)]
    elif args.script_ids:
        script_ids = args.script_ids
    elif args.global_only:
        script_ids = [sid for sid, _ in iter_play_paths(cfg.cleaned_dir)]
    else:
        script_ids = ["01001012"]

    if not script_ids:
        print("未找到可分析的剧本，请先运行预处理。", file=sys.stderr)
        return 1

    plays_meta = _plays_meta(catalog, script_ids)
    results: dict[str, dict] = {}

    if args.global_only:
        for sid in script_ids:
            play_dir = cfg.analytics_dir / "plays" / sid
            try:
                results[sid] = {
                    "role": load_play(play_dir / "role.json"),
                    "network": load_play(play_dir / "network.json"),
                    "themes": load_play(play_dir / "themes.json"),
                    "narrative": load_play(play_dir / "narrative.json"),
                }
            except FileNotFoundError:
                print(f"跳过 {sid}：缺少分析产物", file=sys.stderr)
        plays = [load_play(cfg.cleaned_dir / "plays" / f"{sid}.json") for sid in results]
        theme_model = None if cfg.llm_theme.enabled else train_theme_model(
            plays, cfg.num_topics, cfg.random_seed
        )
        run_global(cfg, plays_meta, results, theme_model, validate)
        print(f"全局聚合完成（{len(results)} 剧）")
        return 0

    plays = []
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
        results[sid] = run_play_analytics(play, cfg, theme_model, validate)

    run_global(cfg, plays_meta, results, theme_model, validate)
    print(f"完成：{len(results)} 剧 → {cfg.analytics_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
