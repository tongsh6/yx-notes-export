# Scripts

## gui_regression.ps1
Runs GUI-related regressions quickly.

Usage:

```powershell
./scripts/gui_regression.ps1
./scripts/gui_regression.ps1 -Screenshot
./scripts/gui_regression.ps1 -Full
```

## export_stall_report.py
Summarizes stall/retry patterns from exporter JSONL logs.

Usage:

```powershell
python scripts/export_stall_report.py
python scripts/export_stall_report.py --dir "C:\Users\<you>\AppData\Local\YxNotesExport\Logs"
python scripts/export_stall_report.py --log "C:\path\export-xxx.jsonl"
```

## ui_layout_audit.py
Scans key GUI files for common layout risk patterns (fixed sizes, tiny min-height).

Usage:

```powershell
python scripts/ui_layout_audit.py
```
