from src.summary import build_export_summary, format_summary_lines, write_export_summary


def test_build_export_summary_includes_retry_and_top_failure_reasons():
    summary = build_export_summary(
        success=3,
        failed=2,
        skipped=1,
        elapsed_sec=12.5,
        retries_total=4,
        retries_by_reason={"timeout": 3, "rate_limit": 1},
        failed_errors=["TimeoutError: read timed out", "TimeoutError: socket timeout"],
        failed_error_codes=["network_timeout", "network_timeout"],
        output_dir="/tmp/out",
        stopped=False,
    )

    assert summary.get("processed") == 6
    assert summary.get("retries_total") == 4
    assert summary.get("retries_by_reason") == {"timeout": 3, "rate_limit": 1}

    top = summary.get("failure_reasons_top")
    assert isinstance(top, list)
    assert len(top) > 0
    first = top[0]
    assert isinstance(first, dict)
    assert first.get("reason") == "TimeoutError"
    assert first.get("count") == 2

    top_codes = summary.get("failure_codes_top")
    assert isinstance(top_codes, list)
    assert len(top_codes) > 0
    first_code = top_codes[0]
    assert isinstance(first_code, dict)
    assert first_code.get("error_code") == "network_timeout"
    assert first_code.get("count") == 2

    lines = format_summary_lines(summary)
    assert any("重试 4 次" in line for line in lines)
    assert any("TimeoutError x2" in line for line in lines)
    assert any("network_timeout x2" in line for line in lines)


def test_write_export_summary_creates_json_file(tmp_path):
    path = write_export_summary(
        {"runs": 1, "ok": True}, str(tmp_path / "export-summary.json")
    )
    assert path.endswith("export-summary.json")
    assert (tmp_path / "export-summary.json").exists()
