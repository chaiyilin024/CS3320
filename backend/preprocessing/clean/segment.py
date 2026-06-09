from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..utils.ids import character_id
from .noise import is_hangdang_word, is_noise_line, is_valid_character_name

SCENE_RE = re.compile(
    r"^(第[零一二三四五六七八九十百千〇两\d]+[场幕折出]|【第[零一二三四五六七八九十百千〇两\d]+[场幕]】)"
)
DIALOGUE_RE = re.compile(
    r"^([^：:\s\(（]{1,12}?)(?:[（(]([^）)]+)[）)])?[：:](.*)$"
)
STAGE_ONLY_RE = re.compile(r"^[（(]([^）)]+)[）)]\s*$")
ARIA_MARK_RE = re.compile(r"【[^】]{2,30}】")
CHAR_LIST_HEADER_RE = re.compile(r"^(人物|角色|登场人物?|主要角色)[:：]?$")
CAST_SECTION_END_RE = re.compile(r"^(剧情|故事)")
PLOT_HEADER_RE = re.compile(r"^情节\s*(.*)$")
ANNOTATION_HEADER_RE = re.compile(r"^注释\s*(.*)$")
# Fine Peking opera hangdang → coarse category (full mapping)
COARSE_MAP = {
    # ========== sheng ==========
    "生": "生",
    "老生": "生",
    "小生": "生",
    "武生": "生",
    "红生": "生",
    "外": "生",
    "娃娃生": "生",
    "冠生": "生",
    "巾生": "生",
    "穷生": "生",
    "翎子生": "生",
    "袍带生": "生",
    "箭衣生": "生",
    "长靠武生": "生",
    "短打武生": "生",
    "把子生": "生",

    # ========== dan ==========
    "旦": "旦",
    "青衣": "旦",
    "花旦": "旦",
    "刀马旦": "旦",
    "武旦": "旦",
    "老旦": "旦",
    "彩旦": "旦",
    "闺门旦": "旦",
    "花衫": "旦",
    "泼辣旦": "旦",
    "刺杀旦": "旦",
    "贴旦": "旦",
    "正旦": "旦",
    "奴旦": "旦",
    "疯旦": "旦",

    # ========== jing ==========
    "净": "净",
    "正净": "净",
    "副净": "净",
    "武净": "净",
    "铜锤花脸": "净",
    "架子花脸": "净",
    "摔打花脸": "净",
    "黑净": "净",
    "白净": "净",
    "红净": "净",

    # ========== mo ==========
    "末": "末",
    "正末": "末",
    "副末": "末",
    "冲末": "末",
    "外末": "末",

    # ========== chou ==========
    "丑": "丑",
    "文丑": "丑",
    "武丑": "丑",
    "老丑": "丑",
    "文武丑": "丑",
    "茶衣丑": "丑",
    "袍带丑": "丑",
    "鞋皮丑": "丑",
    "方巾丑": "丑",
    "婆子丑": "丑",
    "小丑": "丑"
}

# Sort by length descending so longer terms match first
_HANGDANG_KEYS = "|".join(sorted(COARSE_MAP.keys(), key=len, reverse=True))

CAST_LINE_RE = re.compile(
    rf"^([\u4e00-\u9fff·]{{2,4}})[：:]\s*({_HANGDANG_KEYS})$")
# Liu Bei （白） 孤，刘备……
ROLE_ACTION_RE = re.compile(
    r"^([\u4e00-\u9fff·]{2,4})\s+[（(]([^）)]+)[）)]\s*(.*)$"
)
# （念） 日月重明…… — continuation from previous speaker, name omitted
CUE_CONTINUATION_RE = re.compile(r"^[（(]([^）)]+)[）)]\s+(.+)$")
# （西皮原板） 唱词…… — board-cue marker, starts an aria
BOARD_CUE_RE = re.compile(
    r"^[（(]([^）)]+)[）)]\s*(.*)$"
)
BOARD_CUE_LABEL_RE = re.compile(r"西皮|二黄|流水|摇板|散板|垛板|明堂|原板|慢板")
# First aria line (prefix before colon too long or not name-like)
ARIA_COLON_RE = re.compile(r"^([^：:]{2,40})[：:](.*)$")

PERFORMANCE_CUE_MAP = {
    "白": "念",
    "念": "念",
    "唱": "唱",
    "做": "做",
    "打": "打",
    "板": "念",
    "垛": "念",
    "引子": "念",
    "叫头": "念",
}
# Parentheses contain stage directions, not performance cues (not continuation dialogue)
STAGE_PAREN_HINTS = (
    "龙套",
    "同上",
    "同下",
    "上场",
    "下场",
    "分上",
    "入内",
    "引刘备",
    "引赵云",
    "同上场",
    "同下场",
    "套",
    "排队",
)

