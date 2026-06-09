from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .corpus import (
    _metadata_stopwords,
    build_corpus_stopwords,
    build_corpus_stopwords_from_paths,
    build_dynamic_stopwords,
    iter_text_blocks,
    play_document,
    tokenize,
)

# Topic label rules are loaded from theme.json only; no hardcoded keywords in Python.
THEME_RULES_FILE = Path(__file__).resolve().parent / "theme.json"
FALLBACK_LABEL = "其他情节"
GLOBAL_THEME_MODEL_FILENAME = "theme_model.pkl"

# Corpus-wide NMF anchor topics (aligned with theme.json; stable T0–T7 semantics)
GLOBAL_SEED_LABELS = (
    "朝堂奏对",
    "战争征伐",
    "计策谋略",
    "行军调度",
    "公案侠义",
    "才子佳人",
    "冲突怒斥",
    "团圆喜庆",
)


@dataclass(frozen=True)
class LabelRule:
    """Single topic label rule.

    Score: sum(keywords[w] if w in topic_words) + sum(neg_keywords[w] if w in topic_words)
    (neg_keywords weights are usually negative; hits reduce the score)
    """

    label: str
    keywords: dict[str, float]
    neg_keywords: dict[str, float]


@lru_cache(maxsize=1)
def _load_label_rules() -> tuple[tuple[LabelRule, ...], float, int, float]:
    """Load (rules, hit_threshold, min_keyword_hits, fallback_threshold) from theme.json."""
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
    """Whether this topic is header/series noise (should be dropped from output)."""
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


def _score_label_fuzzy(rule: LabelRule, words: list[str]) -> tuple[float, list[str]]:
    """Exact match first; else substring fuzzy match between topic words and rule words (corpus NMF often yields phrases)."""
    word_set = frozenset(words)
    score = _score_label(rule, word_set)
    hits = [k for k in rule.keywords if k in word_set]
    if score > 0 or hits:
        return score, hits
    fuzzy: set[str] = set()
    for w in words[:20]:
        for k in rule.keywords:
            if len(k) >= 2 and (k in w or w in k):
                fuzzy.add(k)
    if not fuzzy:
        return 0.0, []
    fuzzy_score = sum(rule.keywords[k] for k in fuzzy) * 0.6
    return fuzzy_score, sorted(fuzzy)


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
    corpus_stopwords: frozenset[str] = field(default_factory=frozenset)
    pinned_labels: dict[int, str] = field(default_factory=dict)

    def _block_extra_stop(self, play: dict) -> frozenset[str]:
        return build_dynamic_stopwords(play) | self.corpus_stopwords

    def _nmf_block_matrix(self, play: dict):
        """Return (blocks, raw_W)."""
        import numpy as np

        blocks = iter_text_blocks(play)
        if not blocks or self._nmf is None or self._vectorizer is None:
            return [], None
        extra_stop = self._block_extra_stop(play)
        docs = [" ".join(tokenize(b["text"], extra_stop)) for b in blocks]
        X = self._vectorizer.transform(docs)
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            W = self._nmf.transform(X)
        W = np.nan_to_num(W, nan=0.0, posinf=0.0, neginf=0.0)
        return blocks, W

    def transform_blocks(self, play: dict) -> list[tuple[str, int, str, list[float]]]:
        """Return (block_id, block_index, text, topic_vector)."""
        blocks = iter_text_blocks(play)
        if not blocks:
            return []
        extra_stop = self._block_extra_stop(play)
        if self.method in ("keyword", "global_keyword") and isinstance(
            self._vectorizer, list
        ):
            seeds = self._vectorizer
            out = []
            for b in blocks:
                words = tokenize(b["text"], extra_stop)
                vec = _topic_seed_scores(words, seeds)
                s = sum(vec) or 1.0
                out.append(
                    (b["block_id"], b["block_index"], b["text"], [v / s for v in vec])
                )
            return out
        if self._nmf is None or self._vectorizer is None:
            return []
        blocks, W = self._nmf_block_matrix(play)
        if W is None:
            return []
        out = []
        for b, vec in zip(blocks, W):
            row = vec
            s = row.sum() or 1.0
            out.append(
                (b["block_id"], b["block_index"], b["text"], (row / s).tolist())
            )
        return out

    def play_composition(self, play: dict) -> list[float]:
        """Per-play topic proportions: block-level argmax counts to avoid one topic absorbing all weight."""
        k = self.num_topics
        if self.method == "nmf" and self._nmf is not None:
            _blocks, W = self._nmf_block_matrix(play)
            if W is None or len(_blocks) == 0:
                return [1.0 / k] * k
            counts = [0.0] * k
            for vec in W:
                if len(vec) == 0:
                    continue
                best_score = float(max(vec))
                if best_score <= 0:
                    continue
                best = int(max(range(len(vec)), key=lambda i: vec[i]))
                if 0 <= best < k:
                    counts[best] += 1.0
            total = sum(counts) or 1.0
            return [c / total for c in counts]
        rows = self.transform_blocks(play)
        if not rows:
            return [1.0 / k] * k
        counts = [0.0] * k
        for _bid, _bidx, _text, vec in rows:
            if not vec:
                continue
            best_score = max(vec)
            if best_score <= 0:
                continue
            best = int(max(range(len(vec)), key=lambda i: vec[i]))
            if 0 <= best < k:
                counts[best] += 1.0
        total = sum(counts) or 1.0
        return [c / total for c in counts]

    def assign_unique_labels(self) -> None:
        """Assign each topic a label per theme.json rules.

        Priority:
          1) score ≥ hit_threshold and hits ≥ min_keyword_hits (or single-word score≥8) → use best_label
          2) score ≥ fallback_threshold → still use best_label (closest topic, weak hit)
          3) otherwise → 「其他情节」 (no more 「词A·词B」 glue labels)

        Disambiguation: when multiple topics hit the same label, append a secondary hit keyword
        as suffix (from theme.json only, not noise words).
        """
        rules, threshold, min_hits, fb_threshold = _load_label_rules()

        topic_hits: dict[int, dict] = {}
        for tid in range(self.num_topics):
            words = [w for w, _ in self.topic_words.get(tid, [])[:20]]
            scored: list[tuple[str, float, list[str]]] = []
            for rule in rules:
                score, hits = _score_label_fuzzy(rule, words)
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
                final[tid] = FALLBACK_LABEL
                continue
            strong = bool(label) and score >= threshold and (
                len(hits) >= min_hits or score >= 8.0
            )
            weak = bool(label) and score >= fb_threshold
            # Do not append "·xxx" disambiguators: schema allows multiple topics with the same label;
            # differences show via keywords and representative_blocks.
            final[tid] = label if (strong or weak) else FALLBACK_LABEL
        self._label_cache = final

    def topic_label(self, topic_id: int) -> str:
        if topic_id in self.pinned_labels:
            return self.pinned_labels[topic_id]
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
    """Convert LLM-produced themes.json into a static theme model for the narrative module."""
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
    """Adapt K to corpus size: for a single play, scale down by sqrt(text_blocks)/4."""
    import math

    total_blocks = sum(len(iter_text_blocks(p)) for p in plays)
    if total_blocks <= 0:
        return max(2, requested)
    if len(plays) <= 1:
        suggested = max(3, int(math.sqrt(total_blocks) / 4))
        return max(2, min(requested, suggested))
    return max(2, requested)


