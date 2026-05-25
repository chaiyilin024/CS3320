from __future__ import annotations

from dataclasses import dataclass, field

from .corpus import build_dynamic_stopwords, iter_text_blocks, play_document, tokenize

# (种子词, label) — 全词命中权重 1，子串命中权重 0.5，叠加 ≥ THRESHOLD 才赋名
LABEL_RULES: list[tuple[list[str], str]] = [
    (["忠心", "为臣", "君臣", "万岁", "圣上", "保驾", "尽忠", "义气", "忠义"], "忠义君臣"),
    (["厮杀", "破敌", "曹兵", "出兵", "鏖兵", "杀敌", "战事"], "战争厮杀"),
    (["妙计", "谋略", "中计", "识破", "调遣", "差遣", "巧计", "奸计", "命箭", "令箭"], "计策调度"),
    (["锦囊", "出宝", "竹节", "八卦", "暗有", "埋伏", "无虚", "打开", "妙策"], "锦囊设防"),
    (["回朝", "进宫", "退朝", "上朝", "朝堂", "金殿", "圣旨", "面奏"], "宫廷议政"),
    (["拜见", "参见", "少礼", "恭迎", "失敬", "请坐", "有请", "免礼"], "礼仪问答"),
    (["佳人", "良缘", "婚配", "夫妻", "妻房", "姻缘", "情深", "爱慕"], "情感姻缘"),
    (["饮宴", "宴尝", "把盏", "酒席", "举杯", "赴宴"], "宴饮场面"),
    (["怒喝", "怒目", "羞恼", "争执", "厉声", "动怒", "拍案"], "冲突怒斥"),
    (["哈哈", "嬉笑", "戏言", "恭喜", "诙谐", "玩笑"], "喜庆诙谐"),
    (["天意", "天命", "神明", "龙颜", "苍天", "上苍"], "神话天命"),
    (["过江", "登程", "出使", "迎接", "护送", "起兵", "回营", "下楼", "上路"], "出使行程"),
    (["保驾", "护驾", "前去", "护卫", "无妨", "敢死", "防备", "防计"], "护驾防计"),
    (["结拜", "义气", "手足", "兄长", "贤弟", "结义"], "兄弟情义"),
]
# label 命中阈值：全词得 1.0，子串得 0.5；总分 ≥ THRESHOLD 赋名
LABEL_HIT_THRESHOLD = 1.0


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
        """全局算一次：全词命中 1.0 + 子串命中 0.5，总分 ≥ THRESHOLD 才赋 LABEL；
        同名时追加判别关键词后缀。命中失败时 fallback 用 top-2 keyword 拼接。"""
        raw: dict[int, str] = {}
        for tid in range(self.num_topics):
            words = [w for w, _ in self.topic_words.get(tid, [])[:15]]
            word_set = set(words)
            text_join = "".join(words)
            best_label, best_score = None, 0.0
            for seeds, lab in LABEL_RULES:
                whole = sum(1 for s in seeds if s in word_set)
                substr = sum(
                    0.5 for s in seeds if s not in word_set and s in text_join
                )
                score = whole + substr
                if score > best_score:
                    best_label, best_score = lab, score
            if best_label and best_score >= LABEL_HIT_THRESHOLD:
                raw[tid] = best_label
            else:
                # fallback: 用前两个长度 >=2 的 keyword 拼接，比单词更有信息量
                informative = [w for w in words if len(w) >= 2][:2]
                if len(informative) >= 2:
                    raw[tid] = f"{informative[0]}·{informative[1]}"
                elif informative:
                    raw[tid] = informative[0][:6]
                else:
                    raw[tid] = f"主题{tid}"

        seen: dict[str, list[int]] = {}
        for tid, lab in raw.items():
            seen.setdefault(lab, []).append(tid)
        final: dict[int, str] = {}
        all_seed_words = {s for seeds, _ in LABEL_RULES for s in seeds}
        for lab, tids in seen.items():
            if len(tids) == 1:
                final[tids[0]] = lab
                continue
            for tid in tids:
                words = [w for w, _ in self.topic_words.get(tid, [])[:6]]
                discriminator = next(
                    (w for w in words if w not in all_seed_words and len(w) >= 2),
                    words[0] if words else "",
                )
                final[tid] = f"{lab}·{discriminator}" if discriminator else f"{lab}#{tid}"
        self._label_cache = final

    def topic_label(self, topic_id: int) -> str:
        if not self._label_cache:
            self.assign_unique_labels()
        if topic_id in self._label_cache:
            return self._label_cache[topic_id]
        words = [w for w, _ in self.topic_words.get(topic_id, [])[:12]]
        for keys, label in LABEL_RULES:
            if any(k in "".join(words) for k in keys):
                return label
        if words:
            return words[0][:6]
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
    ("忠义君臣", ["忠", "义", "臣", "君臣", "万岁", "圣上", "保驾"]),
    ("战争厮杀", ["战", "兵", "杀", "敌", "营", "阵", "厮杀", "破敌"]),
    ("计策调度", ["计", "谋", "智", "破", "中计", "令箭", "调兵", "差遣"]),
    ("宫廷议政", ["朝", "殿", "议", "奏", "旨", "回朝", "进宫"]),
    ("礼仪问答", ["请", "拜见", "失敬", "恭迎"]),
    ("情感姻缘", ["情", "爱", "妻", "郎", "婚", "佳人"]),
    ("宴饮场面", ["酒", "宴", "楼", "席", "杯", "饮宴"]),
    ("冲突怒斥", ["怒", "恨", "骂", "吓", "羞恼"]),
    ("喜庆诙谐", ["笑", "喜", "贺", "恭喜"]),
    ("神话天命", ["天", "神", "仙", "龙", "命", "天意"]),
    ("行旅行程", ["行", "路", "走", "过江", "船", "登程"]),
    ("兄弟情义", ["兄", "弟", "结拜", "义气", "手足"]),
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
        extra_stop = build_dynamic_stopwords(play)
        for b in iter_text_blocks(play):
            words = tokenize(b["text"], extra_stop)
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
