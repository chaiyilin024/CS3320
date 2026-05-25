"""从 cleaned/plays/{id}.json 的 blocks/scenes 中抽取人物扩展特征。

输出写入 role.json 的 characters[].traits_derived，结构对齐 schemas/common
definitions.schema.json#/$defs/traits（gender / age / identity / personality / performance_cues）。

策略：纯规则。所有线索仅来自台词文本与上下文，不引入历史人物姓名先验。
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

# 自称代词 → 性别 / 身份倾向
SELF_REF_MALE_HIGH = {"孤", "朕", "寡人", "本王", "本帅", "本督", "本将"}
SELF_REF_FEMALE = {"奴", "妾", "奴家", "哀家", "妾身", "本宫"}
SELF_REF_HUMBLE = {"俺", "咱", "在下", "末将", "小生", "小弟", "微臣", "为臣", "为兄", "为弟"}

# 第二人称 → 对方身份线索
ADDRESS_TO_RULER = {"主公", "王爷", "千岁", "万岁", "圣上", "陛下", "皇上", "大王"}
ADDRESS_TO_GENERAL = {"将军", "都督", "元帅", "大将军"}
ADDRESS_TO_ADVISOR = {"先生", "军师", "丞相", "国师", "大夫"}
ADDRESS_TO_BROTHER = {"大哥", "二哥", "三弟", "四弟", "贤弟", "兄长", "皇兄", "皇叔"}
ADDRESS_TO_FEMALE = {"夫人", "娘娘", "小姐", "公主", "妃子", "贵妃", "太后"}
ADDRESS_TO_ELDER = {"老爷", "老将军", "老大人", "老相国"}
ADDRESS_TO_YOUTH = {"小将", "小生", "公子", "少爷"}

# 身份关键字
IDENTITY_KEYWORDS = {
    "君主": ["皇上", "万岁", "孤王", "寡人", "朕", "主公", "圣上"],
    "将领": ["大将军", "元帅", "都督", "将军", "末将", "本帅", "本督"],
    "谋士": ["军师", "丞相", "先生", "国师", "孔明"],
    "妃后": ["娘娘", "贵妃", "太后", "皇后", "妾身"],
    "公子": ["公子", "少爷", "小生"],
    "弟兄": ["三弟", "四弟", "贤弟", "皇兄", "皇叔", "结拜"],
    "兵卒": ["小卒", "兵卒", "马夫"],
    "书生": ["秀才", "举人", "寒儒"],
}

# 年龄词
AGE_OLD = {"老将", "老臣", "老朽", "老身", "白发", "苍老", "古稀"}
AGE_YOUNG = {"小将", "小生", "少年", "少将", "孩儿", "孺子"}

# 性格词
PERSONALITY_KEYWORDS = {
    "勇猛": ["勇猛", "厉害", "杀气", "猛虎", "勇冠", "敢死"],
    "智谋": ["妙计", "智谋", "巧计", "谋略", "高见", "妙策"],
    "忠义": ["忠心", "为臣", "尽忠", "义气", "忠义"],
    "刚烈": ["大怒", "怒喝", "怒目", "厉声", "拍案"],
    "诙谐": ["哈哈", "哈哈哈", "笑曰", "戏言"],
    "稳重": ["且慢", "三思", "慎重", "稳妥"],
}


def extract_traits(play: dict) -> dict[str, dict]:
    """返回 {character_id: traits_derived}。"""
    blocks = play.get("blocks") or []
    chars = play.get("characters") or []

    own_lines = _group_lines_by_speaker(blocks)
    addressed = _detect_addressed_terms(blocks, chars)

    out: dict[str, dict] = {}
    for ch in chars:
        cid = ch["character_id"]
        own_text = " ".join(own_lines.get(cid, []))
        addr_terms = addressed.get(cid, Counter())

        gender = _infer_gender(own_text, addr_terms)
        identity = _infer_identity(own_text, addr_terms)
        age = _infer_age(own_text, addr_terms, ch.get("line_count") or 0)
        personality = _infer_personality(own_text)
        cues = list((ch.get("traits") or {}).get("performance_cues") or [])

        derived: dict = {}
        if gender != "未知":
            derived["gender"] = gender
        if identity:
            derived["identity"] = identity
        if age:
            derived["age"] = age
        if personality:
            derived["personality"] = personality
        if cues:
            derived["performance_cues"] = cues
        if derived:
            out[cid] = derived
    return out


def _group_lines_by_speaker(blocks: Iterable[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for b in blocks:
        sp = b.get("speaker_id")
        if not sp:
            continue
        if b.get("type") not in ("dialogue", "aria", "recitation"):
            continue
        t = (b.get("text") or "").strip()
        if not t:
            continue
        out.setdefault(sp, []).append(t)
    return out


def _detect_addressed_terms(
    blocks: list[dict], chars: list[dict]
) -> dict[str, Counter[str]]:
    """根据"上一句的说话人对当前未指明对象使用了称呼"近似抓被称呼词。

    简化：对每条 dialogue/aria，若文本中出现某个 ADDRESS_* 词，
    则把它累计到「同一场内的其他主要角色」（即可能的被称呼者）。
    """
    main_ids = [c["character_id"] for c in chars]

    address_pool = (
        ADDRESS_TO_RULER
        | ADDRESS_TO_GENERAL
        | ADDRESS_TO_ADVISOR
        | ADDRESS_TO_BROTHER
        | ADDRESS_TO_FEMALE
        | ADDRESS_TO_ELDER
        | ADDRESS_TO_YOUTH
    )

    out: dict[str, Counter[str]] = {cid: Counter() for cid in main_ids}
    for i, b in enumerate(blocks):
        if b.get("type") not in ("dialogue", "aria", "recitation"):
            continue
        speaker = b.get("speaker_id")
        text = b.get("text") or ""
        if not text:
            continue
        hits = [w for w in address_pool if w in text]
        if not hits:
            continue
        # 同一段对话的下一个/上一个不同 speaker 视为受话人
        receiver_ids: set[str] = set()
        for j in range(max(0, i - 2), min(len(blocks), i + 3)):
            if j == i:
                continue
            other = blocks[j].get("speaker_id")
            if other and other != speaker:
                receiver_ids.add(other)
        if not receiver_ids:
            continue
        for cid in receiver_ids:
            if cid in out:
                for h in hits:
                    out[cid][h] += 1
    return out


def _infer_gender(own_text: str, addr_terms: Counter[str]) -> str:
    if any(w in own_text for w in SELF_REF_FEMALE):
        return "女"
    if any(w in own_text for w in SELF_REF_MALE_HIGH):
        return "男"
    if any(w in own_text for w in SELF_REF_HUMBLE):
        return "男"
    if any(t in ADDRESS_TO_FEMALE for t in addr_terms):
        return "女"
    if any(t in (ADDRESS_TO_RULER | ADDRESS_TO_GENERAL | ADDRESS_TO_BROTHER) for t in addr_terms):
        return "男"
    return "未知"


def _infer_identity(own_text: str, addr_terms: Counter[str]) -> str | None:
    scores: Counter[str] = Counter()
    # 自称/禀报语境
    if "父王" in own_text or "参见父王" in own_text:
        scores["公子"] += 2
    if own_text.startswith("启") and any(
        w in own_text for w in ADDRESS_TO_GENERAL | ADDRESS_TO_RULER
    ):
        scores["将领"] += 2
    for ident, keys in IDENTITY_KEYWORDS.items():
        scores[ident] += sum(1 for k in keys if k in own_text)
    for term in addr_terms:
        if term in ADDRESS_TO_RULER:
            scores["君主"] += addr_terms[term]
        elif term in ADDRESS_TO_GENERAL:
            scores["将领"] += addr_terms[term]
        elif term in ADDRESS_TO_ADVISOR:
            scores["谋士"] += addr_terms[term]
        elif term in ADDRESS_TO_FEMALE:
            scores["妃后"] += addr_terms[term]
        elif term in ADDRESS_TO_YOUTH:
            scores["公子"] += addr_terms[term]
        elif term in ADDRESS_TO_BROTHER:
            scores["弟兄"] += addr_terms[term]
    if not scores:
        return None
    top, count = scores.most_common(1)[0]
    return top if count > 0 else None


def _infer_age(own_text: str, addr_terms: Counter[str], line_count: int) -> str | None:
    if any(w in own_text for w in AGE_OLD):
        return "老年"
    if any(t in ADDRESS_TO_ELDER for t in addr_terms):
        return "老年"
    if any(w in own_text for w in AGE_YOUNG):
        return "少年"
    if any(t in ADDRESS_TO_YOUTH for t in addr_terms):
        return "少年"
    return None


def _infer_personality(own_text: str) -> list[str]:
    hits = []
    for tag, keys in PERSONALITY_KEYWORDS.items():
        if any(k in own_text for k in keys):
            hits.append(tag)
    return hits[:3]