def global_theme_model_path(analytics_dir: Path) -> Path:
    return analytics_dir / "global" / GLOBAL_THEME_MODEL_FILENAME


def save_theme_model(model: ThemeModel, path: Path) -> None:
    import pickle

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_theme_model(path: Path) -> ThemeModel:
    import pickle

    with path.open("rb") as f:
        return pickle.load(f)


def canonical_topic_labels(model: ThemeModel) -> list[str]:
    """Semantic label column for each global-model topic; when pinned, keep T0…T(K-1) order."""
    if getattr(model, "pinned_labels", None) and len(model.pinned_labels) >= model.num_topics:
        labels = [model.pinned_labels[i] for i in range(model.num_topics)]
    else:
        if not model._label_cache:
            model.assign_unique_labels()
        labels = []
        seen: set[str] = set()
        for tid in range(model.num_topics):
            lab = model.topic_label(tid)
            if lab not in seen:
                labels.append(lab)
                seen.add(lab)
    if FALLBACK_LABEL in labels:
        labels = [lab for lab in labels if lab != FALLBACK_LABEL] + [FALLBACK_LABEL]
    return labels


def global_topic_label_entries(model: ThemeModel) -> list[dict]:
    """Global column definitions for theme_patterns.json (by semantic label, not T0/T1 slots)."""
    canonical = canonical_topic_labels(model)
    label_kw: dict[str, list[str]] = {}
    for tid in range(model.num_topics):
        lab = model.topic_label(tid)
        if lab not in label_kw:
            words = model.topic_words.get(tid, [])
            label_kw[lab] = [w for w, _ in words[:10]]
    return [
        {"topic_id": i, "label": lab, "keywords": label_kw.get(lab, [])}
        for i, lab in enumerate(canonical)
    ]


