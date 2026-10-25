"""Synthetic-only Candidate D sealed source-partition boundary tests."""
import datetime as dt
from types import SimpleNamespace

import pytest

from L1_CORE.market_data_platform.research import (
    candidate_d_d0_time_conditioning as candidate,
    run_trade_flow_vs_momentum_screen as runner,
)


def forbidden(*args, **kwargs):
    raise AssertionError("Forbidden source access or output operation")


def test_safe_date_resolves_real_temporary_directories(tmp_path, monkeypatch):
    expected = ["2026-09-01", "2026-09-02", "2026-09-03"]
    for day in expected:
        (tmp_path / f"date={day}").mkdir()
    monkeypatch.setattr(runner, "CANONICAL_TRADES_ROOT", tmp_path)

    checked = candidate.verify_source_partition_dates("2026-09-02")
    resolved = candidate._resolve_source_partitions("2026-09-02")
    assert checked["required_partition_dates"] == expected
    assert [label for label, _ in resolved] == expected
    assert all(directory.parent == tmp_path for _, directory in resolved)


@pytest.mark.parametrize("day", ["2026-09-03", "2026-09-04", "2026-10-02"])
def test_blocked_loader_never_resolves_or_reads(day, monkeypatch):
    monkeypatch.setattr(candidate, "_resolve_source_partitions", forbidden)
    monkeypatch.setattr(candidate, "count_target_rows", forbidden)
    monkeypatch.setattr(candidate, "load_instrument_day", forbidden)
    with pytest.raises(RuntimeError, match="SEALED RESERVE"):
        candidate.load_complete_instrument_day("BTC-USD", day)


def test_partition_guard_performs_no_filesystem_access(monkeypatch):
    monkeypatch.setattr(candidate.Path, "is_dir", forbidden)
    monkeypatch.setattr(candidate.Path, "iterdir", forbidden)
    monkeypatch.setattr(candidate.Path, "glob", forbidden)
    with pytest.raises(RuntimeError, match="2026-09-04"):
        candidate.verify_source_partition_dates("2026-09-03")
    assert candidate.verify_source_partition_dates(
        "2026-09-02"
    )["required_partition_dates"][-1] == "2026-09-03"


def test_entire_frozen_matrix_is_blocked_without_source_access(monkeypatch):
    monkeypatch.setattr(candidate, "_resolve_source_partitions", forbidden)
    monkeypatch.setattr(candidate, "count_target_rows", forbidden)
    candidate.verify_frozen_matrix()
    with pytest.raises(RuntimeError, match="2026-09-04"):
        candidate.verify_matrix_source_boundaries()


def test_main_blocks_before_output_or_analysis(tmp_path, monkeypatch):
    output = tmp_path / "must-not-exist"
    monkeypatch.setattr(
        candidate, "parse_args",
        lambda: SimpleNamespace(output_dir=str(output)),
    )
    # Isolate boundary enforcement from the unavailable historical artifact.
    monkeypatch.setattr(candidate, "verify_predeclaration", lambda: None)
    monkeypatch.setattr(candidate, "prepare_output_dir", forbidden)
    monkeypatch.setattr(candidate, "write_json_atomic", forbidden)
    monkeypatch.setattr(candidate, "analyze_instrument_day", forbidden)
    monkeypatch.setattr(candidate, "_resolve_source_partitions", forbidden)
    with pytest.raises(RuntimeError, match="2026-09-04"):
        candidate.main()
    assert not output.exists()


def test_boundary_record_describes_checks_not_actual_access(monkeypatch):
    monkeypatch.setattr(
        candidate, "FROZEN_MATRIX",
        [("BTC-USD", "2026-09-02"), ("ETH-USD", "2026-09-02")],
    )
    record = candidate.verify_matrix_source_boundaries()
    assert record["instrument_days_checked"] == 2
    assert record["blocked_partition_dates"] == []
    assert record["checks"][0]["required_partition_dates"] == [
        "2026-09-01", "2026-09-02", "2026-09-03",
    ]
    assert "not a record of actual file access" in record["limitations"]


def test_frozen_dates_matrix_and_anchor_remain_exact():
    expected_dates = [
        (dt.date(2026, 7, 22) + dt.timedelta(days=index)).isoformat()
        for index in range(19)
    ] + [
        "2026-08-26", "2026-08-27", "2026-08-28",
        "2026-08-29", "2026-08-30", "2026-09-03",
    ]
    assert candidate.FROZEN_DATES == expected_dates
    assert candidate.FROZEN_MATRIX == [
        (instrument, day)
        for day in expected_dates
        for instrument in ("BTC-USD", "ETH-USD")
    ]
    assert candidate.PREDECLARATION_SHA256 == (
        "9fce77d46174cd22be28bcae5d244de45cb404222f74e5c30539cb90f78c68f5"
    )
