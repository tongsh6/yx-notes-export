from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from platformdirs import user_log_dir


def find_latest_log(log_dir: Path) -> Path | None:
    files = sorted(log_dir.glob("export-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def parse_events(log_file: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize stall/retry events from exporter JSONL logs."
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Path to a JSONL log file. Defaults to latest file in app log dir.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(user_log_dir("YxNotesExport", appauthor=False)),
        help="Directory containing export-*.jsonl files.",
    )
    args = parser.parse_args()

    log_file = args.log or find_latest_log(args.dir)
    if log_file is None or not log_file.exists():
        print("No log file found.")
        return 1

    events = parse_events(log_file)
    if not events:
        print(f"No events parsed: {log_file}")
        return 1

    stall_events = [e for e in events if e.get("event") == "export.stall_hint"]
    retry_events = [e for e in events if e.get("event") == "api_req_retry"]
    wait_reasons = Counter(str(e.get("reason", "unknown")) for e in retry_events)

    print(f"Log: {log_file}")
    print(f"Total events: {len(events)}")
    print(f"Stall hints: {len(stall_events)}")
    if stall_events:
        last_stall = stall_events[-1]
        print(
            "Last stall: "
            f"idle={last_stall.get('idle_sec', '?')}s, "
            f"status={last_stall.get('last_status', '')}"
        )

    print("Retry reasons:")
    if wait_reasons:
        for reason, count in wait_reasons.most_common():
            print(f"- {reason}: {count}")
    else:
        print("- none")

    failures = [e for e in events if str(e.get("level", "")).upper() == "ERROR"]
    print(f"Error-level events: {len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
