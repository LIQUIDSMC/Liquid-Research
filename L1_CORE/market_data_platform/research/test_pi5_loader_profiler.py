"""Small synthetic fixtures only; no historical files or Pi access."""
import json
import os
from pathlib import Path

import pytest

from L1_CORE.market_data_platform.research import (
    pi5_loader_profiler as profiler,
    run_trade_flow_vs_momentum_screen as runner,
    trade_flow_vs_momentum_screen as kernel,
)


@pytest.fixture
def attempt(tmp_path):
    root = tmp_path / "attempt"
    root.mkdir(mode=0o700)
    return root


def test_real_loader_filters_controls_and_preserves_global_root(attempt, monkeypatch):
    original = runner.CANONICAL_TRADES_ROOT
    def forbidden(*args, **kwargs):
        raise AssertionError("Calculation kernel must not run")
    monkeypatch.setattr(kernel, "compute_screen", forbidden)
    record = profiler.measure_loader(300, attempt, files_per_partition=2)
    assert record["loaded_target_rows"] == 300
    assert record["fixture_files"] == 6
    assert record["fixture_rows"] == 318
    assert record["control_rows"] == 18
    assert record["input_array_bytes"] == 9900
    assert record["selected_ids_verified"] is True
    assert sum(
        item["in_range_rows"] for item in record["partition_statistics"]
    ) == 300
    assert runner.CANONICAL_TRADES_ROOT == original
    assert len(list((attempt / "synthetic-trades").glob("*/*.parquet"))) == 6


def test_actual_reads_stay_inside_synthetic_fixture(attempt, monkeypatch):
    original_read = runner.pq.read_table
    seen = []
    def checked(path, *args, **kwargs):
        assert Path(path).is_relative_to(attempt / "synthetic-trades")
        seen.append(str(path))
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(runner.pq, "read_table", checked)
    profiler.measure_loader(120, attempt, files_per_partition=1)
    assert len(seen) == 6


def test_existing_fixture_is_not_overwritten(attempt):
    root = attempt / "synthetic-trades"
    root.mkdir()
    marker = root / "retained"
    marker.write_text("unchanged")
    with pytest.raises(FileExistsError):
        profiler.build_fixture(root, 100, files_per_partition=1)
    assert marker.read_text() == "unchanged"


@pytest.mark.parametrize("rows,files", [(0, 1), (True, 1), (100, 0), (100, 8956)])
def test_invalid_limits_rejected_before_fixture_creation(attempt, rows, files):
    with pytest.raises(profiler.base.ProfileError):
        profiler.build_fixture(
            attempt / "synthetic-trades", rows, files_per_partition=files
        )
    assert not (attempt / "synthetic-trades").exists()


def test_fixture_byte_limit_retains_partial_directory(attempt):
    with pytest.raises(profiler.base.ProfileError, match="Fixture-byte"):
        profiler.build_fixture(
            attempt / "synthetic-trades", 100,
            files_per_partition=1, max_bytes=1,
        )
    assert (attempt / "synthetic-trades").is_dir()
    assert not list((attempt / "synthetic-trades").glob("*/*.parquet"))


def test_free_space_reserve_blocks_writes(attempt, monkeypatch):
    class Space:
        f_bavail = 0
        f_frsize = 4096
    monkeypatch.setattr(profiler.os, "fstatvfs", lambda descriptor: Space())
    with pytest.raises(profiler.base.ProfileError, match="free-space"):
        profiler.build_fixture(
            attempt / "synthetic-trades", 100, files_per_partition=1
        )
    assert not list((attempt / "synthetic-trades").glob("*/*.parquet"))


def test_expired_generation_stops_before_fixture_creation(attempt):
    with pytest.raises(profiler.base.ProfileError, match="runtime"):
        profiler.build_fixture(
            attempt / "synthetic-trades", 100,
            files_per_partition=1, deadline=0,
        )
    assert not (attempt / "synthetic-trades").exists()


def test_global_root_restored_after_loader_failure(attempt, monkeypatch):
    original = runner.CANONICAL_TRADES_ROOT
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic counting failure")
    monkeypatch.setattr(runner, "count_target_rows", fail)
    with pytest.raises(RuntimeError, match="synthetic counting"):
        profiler.measure_loader(100, attempt, files_per_partition=1)
    assert runner.CANONICAL_TRADES_ROOT == original
    assert (attempt / "synthetic-trades").exists()


def test_failed_worker_retains_attempt(tmp_path, monkeypatch):
    output = tmp_path / "profiles"
    output.mkdir(mode=0o700)
    monkeypatch.setattr(profiler.base, "capture", lambda *args, **kwargs: {
        "exit_status": -9, "error": "synthetic timeout",
        "stderr_tail": "", "stdout": b"",
    })
    with pytest.raises(profiler.base.ProfileError) as caught:
        profiler.launch(678382, output)
    root = Path(caught.value.attempt)
    assert (root / "incomplete.json").exists()
    assert (root / "failure.json").exists()
    assert not (root / "complete.json").exists()


def test_invalid_scale_has_no_output_side_effects(attempt):
    with pytest.raises(profiler.base.ProfileError):
        profiler.launch(100, attempt)
    assert list(attempt.iterdir()) == []


def test_worker_result_rejects_wrong_identity():
    with pytest.raises(profiler.base.ProfileError, match="mismatch"):
        profiler.parse_result(b'{"version":"wrong"}', 678382, "/tmp/attempt")


def test_worker_result_rejects_duplicate_keys():
    with pytest.raises(profiler.base.ProfileError, match="Duplicate"):
        profiler.parse_result(b'{"x":1,"x":2}', 678382, "/tmp/attempt")


def test_worker_result_rejects_nonfinite_constant():
    with pytest.raises(profiler.base.ProfileError, match="Nonfinite"):
        profiler.parse_result(b'{"x":NaN}', 678382, "/tmp/attempt")
