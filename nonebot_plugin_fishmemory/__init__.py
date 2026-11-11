"""nonebot-plugin-fishmemory —— 给 bot 一份「关于每个人的长期记忆」。

命令：

| 命令 | 说明 |
|------|------|
| `/记忆` | 看 bot 记得你什么 |
| `/记住 我怕黑` | 手动记一条事实 |
| `/忘记` | 清空自己的记忆 |
| `/忘记 喜欢 奶茶` | 删掉某一条 |

给别的插件用（推荐）：

```python
from nonebot_plugin_fishmemory import learn, mem_block

learn(uid, text)                 # 从这句话里抽名字/年龄/喜好…（零 LLM）
block = mem_block(uid)           # 取"你记得这个人"的一段，拼进 system prompt
```

设计：**零 LLM 开销** —— 抽取是正则，注入有字数上限。
"""

from __future__ import annotations

import os

from nonebot import get_plugin_config, on_command
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from . import extract, render, store
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-fishmemory",
    description="长期记忆：从聊天里抽名字/年龄/生日/喜好（正则，零 LLM 开销），注入时带字数上限",
    usage="/记忆 | /记住 怕黑 | /忘记 | /忘记 喜欢 奶茶",
    type="application",
    config=Config,
    homepage="https://github.com/173ababah/nonebot-plugin-fishmemory",
    supported_adapters={"~onebot.v11"},
)

cfg = get_plugin_config(Config)
FILE = cfg.fishmem_file or os.path.join(os.getcwd(), "data", "fishmemory", "memory.json")

mem_cmd = on_command("记忆", aliases={"memory"}, priority=19, block=True)
remember_cmd = on_command("记住", priority=19, block=True)
forget_cmd = on_command("忘记", priority=19, block=True)


def _uid(event: Event) -> str:
    fn = getattr(event, "get_user_id", None)
    if callable(fn):
        try:
            return str(fn())
        except Exception:
            pass
    return ""


# ---------------- 给别的插件用的 API ----------------

def learn(uid: str, text: str) -> list:
    """从一句话里抽事实并落盘，返回这次记住了什么（形如 `["名字=小明"]`）。"""
    if not cfg.fishmem_enabled or not uid or not text:
        return []
    pairs = extract.extract(text, junk_filter=cfg.fishmem_junk_filter)
    if not pairs:
        return []
    data = store.load(FILE)
    got = []
    for key, value in pairs:
        if store.remember(data, uid, key, value, limit=cfg.fishmem_limit,
                          value_max=cfg.fishmem_value_max):
            got.append("%s=%s" % (extract.label_of(key), value))
    if got:
        store.save(FILE, data)
    return got


def mem_block(uid: str, *, who: str = "") -> str:
    """取"你记得这个人"的一段（没内容返回空串）。"""
    if not cfg.fishmem_enabled:
        return ""
    rec = store.get(store.load(FILE), uid)
    return render.block(rec, show_likes=cfg.fishmem_show_likes,
                        show_dislikes=cfg.fishmem_show_dislikes,
                        show_facts=cfg.fishmem_show_facts,
                        max_chars=cfg.fishmem_max_chars, who=who)


# ---------------- 命令 ----------------

@mem_cmd.handle()
async def _(event: Event):
    uid = _uid(event)
    rec = store.get(store.load(FILE), uid)
    await mem_cmd.finish(render.plain(rec))


@remember_cmd.handle()
async def _(event: Event, arg: Message = CommandArg()):
    text = arg.extract_plain_text().strip()
    if not text:
        await remember_cmd.finish("记什么？用法：/记住 我怕黑")
    uid = _uid(event)
    if not extract.value_ok(text, junk_filter=cfg.fishmem_junk_filter):
        await remember_cmd.finish("这个不值得记…换点具体的")
    data = store.load(FILE)
    ok = store.remember(data, uid, "facts", text, limit=cfg.fishmem_limit,
                        value_max=cfg.fishmem_value_max)
    if ok:
        store.save(FILE, data)
    await remember_cmd.finish("记住了" if ok else "这条已经记过了")


@forget_cmd.handle()
async def _(event: Event, arg: Message = CommandArg()):
    uid = _uid(event)
    parts = arg.extract_plain_text().split()
    data = store.load(FILE)
    key = ""
    value = ""
    if parts:
        key = {"喜欢": "likes", "讨厌": "dislikes", "事实": "facts"}.get(parts[0], parts[0])
        value = " ".join(parts[1:])
    n = store.forget(data, uid, key, value)
    if n:
        store.save(FILE, data)
    await forget_cmd.finish("忘掉了" if n else "本来就没记这个")