HANGDANG_PATTERN = re.compile(rf"({_HANGDANG_KEYS})")


@dataclass
class RawBlock:
    block_index: int
    type: str
    text: str
    speaker_name: str | None = None
    performance_tags: list[str] = field(default_factory=list)
    performance_cues_raw: list[str] = field(default_factory=list)
    page_no: int | None = None
    scene_index: int | None = None


@dataclass
class SegmentResult:
    blocks: list[RawBlock]
    character_hints: dict[str, dict]


def segment_lines(
    lines: list[str],
    page_boundaries: list[int] | None = None,
) -> SegmentResult:
    """Split line list into RawBlocks and collect character hints."""
    blocks: list[RawBlock] = []
    hints: dict[str, dict] = {}
    scene_index = 0
    in_cast_section = False
    in_plot_summary = False
    in_annotation = False
    last_speaker: str | None = None
    in_aria: bool = False
    last_aria_speaker: str | None = None
    idx = 0
    # Track "根据《戏考》" so the next line exits plot-summary mode
    pending_plot_exit = False

    for line_no, line in enumerate(lines):
        page_no = _page_for_line(line_no, page_boundaries)

        if SCENE_RE.match(line):
            in_cast_section = False
            in_plot_summary = False
            in_annotation = False
            in_aria = False

        m_plot = PLOT_HEADER_RE.match(line)
        if m_plot:
            in_cast_section = False
            in_plot_summary = True
            in_annotation = False
            body = m_plot.group(1).strip()
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="plot_summary",
                    text=body if body else "情节",
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        m_note = ANNOTATION_HEADER_RE.match(line)
        if m_note:
            in_cast_section = False
            in_plot_summary = False
            in_annotation = True
            body = m_note.group(1).strip()
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="annotation",
                    text=body if body else "注释",
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        if in_plot_summary:
            # If previous line was "根据《戏考》", exit plot-summary mode
            if pending_plot_exit:
                in_plot_summary = False
                pending_plot_exit = False
            else:
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type="plot_summary",
                        text=line,
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                idx += 1
                # If line contains "根据《戏考》", flag next line to exit
                if "根据" in line and "整理" in line:
                    pending_plot_exit = True
                continue

        if in_annotation:
            # Dialogue line: exit annotation mode and process normally
            m_role = ROLE_ACTION_RE.match(line)
            m_dialogue = DIALOGUE_RE.match(line)
            m_cue_cont = CUE_CONTINUATION_RE.match(line)
            m_board = BOARD_CUE_RE.match(line)
            
            if m_role or m_dialogue or (m_cue_cont and last_speaker) or (m_board and _is_board_cue_label(m_board.group(1))):
                in_annotation = False
            else:
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type="annotation",
                        text=line,
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                idx += 1
                continue

        if CHAR_LIST_HEADER_RE.match(line):
            in_cast_section = True
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="character_list",
                    text=line,
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        if in_cast_section:
            if CAST_SECTION_END_RE.match(line):
                in_cast_section = False
            elif PLOT_HEADER_RE.match(line) or ANNOTATION_HEADER_RE.match(line):
                in_cast_section = False
            else:
                m_cast = CAST_LINE_RE.match(line)
                if m_cast:
                    name, hangdang = m_cast.group(1), m_cast.group(2)
                    hints.setdefault(name, {})["hangdang_labeled"] = hangdang
                    blocks.append(
                        RawBlock(
                            block_index=idx,
                            type="character_list",
                            text=line,
                            page_no=page_no,
                            scene_index=scene_index or None,
                        )
                    )
                    idx += 1
                    continue
                if line.strip() and not is_noise_line(line):
                    blocks.append(
                        RawBlock(
                            block_index=idx,
                            type="character_list",
                            text=line,
                            page_no=page_no,
                            scene_index=scene_index or None,
                        )
                    )
                    idx += 1
                continue

        m_cast_inline = CAST_LINE_RE.match(line)
        if m_cast_inline:
            name, hangdang = m_cast_inline.group(1), m_cast_inline.group(2)
            hints.setdefault(name, {})["hangdang_labeled"] = hangdang
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="character_list",
                    text=line,
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        if SCENE_RE.match(line):
            scene_index += 1
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="scene_heading",
                    text=line,
                    page_no=page_no,
                    scene_index=scene_index,
                )
            )
            idx += 1
            continue

        if is_noise_line(line):
            continue

        if in_aria and _is_plain_aria_line(line):
            speaker = last_aria_speaker or last_speaker
            if speaker:
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type="aria",
                        text=line,
                        speaker_name=speaker,
                        performance_tags=["唱"],
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                _hint_speaker(hints, speaker, ["唱"])
                idx += 1
                continue

        m_role = ROLE_ACTION_RE.match(line)
        if m_role:
            name, cue, content = m_role.group(1), m_role.group(2), m_role.group(3)
            if is_valid_character_name(name):
                tags, raw_cues = _perf_from_cue(cue)
                block_type = "aria" if "唱" in cue or "板" in cue or "垛" in cue else "dialogue"
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type=block_type,
                        text=content.strip() if content.strip() else line,
                        speaker_name=name,
                        performance_tags=tags or (["唱"] if block_type == "aria" else ["念"]),
                        performance_cues_raw=raw_cues,
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                _hint_speaker(hints, name, tags)
                last_speaker = name
                in_aria = False
                idx += 1
                continue

        m_board = BOARD_CUE_RE.match(line)
        if m_board and _is_board_cue_label(m_board.group(1)):
            cue, body = m_board.group(1).strip(), m_board.group(2).strip()
            speaker = last_speaker
            if speaker and body:
                in_aria = True
                last_aria_speaker = speaker
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type="aria",
                        text=body,
                        speaker_name=speaker,
                        performance_tags=["唱"],
                        performance_cues_raw=[cue],
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                _hint_speaker(hints, speaker, ["唱"])
                idx += 1
                continue

        m_cue_cont = CUE_CONTINUATION_RE.match(line)
        if m_cue_cont:
            cue, body = m_cue_cont.group(1).strip(), m_cue_cont.group(2).strip()
            if _is_board_cue_label(cue):
                pass
            elif (
                last_speaker
                and body
                and not _is_stage_paren_cue(cue)
            ):
                tags, raw_cues = _perf_from_cue(cue)
                block_type = (
                    "aria"
                    if "唱" in cue or "垛" in cue
                    else "dialogue"
                )
                in_aria = block_type == "aria"
                if in_aria:
                    last_aria_speaker = last_speaker
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type=block_type,
                        text=body,
                        speaker_name=last_speaker,
                        performance_tags=tags or ["念"],
                        performance_cues_raw=raw_cues,
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                _hint_speaker(hints, last_speaker, tags)
                idx += 1
                continue

        m_dialogue = DIALOGUE_RE.match(line)
        if m_dialogue:
            name, cue, content = m_dialogue.group(1), m_dialogue.group(2), m_dialogue.group(3)
            name = name.strip()
            body = (content or "").strip()

            if is_hangdang_word(body) and is_valid_character_name(name):
                hints.setdefault(name, {})["hangdang_labeled"] = body
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type="character_list",
                        text=line,
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                idx += 1
                continue

            if not is_valid_character_name(name):
                blocks.append(
                    RawBlock(
                        block_index=idx,
                        type="aria" if body or len(name) > 4 else "unknown",
                        text=line,
                        performance_tags=["唱"] if "板" in line or "唱" in line else [],
                        page_no=page_no,
                        scene_index=scene_index or None,
                    )
                )
                idx += 1
                continue

            tags, raw_cues = _perf_from_cue(cue)
            text = body if body else line
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="dialogue",
                    text=text,
                    speaker_name=name,
                    performance_tags=tags,
                    performance_cues_raw=raw_cues,
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            _hint_speaker(hints, name, tags)
            last_speaker = name
            in_aria = False
            idx += 1
            continue

        if STAGE_ONLY_RE.match(line):
            body = STAGE_ONLY_RE.match(line).group(1)
            tags = _tags_from_stage(body)
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="stage_direction",
                    text=line,
                    performance_tags=tags,
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            _hint_stage_characters(body, hints)
            in_aria = False
            idx += 1
            continue

        m_aria_colon = ARIA_COLON_RE.match(line)
        if m_aria_colon and _should_treat_as_aria_colon(
            line, m_aria_colon.group(1).strip()
        ):
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="aria",
                    text=line,
                    performance_tags=["唱"],
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        if ARIA_MARK_RE.search(line) and "：" not in line and ":" not in line:
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="aria",
                    text=line,
                    performance_tags=["唱"],
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        if "唱" in line and ("【" in line or "（唱" in line):
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="aria",
                    text=line,
                    performance_tags=["唱"],
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        if any(k in line for k in ("上", "下", "进", "出", "同", "幕", "闭")) and (
            line.startswith("（") or line.startswith("(")
        ):
            blocks.append(
                RawBlock(
                    block_index=idx,
                    type="stage_direction",
                    text=line,
                    performance_tags=_tags_from_stage(line),
                    page_no=page_no,
                    scene_index=scene_index or None,
                )
            )
            idx += 1
            continue

        blocks.append(
            RawBlock(
                block_index=idx,
                type="unknown",
                text=line,
                page_no=page_no,
                scene_index=scene_index or None,
            )
        )
        idx += 1

    return SegmentResult(blocks=blocks, character_hints=hints)


