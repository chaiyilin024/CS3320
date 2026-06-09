"""Preprocessing logic unit tests (no PDF dependency)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.preprocessing.clean.normalize import normalize_full_text
from backend.preprocessing.clean.pipeline import process_text_to_play

SAMPLE_TEXT = """
人物：刘备（老生）、关羽（老生）、张飞（武生）

第一场

（周瑜上）

周瑜：恭喜都督。
【西皮原板】
周瑜：（唱）江山如画。
刘备：备久闻都督英名。
关羽：某愿随兄长。
（同下）

第二场

张飞：（白）大哥！
"""


def test_process_text_to_play_structure():
    play = process_text_to_play(
        full_text=SAMPLE_TEXT,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    assert play["script_id"] == "01001012"
    assert len(play["blocks"]) >= 1
    assert play["characters"]
    assert play["metadata"]["parse_quality"] > 0
    assert all(c["hangdang_inferred"] is None for c in play["characters"])
    types = {b["type"] for b in play["blocks"]}
    assert "dialogue" in types
    assert play["cooccurrence_edges_raw"]


def test_aria_continuation_and_board_cue_split():
    text = """诸葛亮 （白） 主公吓！
（西皮原板） 自古道吉人有天相，主公何必带愁肠？
黄鹤楼上把宴尝，四将军保驾谅无妨。
刘备 （白） 先生，
（西皮原板） 先生把话错来讲，休提起当年赴会在河梁。
"""
    play = process_text_to_play(
        full_text=text,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    blocks = play["blocks"]
  # Liu Bei dialogue should not contain xipi yuanban
    liu_bai = [b for b in blocks if b.get("speaker_id") == "c_刘备" and b["type"] == "dialogue"]
    assert liu_bai
    assert "西皮原板" not in liu_bai[0]["text"]
    assert "先生，" in liu_bai[0]["text"] or liu_bai[0]["text"].startswith("先生")
    # Aria continuation lines inherit Zhuge Liang as speaker
    zhuge_aria = [
        b
        for b in blocks
        if b.get("speaker_id") == "c_诸葛亮" and b["type"] == "aria"
    ]
    assert any("黄鹤楼上" in b["text"] for b in zhuge_aria)
    assert all("唱" in b.get("performance_tags", []) for b in zhuge_aria)
    zhuge_bai = [
        b
        for b in blocks
        if b.get("speaker_name_raw") == "诸葛亮" and b["type"] == "dialogue"
    ]
    assert zhuge_bai[0].get("performance_cues_raw") == ["白"]
    assert zhuge_bai[0]["performance_tags"] == ["念"]
    board_open = [
        b for b in zhuge_aria if b.get("performance_cues_raw") == ["西皮原板"]
    ]
    assert board_open and "自古道" in board_open[0]["text"]


def test_subplay_title_is_stage_not_aria():
    play = process_text_to_play(
        full_text="（一名：《过江赴宴》；一名：《竹中藏令》）\n主要角色\n刘备：老生",
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    b0 = play["blocks"][0]
    assert b0["type"] == "stage_direction"
    assert b0.get("performance_tags") != ["唱"] or "唱" not in (b0.get("performance_tags") or [])


def test_page_header_stripped():
    play = process_text_to_play(
        full_text="中国京剧戏考 《黄鹤楼》 1\n"
        "中国京剧戏考 《黄鹤楼》 2\n"
        "诸葛亮 （念） 东吴摆下杀人场，狸猫焉能胜虎狼。",
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    for b in play["blocks"]:
        assert "中国京剧戏考" not in b["text"]
        assert not b["text"].startswith("2诸")
    assert any("东吴摆下" in b["text"] for b in play["blocks"])


def test_cue_continuation_inherits_speaker():
    text = """【第一场】
