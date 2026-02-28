param(
    [switch]$Screenshot,
    [switch]$Full
)

$ErrorActionPreference = "Stop"

if ($Screenshot) {
    $env:YX_SCREENSHOT = "1"
} else {
    Remove-Item Env:YX_SCREENSHOT -ErrorAction SilentlyContinue
}

Write-Host "[1/2] Running targeted GUI regressions..."
python -m pytest tests/test_gui_e2e.py tests/test_fetcher_retry.py -q

if ($Full) {
    Write-Host "[2/2] Running full test suite..."
    python -m pytest -q
}

Write-Host "Done."
