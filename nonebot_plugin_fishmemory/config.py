"""配置（.env 前缀 FISHMEM_）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Config(BaseModel):
    fishmem_enabled: bool = Field(default=True, description="总开关")
    fishmem_file: str = Field(default="", description="记忆文件；留空 = <cwd>/data/fishmemory/memory.json")
    fishmem_limit: int = Field(default=8, description="每个列表（喜欢/讨厌/事实）最多留几条")
    fishmem_show_likes: int = Field(default=6, description="注入提示词时最多显示几条「喜欢」")
    fishmem_show_dislikes: int = Field(default=4, description="最多几条「讨厌」")
    fishmem_show_facts: int = Field(default=6, description="最多几条「事实」")
    fishmem_max_chars: int = Field(default=400, description="整段记忆注入的最大字符数")
    fishmem_value_max: int = Field(default=40, description="单条事实最长字符数")
    fishmem_junk_filter: bool = Field(default=True, description="是否过滤「什么/哈哈/的」这类水词")
