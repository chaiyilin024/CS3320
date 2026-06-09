from __future__ import annotations

import re

URL_OR_SITE_RE = re.compile(
    r"(https?://|www\.|xikao\.com|scripts\.xikao|\.com/play/|\.cn/)",
    re.IGNORECASE,
)
DATE_FOOTER_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
INVALID_SPEAKER_RE = re.compile(
    r"^(https?|http|www|ftp|com|cn|org|play)$",
    re.IGNORECASE,
)
VALID_CHARACTER_NAME_RE = re.compile(r"^[\u4e00-\u9fff·]{2,4}$")

# Lyric/stage-direction fragments mis-parsed as "character names"
NAME_FRAGMENT_RE = re.compile(
    r"(言来|听端详|龙套|下场门|套同|排队|两边|催船|引.+同|同抄|同上场|白龙)"
)

# Non-name mood/structure words
NOT_A_PERSON = frozenset(
    {
        "正是",
        "哦",
        "呵",
        "呀",
        "唉",
        "罢",
        "哼",
        "嘎",
        "啊",
        "呃",
        "竹",
        "情节",
        "注释",
    }
)

# lyf: honorific phrases that must not become character names (e.g. "启禀丞相")
NON_NAME_PREFIXES = (
    "启禀",
    "参见",
    "启奏",
    "禀报",
    "参见",
    "他言"
)

HANGDANG_WORDS = frozenset(
    {
        "老生",
        "小生",
        "武生",
        "红生",
        "青衣",
        "花旦",
        "刀马旦",
        "老旦",
        "净",
        "丑",
        "文武丑",
    }
)


def is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if URL_OR_SITE_RE.search(s):
        return True
    if DATE_FOOTER_RE.search(s) and len(s) < 60 and "：" not in s and ":" not in s:
        if URL_OR_SITE_RE.search(s) or s.count("-") >= 2:
            return True
    if re.match(r"^https?://\S+$", s, re.IGNORECASE):
        return True
    return False


def is_valid_character_name(name: str) -> bool:
    """Valid Peking opera character name: 2–4 Han characters, not lyric/stage fragments."""
    n = name.strip()
    if not n or n in NOT_A_PERSON:
        return False
    if len(n) > 4 or len(n) < 2:
        return False
    if INVALID_SPEAKER_RE.match(n):
        return False
    if URL_OR_SITE_RE.search(n):
        return False
    if re.search(r"[A-Za-z]{2,}", n):
        return False
    if NAME_FRAGMENT_RE.search(n):
        return False
    if n.endswith("同") and n not in {"同人"}:
        return False
    # Exclude honorific phrases (e.g. "启禀丞相" must not be a character name)
    if any(n.startswith(prefix) for prefix in NON_NAME_PREFIXES):
        return False
    if not VALID_CHARACTER_NAME_RE.match(n):
        return False
    return True


def is_hangdang_word(text: str) -> bool:
    return text.strip() in HANGDANG_WORDS


# Xiqu PDF page header, e.g.: 中国京剧戏考 《黄鹤楼》 2
PAGE_HEADER_LINE_RE = re.compile(
    r"^中国京剧戏考\s*[《《]([^》》]+)[》》]\s*\d+\s*$"
)
PAGE_HEADER_PREFIX_RE = re.compile(
    r"^中国京剧戏考\s*[《《][^》》]+[》》]\s*\d+"
)
# Page number glued to title after header, e.g.: 1《黄鹤楼》
PAGE_HEADER_TITLE_TAIL_RE = re.compile(r"^《[^》》]{1,20}》\s*\d*")


def is_page_header_line(line: str) -> bool:
    s = line.strip()
    if PAGE_HEADER_LINE_RE.match(s):
        return True
    if re.match(r"^\d{1,3}$", s):
        return True
    return False


def strip_page_header_prefix(text: str) -> str:
    """Strip line-leading header; return empty string if the line is header-only."""
    s = text.strip()
    if is_page_header_line(s):
        return ""
    s = PAGE_HEADER_PREFIX_RE.sub("", s)
    s = PAGE_HEADER_TITLE_TAIL_RE.sub("", s, count=1)
    return s.strip()


def strip_inline_noise(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"scripts\.xikao\.com\S*", "", text, flags=re.IGNORECASE)
    return strip_page_header_prefix(text)