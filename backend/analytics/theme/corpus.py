from __future__ import annotations

import re

TEXT_BLOCK_TYPES = frozenset({"dialogue", "aria", "recitation"})

# 戏曲常见虚词/拟声词/称呼语/低区分对白套话
STOPWORDS = frozenset(
    """
    的 了 在 是 我 你 他 她 它 这 那 有 与 及 而 也 就 都 还 又 之 其 此 所 因 但
    一个 一位 一场 一名 一人 二人 三人 同 下 上 内 外 中 来 去 到 把 被 让 给 对 从
    哈哈哈 哈哈 呵呵 呀 啊 哇 唉 哎 嗯 么 呢 吧 吗 哩 哟 嘿 嗨 嘞 噢 嘛
    参见 遵命 少礼 恕罪 休要 岂敢 为何 不知 何不 这般 那般 这里 那里 当面 进帐
    兄长 大人 哪里 看来 既是 倘若 既然 多少 一根 一边 一齐 一面
    便是 就是 还有 没有 不曾 怎么 如何 何故 怎敢 莫非 难道 已是 乃是
    本督 本帅 本将 本王 本宫 末将 在下 大胆
    先请 请进 请坐 起来 起身 落座 退下 启奏
    """.split()
)

# 京剧常见称呼 — 单独用作角色身份线索时由 traits_extract 提取，作为词袋特征时太通用，纳入停用
TITLE_STOPWORDS = frozenset(
    "皇叔 主公 都督 丞相 军师 元帅 王爷 千岁 万岁 圣上 公子 小姐 夫人 娘娘 老爷 太子 王子".split()
)


def build_dynamic_stopwords(play: dict | None) -> frozenset[str]:
    """从剧本动态构造停用词：角色名 + 别名 + 标题字。"""
    if not play:
        return frozenset()
    extra: set[str] = set()
    for ch in play.get("characters") or []:
        name = (ch.get("name") or "").strip()
        if name:
            extra.add(name)
            # 单字姓名（如「飞」「亮」）信息量低，加入；多字姓名整体加入
            for c in name:
                if "\u4e00" <= c <= "\u9fff":
                    extra.add(c)
        for alias in ch.get("aliases") or []:
            alias = (alias or "").strip()
            if alias:
                extra.add(alias)
    title = (play.get("title") or "").strip()
    if title:
        extra.add(title)
    for c in title:
        if "\u4e00" <= c <= "\u9fff":
            extra.add(c)
    return frozenset(w for w in extra if len(w) >= 1)


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


def tokenize(text: str, extra_stopwords: frozenset[str] | None = None) -> list[str]:
    extra = extra_stopwords or frozenset()
    try:
        from ..utils.jieba_env import ensure_jieba

        ensure_jieba()
        import jieba
    except ImportError:
        return _fallback_tokenize(text, extra)
    words = []
    for w in jieba.lcut(text):
        w = w.strip()
        if len(w) < 2:
            continue
        if w in STOPWORDS or w in TITLE_STOPWORDS or w in extra:
            continue
        if re.match(r"^[\W\d_]+$", w):
            continue
        words.append(w)
    return words


def _fallback_tokenize(text: str, extra: frozenset[str]) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    if words:
        return [
            w for w in words
            if w not in STOPWORDS and w not in TITLE_STOPWORDS and w not in extra
        ]
    return [
        c for c in text
        if "\u4e00" <= c <= "\u9fff"
        and c not in STOPWORDS
        and c not in TITLE_STOPWORDS
        and c not in extra
    ]
