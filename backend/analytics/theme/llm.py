"""可选：调用 OpenAI 兼容 API，从 cleaned play 抽样文本生成 themes.json。"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .quality import attach_quality

TEXT_TYPES = frozenset({"dialogue", "aria", "recitation"})

THEME_JSON_SCHEMA_HINT = """
{
  "topics": [
    {
      "topic_id": 0,
      "label": "2-6字主题名",
      "weight": 0.0到1.0,
      "keywords": ["词1", "词2", "..."],
      "representative_quotes": [
        {"block_id": "b_12", "text_snippet": "原文短句", "score": 0.9}
      ]
    }
  ]
}
"""


@dataclass
class LlmThemeConfig:
    enabled: bool = False
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    num_topics: int = 6
    max_sample_chars: int = 12000
    max_blocks: int = 120
    timeout_sec: int = 120

    @classmethod
    def from_env_and_yaml(cls, analytics_cfg: dict) -> LlmThemeConfig:
        llm = analytics_cfg.get("llm") or {}
        key = os.environ.get("OPENAI_API_KEY") or llm.get("api_key") or ""
        base = (
            os.environ.get("OPENAI_BASE_URL")
            or llm.get("base_url")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        enabled = bool(
            analytics_cfg.get("theme_use_llm")
            or os.environ.get("THEME_USE_LLM", "").lower() in ("1", "true", "yes")
        )
        return cls(
            enabled=enabled and bool(key),
            api_key=key,
            base_url=base,
            model=os.environ.get("LLM_MODEL") or llm.get("model") or "gpt-4o-mini",
            num_topics=int(llm.get("num_topics") or analytics_cfg.get("num_topics") or 6),
            max_sample_chars=int(llm.get("max_sample_chars", 12000)),
            max_blocks=int(llm.get("max_blocks", 120)),
            timeout_sec=int(llm.get("timeout_sec", 120)),
        )


def sample_play_excerpt(play: dict, cfg: LlmThemeConfig) -> tuple[str, set[str]]:
    """从 cleaned play 抽取带 block_id 的台词/唱段样本。"""
    lines: list[str] = []
    valid_ids: set[str] = set()
    chars = {c["character_id"]: c["name"] for c in play.get("characters") or []}
    meta = play.get("metadata") or {}
    header = (
        f"剧本ID: {play.get('script_id')}\n"
        f"剧名: {play.get('title', '')}\n"
        f"集合: {play.get('collection_name', '')}\n"
        f"体裁: {(play.get('tags') or {}).get('genre_inferred', '未知')}\n"
        "人物: "
        + ", ".join(
            f"{c['name']}({c['character_id']})"
            for c in (play.get("characters") or [])[:20]
        )
        + "\n"
        f"块数: {meta.get('block_count', len(play.get('blocks') or []))}\n"
        "---\n"
    )
    budget = cfg.max_sample_chars - len(header)
    used = 0
    count = 0
    for b in play.get("blocks") or []:
        if count >= cfg.max_blocks:
            break
        if b.get("type") not in TEXT_TYPES:
            continue
        text = (b.get("text") or "").strip()
        if len(text) < 2:
            continue
        bid = b.get("block_id") or f"b_{b.get('block_index', count)}"
        valid_ids.add(bid)
        sp = b.get("speaker_id")
        name = chars.get(sp, "") if sp else ""
        cues = b.get("performance_cues_raw") or b.get("performance_tags") or []
        cue_s = "/".join(cues) if cues else ""
        line = f"[{bid}]"
        if name:
            line += f" {name}"
        if cue_s:
            line += f"（{cue_s}）"
        line += f": {text[:300]}\n"
        if used + len(line) > budget:
            break
        lines.append(line)
        used += len(line)
        count += 1
    return header + "".join(lines), valid_ids


def build_play_themes_llm(play: dict, cfg: LlmThemeConfig) -> dict:
    excerpt, valid_block_ids = sample_play_excerpt(play, cfg)
    raw = call_llm_theme_api(excerpt, play, cfg)
    return normalize_llm_themes(play, raw, cfg, valid_block_ids)


def call_llm_theme_api(excerpt: str, play: dict, cfg: LlmThemeConfig) -> dict:
    system = (
        "你是京剧剧本主题分析助手。根据给出的剧本结构化摘录，"
        f"识别全剧 {cfg.num_topics} 个核心主题（如忠义、谋略、宴饮、冲突等）。"
        "只输出一个 JSON 对象，不要 markdown 说明。"
        f"topics 长度必须为 {cfg.num_topics}，topic_id 从 0 连续编号。"
        "weight 为各主题占比，总和应为 1。"
        "keywords 每个主题 5-12 个中文词。"
        "representative_quotes 每主题 1-3 条，block_id 必须来自摘录中的 [b_xxx]。"
        f"JSON 结构示例：{THEME_JSON_SCHEMA_HINT}"
    )
    user = f"请分析以下剧本摘录：\n\n{excerpt}"
    content = _chat_completion(cfg, system, user)
    return _parse_json_content(content)


def _chat_completion(cfg: LlmThemeConfig, system: str, user: str) -> str:
    url = f"{cfg.base_url}/chat/completions"
    body: dict[str, Any] = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    if "gpt" in cfg.model or "o1" in cfg.model or "o3" in cfg.model:
        body["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM API HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API 连接失败: {e}") from e

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM API 返回空 choices")
    return choices[0].get("message", {}).get("content") or ""


def _parse_json_content(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM 返回非合法 JSON: {text[:200]}…") from e


def normalize_llm_themes(
    play: dict,
    raw: dict,
    cfg: LlmThemeConfig,
    valid_block_ids: set[str],
) -> dict:
    topics_in = raw.get("topics") or []
    if not topics_in:
        raise RuntimeError("LLM 未返回 topics 数组")

    topics_in = sorted(topics_in, key=lambda t: int(t.get("topic_id", 0)))[: cfg.num_topics]
    weights: list[float] = []
    topics_out: list[dict] = []
    reps_out: list[dict] = []

    for i, t in enumerate(topics_in):
        tid = int(t.get("topic_id", i))
        label = str(t.get("label") or f"主题{tid}").strip()[:20]
        w = float(t.get("weight", 0))
        weights.append(max(0.0, w))
        kws = [str(k).strip() for k in (t.get("keywords") or []) if str(k).strip()][:20]
        if not kws:
            kws = [label]
        topics_out.append(
            {
                "topic_id": tid,
                "label": label,
                "weight": w,
                "keywords": kws,
            }
        )
        for q in t.get("representative_quotes") or t.get("representative_blocks") or []:
            bid = q.get("block_id", "")
            if bid and bid not in valid_block_ids:
                continue
            snippet = str(q.get("text_snippet") or q.get("text") or "")[:500]
            if not snippet:
                continue
            reps_out.append(
                {
                    "topic_id": tid,
                    "block_id": bid or f"b_{q.get('block_index', 0)}",
                    "block_index": q.get("block_index"),
                    "text_snippet": snippet,
                    "score": round(float(q.get("score", 0.8)), 4),
                }
            )

    s = sum(weights) or 1.0
    comp = [round(w / s, 4) for w in weights]
    for t, w in zip(topics_out, comp):
        t["weight"] = w

    if not reps_out:
        reps_out = _fallback_representative_blocks(play, topics_out)

    return attach_quality({
        "script_id": play["script_id"],
        "title": play.get("title", ""),
        "model": {
            "method": "llm",
            "num_topics_global": len(topics_out),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        },
        "topics": topics_out,
        "topic_composition": comp,
        "representative_blocks": reps_out[: cfg.num_topics * 3],
    })


def _fallback_representative_blocks(
    play: dict, topics: list[dict]
) -> list[dict]:
    """LLM 未给证据块时，用关键词在正文块中粗匹配。"""
    reps: list[dict] = []
    blocks = [
        b
        for b in play.get("blocks") or []
        if b.get("type") in TEXT_TYPES and (b.get("text") or "").strip()
    ]
    for t in topics:
        tid = t["topic_id"]
        kws = t.get("keywords") or []
        scored: list[tuple[float, dict]] = []
        for b in blocks:
            text = b["text"]
            score = sum(1 for k in kws if k in text) / max(len(kws), 1)
            if score > 0:
                scored.append((score, b))
        for score, b in sorted(scored, reverse=True)[:2]:
            reps.append(
                {
                    "topic_id": tid,
                    "block_id": b["block_id"],
                    "block_index": b.get("block_index"),
                    "text_snippet": b["text"][:200],
                    "score": round(score, 4),
                }
            )
    return reps
