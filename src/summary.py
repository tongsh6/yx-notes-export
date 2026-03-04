from __future__ import annotations

from collections import Counter
import json
import os
from typing import Iterable


def build_export_summary(
    *,
    success: int,
    failed: int,
    skipped: int,
    elapsed_sec: float,
    retries_total: int,
    retries_by_reason: dict[str, int] | None,
    failed_errors: Iterable[str],
    failed_error_codes: Iterable[str],
    output_dir: str,
    stopped: bool,
) -> dict[str, object]:
    processed = success + failed + skipped
    avg_sec_per_note = elapsed_sec / processed if processed > 0 else 0.0
    reason_counter = Counter(_normalize_reason(err) for err in failed_errors if err)
    top_reasons = [
        {"reason": reason, "count": count}
        for reason, count in reason_counter.most_common(3)
    ]
    code_counter = Counter(code for code in failed_error_codes if code)
    top_codes = [
        {"error_code": code, "count": count}
        for code, count in code_counter.most_common(3)
    ]
    return {
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "processed": processed,
        "elapsed_sec": round(max(0.0, elapsed_sec), 3),
        "avg_sec_per_note": round(avg_sec_per_note, 3),
        "retries_total": retries_total,
        "retries_by_reason": dict(retries_by_reason or {}),
        "failure_reasons_top": top_reasons,
        "failure_codes_top": top_codes,
        "output_dir": output_dir,
        "stopped": stopped,
    }


def format_summary_lines(summary: dict[str, object]) -> list[str]:
    lines = [
        "导出摘要："
        f" 用时 {summary.get('elapsed_sec', 0)}s，"
        f"平均 {summary.get('avg_sec_per_note', 0)}s/条，"
        f"重试 {summary.get('retries_total', 0)} 次"
    ]
    top = summary.get("failure_reasons_top")
    if isinstance(top, list) and top:
        brief = []
        for item in top:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason", "unknown"))
            count = int(item.get("count", 0))
            brief.append(f"{reason} x{count}")
        if brief:
            lines.append("失败原因 Top: " + " | ".join(brief))
    top_codes = summary.get("failure_codes_top")
    if isinstance(top_codes, list) and top_codes:
        brief_codes = []
        for item in top_codes:
            if not isinstance(item, dict):
                continue
            code = str(item.get("error_code", "unknown_error"))
            count = int(item.get("count", 0))
            brief_codes.append(f"{code} x{count}")
        if brief_codes:
            lines.append("失败代码 Top: " + " | ".join(brief_codes))
    return lines


def _normalize_reason(error: str) -> str:
    msg = (error or "").strip()
    if not msg:
        return "unknown"
    first = msg.split(":", 1)[0].strip()
    return first or msg


def write_export_summary(summary: dict[str, object], output_path: str) -> str:
    resolved = os.path.abspath(output_path)
    parent = os.path.dirname(resolved)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return resolved
