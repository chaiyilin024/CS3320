from __future__ import annotations

import re

# Peking opera genre classification rules (more precise keywords → more stable matching)
GENRE_RULES: list[tuple[str, list[str]]] = [
    # Historical drama (major events, dynastic rise/fall, famous ministers/generals)
    ("历史剧", [
        "三国", "汉", "唐", "宋", "明", "清", "秦", "隋", "元",
        "始皇", "项羽", "刘邦", "曹操", "刘备", "诸葛亮", "关羽", "张飞",
        "周瑜", "吕布", "李世民", "武则天", "赵匡胤", "岳飞", "朱元璋",
        "康熙", "乾隆", "雍正", "杨家将", "薛仁贵", "成吉思汗"
    ]),
    
    # Court cases, criminal justice, upright officials
    ("公案剧", [
        "判案", "衙门", "包公", "包拯", "包拯", "展昭", "王朝", "马汉",
        "状告", "升堂", "断案", "冤案", "刑狱", "清官", "海瑞", "狄仁杰"
    ]),
    
    # Immortals, demons, fantasy, heaven/underworld
    ("神话剧", [
        "天庭", "神仙", "玉帝", "孙悟空", "哪吒", "妖魔", "妖怪",
        "龙王", "观音", "如来", "地府", "阎罗", "八仙", "二郎神", "牛魔王"
    ]),
    
    # Love, marriage, longing, joy and sorrow
    ("爱情剧", [
        "情", "婚", "娶", "嫁", "相思", "恩爱", "离别", "佳人",
        "才子", "洞房", "鸳鸯", "西厢", "牡丹亭", "断桥", "白蛇"
    ]),
    
    # Family ethics: mother/son, filial piety, in-laws, clans
    ("家庭剧", [
        "家", "母", "子", "孝", "婆媳", "父子", "兄弟", "亲情",
        "家规", "宗族", "慈母", "孝子", "团圆", "分家"
    ]),
    
    # Chivalry / martial heroes (outlaws, knights-errant, rob the rich to aid the poor)
    ("侠义剧", [
        "侠", "义", "盗", "劫", "绿林", "好汉", "武松", "林冲", "鲁智深",
        "江湖", "剑客", "刀客", "忠义", "除暴", "安良"
    ]),
]

# Peking opera dynasty/era background rules (precise era matching)
ERA_RULES: list[tuple[str, list[str]]] = [
    ("清代", [
        "清朝", "康熙", "乾隆", "雍正", "慈禧", "李鸿章",
        "曾国藩", "和珅"
    ]),
    ("明代", [
        "明朝", "朱元璋", "洪武", "朱棣", "崇祯", "海瑞",
        "戚继光", "郑成功"
    ]),
    ("元代", ["元朝", "成吉思汗", "忽必烈"]),
    ("宋代", [
        "北宋", "南宋", "赵匡胤", "岳飞", "杨家将", "包拯",
        "包公", "林冲", "武松", "鲁智深"
    ]),
    ("唐代", [
        "唐朝", "李世民", "唐太宗", "武则天", "杨贵妃",
        "狄仁杰", "秦琼", "尉迟恭", "薛仁贵"
    ]),
    ("三国", [
        "三国", "刘备", "关羽", "张飞", "曹操", "周瑜", "诸葛亮",
        "赵云", "马超", "黄忠", "吕布", "貂蝉", "司马懿"
    ]),
    ("汉代", ["西汉", "东汉", "刘邦", "项羽", "韩信", "张良", "萧何"]),
    ("秦代", ["始皇", "嬴政", "李斯", "蒙恬"]),
    # Ancient / no explicit dynasty (myth, fiction)
    ("神话", ["神仙", "天庭", "妖魔", "八仙", "白蛇", "哪吒"])
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
