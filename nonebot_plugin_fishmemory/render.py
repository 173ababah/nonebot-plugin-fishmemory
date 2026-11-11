"""把记忆渲染成提示词里那一段（纯函数）。

长度必须可控：记忆是最容易越滚越大的东西，不设上限的话
一个月后 system prompt 里一半是"某某喜欢喝奶茶"。
"""

from __future__ import annotations

from typing import Any, Dict, List


def bits_of(rec: Dict[str, Any], *, show_likes: int = 6, show_dislikes: int = 4,
            show_facts: int = 6) -> List[str]:
    """一个人 → 几行短句。"""
    if not isinstance(rec, dict):
        return []
    bits: List[str] = []
    name = str(rec.get("name") or "").strip()
    age = str(rec.get("age") or "").strip()
    gender = str(rec.get("gender") or "").strip()
    birthday = str(rec.get("birthday") or "").strip()
    head = name
    if age:
        head = (head + "，" if head else "") + age + " 岁"
    if gender:
        head = (head + "，" if head else "") + gender
    if birthday:
        head = (head + "，" if head else "") + "生日 " + birthday
    if head:
        bits.append(head)
    likes = [str(x) for x in (rec.get("likes") or [])][-max(0, show_likes):]
    if likes:
        bits.append("喜欢" + "、".join(likes))
    dislikes = [str(x) for x in (rec.get("dislikes") or [])][-max(0, show_dislikes):]
    if dislikes:
        bits.append("讨厌" + "、".join(dislikes))
    facts = [str(x) for x in (rec.get("facts") or [])][-max(0, show_facts):]
    if facts:
        bits.append("；".join(facts))
    return bits


def block(rec: Dict[str, Any], *, show_likes: int = 6, show_dislikes: int = 4,
          show_facts: int = 6, max_chars: int = 400,
          who: str = "") -> str:
    """渲染成注入用的一段；没有内容返回空串（调用方据此跳过）。"""
    bits = bits_of(rec, show_likes=show_likes, show_dislikes=show_dislikes,
                   show_facts=show_facts)
    if not bits:
        return ""
    prefix = "【你记得关于%s的事】" % (who or "这个人")
    body = "；".join(bits)
    room = max(0, int(max_chars) - len(prefix))
    if len(body) > room:
        body = body[:max(0, room - 1)].rstrip("；，") + "…"
    return prefix + body


def plain(rec: Dict[str, Any], *, who: str = "") -> str:
    """`/记忆` 命令用的可读版本（不限那么死，但也不给一堆空行）。"""
    bits = bits_of(rec, show_likes=20, show_dislikes=20, show_facts=20)
    if not bits:
        return "还没有关于%s的记忆。" % (who or "你")
    lines = ["关于%s：" % (who or "你")] + ["· " + b for b in bits]
    upd = str(rec.get("updated") or "")
    if upd:
        lines.append("（更新于 %s）" % upd)
    return "\n".join(lines)
