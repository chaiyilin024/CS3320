from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .corpus import (
    _metadata_stopwords,
    build_dynamic_stopwords,
    iter_text_blocks,
    play_document,
    tokenize,
)

# 主题标签规则统一从 theme.json 读取，py 中不再硬编码关键词。
THEME_RULES_FILE = Path(__file__).resolve().parent / "theme.json"


@dataclass(frozen=True)
class LabelRule:
    """单个主题标签规则。

    评分：sum(keywords[w] if w in topic_words) + sum(neg_keywords[w] if w in topic_words)
    （neg_keywords 的 weight 通常为负，命中会减分）
    """

    label: str
    keywords: dict[str, float]
    neg_keywords: dict[str, float]


@lru_cache(maxsize=1)
def _load_label_rules() -> tuple[tuple[LabelRule, ...], float, int, float]:
    """从 theme.json 加载 (规则, hit_threshold, min_keyword_hits, fallback_threshold)。"""
    if not THEME_RULES_FILE.is_file():
        return tuple(), 4.0, 2, 1.0
    try:
        doc = json.loads(THEME_RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return tuple(), 4.0, 2, 1.0

    meta = doc.get("_meta") or {}
    threshold = float(meta.get("hit_threshold", 4.0))
    min_hits = int(meta.get("min_keyword_hits", 2))
    fallback_threshold = float(meta.get("fallback_threshold", 1.0))

    raw_labels = doc.get("labels") or doc.get("themes") or {}
    rules: list[LabelRule] = []
    for label, body in raw_labels.items():
        if not isinstance(body, dict):
            continue
        kw = {str(k): float(v) for k, v in (body.get("keywords") or {}).items()}
        neg = {
            str(k): float(v)
            for k, v in (body.get("neg_keywords") or {}).items()
        }
        if kw or neg:
            rules.append(LabelRule(label=label, keywords=kw, neg_keywords=neg))
    return tuple(rules), threshold, min_hits, fallback_threshold


def _is_noise_keyword(word: str) -> bool:
    w = (word or "").strip()
    if not w or len(w) < 2:
        return True
    if w in _metadata_stopwords():
        return True
    if "京剧" in w or w in {"戏考", "全本", "头本", "后本", "前本"}:
        return True
    return False


def is_metadata_topic(keywords: list[str]) -> bool:
    """判断该 topic 是否为页眉/丛书噪声（应从输出中剔除）。"""
    if not keywords:
        return True
    top = keywords[:8]
    noise = sum(1 for w in top if _is_noise_keyword(w))
    return noise >= 2 or (top and _is_noise_keyword(top[0]))


def _sanitize_topic_word_list(
    pairs: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    clean = [(w, s) for w, s in pairs if not _is_noise_keyword(w)]
    return clean if clean else pairs[:3]


def _score_label(rule: LabelRule, word_set: frozenset[str]) -> float:
    pos = sum(w for k, w in rule.keywords.items() if k in word_set)
    neg = sum(w for k, w in rule.neg_keywords.items() if k in word_set)
    return pos + neg


@dataclass
class ThemeModel:
    num_topics: int
    method: str = "nmf"
    random_seed: int = 42
    feature_names: list[str] = field(default_factory=list)
    topic_words: dict[int, list[tuple[str, float]]] = field(default_factory=dict)
    _vectorizer: object | None = None
    _nmf: object | None = None
    block_keys: list[tuple[str, str, int]] = field(default_factory=list)
    trained_at: str = ""
    _label_cache: dict[int, str] = field(default_factory=dict)

    def transform_blocks(self, play: dict) -> list[tuple[str, int, str, list[float]]]:
        """返回 (block_id, block_index, text, topic_vector)。"""
        blocks = iter_text_blocks(play)
        if not blocks:
            return []
        extra_stop = build_dynamic_stopwords(play)
        if self.method == "keyword" and isinstance(self._vectorizer, list):
            seeds = self._vectorizer
            out = []
            for b in blocks:
                words = tokenize(b["text"], extra_stop)
                vec = [_seed_score(words, seed) for _label, seed in seeds]
                s = sum(vec) or 1.0
                out.append(
                    (b["block_id"], b["block_index"], b["text"], [v / s for v in vec])
                )
            return out
        if self._nmf is None or self._vectorizer is None:
            return []
        import warnings

        import numpy as np

        docs = [" ".join(tokenize(b["text"], extra_stop)) for b in blocks]
        X = self._vectorizer.transform(docs)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            W = self._nmf.transform(X)
        out = []
        for b, vec in zip(blocks, W):
            row = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
            s = row.sum() or 1.0
            out.append(
                (b["block_id"], b["block_index"], b["text"], (row / s).tolist())
            )
        return out

    def play_composition(self, play: dict) -> list[float]:
        rows = self.transform_blocks(play)
        if not rows:
            return [1.0 / self.num_topics] * self.num_topics
        k = self.num_topics
        sums = [0.0] * k
        for _bid, _bidx, _text, vec in rows:
            for i, v in enumerate(vec[:k]):
                sums[i] += v
        total = sum(sums) or 1.0
        return [s / total for s in sums]

    def assign_unique_labels(self) -> None:
        """根据 theme.json 规则给每个主题打标签。

        优先级：
          1) score ≥ hit_threshold 且命中 ≥ min_keyword_hits（或单词 score≥8）→ 直接用 best_label
          2) score ≥ fallback_threshold → 仍用 best_label（最接近的主题，弱命中）
          3) 都不满足 → 「其他情节」（不再用「词A·词B」拼接，避免毫无意义的标签）

        同名解歧：在多 topic 命中同一 label 时，追加命中关键词中的次级词作后缀（来自
        theme.json 本身，不会出现噪声词）。
        """
        rules, threshold, min_hits, fb_threshold = _load_label_rules()

        topic_hits: dict[int, dict] = {}
        for tid in range(self.num_topics):
            words = [w for w, _ in self.topic_words.get(tid, [])[:20]]
            word_set = frozenset(words)
            scored: list[tuple[str, float, list[str]]] = []
            for rule in rules:
                score = _score_label(rule, word_set)
                hits = [k for k in rule.keywords if k in word_set]
                scored.append((rule.label, score, hits))
            scored.sort(key=lambda x: -x[1])
            best = scored[0] if scored else ("", 0.0, [])
            topic_hits[tid] = {
                "words": words,
                "best_label": best[0],
                "best_score": best[1],
                "best_hits": best[2],
                "scored": scored,
            }

        final: dict[int, str] = {}
        for tid, info in topic_hits.items():
            score = info["best_score"]
            hits = info["best_hits"]
            label = info["best_label"]
            if is_metadata_topic(info["words"]):
                final[tid] = "其他情节"
                continue
            strong = bool(label) and score >= threshold and (
                len(hits) >= min_hits or score >= 8.0
            )
            weak = bool(label) and score >= fb_threshold
            # 不再追加 "·xxx" 区分词：schema 允许多个 topic 同 label，
            # 它们的差异由各自的 keywords 与 representative_blocks 体现。
            final[tid] = label if (strong or weak) else "其他情节"
        self._label_cache = final

    def topic_label(self, topic_id: int) -> str:
        if not self._label_cache:
            self.assign_unique_labels()
        if topic_id in self._label_cache:
            return self._label_cache[topic_id]
        words = [w for w, _ in self.topic_words.get(topic_id, [])[:12]]
        rules, _, _, _ = _load_label_rules()
        word_set = frozenset(words)
        best_label, best_score = None, 0.0
        for rule in rules:
            score = _score_label(rule, word_set)
            if score > best_score:
                best_label, best_score = rule.label, score
        if best_label:
            return best_label
        if words:
            return words[0][:8]
        return f"主题{topic_id}"


def model_from_themes(themes_doc: dict) -> ThemeModel:
    """将 LLM 产出的 themes.json 转为可给叙事模块用的静态主题模型。"""
    topics = themes_doc.get("topics") or []
    m = ThemeModel(num_topics=len(topics), method="llm")
    m.trained_at = (themes_doc.get("model") or {}).get("trained_at", "")
    seeds: list[tuple[str, list[str]]] = []
    for t in topics:
        tid = int(t["topic_id"])
        kws = list(t.get("keywords") or [t.get("label", "")])
        m.topic_words[tid] = [(k, float(i + 1)) for i, k in enumerate(kws)]
        seeds.append((t.get("label", ""), kws))
    m._vectorizer = seeds
    m._nmf = None
    return m


def adaptive_num_topics(plays: list[dict], requested: int) -> int:
    """根据语料规模自适应 K：单剧时按 sqrt(text_blocks)/4 缩减。"""
    import math

    total_blocks = sum(len(iter_text_blocks(p)) for p in plays)
    if total_blocks <= 0:
        return max(2, requested)
    if len(plays) <= 1:
        suggested = max(3, int(math.sqrt(total_blocks) / 4))
        return max(2, min(requested, suggested))
    return max(2, requested)


def train_theme_model(
    plays: list[dict],
    num_topics: int = 8,
    random_seed: int = 42,
) -> ThemeModel:
    num_topics = adaptive_num_topics(plays, num_topics)
    try:
        model = _train_nmf_model(plays, num_topics, random_seed)
    except ImportError:
        model = _train_keyword_model(plays, num_topics, random_seed)
    except (ValueError, FloatingPointError):
        model = _train_keyword_model(plays, num_topics, random_seed)
    model.assign_unique_labels()
    return model


def _train_nmf_model(
    plays: list[dict], num_topics: int, random_seed: int
) -> ThemeModel:
    import warnings
    from datetime import datetime, timezone

    import numpy as np
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    docs = [d for d in _collect_docs(plays) if d.strip()]
    if len(docs) < max(3, num_topics):
        return _train_keyword_model(plays, num_topics, random_seed)

    num_topics = max(2, min(num_topics, len(docs) - 1))
    min_df = 2 if len(docs) >= 30 else 1

    vectorizer = TfidfVectorizer(
        max_df=0.9,
        min_df=min_df,
        max_features=5000,
        sublinear_tf=True,
        norm="l2",
        token_pattern=r"(?u)\b\w+\b",
    )
    X = vectorizer.fit_transform(docs)
    if X.shape[1] < num_topics:
        return _train_keyword_model(plays, num_topics, random_seed)

    nmf = NMF(
        n_components=num_topics,
        random_state=random_seed,
        max_iter=300,
        init="nndsvd",
        solver="cd",
        beta_loss="frobenius",
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            W = nmf.fit_transform(X)
            H = nmf.components_
        except Exception:
            return _train_keyword_model(plays, num_topics, random_seed)

    if not (np.isfinite(W).all() and np.isfinite(H).all()):
        return _train_keyword_model(plays, num_topics, random_seed)

    model = ThemeModel(num_topics=num_topics, random_seed=random_seed)
    model.trained_at = datetime.now(timezone.utc).isoformat()
    model.method = "nmf"
    model._vectorizer = vectorizer
    model._nmf = nmf
    model.feature_names = list(vectorizer.get_feature_names_out())

    for tid in range(num_topics):
        row = H[tid]
        top_idx = row.argsort()[::-1][:30]
        pairs = [
            (model.feature_names[i], float(row[i]))
            for i in top_idx
            if row[i] > 0 and np.isfinite(row[i])
        ]
        model.topic_words[tid] = _sanitize_topic_word_list(pairs)[:20]
    if not any(model.topic_words.values()):
        return _train_keyword_model(plays, num_topics, random_seed)
    return model


def _seed_topics_from_theme_rules() -> list[tuple[str, list[str]]]:
    """从 theme.json 派生 (label, seed_words) — 关键词模型的种子。"""
    rules, _, _, _ = _load_label_rules()
    if not rules:
        return [("通用主题", ["主公", "将军", "出兵", "回朝"])]
    out: list[tuple[str, list[str]]] = []
    for rule in rules:
        seeds = sorted(rule.keywords.keys(), key=lambda w: -rule.keywords[w])[:12]
        if seeds:
            out.append((rule.label, seeds))
    return out


def _train_keyword_model(
    plays: list[dict], num_topics: int, random_seed: int
) -> ThemeModel:
    from collections import Counter
    from datetime import datetime, timezone

    model = ThemeModel(num_topics=num_topics, random_seed=random_seed)
    model.trained_at = datetime.now(timezone.utc).isoformat()
    model.method = "keyword"

    all_seeds = _seed_topics_from_theme_rules()
    seeds = all_seeds[:num_topics]
    model.num_topics = len(seeds)
    corpus_words: Counter[str] = Counter()
    topic_counters: list[Counter[str]] = [Counter() for _ in seeds]

    for play in plays:
        extra_stop = build_dynamic_stopwords(play)
        for b in iter_text_blocks(play):
            words = tokenize(b["text"], extra_stop)
            corpus_words.update(words)
            scores = [_seed_score(words, seed) for _label, seed in seeds]
            tid = max(range(len(scores)), key=lambda i: scores[i])
            topic_counters[tid].update(words)

    for tid, (_label, seed) in enumerate(seeds):
        top = [w for w, _ in topic_counters[tid].most_common(15)]
        if not top:
            top = list(seed)[:10]
        model.topic_words[tid] = [(w, float(i + 1)) for i, w in enumerate(top)]
    model._vectorizer = seeds
    model._nmf = None
    return model


def _collect_docs(plays: list[dict]) -> list[str]:
    docs: list[str] = []
    for play in plays:
        extra_stop = build_dynamic_stopwords(play)
        blocks = iter_text_blocks(play)
        for b in blocks:
            tok = tokenize(b["text"], extra_stop)
            docs.append(" ".join(tok) if tok else b["text"][:80])
        if not blocks:
            doc = play_document(play)
            if doc:
                docs.append(" ".join(tokenize(doc, extra_stop)))
    return docs


def _seed_score(words: list[str], seed: list[str]) -> float:
    text = "".join(words)
    return sum(1.0 for s in seed if s in text)
