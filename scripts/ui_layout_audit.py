from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "src" / "gui" / "main_window.py",
    ROOT / "src" / "gui" / "theme.py",
]

PATTERNS = {
    "fixed_width": re.compile(r"setFixedWidth\("),
    "fixed_size": re.compile(r"setFixedSize\("),
    "min_height_qss": re.compile(r"min-height:\s*(\d+)px"),
}


def main() -> int:
    found = 0
    for path in TARGETS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            if PATTERNS["fixed_width"].search(line) or PATTERNS["fixed_size"].search(
                line
            ):
                print(f"[WARN] {path}:{i} uses fixed size -> {line.strip()}")
                found += 1
            m = PATTERNS["min_height_qss"].search(line)
            if m:
                h = int(m.group(1))
                if h < 30:
                    print(
                        f"[WARN] {path}:{i} small min-height ({h}px) -> {line.strip()}"
                    )
                    found += 1

    if found == 0:
        print("No obvious layout risks found.")
    else:
        print(f"Total warnings: {found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
