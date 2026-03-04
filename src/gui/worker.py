"""
后台工作线程：在 QThread 中运行认证和导出，避免阻塞 UI。
"""
# pyright: reportMissingImports=false

from __future__ import annotations

from time import monotonic
from typing import Any, List, Optional

from PySide6.QtCore import QThread, Signal

from src.auth import AuthConfig, build_client, build_client_with_token
from src.error_codes import classify_export_error
from src.event_log import NullEventLogger
from src.exporter import Exporter
from src.fetcher import Fetcher, NotebookInfo
from src.summary import build_export_summary


class ConnectWorker(QThread):
    """线程：认证 + 拉取笔记本列表。"""

    success = Signal(list, str)  # (List[NotebookInfo], session_token)
    failure = Signal(str)  # 错误消息

    def __init__(self, auth_cfg: AuthConfig) -> None:
        super().__init__()
        self._auth_cfg = auth_cfg
        self._abort = False

    def abort(self) -> None:
        self._abort = True

    def run(self) -> None:
        if self._abort:
            self.failure.emit("连接已取消")
            return
        try:
            client, token = build_client_with_token(self._auth_cfg)
            fetcher = Fetcher(client, should_abort=lambda: self._abort)
            notebooks = fetcher.list_notebooks()
            if self._abort:
                self.failure.emit("连接已取消")
                return
            self.success.emit(notebooks, token)
        except Exception as e:
            self.failure.emit(str(e))


