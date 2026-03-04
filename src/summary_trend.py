from __future__ import annotations

import json
from typing import Iterable


def load_summary_files(paths: Iterable[str]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, dict):
            normalized: dict[str, object] = {}
            for key, value in data.items():
                if isinstance(key, str):
                    normalized[key] = value
            items.append(normalized)
    return items


def aggregate_summary_trend(
    summaries: Iterable[dict[str, object]],
) -> dict[str, float | int]:
    runs = 0
    total_success_rate = 0.0
    total_failed_rate = 0.0
    total_elapsed = 0.0
    total_avg_sec_per_note = 0.0
    retry_runs = 0
    total_retries = 0

    for summary in summaries:
        runs += 1
        success = _to_float(summary.get("success"), default=0.0)
        failed = _to_float(summary.get("failed"), default=0.0)
        skipped = _to_float(summary.get("skipped"), default=0.0)
        processed = _to_float(
            summary.get("processed"), default=success + failed + skipped
        )
        if processed > 0:
            total_success_rate += success / processed
            total_failed_rate += failed / processed
        total_elapsed += _to_float(summary.get("elapsed_sec"), default=0.0)
        total_avg_sec_per_note += _to_float(
            summary.get("avg_sec_per_note"), default=0.0
        )
        retries = _to_float(summary.get("retries_total"), default=0.0)
        total_retries += int(retries)
        if retries > 0:
            retry_runs += 1

    if runs == 0:
        return {
            "runs": 0,
            "avg_success_rate": 0.0,
            "avg_failed_rate": 0.0,
            "avg_elapsed_sec": 0.0,
            "avg_sec_per_note": 0.0,
            "retry_runs": 0,
            "avg_retries_per_run": 0.0,
        }

    return {
        "runs": runs,
        "avg_success_rate": round(total_success_rate / runs, 4),
        "avg_failed_rate": round(total_failed_rate / runs, 4),
        "avg_elapsed_sec": round(total_elapsed / runs, 3),
        "avg_sec_per_note": round(total_avg_sec_per_note / runs, 3),
        "retry_runs": retry_runs,
        "avg_retries_per_run": round(total_retries / runs, 3),
    }


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default