def _page_for_line(line_no: int, boundaries: list[int] | None) -> int | None:
    if not boundaries:
        return None
    page = 1
    for i, start in enumerate(boundaries):
        if line_no >= start:
            page = i + 1
    return page


def _is_board_cue_label(cue: str) -> bool:
    return bool(BOARD_CUE_LABEL_RE.search(cue))


def _is_plain_aria_line(line: str) -> bool:
    """Consecutive aria lyric lines within an aria (no speaker, no board-cue marker)."""
    s = line.strip()
    if not s or len(s) < 4:
        return False
    if ROLE_ACTION_RE.match(s) or STAGE_ONLY_RE.match(s) or SCENE_RE.match(s):
        return False
    if BOARD_CUE_RE.match(s) and _is_board_cue_label(
        BOARD_CUE_RE.match(s).group(1)
    ):
        return False
    m_d = DIALOGUE_RE.match(s)
    if m_d and is_valid_character_name(m_d.group(1).strip()):
        return False
    return bool(re.match(r"^[\u4e00-\u9fff，、；？！。,\s]+$", s))


def _should_treat_as_aria_colon(line: str, prefix: str) -> bool:
    """Mark only aria lead lines like 「孤王言来听端详：」 as aria; exclude (一名：《…》) stage directions."""
    if is_valid_character_name(prefix):
        return False
    if prefix.startswith(("（", "(")):
        return False
    if "《" in prefix or "》" in line:
        return False
    if "一名" in prefix or "二名" in prefix:
        return False
    return len(prefix) > 4


