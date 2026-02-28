"""
通用工具：文件名处理、时间格式化等。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

# Windows / macOS / Linux 均不允许的字符集合（取并集）
_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
# 连续空白或连字符压缩
_MULTI_DASH = re.compile(r"-{2,}")
_TRAILING = re.compile(r"[\s\-_.]+$")
_LEADING = re.compile(r"^[\s\-_.]+")


def safe_filename(name: str, max_len: int = 200) -> str:
    """
    将任意字符串转换为合法、可读的文件名（不含扩展名）。

    规则：
    - 非法字符替换为 -
    - 压缩连续 -
    - 去除首尾空白/- /. /_
    - 截断到 max_len 字节（UTF-8）
    - 若结果为空则返回 "untitled"
    """
    s = _ILLEGAL_CHARS.sub("-", name)
    s = _MULTI_DASH.sub("-", s)
    s = _LEADING.sub("", s)
    s = _TRAILING.sub("", s)

    # 按字节截断，避免截断多字节字符
    encoded = s.encode("utf-8")
    if len(encoded) > max_len:
        s = encoded[:max_len].decode("utf-8", errors="ignore")

    return s or "untitled"


def unique_filename(base: str, ext: str, existing: set[str]) -> str:
    """
    确保文件名不与 existing 集合冲突，冲突时追加 -2、-3 …

    base: 不含扩展名的安全文件名
    ext:  含点的扩展名，如 ".md"
    existing: 已使用的文件名集合（含扩展名）
    返回不冲突的文件名（含扩展名）。
    """
    candidate = f"{base}{ext}"
    if candidate not in existing:
        return candidate
    counter = 2
    while True:
        candidate = f"{base}-{counter}{ext}"
        if candidate not in existing:
            return candidate
        counter += 1


def ts_to_iso(timestamp_ms: Optional[int]) -> Optional[str]:
    """将印象笔记毫秒时间戳转换为 ISO 8601 字符串（UTC）。"""
    if timestamp_ms is None:
        return None
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