def train_theme_model(
    plays: list[dict],
    num_topics: int = 8,
    random_seed: int = 42,
) -> ThemeModel:
    """Train a topic model.

    - Full corpus (>10 plays): theme.json-anchored keyword clustering; stable T0–T7 semantics and distinguishable heatmaps.
    - Single play / small sample: NMF (falls back to keyword on failure).
    """
    num_topics = adaptive_num_topics(plays, num_topics)
    if len(plays) > 10:
        model = _train_global_keyword_model(plays, num_topics, random_seed)
    else:
        try:
            model = _train_nmf_model(plays, num_topics, random_seed)
        except ImportError:
            model = _train_keyword_model(plays, num_topics, random_seed)
        except (ValueError, FloatingPointError):
            model = _train_keyword_model(plays, num_topics, random_seed)
    if not model.pinned_labels:
        model.assign_unique_labels()
    elif not model._label_cache:
        model._label_cache = dict(model.pinned_labels)
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
    max_df = 0.82 if len(plays) > 10 else 0.9

    vectorizer = TfidfVectorizer(
        max_df=max_df,
        min_df=min_df,
        max_features=5000,
        sublinear_tf=True,
        norm="l2",
        token_pattern=r"(?u)\b\w+\b",
    )
    X = vectorizer.fit_transform(docs)
    if X.shape[1] < num_topics:
        return _train_keyword_model(plays, num_topics, random_seed)

    feature_names = list(vectorizer.get_feature_names_out())
    use_seeded = len(plays) > 10
    seeds = _global_seed_topics(num_topics) if use_seeded else []

    nmf = NMF(
        n_components=num_topics,
        random_state=random_seed,
        max_iter=400 if use_seeded else 300,
        init="custom" if use_seeded else "nndsvd",
        solver="cd",
        beta_loss="frobenius",
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            if use_seeded:
                H_init = _build_h_init(feature_names, seeds, num_topics, random_seed)
                W_init = np.random.RandomState(random_seed).uniform(
                    0.05, 0.15, (X.shape[0], num_topics)
                )
                W = nmf.fit_transform(X, W=W_init, H=H_init)
            else:
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
    model.feature_names = feature_names
    if use_seeded:
        model.corpus_stopwords = build_corpus_stopwords(plays)
        model.pinned_labels = {i: seeds[i][0] for i in range(min(num_topics, len(seeds)))}
        model._label_cache = dict(model.pinned_labels)

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
    """Derive (label, seed_words) from theme.json — seeds for the keyword model."""
    rules, _, _, _ = _load_label_rules()
    if not rules:
        return [("通用主题", ["主公", "将军", "出兵", "回朝"])]
    out: list[tuple[str, list[str]]] = []
    for rule in rules:
        seeds = sorted(rule.keywords.keys(), key=lambda w: -rule.keywords[w])[:12]
        if seeds:
            out.append((rule.label, seeds))
    return out


def _global_seed_topics(num_topics: int) -> list[tuple[str, list[str]]]:
    """K corpus NMF anchor topic seeds (fixed order = T0…T(K-1))."""
    rules, _, _, _ = _load_label_rules()
    by_label = {r.label: r for r in rules}
    out: list[tuple[str, list[str]]] = []
    for lab in GLOBAL_SEED_LABELS:
        rule = by_label.get(lab)
        if not rule:
            continue
        seeds = sorted(rule.keywords.keys(), key=lambda w: -rule.keywords[w])[:12]
        if seeds:
            out.append((lab, seeds))
        if len(out) >= num_topics:
            break
    if len(out) < num_topics:
        for rule in rules:
            if rule.label in {x[0] for x in out}:
                continue
            seeds = sorted(rule.keywords.keys(), key=lambda w: -rule.keywords[w])[:12]
            if seeds:
                out.append((rule.label, seeds))
            if len(out) >= num_topics:
                break
    return out[:num_topics]


def _build_h_init(
    feature_names: list[str],
    seeds: list[tuple[str, list[str]]],
    num_topics: int,
    random_seed: int,
):
    import numpy as np

    n_features = len(feature_names)
    idx = {f: i for i, f in enumerate(feature_names)}
    H = np.random.RandomState(random_seed).uniform(0.05, 0.12, (num_topics, n_features))
    for tid, (_label, words) in enumerate(seeds[:num_topics]):
        for rank, w in enumerate(words):
            j = idx.get(w)
            if j is not None:
                H[tid, j] = 4.0 + (len(words) - rank) * 0.4
    return H


def train_global_theme_model_from_paths(
    play_paths: list[Path],
    num_topics: int = 8,
    random_seed: int = 42,
    load_play_fn=None,
    on_progress=None,
) -> ThemeModel:
    """Corpus-wide theme model (seconds): theme.json seeds + streaming character stopwords; no full-corpus block scan."""
    from datetime import datetime, timezone

    if load_play_fn is None:
        from ..utils.io import load_play as load_play_fn

    print(f"  collecting corpus character/title stopwords ({len(play_paths)} plays)…", flush=True)
    corpus_stop = build_corpus_stopwords_from_paths(
        play_paths, load_play_fn, on_progress=on_progress
    )
    print(f"  {len(corpus_stop)} stopwords, assembling {num_topics} topic seeds…", flush=True)

    seeds = _global_seed_topics(num_topics)
    if not seeds:
        seeds = _seed_topics_from_theme_rules()[:num_topics] or [
            ("通用主题", ["主公", "将军", "出兵", "回朝"])
        ]

    model = ThemeModel(num_topics=len(seeds), random_seed=random_seed)
    model.trained_at = datetime.now(timezone.utc).isoformat()
    model.method = "global_keyword"
    model.corpus_stopwords = corpus_stop
    model.pinned_labels = {i: seeds[i][0] for i in range(len(seeds))}
    model._label_cache = dict(model.pinned_labels)
    for tid, (_label, seed_words) in enumerate(seeds):
        kws = list(seed_words)[:15]
        model.topic_words[tid] = [
            (w, float(len(kws) - i)) for i, w in enumerate(kws)
        ]
    model._vectorizer = seeds
    model._nmf = None
    return model


def _train_global_keyword_model(
    plays: list[dict], num_topics: int, random_seed: int
) -> ThemeModel:
    """Compatibility entry: when a play list exists, still use fast path (metadata only, no block tokenization)."""
    from datetime import datetime, timezone

    seeds = _global_seed_topics(num_topics)
    if not seeds:
        seeds = _seed_topics_from_theme_rules()[:num_topics] or [
            ("通用主题", ["主公", "将军", "出兵", "回朝"])
        ]
    model = ThemeModel(num_topics=len(seeds), random_seed=random_seed)
    model.trained_at = datetime.now(timezone.utc).isoformat()
    model.method = "global_keyword"
    model.corpus_stopwords = build_corpus_stopwords(plays)
    model.pinned_labels = {i: seeds[i][0] for i in range(len(seeds))}
    model._label_cache = dict(model.pinned_labels)
    for tid, (_label, seed_words) in enumerate(seeds):
        kws = list(seed_words)[:15]
        model.topic_words[tid] = [
            (w, float(len(kws) - i)) for i, w in enumerate(kws)
        ]
    model._vectorizer = seeds
    model._nmf = None
    return model


def _train_keyword_model(
    plays: list[dict], num_topics: int, random_seed: int
) -> ThemeModel:
    from collections import Counter
    from datetime import datetime, timezone

    model = ThemeModel(num_topics=num_topics, random_seed=random_seed)
    model.trained_at = datetime.now(timezone.utc).isoformat()
    model.method = "keyword"

    if len(plays) > 10:
        seeds = _global_seed_topics(num_topics)
        model.corpus_stopwords = build_corpus_stopwords(plays)
    else:
        seeds = _seed_topics_from_theme_rules()[:num_topics]
    if not seeds:
        seeds = _seed_topics_from_theme_rules()[:num_topics] or [("通用主题", ["主公", "将军"])]
    model.num_topics = len(seeds)
    if len(plays) > 10:
        model.pinned_labels = {i: seeds[i][0] for i in range(len(seeds))}
        model._label_cache = dict(model.pinned_labels)
    corpus_words: Counter[str] = Counter()
    topic_counters: list[Counter[str]] = [Counter() for _ in seeds]

    for play in plays:
        extra_stop = build_dynamic_stopwords(play) | model.corpus_stopwords
        for b in iter_text_blocks(play):
            words = tokenize(b["text"], extra_stop)
            corpus_words.update(words)
            scores = _topic_seed_scores(words, seeds)
            tid = max(range(len(scores)), key=lambda i: scores[i])
            if scores[tid] <= 0:
                continue
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
    corpus_stop = build_corpus_stopwords(plays)
    docs: list[str] = []
    for play in plays:
        extra_stop = build_dynamic_stopwords(play) | corpus_stop
        blocks = iter_text_blocks(play)
        for b in blocks:
            tok = tokenize(b["text"], extra_stop)
            docs.append(" ".join(tok) if tok else b["text"][:80])
        if not blocks:
            doc = play_document(play)
            if doc:
                docs.append(" ".join(tokenize(doc, extra_stop)))
    return docs


def _topic_seed_scores(
    words: list[str], seeds: list[tuple[str, list[str]]]
) -> list[float]:
    """Score topic seeds by theme.json weights (shared by global/keyword models)."""
    rules, _, _, _ = _load_label_rules()
    by_label = {r.label: r for r in rules}
    scores: list[float] = []
    for label, seed in seeds:
        rule = by_label.get(label)
        if rule:
            s, _ = _score_label_fuzzy(rule, words)
            scores.append(s)
        else:
            scores.append(_seed_score(words, seed))
    return scores


def _seed_score(words: list[str], seed: list[str]) -> float:
    text = "".join(words)
    return sum(1.0 for s in seed if s in text)
