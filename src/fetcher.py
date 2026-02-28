"""
数据获取模块：封装所有与印象笔记 NoteStore 的交互。
"""
# pyright: reportMissingImports=false

from __future__ import annotations

import socket
import time
from time import monotonic
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, List, Optional

from evernote.api.client import EvernoteClient
from evernote.edam.error.ttypes import EDAMSystemException
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import Note, Notebook, Resource

from src.event_log import NullEventLogger

# 每次 API 调用后的最小间隔（秒），避免触发频率限制
_API_DELAY = 0.5
# 每页最多获取笔记数（API 上限通常为 250）
_PAGE_SIZE = 50
# EDAMErrorCode.RATE_LIMIT_REACHED = 19
_RATE_LIMIT_CODE = 19
# 限流后最大重试次数
_MAX_RETRIES = 3
_SOCKET_TIMEOUT_SEC = 45
_socket_timeout_set = False


@dataclass
class NotebookInfo:
    guid: str
    name: str
    stack: Optional[str]  # 分组名，无分组时为 None


@dataclass
class NoteMetadata:
    guid: str
    title: str
    notebook_guid: str
    updated: Optional[int]


@dataclass
class NoteContent:
    guid: str
    title: str
    content: str  # ENML 原始字符串
    created: Optional[int]  # 毫秒时间戳
    updated: Optional[int]
    tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    resources: List[Resource] = field(default_factory=list)


