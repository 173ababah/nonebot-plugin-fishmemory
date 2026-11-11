"""从聊天里抽事实（纯正则 + 垃圾过滤，零 LLM）。

为什么不交给大模型抽：**每句话都过一次模型 = 每条消息都花钱**，
而"我叫X / 我今年N岁 / 我喜欢Y"这类表达用正则就能覆盖 90%；
剩下 10% 让用户自己 `/记住` 补。

正则都做了保守截断（`{1,10}` 之类），避免把整句话吞进去。
"""

from __future__ import annotations

import re
from typing import List, Tuple

NAME_RE = re.compile(r"(?:我叫|我的名字是|我的名字叫|叫我)\s*([^\s，,。.!！?？]{1,10})")
AGE_RE = re.compile(r"(?:我(?:今年)?|今年)\s*(\d{1,2})\s*岁")   # 「我叫X，今年20岁」也得认
# 生日允许中间有空格（"3 月 5 日"），只按标点截断
BIRTH_RE = re.compile(r"我的?生日(?:是|在)?\s*([^，,。.!！?？\n]{1,12})")
# ⚠️ 这里的排除字符里**必须**有 也/还/又/和/、：
#    否则「我喜欢奶茶也喜欢猫」会被 greedy 吃成「奶茶也喜欢猫」一条。
_STOP = r"([^\s，,。.!！?？也还又和、]{1,12})"   # 带括号：要捕获
LIKE_RE = re.compile(r"我(?:很)?喜欢\s*" + _STOP)
HATE_RE = re.compile(r"我(?:很)?(?:讨厌|不喜欢)\s*" + _STOP)
# 「我喜欢奶茶也喜欢猫」第二句没有"我"，只有"也/还/又" —— 补一条专门的规则
LIKE2_RE = re.compile(r"(?:也|还|又)(?:很)?喜欢\s*" + _STOP)
HATE2_RE = re.compile(r"(?:也|还|又)(?:很)?(?:讨厌|不喜欢)\s*" + _STOP)
REMEMBER_RE = re.compile(r"^(?:/记住|记住)[:：\s]*(.{1,40})$", re.S)
ASK_MEMORY_RE = re.compile(r"(我是谁|我叫什么|你还记得我|记得我吗|我的名字)")

# 这些值存进去只会污染提示词（线上真出现过"名字=###"、"喜欢=什么"）
JUNK = {"什么", "啥", "怎么", "为什么", "不知道", "没事", "随便", "哈哈", "哈哈哈",
        "嗯", "嗯嗯", "哦", "啊", "呀", "吧", "呢", "这个", "那个", "你", "我",
        "他", "她", "它", "无", "没有", "算了", "不是", "就是", "###", "的", "了",
        "谁", "谁呀", "滴", "死", "上", "下"}

BAD_NAME = {"谁", "什么", "你", "谁呀", "我", "他", "她", "它"}
BAD_LIKE = {"你", "这个", "那个", "我", "他", "她", "它"}


def value_ok(value: str, *, junk_filter: bool = True) -> bool:
    """太水的值不记：单字、纯符号、口头禅。"""
    v = str(value or "").strip()
    if not v:
        return False
    # ⚠️ 不要用「长度 < 2」当标准：群里「我喜欢猫」「我讨厌雨」都是合法的一条，
    #    真正的垃圾（什么/哈哈/的/了）靠 JUNK 表和下面的字符检查挡。
    if junk_filter and v in JUNK:
        return False
    if not re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", v):   # 只剩 ### / 。。。 / !!!
        return False
    return True


def extract(text: str, *, junk_filter: bool = True) -> List[Tuple[str, str]]:
    """从一句话里抽 `[(key, value), …]`（**只抽不写**，写由调用方决定）。"""
    text = str(text or "")
    if not text.strip():
        return []
    got: List[Tuple[str, str]] = []
    seen = set()

    def add(key: str, value: str, bad: set | None = None) -> None:
        v = value.strip()
        if bad and v in bad:
            return
        if not value_ok(v, junk_filter=junk_filter):
            return
        if (key, v) in seen:
            return
        seen.add((key, v))
        got.append((key, v))

    m = NAME_RE.search(text)
    if m:
        add("name", m.group(1), BAD_NAME)
    m = AGE_RE.search(text)
    if m:
        add("age", m.group(1))
    m = BIRTH_RE.search(text)
    if m:
        add("birthday", m.group(1))
    for rx in (LIKE_RE, LIKE2_RE):
        for m in rx.finditer(text):
            add("likes", m.group(1), BAD_LIKE)
    for rx in (HATE_RE, HATE2_RE):
        for m in rx.finditer(text):
            add("dislikes", m.group(1), BAD_LIKE)
    m = REMEMBER_RE.match(text.strip())
    if m:
        add("facts", m.group(1))
    return got


def asks_about_memory(text: str) -> bool:
    """用户在问"你还记得我吗"——调用方可以据此把记忆块加进提示词。"""
    return bool(ASK_MEMORY_RE.search(str(text or "")))


def label_of(key: str) -> str:
    return {"likes": "喜欢", "dislikes": "讨厌", "facts": "记住",
            "name": "名字", "age": "年龄", "birthday": "生日",
            "gender": "性别"}.get(key, key)



