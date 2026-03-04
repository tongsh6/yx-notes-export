from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.summary_trend import aggregate_summary_trend, load_summary_files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        dest="dir_path",
        default=".",
        help="summary 搜索目录（默认当前目录）",
    )
    parser.add_argument(
        "--pattern",
        default="export-summary*.json",
        help="文件名匹配模式（glob）",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=False,
        help="是否递归搜索子目录",
    )
    args = parser.parse_args()

    root = Path(args.dir_path)
    if not root.exists() or not root.is_dir():
        print(f"目录不存在：{root}")
        return 1

    paths = (
        sorted(root.rglob(args.pattern))
        if args.recursive
        else sorted(root.glob(args.pattern))
    )
    summaries = load_summary_files(str(p) for p in paths)
    trend = aggregate_summary_trend(summaries)

    print(f"扫描文件数：{len(paths)}")
    print(f"有效 summary：{trend['runs']}")
    print(f"平均成功率：{trend['avg_success_rate']:.2%}")
    print(f"平均失败率：{trend['avg_failed_rate']:.2%}")
    print(f"平均总耗时：{trend['avg_elapsed_sec']:.2f}s")
    print(f"平均单条耗时：{trend['avg_sec_per_note']:.2f}s")
    print(f"重试发生次数：{trend['retry_runs']} runs")
    print(f"每次运行平均重试：{trend['avg_retries_per_run']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
