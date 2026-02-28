"""
输出模块：目录创建、附件落盘、Markdown 文件写入。
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

import yaml

from .converter import ResourceMap, enml_to_markdown, resource_hash_hex
from .fetcher import Fetcher, NoteContent, NoteMetadata, NotebookInfo
from .utils import safe_filename, ts_to_iso, unique_filename


class Exporter:
    def __init__(self, fetcher, output_root: str, resume: bool = True) -> None:
        self._fetcher = fetcher
        self._output_root = os.path.abspath(output_root)
        self._resume = resume
        self._index_cache: Dict[str, _ResumeIndex] = {}

    # ── 主入口 ───────────────────────────────────────────────────────────────

    def export_note(
        self,
        meta: NoteMetadata,
        notebook: NotebookInfo,
        used_filenames: Dict[str, set[str]],
    ) -> tuple[str, bool]:
        """
        导出单条笔记。返回 (写入路径, 是否跳过)。

        used_filenames: {notebook_dir: set(已用文件名)} — 用于同一笔记本内去重
        """
        # 1. 决定输出目录
        nb_dir = self._notebook_dir(notebook)
        assets_dir = os.path.join(nb_dir, "assets")
        os.makedirs(nb_dir, exist_ok=True)

        # 2. 断点续传：未更新则跳过
        index = self._get_index(nb_dir)
        if self._resume and index.should_skip(meta, nb_dir):
            return index.get_path(meta.guid, nb_dir), True

        # 3. 获取笔记完整内容
        content: NoteContent = self._fetcher.get_note_content(meta.guid)

        # 4. 处理附件：下载并建立 hash → 相对路径 映射
        resource_map: ResourceMap = {}
        if content.resources:
            os.makedirs(assets_dir, exist_ok=True)
            resource_map = self._save_resources(content, assets_dir, nb_dir)

        # 5. ENML → Markdown
        md_body = enml_to_markdown(content.content, resource_map)

        # 6. 构造 YAML Front Matter
        front_matter = _build_front_matter(content)

        # 7. 确定不冲突的文件名
        bucket = used_filenames.setdefault(nb_dir, set())
        filename = unique_filename(safe_filename(content.title), ".md", bucket)
        bucket.add(filename)

        # 8. 写入 .md 文件
        md_path = os.path.join(nb_dir, filename)
        _write_md(md_path, content.title, front_matter, md_body)

        # 9. 更新索引
        index.update(meta, content, md_path, nb_dir)
        index.save()
        return md_path, False

    def _get_index(self, nb_dir: str) -> "_ResumeIndex":
        index = self._index_cache.get(nb_dir)
        if index is None:
            index = _ResumeIndex(os.path.join(nb_dir, ".export-index.json"))
            index.load()
            self._index_cache[nb_dir] = index
        return index

    # ── 附件 ─────────────────────────────────────────────────────────────────

    def _save_resources(
        self,
        content: NoteContent,
        assets_dir: str,
        nb_dir: str,
    ) -> ResourceMap:
        """
        下载所有附件，保存到 assets_dir，
        返回 {hash_hex: (mime, relative_path)} 供 converter 使用。
        """
        resource_map: ResourceMap = {}
        used: set[str] = set()

        for res in content.resources:
            if res.data is None:
                continue

            if not res.guid:
                continue

            hash_bytes = getattr(res.data, "hash", None) or getattr(
                res.data, "bodyHash", None
            )
            hash_hex = resource_hash_hex(hash_bytes)
            if not hash_hex:
                continue

            mime: str = (res.mime or "application/octet-stream").lower()
            orig_name = _resource_filename(res, mime)
            filename = unique_filename(
                safe_filename(f"{hash_hex[:8]}-{os.path.splitext(orig_name)[0]}"),
                os.path.splitext(orig_name)[1] or _ext_from_mime(mime),
                used,
            )
            used.add(filename)

            # 下载二进制并写盘
            asset_path = os.path.join(assets_dir, filename)
            if not os.path.exists(asset_path):
                try:
                    data = self._fetcher.get_resource_data(res.guid)
                except Exception:
                    data = b""
                if data:
                    with open(asset_path, "wb") as f:
                        f.write(data)

            rel_path = os.path.join("assets", filename).replace("\\", "/")
            resource_map[hash_hex] = (mime, rel_path)

        return resource_map

    # ── 目录计算 ─────────────────────────────────────────────────────────────

    def _notebook_dir(self, nb: NotebookInfo) -> str:
        parts = [self._output_root]
        if nb.stack:
            parts.append(safe_filename(nb.stack))
        parts.append(safe_filename(nb.name))
        return os.path.join(*parts)


# ── 工具函数 ─────────────────────────────────────────────────────────────────


def _build_front_matter(content: NoteContent) -> dict[str, object]:
    fm: dict[str, object] = {"title": content.title}
    if content.created:
        fm["created"] = ts_to_iso(content.created)
    if content.updated:
        fm["updated"] = ts_to_iso(content.updated)
    if content.tags:
        fm["tags"] = content.tags
    if content.source_url:
        fm["source_url"] = content.source_url
    return fm


def _write_md(
    path: str, title: str, front_matter: dict[str, object], body: str
) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(
            front_matter,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        f.write("---\n\n")
        f.write(f"# {title}\n\n")
        f.write(body)
        f.write("\n")


def _resource_filename(res, mime: str) -> str:
    """尽量从附件属性中提取原始文件名。"""
    if res.attributes and res.attributes.fileName:
        return res.attributes.fileName
    ext = _ext_from_mime(mime)
    return f"attachment{ext}"


def _ext_from_mime(mime: str) -> str:
    """从 MIME 类型推断文件扩展名（含点）。"""
    _map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "application/pdf": ".pdf",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/amr": ".amr",
        "video/mp4": ".mp4",
        "text/plain": ".txt",
        "text/html": ".html",
    }
    return _map.get(mime, ".bin")


class _ResumeIndex:
    def __init__(self, path: str) -> None:
        self._path = path
        self._notes: dict[str, dict[str, object]] = {}
        self._dirty = False

    def load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        if not isinstance(data, dict) or data.get("version") != 1:
            return
        notes = data.get("notes") or {}
        if isinstance(notes, dict):
            self._notes = notes

    def save(self) -> None:
        if not self._dirty:
            return
        data = {
            "version": 1,
            "notes": self._notes,
        }
        tmp = f"{self._path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)
        self._dirty = False

    def should_skip(self, meta: NoteMetadata, nb_dir: str) -> bool:
        entry = self._notes.get(meta.guid)
        if not entry:
            return False
        updated = entry.get("updated")
        if updated != meta.updated:
            return False
        rel_path = entry.get("path")
        if not rel_path:
            return False
        if not isinstance(rel_path, str):
            return False
        full_path = os.path.join(nb_dir, rel_path)
        return os.path.exists(full_path)

    def get_path(self, guid: str, nb_dir: str) -> str:
        entry = self._notes.get(guid)
        rel_path = entry.get("path") if entry else None
        if isinstance(rel_path, str) and rel_path:
            return os.path.join(nb_dir, rel_path)
        return os.path.join(nb_dir, "")

    def update(
        self, meta: NoteMetadata, content: NoteContent, md_path: str, nb_dir: str
    ) -> None:
        updated = content.updated if content.updated is not None else meta.updated
        rel_path = os.path.relpath(md_path, nb_dir)
        self._notes[meta.guid] = {
            "updated": updated,
            "path": rel_path.replace("\\", "/"),
        }
        self._dirty = True
