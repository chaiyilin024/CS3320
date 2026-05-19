from __future__ import annotations

from dataclasses import dataclass, field

from .corpus import iter_text_blocks, play_document, tokenize

LABEL_RULES: list[tuple[list[str], str]] = [
    (["忠", "义", "臣", "主公", "万岁"], "忠义君臣"),
    (["战", "兵", "杀", "江", "营", "阵", "敌"], "战争谋略"),
    (["情", "爱", "婚", "妻", "郎"], "情感姻缘"),
    (["酒", "宴", "楼", "席"], "宴饮场面"),
    (["怒", "恨", "骂", "恨"], "冲突怒斥"),
    (["笑", "喜", "贺", "恭喜"], "喜庆诙谐"),
    (["天", "神", "仙", "龙"], "神话天命"),
    (["走", "行", "路", "过"], "行旅行程"),
]


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

    def transform_blocks(self, play: dict) -> list[tuple[str, int, str, list[float]]]:
        """返回 (block_id, block_index, text, topic_vector)。"""
        blocks = iter_text_blocks(play)
        if not blocks:
            return []
        if self.method == "keyword" and isinstance(self._vectorizer, list):
            seeds = self._vectorizer
            out = []
            for b in blocks:
                words = tokenize(b["text"])
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

        docs = [" ".join(tokenize(b["text"])) for b in blocks]
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

    def topic_label(self, topic_id: int) -> str:
        words = [w for w, _ in self.topic_words.get(topic_id, [])[:12]]
        for keys, label in LABEL_RULES:
            if any(k in "".join(words) for k in keys):
                return label
        if words:
            return words[0][:6]
        return f"主题{topic_id}"


def train_theme_model(
    plays: list[dict],
    num_topics: int = 8,
    random_seed: int = 42,
) -> ThemeModel:
    try:
        return _train_nmf_model(plays, num_topics, random_seed)
    except ImportError:
        return _train_keyword_model(plays, num_topics, random_seed)
    except (ValueError, FloatingPointError):
        return _train_keyword_model(plays, num_topics, random_seed)


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
        top_idx = row.argsort()[::-1][:20]
        model.topic_words[tid] = [
            (model.feature_names[i], float(row[i]))
            for i in top_idx
            if row[i] > 0 and np.isfinite(row[i])
        ]
    if not any(model.topic_words.values()):
        return _train_keyword_model(plays, num_topics, random_seed)
    return model


SEED_TOPICS: list[tuple[str, list[str]]] = [
    ("忠义君臣", ["忠", "义", "臣", "主公", "万岁", "皇上", "圣"]),
    ("战争谋略", ["战", "兵", "杀", "江", "敌", "营", "阵", "军"]),
    ("宴饮场面", ["酒", "宴", "楼", "席", "杯"]),
    ("冲突怒斥", ["怒", "恨", "骂", "吓", "恨"]),
    ("喜庆诙谐", ["笑", "喜", "贺", "恭喜", "哈哈"]),
    ("情感姻缘", ["情", "爱", "妻", "郎", "婚"]),
    ("神话天命", ["天", "神", "仙", "龙", "命"]),
    ("行旅行程", ["行", "路", "走", "过", "船"]),
]


def _train_keyword_model(
    plays: list[dict], num_topics: int, random_seed: int
) -> ThemeModel:
    from collections import Counter
    from datetime import datetime, timezone

    model = ThemeModel(num_topics=num_topics, random_seed=random_seed)
    model.trained_at = datetime.now(timezone.utc).isoformat()
    model.method = "keyword"

    seeds = SEED_TOPICS[:num_topics]
    model.num_topics = len(seeds)
    corpus_words: Counter[str] = Counter()
    topic_counters: list[Counter[str]] = [Counter() for _ in seeds]

    for play in plays:
        for b in iter_text_blocks(play):
            words = tokenize(b["text"])
            corpus_words.update(words)
            scores = [_seed_score(words, seed) for _label, seed in seeds]
            tid = max(range(len(scores)), key=lambda i: scores[i])
            topic_counters[tid].update(words)

    for tid, (label, seed) in enumerate(seeds):
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
        for b in iter_text_blocks(play):
            tok = tokenize(b["text"])
            docs.append(" ".join(tok) if tok else b["text"][:80])
        if not iter_text_blocks(play):
            doc = play_document(play)
            if doc:
                docs.append(" ".join(tokenize(doc)))
    return docs


def _seed_score(words: list[str], seed: list[str]) -> float:
    text = "".join(words)
    return sum(1.0 for s in seed if s in text)