class ExportWorker(QThread):
    """线程：执行批量导出。"""

    # (当前条数, 总条数, 笔记标题)
    progress = Signal(int, int, str)
    # (笔记guid, 笔记标题, 是否成功, 错误信息)
    note_done = Signal(str, str, bool, str)
    # (成功数, 失败数, 跳过数)
    export_done = Signal(int, int, int)
    # 运行时活动状态（用于 UI 显示“仍在处理中”）
    activity = Signal(str)
    # 严重错误（认证失效等）
    error = Signal(str)

    def __init__(
        self,
        auth_cfg: AuthConfig,
        output_dir: str,
        notebooks: List[NotebookInfo],  # 要导出的笔记本（空表示全量）
        note_guid: Optional[str],  # 单条笔记 GUID（优先级最高）
        failed_guids: Optional[List[str]],  # 仅导出失败记录（GUID 列表）
        all_notebooks: List[NotebookInfo],  # 账户全量笔记本（用于 guid→info 映射）
        resume: bool,
        event_logger: Any = None,
    ) -> None:
        super().__init__()
        self._auth_cfg = auth_cfg
        self._output_dir = output_dir
        self._notebooks = notebooks
        self._note_guid = note_guid
        self._failed_guids = failed_guids or []
        self._all_notebooks = all_notebooks
        self._resume = resume
        self._abort = False
        self._skip_current = False
        self._event_logger = event_logger or NullEventLogger()
        self._last_activity_msg = ""
        self._last_activity_ts = 0.0
        self._retry_total = 0
        self._retry_by_reason: dict[str, int] = {}
        self._failed_errors: list[str] = []
        self._failed_error_codes: list[str] = []
        self._run_summary: dict[str, object] = {}

    def abort(self) -> None:
        self._abort = True

    def request_skip_current_note(self) -> None:
        if self._abort:
            return
        self._skip_current = True
        self._emit_activity("已请求跳过当前笔记，等待当前请求返回…", force=True)

    def _should_cancel_io(self) -> bool:
        return self._abort or self._skip_current or self.isInterruptionRequested()

    def run(self) -> None:
        started_at = monotonic()
        try:
            client = build_client(self._auth_cfg)
        except Exception as e:
            self._event_logger.emit("auth.failed", level="ERROR", error=str(e))
            self.error.emit(f"认证失败：{e}")
            return

        self._event_logger.emit(
            "export.started",
            output_dir=self._output_dir,
            mode=(
                "failed_guids"
                if self._failed_guids
                else "note"
                if self._note_guid
                else "scope"
            ),
            resume=self._resume,
        )
        fetcher = Fetcher(
            client,
            should_abort=self._should_cancel_io,
            status_cb=self._on_fetch_status,
            event_logger=self._event_logger,
        )
        exporter = Exporter(fetcher, self._output_dir, resume=self._resume)
        nb_index = {nb.guid: nb for nb in self._all_notebooks}
        used_filenames: dict[str, set[str]] = {}
        ok = fail = skipped = 0

        # 确定目标笔记本列表
        target_nbs = self._notebooks if self._notebooks else self._all_notebooks

        try:
            if self._failed_guids:
                total = len(self._failed_guids)
                self.progress.emit(0, total, "开始导出失败记录")
                for idx, guid in enumerate(self._failed_guids):
                    if self._abort:
                        break
                    self._skip_current = False
                    metas = list(fetcher.iter_notes(note_guid=guid))
                    if not metas:
                        err = "失败记录中 GUID 无法找到"
                        self._failed_errors.append(err)
                        self._failed_error_codes.append(classify_export_error(err))
                        self._event_logger.emit(
                            "note.failed",
                            level="ERROR",
                            note_guid=guid,
                            note_title="(未知标题)",
                            error="失败记录中 GUID 无法找到",
                        )
                        self.note_done.emit(
                            guid, "(未知标题)", False, "失败记录中 GUID 无法找到"
                        )
                        fail += 1
                        continue
                    meta = metas[0]
                    self.progress.emit(idx, total, meta.title)
                    self._emit_activity(f"正在处理：{meta.title}", force=True)
                    nb = nb_index.get(meta.notebook_guid) or _fallback_nb(
                        meta.notebook_guid
                    )
                    ok, fail, skipped = self._export_one(
                        meta, nb, exporter, used_filenames, ok, fail, skipped
                    )
            elif self._note_guid:
                # 单条笔记
                note_metas = list(fetcher.iter_notes(note_guid=self._note_guid))
                total = len(note_metas)
                self.progress.emit(0, total, "开始导出")
                for idx, meta in enumerate(note_metas):
                    if self._abort:
                        break
                    self._skip_current = False
                    self.progress.emit(idx, total, meta.title)
                    self._emit_activity(f"正在处理：{meta.title}", force=True)
                    nb = nb_index.get(meta.notebook_guid) or _fallback_nb(
                        meta.notebook_guid
                    )
                    ok, fail, skipped = self._export_one(
                        meta, nb, exporter, used_filenames, ok, fail, skipped
                    )
            else:
                # 先统计总数（遍历元数据，速度较快）
                all_metas = []
                self.progress.emit(0, 0, "统计笔记列表…")
                for nb in target_nbs:
                    if self._abort:
                        break
                    for meta in fetcher.iter_notes(notebook_guid=nb.guid):
                        if self._abort:
                            break
                        all_metas.append((meta, nb))
                total = len(all_metas)
                if self._abort:
                    self.export_done.emit(ok, fail, skipped)
                    return
                self.progress.emit(0, total, "开始导出")

                for idx, (meta, nb) in enumerate(all_metas):
                    if self._abort:
                        break
                    self._skip_current = False
                    self.progress.emit(idx, total, meta.title)
                    self._emit_activity(f"正在处理：{meta.title}", force=True)
                    ok, fail, skipped = self._export_one(
                        meta, nb, exporter, used_filenames, ok, fail, skipped
                    )
        except InterruptedError:
            self._abort = True
            self._event_logger.emit("export.aborted")
        except Exception as e:
            self._event_logger.emit("export.crashed", level="ERROR", error=str(e))
            self.error.emit(str(e))
            return

        self._event_logger.emit(
            "export.finished",
            success=ok,
            failed=fail,
            skipped=skipped,
            aborted=self._abort,
            retries_total=self._retry_total,
        )
        self._run_summary = build_export_summary(
            success=ok,
            failed=fail,
            skipped=skipped,
            elapsed_sec=monotonic() - started_at,
            retries_total=self._retry_total,
            retries_by_reason=self._retry_by_reason,
            failed_errors=self._failed_errors,
            failed_error_codes=self._failed_error_codes,
            output_dir=self._output_dir,
            stopped=self._abort,
        )
        self.export_done.emit(ok, fail, skipped)

    def get_summary(self) -> dict[str, object]:
        return dict(self._run_summary)

    def _on_fetch_status(
        self, event: str, api_name: str, data: dict[str, object]
    ) -> None:
        if self._abort:
            return
        if event == "api_start":
            self._emit_activity(f"网络请求：{api_name}…")
            return
        if event == "api_wait_retry":
            self._retry_total += 1
            reason_key = str(data.get("reason", "unknown"))
            self._retry_by_reason[reason_key] = (
                self._retry_by_reason.get(reason_key, 0) + 1
            )
            wait_raw = data.get("wait_sec", 0.0)
            wait_sec = float(wait_raw) if isinstance(wait_raw, (int, float)) else 0.0
            reason = str(data.get("reason", ""))
            if reason == "rate_limit":
                self._emit_activity(
                    f"触发限流，{wait_sec:.0f}s 后重试（{api_name}）", force=True
                )
            else:
                self._emit_activity(
                    f"请求超时，{wait_sec:.1f}s 后重试（{api_name}）", force=True
                )
            return
        if event == "api_fail":
            reason = str(data.get("reason", ""))
            if reason == "timeout":
                self._emit_activity(f"请求失败：{api_name}（超时）", force=True)
            else:
                self._emit_activity(f"请求失败：{api_name}", force=True)
            return
        if event == "aborted":
            self._emit_activity("已收到停止信号，正在收尾…", force=True)

    def _emit_activity(self, msg: str, force: bool = False) -> None:
        now = monotonic()
        if (
            not force
            and msg == self._last_activity_msg
            and now - self._last_activity_ts < 2.0
        ):
            return
        self._last_activity_msg = msg
        self._last_activity_ts = now
        self.activity.emit(msg)

    def _export_one(self, meta, nb, exporter, used_filenames, ok, fail, skipped):
        try:
            _path, did_skip = exporter.export_note(meta, nb, used_filenames)
            if did_skip:
                self._event_logger.emit(
                    "note.skipped",
                    note_guid=meta.guid,
                    note_title=meta.title,
                    notebook_guid=meta.notebook_guid,
                )
                self.note_done.emit(meta.guid, meta.title, True, "跳过")
                return ok, fail, skipped + 1
            self._event_logger.emit(
                "note.exported",
                note_guid=meta.guid,
                note_title=meta.title,
                notebook_guid=meta.notebook_guid,
            )
            self.note_done.emit(meta.guid, meta.title, True, "")
            return ok + 1, fail, skipped
        except InterruptedError:
            if self._abort or self.isInterruptionRequested():
                self._abort = True
                return ok, fail, skipped
            if self._skip_current:
                self._skip_current = False
                self._event_logger.emit(
                    "note.skipped",
                    note_guid=meta.guid,
                    note_title=meta.title,
                    notebook_guid=meta.notebook_guid,
                    reason="user_skip",
                )
                self.note_done.emit(meta.guid, meta.title, True, "用户跳过")
                return ok, fail, skipped + 1
            self._abort = True
            return ok, fail, skipped
        except Exception as e:
            err = str(e)
            error_code = classify_export_error(err)
            self._failed_errors.append(err)
            self._failed_error_codes.append(error_code)
            self._event_logger.emit(
                "note.failed",
                level="ERROR",
                note_guid=meta.guid,
                note_title=meta.title,
                notebook_guid=meta.notebook_guid,
                error=err,
                error_code=error_code,
            )
            self.note_done.emit(meta.guid, meta.title, False, err)
            return ok, fail + 1, skipped


def _fallback_nb(guid: str) -> NotebookInfo:
    return NotebookInfo(guid=guid, name="未知笔记本", stack=None)
