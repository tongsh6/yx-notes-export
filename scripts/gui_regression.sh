#!/usr/bin/env bash
set -euo pipefail

SCREENSHOT=0
FULL=0

for arg in "$@"; do
  case "$arg" in
    --screenshot)
      SCREENSHOT=1
      ;;
    --full)
      FULL=1
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: ./scripts/gui_regression.sh [--screenshot] [--full]" >&2
      exit 2
      ;;
  esac
done

if [[ "$SCREENSHOT" -eq 1 ]]; then
  export YX_SCREENSHOT=1
else
  unset YX_SCREENSHOT || true
fi

echo "[1/2] Running targeted GUI regressions..."
python3 -m pytest tests/test_gui_e2e.py tests/test_fetcher_retry.py -q

if [[ "$FULL" -eq 1 ]]; then
  echo "[2/2] Running full test suite..."
  python3 -m pytest -q
fi

echo "Done."