def _is_stage_paren_cue(cue: str) -> bool:
    """Distinguish (念) continuation dialogue from (四龙套引刘备同上) stage directions."""
    if cue in ("白", "念", "唱", "引子", "叫头", "垛", "板"):
        return False
    if any(k in cue for k in STAGE_PAREN_HINTS):
        return True
    if len(cue) >= 5 and any(cue.endswith(x) for x in ("上", "下", "场")):
        return True
    if len(cue) > 8:
        return True
    return False


def _perf_from_cue(cue: str | None) -> tuple[list[str], list[str]]:
    label = (cue or "").strip()
    raw = [label] if label else []
    return _tags_from_cue(label), raw


def _tags_from_cue(cue: str) -> list[str]:
    tags: list[str] = []
    for ch in cue:
        if ch in PERFORMANCE_CUE_MAP:
            mapped = PERFORMANCE_CUE_MAP[ch]
            if mapped not in tags:
                tags.append(mapped)
    if not tags and cue:
        if "唱" in cue:
            tags.append("唱")
        elif "白" in cue or "念" in cue:
            tags.append("念")
    return tags or []


def _tags_from_stage(text: str) -> list[str]:
    tags: list[str] = []
    if any(k in text for k in ("唱", "板", "垛")):
        tags.append("唱")
    if "白" in text or "念" in text:
        tags.append("念")
    if any(k in text for k in ("打", "战")):
        tags.append("打")
    if any(k in text for k in ("上", "下", "走", "跪", "舞")):
        tags.append("做")
    return tags


def _parse_character_line(line: str, hints: dict[str, dict]) -> None:
    parts = re.split(r"[、,，\s]+", line)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.+?)[（(]([^）)]+)[）)]$", part)
        if m:
            name, info = m.group(1).strip(), m.group(2)
            hd = HANGDANG_PATTERN.search(info)
            hints.setdefault(name, {})
            if hd:
                hints[name]["hangdang_labeled"] = hd.group(1)
            if "女" in info:
                hints[name].setdefault("traits", {})["gender"] = "女"
            elif "男" in info:
                hints[name].setdefault("traits", {})["gender"] = "男"
        elif len(part) <= 6:
            hints.setdefault(part, {})


def _hint_speaker(hints: dict[str, dict], name: str, tags: list[str]) -> None:
    hints.setdefault(name, {})
    if tags:
        hints[name].setdefault("performance_cues", [])
        for t in tags:
            if t not in hints[name]["performance_cues"]:
                hints[name]["performance_cues"].append(t)


def _hint_stage_characters(body: str, hints: dict[str, dict]) -> None:
    """Extract entered characters only from 「引XXX上」 stage directions; avoid spurious names like 「引刘备同」."""
    for m in re.finditer(r"引([\u4e00-\u9fff·]{2,4})[同上]", body):
        name = m.group(1)
        if is_valid_character_name(name):
            hints.setdefault(name, {})