"""结构化事件日志（JSONL）。"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from platformdirs import user_log_dir

_APP_NAME = "YxNotesExport"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class EventLogger:
    file_path: str
    run_id: str
    channel: str
    _lock: threading.Lock = field(init=False)

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def emit(self, event: str, level: str = "INFO", **fields) -> None:
        payload = {
            "ts": _now_iso(),
            "level": level,
            "event": event,
            "run_id": self.run_id,
            "channel": self.channel,
        }
        payload.update(fields)

        line = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")


class NullEventLogger:
    def emit(self, event: str, level: str = "INFO", **fields) -> None:
        _ = (event, level, fields)


def get_log_dir() -> str:
    """返回平台标准日志目录（只读查询，不创建）。"""
    return user_log_dir(_APP_NAME, appauthor=False)


def create_export_logger(channel: str) -> "EventLogger":
    """在平台标准日志目录下创建本次导出的 JSONL 日志文件。"""
    logs_dir = user_log_dir(_APP_NAME, appauthor=False)
    os.makedirs(logs_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = uuid4().hex[:12]
    path = os.path.join(logs_dir, f"export-{stamp}-{channel}-{run_id}.jsonl")
    return EventLogger(file_path=path, run_id=run_id, channel=channel)
