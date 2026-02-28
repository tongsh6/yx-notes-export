# YX Notes Export

A Python tool to export Yinxiang Notes (Evernote China) content to Markdown using official APIs.

## Features

- Export all notes, a notebook, or a single note by GUID
- Preserve note content, metadata, tags, and resources
- GUI mode (`PySide6`) and CLI mode
- Retry, timeout handling, and structured run logs
- Resume mode and failed-item re-export support

## Requirements

- Python 3.11+
- Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Quick Start

### GUI

```bash
python gui_main.py
```

### CLI

```bash
python main.py --all --output ./output
python main.py --notebook "Notebook Name" --output ./output
python main.py --note "NOTE_GUID" --output ./output
```

## Configuration

Copy the example file and update your credentials:

```bash
copy config.example.yaml config.yaml
```

> Do not commit `config.yaml`. It may contain private tokens.

## Tests

```bash
python -m pytest -q
```

## Project Structure

- `src/` core logic
- `src/gui/` GUI implementation
- `tests/` automated tests
- `context/` project context and engineering knowledge base
- `scripts/` helper scripts for regression and diagnostics

## License

MIT
