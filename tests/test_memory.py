"""记忆：存储 + 抽取 + 渲染 的单元测试（纯函数，不依赖 nonebot）。"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nonebot_plugin_fishmemory"))

import extract  # noqa: E402
import render  # noqa: E402
import store  # noqa: E402


def _file():
    return os.path.join(tempfile.mkdtemp(), "memory.json")


# ---------------- store ----------------

def test_scalar_overwrite_and_list_append():
    d = {}
    assert store.remember(d, "1", "name", "小明") is True
    assert store.remember(d, "1", "name", "小红") is True          # 改口要覆盖
    assert d["1"]["name"] == "小红"
    assert store.remember(d, "1", "likes", "奶茶") is True
    assert store.remember(d, "1", "likes", "奶茶") is False        # 去重
    assert d["1"]["likes"] == ["奶茶"]


def test_list_limit_keeps_latest():
    d = {}
    for i in range(12):
        store.remember(d, "1", "likes", "东西%d" % i, limit=5)
    assert d["1"]["likes"] == ["东西7", "东西8", "东西9", "东西10", "东西11"]


def test_empty_and_too_long_values():
    d = {}
    assert store.remember(d, "1", "likes", "  ") is False
    assert store.remember(d, "", "likes", "奶茶") is False
    store.remember(d, "1", "facts", "x" * 100, value_max=10)
    assert len(d["1"]["facts"][0]) == 10


def test_save_drops_empty_records():
    p = _file()
    d = {"1": {"updated": "2026-01-01 00:00"}, "2": {"name": "小明"}}
    store.save(p, d)
    back = store.load(p)
    assert "1" not in back and back["2"]["name"] == "小明"


def test_forget_variants():
    d = {"1": {"name": "小明", "likes": ["奶茶", "猫"]}}
    assert store.forget(d, "1", "likes", "奶茶") == 1
    assert d["1"]["likes"] == ["猫"]
    assert store.forget(d, "1", "likes", "") == 1
    assert "likes" not in d["1"]
    assert store.forget(d, "1") == 1
    assert "1" not in d


# ---------------- extract ----------------

def test_extract_name_age_birthday():
    got = dict(extract.extract("我叫小明，今年 20 岁，我的生日是 3 月 5 日"))
    assert got["name"] == "小明"
    assert got["age"] == "20"
    assert got["birthday"] == "3 月 5 日"        # 生日允许中间有空格，只按标点截断


def test_extract_like_hate_multiple():
    got = extract.extract("我喜欢奶茶也喜欢猫，我讨厌香菜")
    keys = [k for k, _ in got]
    assert keys.count("likes") == 2
    assert ("dislikes", "香菜") in got


def test_extract_remember_command():
    got = dict(extract.extract("/记住 我怕黑"))
    assert got["facts"] == "我怕黑"


def test_junk_filtered():
    assert extract.extract("我喜欢什么") == [] or all(
        v not in ("什么",) for _, v in extract.extract("我喜欢什么"))
    assert extract.extract("我叫谁") == []
    assert extract.extract("我叫###") == []
    assert extract.value_ok("什么") is False
    assert extract.value_ok("奶茶") is True


def test_no_match_returns_empty():
    assert extract.extract("今天天气不错") == []
    assert extract.extract("") == []


def test_asks_about_memory():
    assert extract.asks_about_memory("你还记得我吗")
    assert not extract.asks_about_memory("今天吃什么")


# ---------------- render ----------------

def test_bits_and_block():
    rec = {"name": "小明", "age": "20", "likes": ["奶茶", "猫"], "dislikes": ["香菜"],
           "facts": ["怕黑"]}
    bits = render.bits_of(rec)
    assert any("小明" in b for b in bits)
    assert any("奶茶" in b for b in bits)
    text = render.block(rec, who="小明")
    assert text.startswith("【你记得关于小明的事】")
    assert "奶茶" in text


def test_block_respects_max_chars():
    rec = {"likes": ["喜欢%d" % i for i in range(50)]}
    text = render.block(rec, show_likes=50, max_chars=80)
    assert len(text) <= 80
    assert text.endswith("…") or len(text) <= 80


def test_block_empty_when_no_memory():
    assert render.block({}) == ""
    assert "还没有" in render.plain({})


def test_plain_shows_updated():
    rec = {"name": "小明", "updated": "2026-11-11 21:00"}
    out = render.plain(rec)
    assert "更新于 2026-11-11 21:00" in out

