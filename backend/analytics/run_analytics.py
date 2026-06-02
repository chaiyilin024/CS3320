#!/usr/bin/env python3
"""分析流水线入口 — 单剧四任务（行当 / 网络 / 主题 / 叙事）。

批处理结束后可聚合 global/*.json 供前端全库对比图使用。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.analytics.config import AnalyticsConfig
from backend.analytics.integrated.correlate import analyze_integrated
from backend.analytics.integrated.aggregate import run_global_aggregation
from backend.analytics.narrative.rhythm import analyze_play_narrative
from backend.analytics.network.build_graph import analyze_play_network
from backend.analytics.role.infer import analyze_play_role
from backend.analytics.theme.export import build_play_themes
from backend.analytics.theme.llm import build_play_themes_llm
from backend.analytics.theme.model import model_from_themes, train_theme_model
from backend.analytics.utils.io import iter_play_paths, load_play, save_json
from backend.analytics.utils.jieba_env import configure_jieba
from backend.analytics.utils.schema import validate_analytics
from backend.analytics.workers import (
    analyze_play_task,
    integrated_only_task,
    theme_quality_task,
)
from backend.utils.parallel import resolve_workers, run_parallel

SCHEMA_MAP = {
    "role.json": "play_role.schema.json",
    "network.json": "network.schema.json",
    "themes.json": "theme.schema.json",
    "narrative.json": "narrative.schema.json",
    "integrated.json": "integrated.schema.json",
}

GLOBAL_SCHEMA_MAP = {
    "role_analysis.json": "role_analysis.schema.json",
    "network_compare.json": "network_compare.schema.json",
    "theme_patterns.json": "theme_patterns.schema.json",
    "theme_quality.json": "theme_quality.schema.json",
    "narrative_templates.json": "narrative_templates.schema.json",
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
    integrated = analyze_integrated(play, role, network, themes, narrative)
    outputs["integrated.json"] = integrated
    for name, doc in outputs.items():
        save_json(out_dir / name, doc)
        if validate:
            errs = validate_analytics(doc, SCHEMA_MAP[name], cfg.root)
            if errs:
                print(f"  WARN {sid}/{name}: {errs[0]}", file=sys.stderr)
    return outputs


def _analytics_cfg_payload(cfg: AnalyticsConfig, validate: bool) -> dict:
    llm = cfg.llm_theme
    return {
        "validate": validate,
        "num_topics": cfg.num_topics,
        "random_seed": cfg.random_seed,
        "rhythm_window": cfg.rhythm_window,
        "cleaned_rel": str(cfg.cleaned_dir.relative_to(cfg.root)),
        "analytics_rel": str(cfg.analytics_dir.relative_to(cfg.root)),
        "llm_theme": {
            "enabled": llm.enabled,
            "model": llm.model,
            "base_url": llm.base_url,
            "api_key": llm.api_key,
            "num_topics": llm.num_topics,
            "max_sample_chars": llm.max_sample_chars,
            "max_blocks": llm.max_blocks,
            "timeout_sec": llm.timeout_sec,
        },
    }


def _run_plays_parallel(
    script_ids: list[str],
    cfg: AnalyticsConfig,
    validate: bool,
    workers: int,
) -> tuple[int, int]:
    w = resolve_workers(workers)
    print(f"并行进程数: {w}，分析 {len(script_ids)} 部剧本…")
    cfg_payload = _analytics_cfg_payload(cfg, validate)
    tasks = [
        {"root": str(cfg.root), "script_id": sid, "cfg": cfg_payload}
        for sid in script_ids
    ]

    def _progress(done: int, total: int, _result: dict) -> None:
        if done % 100 == 0 or done == total:
            print(f"  … 已完成 {done}/{total}")

    results = run_parallel(analyze_play_task, tasks, workers, progress=_progress)
    ok = 0
    for r in results:
        print(r.get("log", ""))
        for warn in r.get("warnings") or []:
            print(f"  WARN {r.get('script_id')}/{warn}", file=sys.stderr)
        if r.get("ok"):
            ok += 1
    return ok, len(script_ids)


def run_integrated_exports(
    cfg: AnalyticsConfig,
    script_ids: list[str],
    validate: bool,
    workers: int = 1,
) -> int:
    w = resolve_workers(workers)
    print(f"并行进程数: {w}，生成 integrated.json（{len(script_ids)} 剧）…")
    tasks = [
        {
            "root": str(cfg.root),
            "script_id": sid,
            "cleaned_rel": str(cfg.cleaned_dir.relative_to(cfg.root)),
            "analytics_rel": str(cfg.analytics_dir.relative_to(cfg.root)),
            "validate": validate,
        }
        for sid in script_ids
    ]

    def _progress(done: int, total: int, _result: dict) -> None:
        if done % 200 == 0 or done == total:
            print(f"  … 已完成 {done}/{total}")

    results = run_parallel(integrated_only_task, tasks, workers, progress=_progress)
    ok = 0
    for r in results:
        if r.get("log"):
            if not r.get("ok") and "跳过" not in r["log"]:
                print(r["log"], file=sys.stderr)
        for warn in r.get("warnings") or []:
            print(f"  WARN {r.get('script_id')}/integrated.json: {warn}", file=sys.stderr)
        if r.get("ok"):
            ok += 1
    print(f"综合关联完成：{ok} 剧 → {cfg.analytics_dir}/plays/*/integrated.json")
    return 0 if ok else 1


def run_theme_quality_backfill(cfg: AnalyticsConfig, workers: int = 1) -> int:
    plays_dir = cfg.analytics_dir / "plays"
    if not plays_dir.is_dir():
        print("未找到 analytics/plays 目录。", file=sys.stderr)
        return 1
    paths = sorted(
        play_dir / "themes.json"
        for play_dir in plays_dir.iterdir()
        if play_dir.is_dir() and (play_dir / "themes.json").is_file()
    )
    w = resolve_workers(workers)
    print(f"并行进程数: {w}，回填主题质量 {len(paths)} 剧…")
    tasks = [{"path": str(p)} for p in paths]

    def _progress(done: int, total: int, _result: dict) -> None:
        if done % 300 == 0 or done == total:
            print(f"  … 已完成 {done}/{total}")

    results = run_parallel(theme_quality_task, tasks, workers, progress=_progress)
    ok = sum(1 for r in results if r.get("ok"))
    print(f"主题质量回填完成：{ok} 剧 themes.json")
    return 0 if ok else 1


def run_global_exports(cfg: AnalyticsConfig, validate: bool) -> int:
    outputs = run_global_aggregation(cfg)
    global_dir = cfg.analytics_dir / "global"
    for name, doc in outputs.items():
        save_json(global_dir / name, doc)
        n = len(doc.get("play_topic_matrix") or doc.get("plays") or doc.get("templates") or [])
        extra = ""
        if name == "role_analysis.json":
            extra = f", 特征格 {len(doc.get('global_feature_hangdang_matrix', []))}"
        elif name == "theme_patterns.json":
            extra = f", 剧本 {len(doc.get('play_topic_matrix', []))}"
        elif name == "theme_quality.json":
            extra = f", 剧本 {len(doc.get('plays', []))}"
        elif name == "network_compare.json":
            extra = f", 剧本 {len(doc.get('plays', []))}"
        print(f"  global/{name}{extra or (', 条目 ' + str(n) if n else '')}")
        if validate:
            errs = validate_analytics(doc, GLOBAL_SCHEMA_MAP[name], cfg.root)
            if errs:
                print(f"  WARN global/{name}: {errs[0]}", file=sys.stderr)
    print(f"全局聚合完成 → {global_dir}")
    return 0


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
    parser.add_argument(
        "--global-only",
        action="store_true",
        help="仅从已有 plays 分析产物聚合 global/*.json",
    )
    parser.add_argument(
        "--integrated-only",
        action="store_true",
        help="仅从已有四模块产物生成 plays/*/integrated.json",
    )
    parser.add_argument(
        "--theme-quality-only",
        action="store_true",
        help="为已有 themes.json 回填 quality 并聚合 global/theme_quality.json",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="并行进程数（0=自动 min(CPU,8)，1=串行）",
    )
    args = parser.parse_args()

    cfg = AnalyticsConfig.load(ROOT)
    if args.num_topics:
        cfg.num_topics = args.num_topics
    if args.workers is not None:
        cfg.workers = args.workers
    if args.theme_llm and cfg.llm_theme.api_key:
        cfg.llm_theme.enabled = True
        cfg.num_topics = cfg.llm_theme.num_topics
    elif args.theme_llm:
        print("WARN: --theme-llm 已指定但未设置 OPENAI_API_KEY", file=sys.stderr)
    validate = not args.no_validate
    workers = cfg.workers

    if args.theme_quality_only:
        print("回填单剧主题质量…")
        code = run_theme_quality_backfill(cfg, workers)
        if code != 0:
            return code
        print("聚合全局主题质量…")
        return run_global_exports(cfg, validate)

    if args.global_only:
        print("聚合全局分析…")
        return run_global_exports(cfg, validate)

    if args.integrated_only:
        if args.all:
            script_ids = [sid for sid, _ in iter_play_paths(cfg.cleaned_dir)]
        elif args.script_ids:
            script_ids = args.script_ids
        else:
            plays_dir = cfg.analytics_dir / "plays"
            script_ids = sorted(p.name for p in plays_dir.iterdir() if p.is_dir())
        if not script_ids:
            print("未找到可生成 integrated 的剧本。", file=sys.stderr)
            return 1
        return run_integrated_exports(cfg, script_ids, validate, workers)

    if cfg.llm_theme.enabled and resolve_workers(workers) > 1:
        print("WARN: LLM 主题模式使用串行（--workers 1）", file=sys.stderr)
        workers = 1

    if resolve_workers(workers) == 1:
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

    # 过滤不存在的剧本
    valid_ids: list[str] = []
    for sid in script_ids:
        path = cfg.cleaned_dir / "plays" / f"{sid}.json"
        if not path.exists():
            print(f"跳过 {sid}：{path} 不存在", file=sys.stderr)
            continue
        valid_ids.append(sid)

    if not valid_ids:
        return 1

    if cfg.llm_theme.enabled:
        print(f"主题分析: LLM 模式（{cfg.llm_theme.model}，K={cfg.llm_theme.num_topics}）")

    ok, total = _run_plays_parallel(valid_ids, cfg, validate, workers)
    print(f"完成：{ok}/{total} 剧 → {cfg.analytics_dir}/plays")
    print("聚合全局分析…")
    run_global_exports(cfg, validate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
