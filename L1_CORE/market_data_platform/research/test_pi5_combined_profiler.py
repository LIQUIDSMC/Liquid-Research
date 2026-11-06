"""Small synthetic combined-pipeline and publication tests."""
import copy
import json
from pathlib import Path

import pytest

from L1_CORE.market_data_platform.research import (
    pi5_combined_profiler as profiler,
    run_trade_flow_vs_momentum_screen as runner,
    trade_flow_vs_momentum_screen as kernel,
)


def test_actual_combined_pipeline_stays_in_fixture_and_restores_globals(
    tmp_path, monkeypatch
):
    attempt = tmp_path / "attempt"
    attempt.mkdir(mode=0o700)
    original_root = runner.CANONICAL_TRADES_ROOT
    original_read = runner.pq.read_table
    original_kernel = kernel.compute_screen
    calls = []

    def checked(*args):
        calls.append(len(args[0]))
        return original_kernel(*args)

    monkeypatch.setattr(kernel, "compute_screen", checked)
    record = profiler.measure(6000, attempt, files_per_partition=1)
    assert calls == [6000] * 48
    assert record["loaded_target_rows"] == 6000
    assert record["input_array_bytes"] == 6000 * 33
    assert record["fixture_files"] == 3
    assert record["synthetic_read_calls"] == 6
    assert record["kernel_calls"] == record["instrument_day_count"] == 48
    assert record["report_classification"] == "COMPLETE_DESCRIPTIVE"
    assert 0 < record["report_bytes"] <= 1024**2
    assert len(record["report_sha256"]) == 64
    assert set(record["phase_seconds"]) == set(profiler.PHASES)
    assert runner.CANONICAL_TRADES_ROOT == original_root
    assert runner.pq.read_table is original_read
    assert len(list((attempt / "synthetic-trades").glob("*/*.parquet"))) == 3


def test_loader_failure_restores_globals_and_retains_fixture(tmp_path, monkeypatch):
    attempt = tmp_path / "attempt"
    attempt.mkdir(mode=0o700)
    original_root = runner.CANONICAL_TRADES_ROOT
    original_read = runner.pq.read_table

    def fail(*args):
        raise RuntimeError("synthetic loader failure")

    monkeypatch.setattr(runner, "count_target_rows", fail)
    with pytest.raises(RuntimeError, match="synthetic loader failure"):
        profiler.measure(100, attempt, files_per_partition=1)
    assert runner.CANONICAL_TRADES_ROOT == original_root
    assert runner.pq.read_table is original_read
    assert (attempt / "synthetic-trades").is_dir()


def valid_record(attempt):
    rows = 678382
    return {
        "version": profiler.VERSION,
        "stage": "synthetic_loader_kernel_adapter_reporting",
        "row_count": rows, "loaded_target_rows": rows,
        "input_array_bytes": rows * 33,
        "fixture_root": str(attempt / "synthetic-trades"),
        "fixture_files": 26865, "fixture_rows": rows + 80595,
        "control_rows": 80595, "expected_selected_rows": rows,
        "compression": "NONE", "synthetic_read_calls": 53730,
        "selected_ids_verified": True, "replication_policy": profiler.POLICY,
        "kernel_calls": 48, "instrument_day_count": 48,
        "report_classification": "COMPLETE_DESCRIPTIVE",
        "fixture_logical_bytes": 1000, "report_bytes": 1000,
        "report_sha256": "a" * 64, "peak_rss_bytes": 100000,
        "elapsed_seconds": 10,
        "phase_seconds": {name: 1 for name in profiler.PHASES},
        "phase_peak_rss_bytes": {name: 100000 for name in profiler.PHASES},
        "valid_date_pairs": {
            name: {h: 0 for h in ("5", "15", "30", "60")}
            for name in ("hour", "session")
        },
        **profiler.hashes(),
    }


def test_valid_production_record_parses(tmp_path):
    record = valid_record(tmp_path)
    raw = profiler.base.encode(record)
    assert profiler.parse_result(raw, 678382, tmp_path) == record


@pytest.mark.parametrize("field,value", [
    ("kernel_calls", 47),
    ("row_count", True),
    ("selected_ids_verified", False),
    ("report_bytes", 1024**2 + 1),
    ("elapsed_seconds", 301),
    ("replication_policy", "INDEPENDENT_CORPORA"),
    ("report_sha256", "not-a-digest"),
])
def test_record_rejects_wrong_or_unbounded_measurements(tmp_path, field, value):
    record = valid_record(tmp_path)
    record[field] = value
    with pytest.raises(profiler.base.ProfileError):
        profiler.parse_result(profiler.base.encode(record), 678382, tmp_path)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}'])
def test_malformed_worker_json_rejected(tmp_path, raw):
    with pytest.raises(profiler.base.ProfileError):
        profiler.parse_result(raw, 678382, tmp_path)


def test_invalid_scale_has_no_output_side_effects(tmp_path):
    with pytest.raises(profiler.base.ProfileError):
        profiler.launch(100, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_failed_worker_retains_failure_record(tmp_path, monkeypatch):
    root = tmp_path / "profiles"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(profiler.base, "capture", lambda *a, **k: {
        "error": "synthetic timeout", "exit_status": -9,
        "stdout": b"", "stderr_tail": "",
    })
    with pytest.raises(profiler.base.ProfileError) as caught:
        profiler.launch(678382, root)
    attempt = Path(caught.value.attempt)
    assert (attempt / "incomplete.json").is_file()
    assert (attempt / "failure.json").is_file()
    assert not (attempt / "complete.json").exists()


def test_success_publishes_exclusively(tmp_path, monkeypatch):
    root = tmp_path / "profiles"
    root.mkdir(mode=0o700)

    def capture(command, environment):
        attempt = Path(command[-1])
        assert all(environment[name] == "1"
                   for name in profiler.base.THREAD_VARIABLES)
        return {
            "error": None, "exit_status": 0, "stderr_tail": "",
            "stdout": profiler.base.encode(valid_record(attempt)),
        }

    monkeypatch.setattr(profiler.base, "capture", capture)
    record = profiler.launch(678382, root)
    attempt = Path(record["attempt"])
    saved = json.loads((attempt / "complete.json").read_text())
    assert saved == record
    assert not (attempt / "failure.json").exists()
    descriptor = profiler.base.open_directory(attempt)
    try:
        with pytest.raises(FileExistsError):
            profiler.base.publish(descriptor, "complete.json", {"overwrite": True})
    finally:
        profiler.os.close(descriptor)
    assert json.loads((attempt / "complete.json").read_text()) == record