class Fetcher:
    def __init__(
        self,
        client: EvernoteClient,
        should_abort: Optional[Callable[[], bool]] = None,
        status_cb: Optional[Callable[[str, str, dict[str, object]], None]] = None,
        event_logger: Any = None,
    ) -> None:
        _ensure_socket_timeout()
        self._note_store = client.get_note_store()
        self._should_abort = should_abort
        self._status_cb = status_cb
        self._event_logger = event_logger or NullEventLogger()

    # ── 笔记本 ──────────────────────────────────────────────────────────────

    def list_notebooks(self) -> List[NotebookInfo]:
        """返回账户下所有笔记本（含 stack 信息）。"""
        notebooks = (
            _with_retry(
                self._note_store.listNotebooks,
                should_abort=self._should_abort,
                status_cb=self._status_cb,
                event_logger=self._event_logger,
                api_name="listNotebooks",
            )
            or []
        )
        result: List[NotebookInfo] = []
        for nb in notebooks:
            if not nb or not nb.guid or not nb.name:
                continue
            result.append(
                NotebookInfo(
                    guid=nb.guid,
                    name=nb.name,
                    stack=nb.stack or None,
                )
            )
        return result

    def find_notebook_by_name(self, name: str) -> Optional[NotebookInfo]:
        """按名称（大小写精确）查找笔记本。"""
        for nb in self.list_notebooks():
            if nb.name == name:
                return nb
        return None

    # ── 笔记列表 ─────────────────────────────────────────────────────────────

    def iter_notes(
        self,
        notebook_guid: Optional[str] = None,
        note_guid: Optional[str] = None,
    ) -> Iterator[NoteMetadata]:
        """
        按需遍历笔记元数据：
        - note_guid 指定：只返回该条笔记
        - notebook_guid 指定：返回该笔记本所有笔记
        - 两者均为 None：返回账户全部笔记
        """
        if note_guid:
            yield from self._iter_single_note(note_guid)
            return

        note_filter = NoteFilter(notebookGuid=notebook_guid)
        spec = NotesMetadataResultSpec(
            includeTitle=True,
            includeNotebookGuid=True,
            includeUpdated=True,
        )
        offset = 0
        while True:
            result = _with_retry(
                self._note_store.findNotesMetadata,
                note_filter,
                offset,
                _PAGE_SIZE,
                spec,
                should_abort=self._should_abort,
                status_cb=self._status_cb,
                event_logger=self._event_logger,
                api_name="findNotesMetadata",
                meta={"notebook_guid": notebook_guid or "", "offset": offset},
            )
            if result is None:
                break
            for meta in result.notes or []:
                if not meta or not meta.guid or not meta.notebookGuid:
                    continue
                yield NoteMetadata(
                    guid=meta.guid,
                    title=meta.title or "(无标题)",
                    notebook_guid=meta.notebookGuid,
                    updated=getattr(meta, "updated", None),
                )
            if result.totalNotes is None or offset + _PAGE_SIZE >= result.totalNotes:
                break
            offset += _PAGE_SIZE

    def _iter_single_note(self, note_guid: str) -> Iterator[NoteMetadata]:
        note = _with_retry(
            self._note_store.getNote,
            note_guid,
            False,
            False,
            False,
            False,
            should_abort=self._should_abort,
            status_cb=self._status_cb,
            event_logger=self._event_logger,
            api_name="getNoteMeta",
            meta={"note_guid": note_guid},
        )
        if note is None:
            return
        yield NoteMetadata(
            guid=note.guid,
            title=note.title or "(无标题)",
            notebook_guid=note.notebookGuid,
            updated=getattr(note, "updated", None),
        )

    # ── 笔记完整内容 ──────────────────────────────────────────────────────────

    def get_note_content(self, guid: str) -> NoteContent:
        """
        获取笔记完整内容（ENML + 标签 + 元数据 + 附件元信息）。
        附件二进制数据通过 get_resource_data 单独获取，避免单次传输过大。
        """
        note = _with_retry(
            self._note_store.getNote,
            guid,
            True,
            False,
            False,
            False,
            should_abort=self._should_abort,
            status_cb=self._status_cb,
            event_logger=self._event_logger,
            api_name="getNoteContent",
            meta={"note_guid": guid},
        )
        if note is None:
            raise RuntimeError("获取笔记内容失败：Note 为空")

        # 解析标签名称
        tag_names: List[str] = []
        if note.tagGuids:
            try:
                tag_names = list(
                    _with_retry(
                        self._note_store.getNoteTagNames,
                        guid,
                        should_abort=self._should_abort,
                        status_cb=self._status_cb,
                        event_logger=self._event_logger,
                        api_name="getNoteTagNames",
                        meta={"note_guid": guid},
                    )
                    or []
                )
            except Exception:
                pass  # 标签获取失败不影响主流程

        # 附件元信息（不含二进制）
        resources: List[Resource] = note.resources or []

        attrs = note.attributes or None
        return NoteContent(
            guid=note.guid,
            title=note.title or "(无标题)",
            content=note.content or "",
            created=note.created,
            updated=note.updated,
            tags=tag_names,
            source_url=(attrs.sourceURL if attrs else None),
            resources=resources,
        )

    # ── 附件二进制 ────────────────────────────────────────────────────────────

    def get_resource_data(self, resource_guid: str) -> bytes:
        """获取附件的原始二进制内容。"""
        resource = _with_retry(
            self._note_store.getResource,
            resource_guid,
            True,
            False,
            True,
            False,
            should_abort=self._should_abort,
            status_cb=self._status_cb,
            event_logger=self._event_logger,
            api_name="getResource",
            meta={"resource_guid": resource_guid},
        )
        if resource is None:
            return b""
        if resource.data and resource.data.body:
            return resource.data.body
        return b""


