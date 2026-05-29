"""任务四：单剧叙事结构分析。

核心思路：
1. 用 5 维节奏序列（对白密度 / 唱段比 / 动作强度 / 情感 / 紧张度）刻画节奏起伏；
2. 用基于 tension 平滑曲线的**峰谷变点检测**找 4 个关键边界 → 5 个阶段（铺垫/发展/冲突/高潮/结局）；
3. 把检测到的变点**对齐到最近的 scene 边界**，让阶段切分尊重原剧场次；
4. 每个阶段根据自身 dominant 信号生成智能标签（·激战 / ·对峙 / ·唱抒 / ·平缓…）；
5. 只输出"关键 block 标注"（阶段边界 + 情感极值 + 主题切换），避免 419 块全量写入。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from ..theme.corpus import build_dynamic_stopwords, tokenize
from ..theme.model import ThemeModel

STAGES = ["铺垫", "发展", "冲突", "高潮", "结局"]
PERF_KEYS = ("唱", "念", "做", "打", "unknown")

# 扩展情感词典（戏曲常见正/负向词）
POS_WORDS = frozenset(
    "喜 贺 笑 欢 欣 庆 乐 美 好 妙 安 宁 平 善 恩 谢 智 巧 妙策 成 胜 凯 安康 福 寿 吉".split()
)
NEG_WORDS = frozenset(
    "怒 恨 杀 死 哭 悲 怕 惊 吓 危 险 败 哀 苦 痛 忧 愁 怨 仇 急 慌 恶 凶 凌 困 逼 难".split()
)
INTENSIFIERS = frozenset("甚 极 大 万 不胜 何等 怎奈 焉得 岂".split())
TENSION_WORDS = frozenset(
    "杀 战 兵 厮杀 破敌 围困 围攻 突围 急速 拿下 切莫 莫要 速速 立刻 不可 危急".split()
)


def analyze_play_narrative(
    play: dict,
    window: int = 20,
    theme_model: ThemeModel | None = None,
) -> dict:
    script_id = play["script_id"]
    title = play.get("title", "")
    raw_blocks = play.get("blocks") or []
    # 只对正文（非角色表/情节梗概等）做节奏；保留 block_index 关联
    blocks = [
        b for b in raw_blocks
        if b.get("type") not in ("character_list", "plot_summary", "annotation")
    ]
    if not blocks:
        return _empty_narrative(script_id, title)

    perf_dist = _performance_distribution(blocks)
    rhythm_series = _rhythm_series(blocks, window)
    scenes = play.get("scenes") or []
    plot_stages = _detect_stages(blocks, rhythm_series, scenes)
    perf_by_stage = _perf_by_stage(blocks, plot_stages)
    extra_stop = build_dynamic_stopwords(play)
    plot_stages = _enrich_stage_labels(
        plot_stages, blocks, rhythm_series, perf_by_stage, extra_stop
    )
    annotations = _key_block_annotations(
        play, blocks, plot_stages, rhythm_series, theme_model
    )

    return {
        "script_id": script_id,
        "title": title,
        "plot_stages": plot_stages,
        "rhythm_series": rhythm_series,
        "performance_mark_distribution": perf_dist,
        "performance_by_stage": perf_by_stage,
        "block_annotations": annotations,
    }


# ───────────────────────── 节奏序列 ─────────────────────────


def _performance_distribution(blocks: list[dict]) -> dict[str, int]:
    dist = {k: 0 for k in PERF_KEYS}
    for b in blocks:
        tags = b.get("performance_tags") or []
        if not tags:
            dist["unknown"] += 1
            continue
        for t in tags:
            dist[t if t in dist else "unknown"] += 1
    return dist


def _rhythm_series(blocks: list[dict], window: int) -> list[dict]:
    half = max(1, window // 2)
    n = len(blocks)
    series: list[dict] = []
    for i, b in enumerate(blocks):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        win = blocks[lo:hi]
        wlen = len(win) or 1

        dialogue = sum(1 for x in win if x.get("type") == "dialogue")
        aria = sum(
            1
            for x in win
            if x.get("type") == "aria"
            or "唱" in (x.get("performance_tags") or [])
        )
        action = sum(
            1
            for x in win
            if x.get("type") in ("action", "combat", "stage_direction")
            or any(t in ("做", "打") for t in (x.get("performance_tags") or []))
        )
        speakers = {x.get("speaker_id") for x in win if x.get("speaker_id")}
        speaker_diversity = len(speakers) / wlen

        text = " ".join(x.get("text", "") for x in win)
        emotion = _emotion_score(text)
        tension = _tension_score(text, action / wlen, speaker_diversity)

        series.append(
            {
                "block_index": b["block_index"],
                "window": window,
                "dialogue_density": round(dialogue / wlen, 4),
                "aria_ratio": round(aria / wlen, 4),
                "action_intensity": round(action / wlen, 4),
                "emotion_score": round(emotion, 4),
                "tension_score": round(tension, 4),
            }
        )
    return series


def _emotion_score(text: str) -> float:
    """0~1，0.5 中性，>0.5 偏正面，<0.5 偏负面。"""
    pos = sum(text.count(w) for w in POS_WORDS)
    neg = sum(text.count(w) for w in NEG_WORDS)
    intens = sum(text.count(w) for w in INTENSIFIERS) * 0.5
    if pos + neg == 0:
        return 0.5
    delta = (pos - neg) / (pos + neg + 2) * (1.0 + intens / max(pos + neg, 1))
    return min(1.0, max(0.0, 0.5 + 0.4 * delta))


def _tension_score(text: str, action_ratio: float, speaker_div: float) -> float:
    excl = text.count("！") + text.count("!") + text.count("？") + text.count("?")
    bang = min(1.0, excl / 6)
    tension_word_hits = sum(text.count(w) for w in TENSION_WORDS)
    tw = min(1.0, tension_word_hits / 5)
    emotion = _emotion_score(text)
    # 情感偏离 0.5 越远越紧张（剧烈情绪都是张力来源）
    emotion_dev = abs(emotion - 0.5) * 2
    return min(
        1.0,
        0.30 * action_ratio
        + 0.20 * bang
        + 0.20 * tw
        + 0.20 * emotion_dev
        + 0.10 * speaker_div,
    )


# ───────────────────────── 阶段切分 ─────────────────────────


def _detect_stages(
    blocks: list[dict], rhythm: list[dict], scenes: list[dict]
) -> list[dict]:
    """基于 tension 平滑曲线找 4 个变点，对齐到 scene 边界，输出 5 段。"""
    n = len(blocks)
    if n < 10:
        return [_make_stage("其他", blocks, 0, n - 1)]
    tension = [p.get("tension_score", 0.5) for p in rhythm]
    smoothed = _moving_average(tension, k=max(5, len(tension) // 20))

    cuts = _find_changepoints(smoothed)
    cuts = _snap_to_scenes(cuts, blocks, scenes, tol=max(5, n // 20))
    cuts = _ensure_monotonic(cuts, n)

    stages_out: list[dict] = []
    for i, stage_name in enumerate(STAGES):
        start, end = cuts[i], cuts[i + 1] - 1
        if start > end:
            continue
        stages_out.append(_make_stage(stage_name, blocks, start, end))
    if not stages_out:
        stages_out = [_make_stage("其他", blocks, 0, n - 1)]
    return stages_out


def _find_changepoints(smoothed: list[float]) -> list[int]:
    """返回 5 段的 [start, c1, c2, c3, c4, end+1] 共 6 个 index（局部下标）。

    策略：
      - climax = argmax(smoothed)
      - ending = climax 之后 smoothed 跌幅最大的点
      - dev = [0, climax] 内 smoothed 首次 > median + 0.3·std
      - conflict = [dev, climax] 内 smoothed 首次 > climax_val * 0.6 + median * 0.4
    """
    n = len(smoothed)
    climax = _argmax(smoothed)
    climax_val = smoothed[climax]
    median = _median(smoothed)
    std = _std(smoothed)

    # 发展起点
    dev_thresh = median + 0.30 * std
    dev = _find_first_above(smoothed, 0, climax, dev_thresh)
    if dev is None:
        dev = max(1, climax // 3)

    # 冲突起点
    conf_thresh = climax_val * 0.6 + median * 0.4
    conflict = _find_first_above(smoothed, dev, climax, conf_thresh)
    if conflict is None or conflict <= dev:
        conflict = (dev + climax) // 2

    # 结局起点（climax 之后跌幅最大）
    if climax < n - 5:
        # 找 climax 之后下降最快的位置（差分最小）
        drop_idx = climax + 1
        min_drop = 0.0
        for j in range(climax + 1, n):
            drop = smoothed[j] - climax_val
            if drop < min_drop:
                min_drop = drop
                drop_idx = j
                if smoothed[j] < median:
                    break
        ending = drop_idx
    else:
        ending = climax + 1

    # 高潮起点 = climax 前的 conflict；高潮终点（=结局起点-1）
    cuts = [0, dev, conflict, climax, ending, n]
    return cuts


def _snap_to_scenes(
    cuts: list[int], blocks: list[dict], scenes: list[dict], tol: int
) -> list[int]:
    """把内部变点对齐到最近的 scene 边界（如距离 ≤ tol）。

    scenes[].block_range 是原始 block_index；这里要映射为正文 blocks 列表里的下标。
    """
    if not scenes:
        return cuts
    # 收集 scene 边界（用 block_range 起止）
    scene_bounds_raw: set[int] = set()
    for sc in scenes:
        rng = sc.get("block_range") or []
        if len(rng) >= 1:
            scene_bounds_raw.add(int(rng[0]))
        if len(rng) >= 2:
            scene_bounds_raw.add(int(rng[1]) + 1)
    # 把 block_index 映射到当前 blocks 列表中的位置
    idx_lookup = {b["block_index"]: i for i, b in enumerate(blocks)}
    scene_positions = sorted(
        {idx_lookup[bi] for bi in scene_bounds_raw if bi in idx_lookup}
    )
    if not scene_positions:
        return cuts

    snapped = list(cuts)
    for k in range(1, len(snapped) - 1):  # 不动首尾
        c = snapped[k]
        nearest = min(scene_positions, key=lambda p: abs(p - c))
        if abs(nearest - c) <= tol:
            snapped[k] = nearest
    return snapped


def _ensure_monotonic(cuts: list[int], n: int) -> list[int]:
    """保证严格递增且首/尾合法；不满足则退化为均分。"""
    cuts = list(cuts)
    cuts[0] = 0
    cuts[-1] = n
    fallback = False
    for i in range(1, len(cuts)):
        if cuts[i] <= cuts[i - 1]:
            fallback = True
            break
    if fallback or cuts[1] >= n:
        # 均分兜底
        return [round(i * n / (len(STAGES))) for i in range(len(STAGES) + 1)]
    return cuts


def _make_stage(name: str, blocks: list[dict], lo: int, hi: int) -> dict:
    return {
        "stage": name,
        "label": name,
        "block_range": [blocks[lo]["block_index"], blocks[hi]["block_index"]],
        "summary": "",
    }


def _enrich_stage_labels(
    stages: list[dict],
    blocks: list[dict],
    rhythm: list[dict],
    perf_by_stage: list[dict],
    extra_stop: frozenset[str],
) -> list[dict]:
    """根据该段实际节奏特征赋更精细的 label，并生成 summary。"""
    idx_of = {b["block_index"]: i for i, b in enumerate(blocks)}
    rhythm_by_idx = {r["block_index"]: r for r in rhythm}
    perf_lookup = {p["stage"]: p["distribution"] for p in perf_by_stage}

    enriched: list[dict] = []
    for st in stages:
        lo_bi, hi_bi = st["block_range"]
        lo, hi = idx_of[lo_bi], idx_of[hi_bi]
        seg_rhythm = [
            rhythm_by_idx[b["block_index"]] for b in blocks[lo : hi + 1]
            if b["block_index"] in rhythm_by_idx
        ]
        avg = _average_metrics(seg_rhythm)
        label_suffix = _label_suffix(avg)
        base = st["stage"]
        # 基础语义标签
        base_label = {
            "铺垫": "引入",
            "发展": "推进",
            "冲突": "对峙",
            "高潮": "激战",
            "结局": "收束",
            "其他": "全剧",
        }.get(base, base)
        label = f"{base_label}{label_suffix}" if label_suffix else base_label
        summary = _stage_summary(
            blocks[lo : hi + 1], perf_lookup.get(base, {}), extra_stop
        )
        enriched.append(
            {
                "stage": base,
                "label": label,
                "block_range": st["block_range"],
                "summary": summary,
            }
        )
    return enriched


def _label_suffix(metrics: dict) -> str:
    """根据该段平均节奏返回 ·激战 / ·对峙 / ·唱抒 等后缀。"""
    if metrics.get("action_intensity", 0) > 0.22:
        return "·激战"
    if metrics.get("aria_ratio", 0) > 0.28:
        return "·唱抒"
    if metrics.get("dialogue_density", 0) > 0.55 and metrics.get("tension_score", 0) > 0.45:
        return "·对峙"
    if metrics.get("emotion_score", 0.5) < 0.38:
        return "·低谷"
    if metrics.get("emotion_score", 0.5) > 0.66:
        return "·高扬"
    if metrics.get("tension_score", 0) > 0.55:
        return "·紧张"
    if metrics.get("tension_score", 0) < 0.25:
        return "·平缓"
    return ""


def _stage_summary(
    segment: list[dict], perf_dist: dict[str, int], extra_stop: frozenset[str]
) -> str:
    """用关键词 + 唱念做打比例做一句话摘要。"""
    words: list[str] = []
    for b in segment[:60]:
        text = b.get("text") or ""
        if not text:
            continue
        words.extend(tokenize(text, extra_stop))
    if not words:
        words = [
            w
            for b in segment[:60]
            for w in re.findall(r"[\u4e00-\u9fff]{2,4}", b.get("text") or "")
        ]
    common = Counter(words).most_common(5)
    kw_part = "、".join(w for w, _ in common) if common else ""
    total = sum(perf_dist.values()) or 1
    perf_part = ""
    if perf_dist:
        ratios = {k: perf_dist.get(k, 0) / total for k in ("唱", "念", "做", "打")}
        dom = max(ratios.items(), key=lambda x: x[1]) if ratios else None
        if dom and dom[1] > 0.3:
            perf_part = f"（以{dom[0]}为主 {int(dom[1] * 100)}%）"
    return (kw_part + perf_part).strip()


# ───────────────────────── 唱念做打按段统计 ─────────────────────────


def _perf_by_stage(blocks: list[dict], stages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for st in stages:
        lo, hi = st["block_range"]
        dist = {k: 0 for k in PERF_KEYS}
        for b in blocks:
            if lo <= b["block_index"] <= hi:
                tags = b.get("performance_tags") or []
                if not tags:
                    dist["unknown"] += 1
                    continue
                for t in tags:
                    dist[t if t in dist else "unknown"] += 1
        out.append({"stage": st["stage"], "distribution": dist})
    return out


# ───────────────────────── 关键块标注（瘦身版） ─────────────────────────


def _key_block_annotations(
    play: dict,
    blocks: list[dict],
    stages: list[dict],
    rhythm: list[dict],
    theme_model: ThemeModel | None,
    max_total: int = 80,
) -> list[dict]:
    """只输出关键块：阶段边界 + 各段情感极值 + 主题切换点。"""
    rhythm_by_idx = {r["block_index"]: r for r in rhythm}
    stage_by_idx: dict[int, str] = {}
    for st in stages:
        lo, hi = st["block_range"]
        for b in blocks:
            if lo <= b["block_index"] <= hi:
                stage_by_idx[b["block_index"]] = st["stage"]

    topic_by_idx: dict[int, int] = {}
    if theme_model is not None:
        try:
            for block_id, _bidx, _text, vec in theme_model.transform_blocks(play):
                if not vec:
                    continue
                tid = max(range(len(vec)), key=lambda i: vec[i])
                # 找该 block_id 对应的 block_index
                # block_id 形式 b_{n}，n 即 block_index
                m = re.match(r"^b_(\d+)$", block_id)
                if m:
                    topic_by_idx[int(m.group(1))] = tid
        except Exception:
            pass

    key_indices: set[int] = set()
    # 1) 阶段边界
    for st in stages:
        key_indices.update(st["block_range"])

    # 2) 各段情感极值
    for st in stages:
        lo, hi = st["block_range"]
        seg = [
            rhythm_by_idx[b["block_index"]]
            for b in blocks
            if lo <= b["block_index"] <= hi and b["block_index"] in rhythm_by_idx
        ]
        if not seg:
            continue
        emax = max(seg, key=lambda p: p.get("emotion_score", 0.5))
        emin = min(seg, key=lambda p: p.get("emotion_score", 0.5))
        tmax = max(seg, key=lambda p: p.get("tension_score", 0.0))
        key_indices.update({emax["block_index"], emin["block_index"], tmax["block_index"]})

    # 3) 主题切换点
    if topic_by_idx:
        sorted_idx = sorted(topic_by_idx.keys())
        prev = None
        for bi in sorted_idx:
            cur = topic_by_idx[bi]
            if prev is not None and cur != prev:
                key_indices.add(bi)
            prev = cur

    # 控制数量上限
    chosen = sorted(key_indices)
    if len(chosen) > max_total:
        # 等距下采样
        step = len(chosen) / max_total
        chosen = [chosen[int(i * step)] for i in range(max_total)]

    annotations: list[dict] = []
    for bi in chosen:
        if bi not in stage_by_idx:
            continue
        item = {
            "block_index": bi,
            "block_id": f"b_{bi}",
            "stage": stage_by_idx[bi],
            "emotion_score": rhythm_by_idx[bi]["emotion_score"]
            if bi in rhythm_by_idx
            else 0.5,
        }
        if bi in topic_by_idx:
            item["dominant_topic_id"] = topic_by_idx[bi]
        annotations.append(item)
    return annotations


# ───────────────────────── 工具函数 ─────────────────────────


def _moving_average(xs: list[float], k: int) -> list[float]:
    k = max(1, k)
    n = len(xs)
    out: list[float] = []
    half = k // 2
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        seg = xs[lo:hi]
        out.append(sum(seg) / len(seg))
    return out


def _argmax(xs: list[float]) -> int:
    return max(range(len(xs)), key=lambda i: xs[i])


def _median(xs: Iterable[float]) -> float:
    sorted_xs = sorted(xs)
    n = len(sorted_xs)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return sorted_xs[n // 2]
    return (sorted_xs[n // 2 - 1] + sorted_xs[n // 2]) / 2


def _std(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / n
    return var ** 0.5


def _find_first_above(
    xs: list[float], lo: int, hi: int, threshold: float
) -> int | None:
    for i in range(max(0, lo), min(len(xs), hi)):
        if xs[i] >= threshold:
            return i
    return None


def _average_metrics(rhythm_seg: list[dict]) -> dict:
    if not rhythm_seg:
        return {}
    keys = (
        "dialogue_density",
        "aria_ratio",
        "action_intensity",
        "emotion_score",
        "tension_score",
    )
    out = {}
    for k in keys:
        vals = [r.get(k, 0.0) for r in rhythm_seg]
        out[k] = sum(vals) / len(vals)
    return out


def _empty_narrative(script_id: str, title: str) -> dict:
    return {
        "script_id": script_id,
        "title": title,
        "plot_stages": [{"stage": "其他", "block_range": [0, 0], "label": "全剧"}],
        "rhythm_series": [
            {
                "block_index": 0,
                "window": 20,
                "dialogue_density": 0,
                "aria_ratio": 0,
                "action_intensity": 0,
                "emotion_score": 0.5,
            }
        ],
        "performance_mark_distribution": {k: 0 for k in PERF_KEYS},
    }
