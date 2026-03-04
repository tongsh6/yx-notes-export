import json

from src.summary_trend import aggregate_summary_trend, load_summary_files


def test_load_summary_files_and_aggregate(tmp_path):
    f1 = tmp_path / "export-summary-1.json"
    f2 = tmp_path / "export-summary-2.json"
    bad = tmp_path / "broken.json"

    f1.write_text(
        json.dumps(
            {
                "success": 8,
                "failed": 2,
                "skipped": 0,
                "processed": 10,
                "elapsed_sec": 40,
                "avg_sec_per_note": 4,
                "retries_total": 3,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    f2.write_text(
        json.dumps(
            {
                "success": 5,
                "failed": 1,
                "skipped": 4,
                "processed": 10,
                "elapsed_sec": 20,
                "avg_sec_per_note": 2,
                "retries_total": 0,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    bad.write_text("{not-json", encoding="utf-8")

    summaries = load_summary_files([str(f1), str(f2), str(bad)])
    trend = aggregate_summary_trend(summaries)

    assert len(summaries) == 2
    assert trend["runs"] == 2
    assert trend["avg_success_rate"] == 0.65
    assert trend["avg_failed_rate"] == 0.15
    assert trend["avg_elapsed_sec"] == 30.0
    assert trend["avg_sec_per_note"] == 3.0
    assert trend["retry_runs"] == 1
    assert trend["avg_retries_per_run"] == 1.5