def _with_retry(
    fn,
    *args,
    retries: int = _MAX_RETRIES,
    should_abort: Optional[Callable[[], bool]] = None,
    status_cb: Optional[Callable[[str, str, dict[str, object]], None]] = None,
    event_logger: Any = None,
    api_name: str = "api_call",
    meta: Optional[dict[str, object]] = None,
):
    """
    执行 API 调用，遇到限流（RATE_LIMIT_REACHED）自动等待后重试。
    其余异常直接向上抛出。
    """
    logger: Any = event_logger or NullEventLogger()
    ctx: dict[str, Any] = dict(meta or {})

    def _notify(event: str, **payload: object) -> None:
        if not status_cb:
            return
        try:
            status_cb(event, api_name, payload)
        except Exception:
            pass

    for attempt in range(retries):
        if should_abort and should_abort():
            _notify("aborted")
            raise InterruptedError("导出已停止")
        attempt_num = attempt + 1
        started = monotonic()
        _notify("api_start", attempt_num=attempt_num, max_retries=retries)
        logger.emit("api_req_start", api=api_name, attempt_num=attempt_num, meta=ctx)
        try:
            result = fn(*args)
            if should_abort and should_abort():
                _notify("aborted")
                raise InterruptedError("导出已停止")
            duration_ms = int((monotonic() - started) * 1000)
            logger.emit(
                "api_req_done",
                api=api_name,
                attempt_num=attempt_num,
                duration_ms=duration_ms,
                meta=ctx,
            )
            _sleep_interruptible(_API_DELAY, should_abort)
            return result
        except EDAMSystemException as exc:
            duration_ms = int((monotonic() - started) * 1000)
            if getattr(exc, "errorCode", None) == _RATE_LIMIT_CODE:
                wait = getattr(exc, "rateLimitDuration", 60) + 1
                if attempt < retries - 1:
                    _notify(
                        "api_wait_retry",
                        attempt_num=attempt_num,
                        max_retries=retries,
                        reason="rate_limit",
                        wait_sec=float(wait),
                    )
                    logger.emit(
                        "api_req_retry",
                        level="WARNING",
                        api=api_name,
                        attempt_num=attempt_num,
                        backoff_ms=int(wait * 1000),
                        duration_ms=duration_ms,
                        reason="rate_limit",
                        error_type=type(exc).__name__,
                        error_msg=str(exc),
                        meta=ctx,
                    )
                    _sleep_interruptible(wait, should_abort)
                    continue
            logger.emit(
                "api_req_fail",
                level="ERROR",
                api=api_name,
                attempt_num=attempt_num,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_msg=str(exc),
                meta=ctx,
            )
            _notify(
                "api_fail",
                attempt_num=attempt_num,
                max_retries=retries,
                reason="edam_error",
            )
            raise
        except (TimeoutError, socket.timeout, OSError):
            duration_ms = int((monotonic() - started) * 1000)
            logger.emit(
                "api_timeout",
                level="WARNING",
                api=api_name,
                attempt_num=attempt_num,
                duration_ms=duration_ms,
                meta=ctx,
            )
            if attempt < retries - 1:
                _notify(
                    "api_wait_retry",
                    attempt_num=attempt_num,
                    max_retries=retries,
                    reason="timeout",
                    wait_sec=float(_API_DELAY),
                )
                logger.emit(
                    "api_req_retry",
                    level="WARNING",
                    api=api_name,
                    attempt_num=attempt_num,
                    backoff_ms=int(_API_DELAY * 1000),
                    reason="timeout",
                    meta=ctx,
                )
                _sleep_interruptible(_API_DELAY, should_abort)
                continue
            logger.emit(
                "api_req_fail",
                level="ERROR",
                api=api_name,
                attempt_num=attempt_num,
                duration_ms=duration_ms,
                error_type="TimeoutError",
                error_msg="socket timeout",
                meta=ctx,
            )
            _notify(
                "api_fail",
                attempt_num=attempt_num,
                max_retries=retries,
                reason="timeout",
            )
            raise


def _sleep_interruptible(
    seconds: float, should_abort: Optional[Callable[[], bool]]
) -> None:
    remain = max(0.0, float(seconds))
    step = 0.2
    while remain > 0:
        if should_abort and should_abort():
            raise InterruptedError("导出已停止")
        chunk = step if remain > step else remain
        time.sleep(chunk)
        remain -= chunk


def _ensure_socket_timeout() -> None:
    global _socket_timeout_set
    if _socket_timeout_set:
        return
    socket.setdefaulttimeout(_SOCKET_TIMEOUT_SEC)
    _socket_timeout_set = True
