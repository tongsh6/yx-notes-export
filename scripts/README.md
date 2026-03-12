# 脚本说明 (Scripts)

## `release_version.py`
跨平台版本发布：更新 VERSION、将 CHANGELOG 中 [Unreleased] 归入新版本、提交并打 tag。使用 `--push` 时会自动创建 GitHub Release（需安装 [GitHub CLI](https://cli.github.com/) 并执行 `gh auth login`）。

用法（在项目根目录执行）：

```bash
python scripts/release_version.py --bump patch          # 0.2.0 -> 0.2.1
python scripts/release_version.py --bump minor          # 0.2.0 -> 0.3.0
python scripts/release_version.py --version 0.3.0       # 指定版本号
python scripts/release_version.py --bump patch --dry-run # 仅预览，不写入、不提交
python scripts/release_version.py --bump patch --push   # 提交并推送分支与 tag，并创建 GitHub Release（需 gh）
python scripts/release_version.py --bump patch --no-commit # 只改 VERSION/CHANGELOG，不 git commit/tag
```

## `gui_regression.ps1`
快速执行 GUI 相关回归测试。

用法：

```powershell
./scripts/gui_regression.ps1
./scripts/gui_regression.ps1 -Screenshot
./scripts/gui_regression.ps1 -Full
```

## `gui_regression.sh`
快速执行 GUI 相关回归测试（macOS/Linux）。

用法：

```bash
./scripts/gui_regression.sh
./scripts/gui_regression.sh --screenshot
./scripts/gui_regression.sh --full
```

## `export_stall_report.py`
汇总结构化日志中的卡顿/重试事件，辅助定位“看起来卡住”的原因。

用法：

```text
# Windows (PowerShell)
py -3 scripts/export_stall_report.py
py -3 scripts/export_stall_report.py --dir "C:\Users\<you>\AppData\Local\YxNotesExport\Logs"
py -3 scripts/export_stall_report.py --log "C:\path\export-xxx.jsonl"

# macOS/Linux (bash)
python3 scripts/export_stall_report.py
python3 scripts/export_stall_report.py --dir "$HOME/Library/Logs/YxNotesExport"
python3 scripts/export_stall_report.py --log "/path/export-xxx.jsonl"
```

## `ui_layout_audit.py`
扫描 GUI 关键文件中的常见布局风险（固定尺寸、过小最小高度）。

用法：

```text
# Windows (PowerShell)
py -3 scripts/ui_layout_audit.py

# macOS/Linux (bash)
python3 scripts/ui_layout_audit.py
```

## `export_summary_trend.py`
聚合多次导出的 `export-summary.json`，输出成功率/失败率/耗时趋势。

用法：

```text
# 当前目录扫描
python3 scripts/export_summary_trend.py

# 指定目录（递归）
python scripts/export_summary_trend.py --dir ./output --recursive

# 指定匹配模式
python scripts/export_summary_trend.py --dir ./artifacts --pattern "*summary*.json" --recursive
```
