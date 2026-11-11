"""记忆存储（JSON，原子写）。

结构：`{"<uid>": {"name": "...", "age": "20", "likes": [...], "dislikes": [...],
                  "facts": [...], "updated": "YYYY-MM-DD HH:MM"}}`

规则（线上定的，别随手改）：

1. **单值字段覆盖写**（name/age/birthday/gender）：说"我叫小明"再改口"我叫小红"，应该记小红。
2. **列表字段追加 + 去重 + 只留最近 N 条**：喜好是会变的，留太多反而互相打架。
3. **空记录清理**：一个人只剩 `updated` 就别留在文件里。
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

_lock = threading.Lock()

SCALAR_KEYS = ("name", "age", "birthday", "gender")
LIST_KEYS = ("likes", "dislikes", "facts")


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def load(path: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path: str, data: Dict[str, Dict[str, Any]]) -> bool:
    clean: Dict[str, Dict[str, Any]] = {}
    for uid, rec in (data or {}).items():
        if not isinstance(rec, dict):
            continue
        keep = {k: v for k, v in rec.items()
                if (k in SCALAR_KEYS and str(v or "").strip())
                or (k in LIST_KEYS and v)}
        if keep:
            clean[str(uid)] = keep
    try:
        _ensure_dir(path)
        tmp = path + ".tmp"
        with _lock:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(clean, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
        return True
    except OSError:
        return False


def get(data: Dict[str, Dict[str, Any]], uid: str) -> Dict[str, Any]:
    rec = data.get(str(uid))
    return rec if isinstance(rec, dict) else {}


def remember(data: Dict[str, Dict[str, Any]], uid: str, key: str, value: str,
             *, limit: int = 8, value_max: int = 40) -> bool:
    """写一条。返回是否真的写进去了（重复/空值返回 False）。"""
    uid = str(uid or "")
    value = str(value or "").strip()[:value_max]
    if not uid or not value:
        return False
    rec = data.setdefault(uid, {})
    if key in SCALAR_KEYS:
        if str(rec.get(key) or "") == value:
            return False
        rec[key] = value
    else:
        bucket = rec.get(key)
        if not isinstance(bucket, list):
            bucket = []
        if value in bucket:
            return False
        bucket.append(value)
        rec[key] = bucket[-max(1, int(limit)):]
    rec["updated"] = time.strftime("%Y-%m-%d %H:%M")
    return True


def forget(data: Dict[str, Dict[str, Any]], uid: str, key: str = "",
           value: str = "") -> int:
    """删一条 / 删一类 / 全删。返回删掉几项。

    · `key=""`            → 这个人的记忆全删
    · `value=""`          → 删掉这一类（标量或整个列表）
    · 都给               → 从列表里删掉这个值
    """
    rec = data.get(str(uid))
    if not isinstance(rec, dict):
        return 0
    if not key:
        data.pop(str(uid), None)
        return 1
    if key not in rec:
        return 0
    if not value:
        rec.pop(key, None)
        return 1
    bucket = rec.get(key)
    if isinstance(bucket, list) and value in bucket:
        bucket.remove(value)
        if not bucket:
            rec.pop(key, None)
        return 1
    if isinstance(bucket, str) and bucket == value:
        rec.pop(key, None)
        return 1
    return 0


def merge_scalar(rec: Dict[str, Any], key: str) -> Optional[str]:
    return str(rec.get(key) or "") or None


def all_users(data: Dict[str, Dict[str, Any]]) -> List[str]:
    return sorted(str(u) for u in (data or {}))
