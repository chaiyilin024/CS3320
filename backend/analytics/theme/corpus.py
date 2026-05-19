from __future__ import annotations

import re

TEXT_BLOCK_TYPES = frozenset({"dialogue", "aria", "recitation"})

# 戏曲常见虚词/舞台词，作简易停用
STOPWORDS = frozenset(
    """
    的 了 在 是 我 你 他 她 它 这 那 有 与 及 而 也 就 都 还 又
    一个 一位 一场 同 下 上 内 外 中 来 去 到 把 被 让 给 对 从
    哈哈哈 哈哈 呵呵 呀 啊 哇 唉 哎 嗯 么 呢 吧 吗 哩 哟
    """.split()
)


def iter_text_blocks(play: dict) -> list[dict]:
    out = []
    for b in play.get("blocks") or []:
        if b.get("type") not in TEXT_BLOCK_TYPES:
            continue
        text = (b.get("text") or "").strip()
        if len(text) < 2:
            continue
        out.append(b)
    return out


def play_document(play: dict) -> str:
    return " ".join(b["text"] for b in iter_text_blocks(play))


def tokenize(text: str) -> list[str]:
    try:
        from ..utils.jieba_env import ensure_jieba

        ensure_jieba()
        import jieba
    except ImportError:
        return _fallback_tokenize(text)
    words = []
    for w in jieba.lcut(text):
        w = w.strip()
        if len(w) < 2:
            continue
        if w in STOPWORDS:
            continue
        if re.match(r"^[\W\d_]+$", w):
            continue
        words.append(w)
    return words


def _fallback_tokenize(text: str) -> list[str]:
    import re

    words = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    if words:
        return [w for w in words if w not in STOPWORDS]
    return [c for c in text if "\u4e00" <= c <= "\u9fff" and c not in STOPWORDS]
