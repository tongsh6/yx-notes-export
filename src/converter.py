"""
格式转换模块：ENML → Markdown。

处理印象笔记特有标签：
  <en-note>      根标签，直接转换内容
  <en-media>     附件/图片引用，根据 hash 替换为 Markdown 链接
  <en-todo>      复选框，转换为 - [x] / - [ ]
  <en-crypt>     加密内容，替换为提示占位符
"""

from __future__ import annotations

import binascii
import re
from typing import Dict, Optional

import html2text
from bs4 import BeautifulSoup, Tag

# hash → (mime, filename) 的映射，由外部在调用前注入
ResourceMap = Dict[str, tuple[str, str]]  # hash_hex -> (mime, saved_filename)


def enml_to_markdown(enml: str, resource_map: Optional[ResourceMap] = None) -> str:
    """
    将 ENML 字符串转换为 Markdown 字符串。

    resource_map：{hash_hex: (mime_type, relative_path)}
      hash_hex  — resource.data.hash 的十六进制字符串（小写）
      mime_type — 如 "image/png"
      relative_path — 相对于笔记 .md 文件的附件路径，如 "assets/abc12345-foo.png"
    """
    if not enml:
        return ""

    resource_map = resource_map or {}
    soup = BeautifulSoup(enml, "lxml-xml")

    en_note = soup.find("en-note")
    if en_note is None:
        # 降级：直接处理整段 HTML
        html_body = enml
    else:
        # 预处理特殊标签（就地替换）
        _replace_en_media(en_note, resource_map)
        _replace_en_todo(en_note)
        _replace_en_crypt(en_note)
        html_body = str(en_note)

    return _html_to_md(html_body)


# ── 特殊标签替换 ──────────────────────────────────────────────────────────────


def _replace_en_media(root: Tag, resource_map: ResourceMap) -> None:
    """
    <en-media type="image/png" hash="abcd1234..."/>
    → 图片：![](assets/abcd1234-filename.png)
    → 其他：[filename](assets/abcd1234-filename.ext)
    """
    for tag in root.find_all("en-media"):
        hash_hex: str = (tag.get("hash") or "").lower().replace(" ", "")
        mime: str = tag.get("type") or ""
        info = resource_map.get(hash_hex)

        if info:
            _mime, rel_path = info
            if _mime.startswith("image/"):
                replacement = soup_tag_from_str(f'<img src="{rel_path}" alt=""/>')
            else:
                filename = rel_path.split("/")[-1]
                replacement = soup_tag_from_str(f'<a href="{rel_path}">{filename}</a>')
        else:
            # 附件未找到（可能下载失败），保留占位
            placeholder = f"[附件 hash={hash_hex[:8] or '?'} type={mime or '?'}]"
            replacement = soup_tag_from_str(f"<span>{placeholder}</span>")

        tag.replace_with(replacement)


def _replace_en_todo(root: Tag) -> None:
    """
    <en-todo checked="true"/>  →  ☑（html2text 会处理为 [x]）
    <en-todo checked="false"/> →  ☐
    使用 input[type=checkbox] 替换，html2text 能正确识别。
    """
    for tag in root.find_all("en-todo"):
        checked = str(tag.get("checked", "false")).lower() == "true"
        checked_attr = ' checked=""' if checked else ""
        replacement = soup_tag_from_str(
            f'<input type="checkbox"{checked_attr} disabled/>'
        )
        tag.replace_with(replacement)


def _replace_en_crypt(root: Tag) -> None:
    """<en-crypt>…</en-crypt> → [🔒 加密内容，无法导出]"""
    for tag in root.find_all("en-crypt"):
        tag.replace_with(soup_tag_from_str("<p>[🔒 加密内容，无法导出]</p>"))


# ── HTML → Markdown ───────────────────────────────────────────────────────────


def _html_to_md(html: str) -> str:
    h = html2text.HTML2Text()
    h.body_width = 0  # 不自动折行
    h.protect_links = True  # 保护链接不被转义
    h.wrap_links = False
    h.unicode_snob = True  # 保留 Unicode 字符
    h.ignore_images = False
    h.bypass_tables = False  # 尝试转换表格
    h.single_line_break = False

    md = h.handle(html)
    # 去掉 html2text 可能保留的 <en-note> 标签残留
    md = re.sub(r"</?en-note[^>]*>", "", md)
    # 合并连续空行（超过 2 行的压缩为 2 行）
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


# ── 工具函数 ─────────────────────────────────────────────────────────────────


def soup_tag_from_str(html_str: str) -> Tag:
    """将 HTML 片段解析为单个 BeautifulSoup Tag 对象。"""
    return BeautifulSoup(html_str, "html.parser").contents[0]


def resource_hash_hex(hash_bytes: Optional[bytes]) -> str:
    """将 resource.data.hash（bytes）转换为小写十六进制字符串。"""
    if not hash_bytes:
        return ""
    return binascii.hexlify(hash_bytes).decode("ascii").lower()
