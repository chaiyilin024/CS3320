from __future__ import annotations

import re

from .noise import is_noise_line, is_page_header_line, strip_inline_noise

PAGE_NOISE_RE = re.compile(
    r"^(第\s*\d+\s*页|\d+|[\-—]\s*\d+\s*[\-—]|共\s*\d+\s*页)$"
)
# 下一行以（白）（念）等开头 — 承上对白，不可与上一行合并
PERF_CUE_LINE_START_RE = re.compile(
    r"^[（(](白|念|唱|笑|引子|叫头|垛|板)[）)]\s+"
)


def normalize_full_text(full_text: str) -> list[str]:
    """全文 → 清洗后的行列表。"""
    text = full_text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw in text.split("\n"):
        line = strip_inline_noise(raw.strip())
        if not line:
            continue
        if PAGE_NOISE_RE.match(line):
            continue
        if is_noise_line(line) or is_page_header_line(line):
            continue
        lines.append(line)

    merged: list[str] = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue
        prev = merged[-1]
        if _should_merge(prev, line):
            merged[-1] = prev + line
        else:
            merged.append(line)
    return merged


def _should_merge(prev: str, curr: str) -> bool:
    if _is_structural_line(curr) or _is_structural_line(prev):
        return False
    if is_page_header_line(prev) or is_page_header_line(curr):
        return False
    if prev.endswith(("。", "！", "？", "；", "」", "】", "：", "，", ",")):
        return False
    if curr.startswith(("（", "(")) and re.search(
        r"^[（(](西皮|二黄|流水|摇板|散板|垛板|明堂)", curr
    ):
        return False
    if re.match(r"^[\u4e00-\u9fff·]{2,4}\s+[（(]", curr):
        return False
    if re.search(r"…+$", prev) and re.match(r"^[\u4e00-\u9fff·]{2,4}\s+[（(]", curr):
        return False
    if PERF_CUE_LINE_START_RE.match(curr):
        return False
    if re.search(r"…", prev) and curr.startswith(("（", "(")):
        return False
    if len(prev) > 80:
        return False
    return True


def _is_structural_line(line: str) -> bool:
    if re.match(r"^第[零一二三四五六七八九十百千〇两\d]+[场幕折出]", line):
        return True
    if re.match(r"^[\(（].+[\)）]$", line) and "：" not in line and ":" not in line:
        return True
    if re.match(r"^[^：:]{1,8}[：:]", line):
        return True
    if line.startswith("【") and line.endswith("】"):
        return True
    if line.startswith("人物") or line.startswith("角色"):
        return True
    if line in ("情节", "注释") or line.startswith(("情节", "注释")):
        return True
    return False
