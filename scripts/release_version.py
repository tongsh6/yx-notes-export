#!/usr/bin/env python3
"""
跨平台版本发布脚本：更新 VERSION、CHANGELOG，并执行 git 提交与打 tag。

用法（在项目根目录执行）：
  python scripts/release_version.py --bump patch           # 0.2.0 -> 0.2.1
  python scripts/release_version.py --bump minor           # 0.2.0 -> 0.3.0
  python scripts/release_version.py --version 0.3.0         # 指定版本号
  python scripts/release_version.py --bump patch --dry-run # 仅打印将要执行的操作
  python scripts/release_version.py --bump patch --push     # 提交并推送 + 推送 tag + 创建 GitHub Release
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


def find_repo_root() -> Path:
    """项目根目录（含 VERSION 与 CHANGELOG.md 的目录）。"""
    root = Path(__file__).resolve().parent.parent
    if not (root / "VERSION").exists() or not (root / "CHANGELOG.md").exists():
        raise SystemExit("错误：请在项目根目录执行，或确保存在 VERSION 与 CHANGELOG.md")
    return root


def read_version(root: Path) -> str:
    with (root / "VERSION").open(encoding="utf-8") as f:
        return f.read().strip()


def parse_version(v: str) -> tuple[int, int, int]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", v.strip())
    if not m:
        raise SystemExit(f"错误：VERSION 格式须为 MAJOR.MINOR.PATCH，当前为：{v!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_version(current: str, kind: str) -> str:
    major, minor, patch = parse_version(current)
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "major":
        return f"{major + 1}.0.0"
    raise ValueError(f"未知 bump 类型: {kind}")


def update_changelog(content: str, new_version: str, release_date: str) -> str:
    """将 CHANGELOG 中 [Unreleased] 下的内容归入新版本区块。"""
    # 匹配：## [Unreleased] 之后到下一个 ## [ 之前的内容
    unreleased_header = "## [Unreleased]"
    if unreleased_header not in content:
        return content
    idx = content.index(unreleased_header)
    rest = content[idx + len(unreleased_header) :].lstrip("\n")
    # 下一个 ## [ 的位置
    next_section = re.search(r"\n## \[", rest)
    if next_section:
        unreleased_body = rest[: next_section.start()].strip()
        after_unreleased = rest[next_section.start() :]
    else:
        unreleased_body = rest.strip()
        after_unreleased = ""

    new_section = f"## [{new_version}] - {release_date}"
    if unreleased_body:
        new_block = f"\n{new_section}\n\n{unreleased_body}\n"
    else:
        new_block = f"\n{new_section}\n\n（无条目时请手动补充 CHANGELOG）\n"

    before = content[: idx + len(unreleased_header)]
    return before + "\n\n" + new_block.lstrip() + after_unreleased


def extract_release_notes(changelog_text: str, version: str) -> str:
    """从 CHANGELOG 文本中提取指定版本区块内容，用作 GitHub Release 说明。"""
    pattern = rf"\n## \[{re.escape(version)}\] - [^\n]+\n\n(.*?)(?=\n## \[|\Z)"
    m = re.search(pattern, changelog_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return f"详见 [CHANGELOG](https://github.com/tongsh6/yx-notes-export/blob/main/CHANGELOG.md)。"


def create_github_release(root: Path, tag_name: str, notes: str, dry_run: bool) -> bool:
    """创建 GitHub Release（需已安装 gh 并已登录）。"""
    cmd = ["gh", "release", "create", tag_name, "--title", tag_name]
    if dry_run:
        print(f"  [dry-run] gh release create {tag_name} --title {tag_name} --notes <CHANGELOG 区块>")
        return True
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(notes)
        notes_file = f.name
    try:
        r = subprocess.run(
            ["gh", "release", "create", tag_name, "--title", tag_name, "--notes-file", notes_file],
            cwd=root,
        )
        return r.returncode == 0
    finally:
        Path(notes_file).unlink(missing_ok=True)


def run(cmd: list[str], cwd: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return True
    r = subprocess.run(cmd, cwd=cwd)
    return r.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="更新 VERSION、CHANGELOG 并执行 git 提交与打 tag（跨平台）。"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bump", choices=["patch", "minor", "major"], help="自动提升版本号")
    group.add_argument("--version", metavar="X.Y.Z", help="指定新版本号")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要执行的操作，不写入文件、不执行 git",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="提交后推送当前分支并推送 tag",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="只更新 VERSION 与 CHANGELOG，不执行 git commit/tag",
    )
    args = parser.parse_args()

    root = find_repo_root()
    current = read_version(root)
    if args.version:
        new_version = args.version.strip()
        parse_version(new_version)
    else:
        new_version = bump_version(current, args.bump)

    release_date = date.today().isoformat()

    print(f"当前版本: {current}")
    print(f"新版本:   {new_version} ({release_date})")
    if args.dry_run:
        print("（dry-run 模式）")

    # 写入 VERSION
    if not args.dry_run:
        (root / "VERSION").write_text(new_version + "\n", encoding="utf-8")
    else:
        print(f"  [dry-run] 将把 VERSION 写为 {new_version}")

    # 更新 CHANGELOG
    changelog_path = root / "CHANGELOG.md"
    changelog_content = changelog_path.read_text(encoding="utf-8")
    new_changelog = update_changelog(changelog_content, new_version, release_date)
    if new_changelog != changelog_content:
        if not args.dry_run:
            changelog_path.write_text(new_changelog, encoding="utf-8")
        else:
            print("  [dry-run] 将更新 CHANGELOG.md 中 [Unreleased] 为新区块")

    if args.no_commit:
        print("已更新 VERSION 与 CHANGELOG（未提交）。")
        return 0

    tag_name = f"v{new_version}"
    commit_message = f"Release {tag_name}"

    if not run(["git", "add", "VERSION", "CHANGELOG.md"], root, args.dry_run):
        print("错误：git add 失败", file=sys.stderr)
        return 1
    if not run(["git", "commit", "-m", commit_message], root, args.dry_run):
        print("错误：git commit 失败（可能无变更或未配置 user）", file=sys.stderr)
        return 1
    if not run(["git", "tag", "-a", tag_name, "-m", tag_name], root, args.dry_run):
        print("错误：git tag 失败", file=sys.stderr)
        return 1

    if args.push and not args.dry_run:
        if not run(["git", "push", "origin", "HEAD"], root, False):
            print("错误：git push 失败", file=sys.stderr)
            return 1
        if not run(["git", "push", "origin", tag_name], root, False):
            print("错误：git push tag 失败", file=sys.stderr)
            return 1
        print(f"已推送分支与 tag {tag_name}")
        # 创建 GitHub Release（从 CHANGELOG 提取本版本说明）
        release_notes = extract_release_notes(new_changelog, new_version)
        if create_github_release(root, tag_name, release_notes, dry_run=False):
            print(f"已创建 GitHub Release: {tag_name}")
        else:
            print("警告：创建 GitHub Release 失败（请确认已安装 gh 并执行 gh auth login）", file=sys.stderr)
    elif args.push and args.dry_run:
        print(f"  [dry-run] 将执行: git push origin HEAD && git push origin {tag_name}")
        release_notes = extract_release_notes(new_changelog, new_version)
        create_github_release(root, tag_name, release_notes, dry_run=True)

    print(f"完成：{tag_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
