from __future__ import annotations

import re

GENRE_RULES: list[tuple[str, list[str]]] = [
    ("历史剧", ["三国", "汉", "唐", "宋", "明", "清", "始皇", "项羽", "曹操", "诸葛亮", "岳飞"]),
    ("公案剧", ["判案", "衙门", "包公", "包拯", "状告", "升堂"]),
    ("神话剧", ["天庭", "神仙", "玉帝", "孙悟空", "哪吒", "妖魔"]),
    ("爱情剧", ["情", "婚", "娶", "嫁", "相思"]),
    ("战争剧", ["战", "兵", "征", "伐", "阵"]),
    ("家庭剧", ["家", "母", "子", "孝", "婆媳"]),
]

ERA_RULES: list[tuple[str, list[str]]] = [
    ("三国", ["三国", "刘备", "关羽", "张飞", "曹操", "周瑜", "诸葛亮"]),
    ("唐代", ["唐", "李世民", "杨贵妃"]),
    ("宋代", ["宋", "岳飞", "杨家将"]),
    ("明代", ["明", "朱元璋"]),
    ("清代", ["清", "康熙", "乾隆"]),
]


def infer_tags(title: str, text_sample: str) -> dict:
    blob = f"{title}\n{text_sample[:3000]}"
    tags: dict = {}

    genre_scores: dict[str, int] = {}
    for genre, kws in GENRE_RULES:
        score = sum(1 for k in kws if k in blob)
        if score:
            genre_scores[genre] = score
    if genre_scores:
        tags["genre_inferred"] = max(genre_scores, key=genre_scores.get)

    for era, kws in ERA_RULES:
        if any(k in blob for k in kws):
            tags["era_inferred"] = era
            break

    return tags
