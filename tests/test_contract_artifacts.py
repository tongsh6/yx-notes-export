import json

from click.testing import CliRunner

import main as cli_main
from src.fetcher import NotebookInfo


class _Meta:
    def __init__(self, guid: str, title: str, notebook_guid: str) -> None:
        self.guid = guid
        self.title = title
        self.notebook_guid = notebook_guid


class _FakeFetcher:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def list_notebooks(self):
        return [NotebookInfo(guid="nb1", name="NB", stack=None)]

    def iter_notes(self, notebook_guid=None, note_guid=None):
        if note_guid:
            yield _Meta(guid=note_guid, title="N1", notebook_guid="nb1")
            return
        if notebook_guid == "nb1":
            yield _Meta(guid="n1", title="N1", notebook_guid="nb1")


class _FakeExporterOK:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def export_note(self, _meta, _nb, _used_filenames):
        return ("/tmp/fake.md", False)


class _FakeExporterFail:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def export_note(self, _meta, _nb, _used_filenames):
        raise TimeoutError("socket timeout")


def _write_config(path, output_dir: str):
    path.write_text(
        "\n".join(
            [
                "auth:",
                "  mode: token",
                "  token: fake-token",
                "export:",
                f"  output_dir: {output_dir}",
            ]
        ),
        encoding="utf-8",
    )


def test_contract_summary_schema_and_default_output(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    out = tmp_path / "out"
    _write_config(cfg, str(out))

    monkeypatch.setattr(cli_main, "build_client", lambda _cfg: object())
    monkeypatch.setattr(cli_main, "Fetcher", _FakeFetcher)
    monkeypatch.setattr(cli_main, "Exporter", _FakeExporterOK)

    result = CliRunner().invoke(
        cli_main.main,
        ["--config", str(cfg), "--all"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    summary_path = out / "export-summary.json"
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required_keys = {
        "success",
        "failed",
        "skipped",
        "processed",
        "elapsed_sec",
        "avg_sec_per_note",
        "retries_total",
        "retries_by_reason",
        "failure_reasons_top",
        "failure_codes_top",
        "output_dir",
        "stopped",
    }
    assert required_keys.issubset(summary.keys())
    assert isinstance(summary["failure_codes_top"], list)
    assert isinstance(summary["retries_by_reason"], dict)


def test_contract_summary_json_argument_and_failures_columns(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    out = tmp_path / "out"
    _write_config(cfg, str(out))
    custom_summary = tmp_path / "artifacts" / "my-summary.json"

    monkeypatch.setattr(cli_main, "build_client", lambda _cfg: object())
    monkeypatch.setattr(cli_main, "Fetcher", _FakeFetcher)
    monkeypatch.setattr(cli_main, "Exporter", _FakeExporterFail)

    result = CliRunner().invoke(
        cli_main.main,
        [
            "--config",
            str(cfg),
            "--all",
            "--summary-json",
            str(custom_summary),
            "--fail-log",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert custom_summary.exists()

    failures = out / "export-failures.txt"
    assert failures.exists()
    row = failures.read_text(encoding="utf-8").strip().split("\n")[0]
    cols = row.split("\t")
    assert len(cols) == 4
    assert cols[2] == "network_timeout"
    assert cols[3] == "socket timeout"
