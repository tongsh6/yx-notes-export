"""
印象笔记导出工具 — CLI 入口

用法示例：
  python main.py --all                          # 导出全部笔记
  python main.py --notebook "工作"              # 导出指定笔记本
  python main.py --note <GUID>                  # 导出单条笔记
  python main.py --all --output ./my-notes      # 指定输出目录
  python main.py --config custom.yaml --all     # 指定配置文件
"""

from __future__ import annotations

import os
import sys
from time import monotonic
from typing import Optional

import click
import yaml
from tqdm import tqdm

from src.auth import AuthConfig, build_client
from src.error_codes import classify_export_error
from src.event_log import NullEventLogger, create_export_logger, get_log_dir
from src.exporter import Exporter
from src.fetcher import Fetcher, NotebookInfo
from src.summary import build_export_summary, format_summary_lines, write_export_summary


# ── CLI 定义 ─────────────────────────────────────────────────────────────────


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--config", default="config.yaml", show_default=True, help="配置文件路径")
@click.option(
    "--all", "export_all", is_flag=True, default=False, help="导出账户下所有笔记"
)
@click.option(
    "--notebook",
    "notebook_name",
    default=None,
    metavar="NAME",
    help="导出指定名称的笔记本（精确匹配）",
)
@click.option(
    "--note", "note_guid", default=None, metavar="GUID", help="导出指定 GUID 的单条笔记"
)
@click.option(
    "--output",
    "output_dir",
    default=None,
    metavar="DIR",
    help="导出根目录（覆盖 config.yaml 中的设置）",
)
@click.option(
    "--resume/--no-resume",
    "resume",
    default=True,
    help="断点续传（跳过已导出且未更新的笔记）",
)
@click.option(
    "--incremental",
    "incremental",
    is_flag=True,
    default=False,
    help="增量导出：仅导出新增或已修改的笔记（依赖本地 .export-index.json，隐含 --resume）",
)
@click.option(
    "--fail-log/--no-fail-log",
    "fail_log",
    default=True,
    help="保存失败记录到输出目录",
)
@click.option(
    "--only-failed-log",
    "only_failed_log",
    default=None,
    metavar="FILE",
    help="仅重导失败记录文件中的 GUID（export-failures.txt）",
)
@click.option(
    "--summary-json",
    "summary_json",
    default=None,
    metavar="FILE",
    help="可选：自定义导出摘要 JSON 路径（默认输出到 output/export-summary.json）",
)
def main(
    config: str,
    export_all: bool,
    notebook_name: Optional[str],
    note_guid: Optional[str],
    output_dir: Optional[str],
    resume: bool,
    incremental: bool,
    fail_log: bool,
    only_failed_log: Optional[str],
    summary_json: Optional[str],
) -> None:
    """印象笔记批量导出工具 — 按层级结构导出为 Markdown"""

    # ── 1. 加载配置 ──────────────────────────────────────────────────────────
    cfg = _load_config(config)
    resolved_output = output_dir or cfg.get("export", {}).get("output_dir", "./output")
    try:
        event_logger = create_export_logger("cli")
        click.echo(f"日志目录：{get_log_dir()}")
    except Exception:
        event_logger = NullEventLogger()

    # ── 2. 校验导出模式 ───────────────────────────────────────────────────────
    modes = [export_all, bool(notebook_name), bool(note_guid), bool(only_failed_log)]
    if sum(modes) == 0:
        click.echo(
            "错误：请指定导出范围：--all / --notebook NAME / --note GUID / --only-failed-log FILE",
            err=True,
        )
        click.echo("使用 -h 查看帮助", err=True)
        sys.exit(1)
    if sum(modes) > 1:
        click.echo(
            "错误：--all、--notebook、--note、--only-failed-log 不能同时使用", err=True
        )
        sys.exit(1)

    # ── 3. 认证 ───────────────────────────────────────────────────────────────
    auth_cfg = _parse_auth(cfg)
    click.echo(f"认证方式：{auth_cfg.mode}")
    try:
        client = build_client(auth_cfg)
    except Exception as e:
        event_logger.emit("auth.failed", level="ERROR", error=str(e))
        click.echo(f"认证失败：{e}", err=True)
        sys.exit(1)
    click.echo("认证成功 ✓")
    event_logger.emit("auth.ok", mode=auth_cfg.mode)

    retry_summary = {"total": 0, "by_reason": {}}

    def _on_fetch_status(event: str, _api_name: str, data: dict[str, object]) -> None:
        if event != "api_wait_retry":
            return
        retry_summary["total"] += 1
        reason = str(data.get("reason", "unknown"))
        by_reason = retry_summary["by_reason"]
        by_reason[reason] = int(by_reason.get(reason, 0)) + 1

    fetcher = Fetcher(client, status_cb=_on_fetch_status, event_logger=event_logger)
    resume_effective = resume or incremental
    exporter = Exporter(fetcher, resolved_output, resume=resume_effective)
    session_started = monotonic()

    # ── 4. 构建笔记本索引 ────────────────────────────────────────────────────
    click.echo("正在获取笔记本列表 …")
    all_notebooks = fetcher.list_notebooks()
    nb_index = {nb.guid: nb for nb in all_notebooks}

    # ── 5. 确定要导出的笔记本范围 ────────────────────────────────────────────
    failed_guids: list[str] = []
    if only_failed_log:
        if not os.path.exists(only_failed_log):
            click.echo(f"错误：失败记录文件不存在：{only_failed_log}", err=True)
            sys.exit(1)
        with open(only_failed_log, encoding="utf-8") as f:
            for line in f:
                cols = line.rstrip("\n").split("\t")
                if cols and cols[0].strip():
                    failed_guids.append(cols[0].strip())
        if not failed_guids:
            click.echo("错误：失败记录文件中没有可用 GUID", err=True)
            sys.exit(1)
        target_notebooks = []
        target_note_guid = None
    elif export_all:
        target_notebooks = all_notebooks
        target_note_guid = None
    elif notebook_name:
        nb = _find_notebook(all_notebooks, notebook_name)
        if nb is None:
            click.echo(f"错误：找不到笔记本「{notebook_name}」", err=True)
            click.echo(
                "可用笔记本：" + ", ".join(n.name for n in all_notebooks), err=True
            )
            sys.exit(1)
        target_notebooks = [nb]
        target_note_guid = None
    else:  # note_guid
        target_notebooks = []
        target_note_guid = note_guid

    # ── 6. 执行导出 ──────────────────────────────────────────────────────────
    used_filenames: dict[str, set[str]] = {}
    total_ok = 0
    total_fail = 0
    total_skip = 0
    failed_items: list[tuple[str, str, str, str]] = []
    event_logger.emit(
        "session_start",
        output_dir=os.path.abspath(resolved_output),
        resume=resume_effective,
        incremental=incremental,
        scope=(
            "failed"
            if bool(only_failed_log)
            else "note"
            if bool(target_note_guid)
            else "notebooks"
        ),
    )

    if failed_guids:
        click.echo(f"仅重导失败记录：{len(failed_guids)} 条")
        metas = []
        for guid in failed_guids:
            metas.extend(list(fetcher.iter_notes(note_guid=guid)))
        ok, fail, skip = _export_notes(
            metas,
            nb_index,
            exporter,
            used_filenames,
            failed_items,
            event_logger,
            show_progress=True,
        )
        total_ok, total_fail, total_skip = ok, fail, skip
    elif target_note_guid:
        # 单条笔记导出
        click.echo(f"导出笔记 GUID={target_note_guid} …")
        note_metas = list(fetcher.iter_notes(note_guid=target_note_guid))
        if not note_metas:
            click.echo("错误：未找到该笔记", err=True)
            sys.exit(1)
        meta = note_metas[0]
        nb = nb_index.get(meta.notebook_guid) or _fallback_notebook(meta.notebook_guid)
        ok, fail, skip = _export_notes(
            [meta],
            nb_index,
            exporter,
            used_filenames,
            failed_items,
            event_logger,
            show_progress=False,
        )
        total_ok, total_fail, total_skip = ok, fail, skip
    else:
        for nb in target_notebooks:
            click.echo(f"  笔记本：{_nb_label(nb)}")
            note_metas = list(
                tqdm(
                    fetcher.iter_notes(notebook_guid=nb.guid),
                    desc=f"    拉取",
                    unit="条",
                    leave=False,
                )
            )
            if incremental:
                to_export = exporter.filter_notes_to_export(note_metas, nb)
                click.echo(f"    增量：共 {len(note_metas)} 条，需导出 {len(to_export)} 条")
                note_metas = to_export
            ok, fail, skip = _export_notes(
                note_metas,
                nb_index,
                exporter,
                used_filenames,
                failed_items,
                event_logger,
                show_progress=True,
            )
            total_ok += ok
            total_fail += fail
            total_skip += skip

    # ── 7. 汇总 ──────────────────────────────────────────────────────────────
    click.echo(
        f"\n导出完成：成功 {total_ok} 条，失败 {total_fail} 条，跳过 {total_skip} 条"
    )
    event_logger.emit(
        "session_done",
        success=total_ok,
        failed=total_fail,
        skipped=total_skip,
    )
    summary = build_export_summary(
        success=total_ok,
        failed=total_fail,
        skipped=total_skip,
        elapsed_sec=monotonic() - session_started,
        retries_total=int(retry_summary["total"]),
        retries_by_reason=dict(retry_summary["by_reason"]),
        failed_errors=[err for _guid, _title, _code, err in failed_items],
        failed_error_codes=[code for _guid, _title, code, _err in failed_items],
        output_dir=os.path.abspath(resolved_output),
        stopped=False,
    )
    for line in format_summary_lines(summary):
        click.echo(line)
    summary_path = summary_json or os.path.join(resolved_output, "export-summary.json")
    summary_path = write_export_summary(summary, summary_path)
    click.echo(f"摘要文件：{summary_path}")
    click.echo(f"输出目录：{os.path.abspath(resolved_output)}")
    if fail_log and failed_items:
        path = os.path.join(resolved_output, "export-failures.txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for guid, title, error_code, err in failed_items:
                f.write(f"{guid}\t{title}\t{error_code}\t{err}\n")
        click.echo(f"失败记录：{path}")


# ── 辅助函数 ─────────────────────────────────────────────────────────────────


def _export_notes(
    note_metas,
    nb_index,
    exporter,
    used_filenames,
    failed_items,
    event_logger,
    show_progress,
):
    ok = fail = skip = 0
    iterator = (
        tqdm(note_metas, desc="    导出", unit="条") if show_progress else note_metas
    )
    for meta in iterator:
        nb = nb_index.get(meta.notebook_guid) or _fallback_notebook(meta.notebook_guid)
        try:
            _path, did_skip = exporter.export_note(meta, nb, used_filenames)
            if did_skip:
                skip += 1
                event_logger.emit(
                    "note.skipped",
                    note_guid=meta.guid,
                    note_title=meta.title,
                    notebook_guid=meta.notebook_guid,
                )
            else:
                ok += 1
                event_logger.emit(
                    "note.exported",
                    note_guid=meta.guid,
                    note_title=meta.title,
                    notebook_guid=meta.notebook_guid,
                )
        except Exception as e:
            click.echo(f"\n  ✗ 《{meta.title}》导出失败：{e}", err=True)
            fail += 1
            error_msg = str(e)
            error_code = classify_export_error(error_msg)
            failed_items.append((meta.guid, meta.title, error_code, error_msg))
            event_logger.emit(
                "note.failed",
                level="ERROR",
                note_guid=meta.guid,
                note_title=meta.title,
                notebook_guid=meta.notebook_guid,
                error=error_msg,
                error_code=error_code,
            )
    return ok, fail, skip


def _load_config(path: str) -> dict:
    if not os.path.exists(path):
        click.echo(f"错误：配置文件不存在：{path}", err=True)
        click.echo("请复制 config.yaml 并填写认证信息", err=True)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_auth(cfg: dict) -> AuthConfig:
    auth = cfg.get("auth", {})
    return AuthConfig(
        mode=auth.get("mode", "token"),
        token=auth.get("token"),
        username=auth.get("username"),
        password=auth.get("password"),
        consumer_key=auth.get("consumer_key"),
        consumer_secret=auth.get("consumer_secret"),
    )


def _find_notebook(notebooks, name: str):
    for nb in notebooks:
        if nb.name == name:
            return nb
    return None


def _nb_label(nb: NotebookInfo) -> str:
    return f"{nb.stack}/{nb.name}" if nb.stack else nb.name


def _fallback_notebook(guid: str) -> NotebookInfo:
    """当笔记本索引中找不到时的兜底（不影响导出，放到根目录下）。"""
    from src.fetcher import NotebookInfo

    return NotebookInfo(guid=guid, name="未知笔记本", stack=None)


if __name__ == "__main__":
    main()
