# 脚本说明 (Scripts)

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
python scripts/export_stall_report.py
python scripts/export_stall_report.py --dir "C:\Users\<you>\AppData\Local\YxNotesExport\Logs"
python scripts/export_stall_report.py --log "C:\path\export-xxx.jsonl"

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
python scripts/ui_layout_audit.py

# macOS/Linux (bash)
python3 scripts/ui_layout_audit.py
```