刘备 （引子） 义得人和，灭孙曹，孤心安乐。
（念） 日月重明照英雄，全仗卧龙建奇功。
（白） 孤，刘备，乃大树楼桑人氏。
刘封 （白） 参见父王。
（白） 罢了，进帐何事？
"""
    play = process_text_to_play(
        full_text=text,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    blocks = {b["block_index"]: b for b in play["blocks"]}
    assert blocks[2]["speaker_id"] == "c_刘备"
    assert blocks[2]["type"] == "dialogue"
    assert "日月重明" in blocks[2]["text"]
    assert blocks[3]["speaker_id"] == "c_刘备"
    assert blocks[5]["speaker_id"] == "c_刘封"
    assert "罢了" in blocks[5]["text"]


def test_plot_summary_and_annotation_types():
    text = """主要角色
刘备：老生
情节
刘备借据荆州，久假不归。
周瑜愤甚。
注释
此剧按之《三国演义》并无其事。
【第一场】
刘备 （白） 参见。
"""
    play = process_text_to_play(
        full_text=text,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    types = {b["type"] for b in play["blocks"]}
    assert "plot_summary" in types
    assert "annotation" in types
    plot_blocks = [b for b in play["blocks"] if b["type"] == "plot_summary"]
    assert any("荆州" in b["text"] for b in plot_blocks)
    note_blocks = [b for b in play["blocks"] if b["type"] == "annotation"]
    assert any("三国演义" in b["text"] for b in note_blocks)


def test_cast_list_parsed_with_hangdang():
    text = """主要角色
刘备：老生
赵云：小生
周瑜：小生
情节
省略
【第一场】
刘备 （白） 参见都督。
"""
    play = process_text_to_play(
        full_text=text,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    by_name = {c["name"]: c for c in play["characters"]}
    assert by_name["刘备"]["hangdang_labeled"] == "老生"
    assert "引刘备同" not in by_name
    assert "孤王言来听端详" not in by_name


def test_url_footer_not_character():
    play = process_text_to_play(
        full_text="http://scripts.xikao.com/play/01001012 2018-08-23\n刘备：久闻都督英名。",
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    names = {c["name"] for c in play["characters"]}
    assert "http" not in names
    assert "刘备" in names


def test_laugh_line_not_merged_with_perf_cue_continuation():
    text = """周瑜 （笑） 哈哈哈……
（白） 刘备吓，刘备！此番过江，中了本督之计也！甘将军，
甘宁 （白） 在。
"""
    lines = normalize_full_text(text)
    assert any("（白）" in ln for ln in lines)
    assert not any("……（白）" in ln for ln in lines)
    play = process_text_to_play(
        full_text=text,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    zhou_blocks = [
        b
        for b in play["blocks"]
        if b.get("speaker_name_raw") == "周瑜" and b["type"] == "dialogue"
    ]
    assert any("刘备吓" in b["text"] for b in zhou_blocks)
    assert all("（白）" not in b["text"] for b in zhou_blocks)
    liubei_line = [b for b in zhou_blocks if "刘备吓" in b["text"]]
    assert liubei_line[0].get("performance_cues_raw") == ["白"]
    assert liubei_line[0]["performance_tags"] == ["念"]


def test_dialogue_has_speaker():
    play = process_text_to_play(
        full_text=SAMPLE_TEXT,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    dialogues = [b for b in play["blocks"] if b["type"] == "dialogue"]
    assert any(b.get("speaker_id") for b in dialogues)


def test_example_pdf_end_to_end():
    if not Path(ROOT / "example" / "01001012_黄鹤楼.pdf").exists():
        return
    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        return
    from backend.preprocessing.extract.pdf_text import extract_pdf_pages
    from backend.preprocessing.clean.pipeline import process_extract_result_to_play

    pdf = ROOT / "example" / "01001012_黄鹤楼.pdf"
    extracted = extract_pdf_pages(pdf)
    assert extracted.page_count > 0
    play = process_extract_result_to_play(
        extracted,
        script_id="01001012",
        title="黄鹤楼",
        collection_id="01000000",
        collection_name="戏考",
        source_pdf="01001012_黄鹤楼.pdf",
    )
    assert len(play["blocks"]) > 5
