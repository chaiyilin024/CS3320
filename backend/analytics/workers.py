"""单剧分析 worker — 供进程池调用。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from backend.analytics.integrated.correlate import analyze_integrated
from backend.analytics.narrative.rhythm import analyze_play_narrative
from backend.analytics.network.build_graph import analyze_play_network
from backend.analytics.role.infer import analyze_play_role
from backend.analytics.theme.export import build_play_themes
from backend.analytics.theme.llm import LlmThemeConfig, build_play_themes_llm
from backend.analytics.theme.model import model_from_themes, train_theme_model
from backend.analytics.theme.quality import backfill_play_quality
from backend.analytics.utils.io import load_play, save_json
from backend.analytics.utils.jieba_env import configure_jieba
from backend.analytics.utils.schema import validate_analytics

SCHEMA_MAP = {
    "role.json": "play_role.schema.json",
    "network.json": "network.schema.json",
    "themes.json": "theme.schema.json",
    "narrative.json": "narrative.schema.json",
    "integrated.json": "integrated.schema.json",
}

_JIEBA_ROOT: Path | None = None


def _ensure_jieba(root: Path) -> None:
    global _JIEBA_ROOT
    if _JIEBA_ROOT != root:
        try:
            configure_jieba(root)
        except ImportError:
            pass
        _JIEBA_ROOT = root


def _build_themes(play: dict, cfg: dict, theme_model):
    llm_cfg = cfg.get("llm_theme") or {}
    if llm_cfg.get("enabled"):
        try:
            llm = LlmThemeConfig(
                enabled=True,
                model=str(llm_cfg.get("model", "gpt-4o-mini")),
                base_url=str(llm_cfg.get("base_url", "https://api.openai.com/v1")),
                api_key=str(llm_cfg.get("api_key") or ""),
                num_topics=int(llm_cfg.get("num_topics", 6)),
                max_sample_chars=int(llm_cfg.get("max_sample_chars", 12000)),
                max_blocks=int(llm_cfg.get("max_blocks", 120)),
                timeout_sec=int(llm_cfg.get("timeout_sec", 120)),
            )
            themes = build_play_themes_llm(play, llm)
            return themes, model_from_themes(themes)
        except Exception as e:
            print(f"  WARN LLM 主题失败，回退 NMF/keyword: {e}", file=sys.stderr)
    themes = build_play_themes(play, theme_model)
    return themes, theme_model


def analyze_play_task(task: dict[str, Any]) -> dict[str, Any]:
    """完整单剧分析并写入 artifacts/analytics/plays/{id}/。"""
    root = Path(task["root"])
    sid = task["script_id"]
    cfg = task["cfg"]
    validate = bool(cfg.get("validate", True))
    _ensure_jieba(root)

    play_path = root / cfg["cleaned_rel"] / "plays" / f"{sid}.json"
    analytics_dir = root / cfg["analytics_rel"]
    try:
        play = load_play(play_path)
        llm_cfg = cfg.get("llm_theme") or {}
        if llm_cfg.get("enabled"):
            theme_model = None
        else:
            theme_model = train_theme_model(
                [play],
                int(cfg.get("num_topics", 8)),
                int(cfg.get("random_seed", 42)),
            )

        role = analyze_play_role(play)
        network = analyze_play_network(play, role)
        themes, theme_model_play = _build_themes(play, cfg, theme_model)
        narrative = analyze_play_narrative(
            play,
            window=int(cfg.get("rhythm_window", 20)),
            theme_model=theme_model_play,
        )
        integrated = analyze_integrated(play, role, network, themes, narrative)

        out_dir = analytics_dir / "plays" / sid
        outputs = {
            "role.json": role,
            "network.json": network,
            "themes.json": themes,
            "narrative.json": narrative,
            "integrated.json": integrated,
        }
        warnings: list[str] = []
        for name, doc in outputs.items():
            save_json(out_dir / name, doc)
            if validate:
                errs = validate_analytics(doc, SCHEMA_MAP[name], root)
                if errs:
                    warnings.append(f"{name}: {errs[0]}")
        return {
            "ok": True,
            "script_id": sid,
            "title": play.get("title", ""),
            "warnings": warnings,
            "log": f"分析 {sid} 《{play.get('title', '')}》",
        }
    except Exception as exc:
        return {
            "ok": False,
            "script_id": sid,
            "title": "",
            "warnings": [],
            "log": f"FAIL {sid}: {exc}",
        }


def integrated_only_task(task: dict[str, Any]) -> dict[str, Any]:
    root = Path(task["root"])
    sid = task["script_id"]
    validate = bool(task.get("validate", True))
    cleaned = root / task["cleaned_rel"]
    analytics_dir = root / task["analytics_rel"]
    out_dir = analytics_dir / "plays" / sid

    try:
        play = load_play(cleaned / "plays" / f"{sid}.json")
        import json

        def _load(name: str) -> dict | None:
            path = out_dir / name
            if not path.is_file():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        role = _load("role.json")
        network = _load("network.json")
        themes = _load("themes.json")
        narrative = _load("narrative.json")
        if not all([role, network, themes, narrative]):
            return {"ok": False, "script_id": sid, "log": f"  跳过 {sid}：缺少四模块分析产物"}

        integrated = analyze_integrated(play, role, network, themes, narrative)
        save_json(out_dir / "integrated.json", integrated)
        warnings: list[str] = []
        if validate:
            errs = validate_analytics(integrated, SCHEMA_MAP["integrated.json"], root)
            if errs:
                warnings.append(errs[0])
        return {"ok": True, "script_id": sid, "warnings": warnings, "log": f"  integrated {sid}"}
    except Exception as exc:
        return {"ok": False, "script_id": sid, "log": f"  FAIL {sid}: {exc}"}


def theme_quality_task(task: dict[str, Any]) -> dict[str, Any]:
    path = Path(task["path"])
    ok = backfill_play_quality(path)
    return {"ok": ok, "script_id": path.parent.name, "log": path.parent.name if ok else ""}
