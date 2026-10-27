"""Fabricated arrays and temporary Parquet fixtures only."""
import datetime as dt

import numpy as np
import pytest

from L1_CORE.market_data_platform.research import (
    pi5_loader_profiler as fixture,
    run_trade_flow_vs_momentum_screen as runner,
    time_conditioning_descriptive as reporting,
    time_conditioning_synthetic_integration as integration,
    trade_flow_vs_momentum_screen as kernel,
)


def epoch(text):
    return int(dt.datetime.fromisoformat(text).timestamp() * 1000)


def screen():
    start, _ = runner._day_bounds_ms(reporting.DATES[0])
    times = start + np.arange(20, dtype=np.int64) * 60_000
    return {
        "sample_trade_time": times,
        "sample_trade_id": np.arange(20, dtype=np.int64),
        "imbalance": np.arange(20, dtype=np.float64),
        "momentum": np.zeros(20, dtype=np.float64),
        "common_eligible": np.ones(20, dtype=np.bool_),
        **{f"return_{h}s": np.arange(20, dtype=np.float64) / 10000
           for h in reporting.HORIZONS},
    }


def summarize(value, **kwargs):
    return integration.summarize_screen(
        value, "BTC-USD", reporting.DATES[0],
        input_classification="SYNTHETIC_DEVELOPMENT", **kwargs
    )


def test_whole_day_deciles_precede_time_split():
    value = screen()
    result = summarize(value)["horizons"]["60"]
    # Global D0 occupies minutes 0,1; global D9 minutes 18,19.
    # Ranking separately inside each temporal group would change these counts.
    assert result["hour"]["in_window"]["n_d0"] == 2
    assert result["hour"]["in_window"]["n_d9"] == 0
    assert result["hour"]["control"]["n_d0"] == 0
    assert result["hour"]["control"]["n_d9"] == 2
    assert result["hour"]["in_window"]["d0_mean_return"] == pytest.approx(.00005)
    assert result["hour"]["control"]["d9_mean_return"] == pytest.approx(.00185)


def test_horizon_eligibility_is_applied_before_ranking():
    value = screen()
    value["common_eligible"][0] = False
    value["return_5s"][1] = np.nan
    result = summarize(value)
    assert result["horizons"]["5"]["eligible_n"] == 18
    assert result["horizons"]["60"]["eligible_n"] == 19


def test_empty_population_remains_explicitly_invalid():
    value = screen()
    value["common_eligible"][:] = False
    result = summarize(value)["horizons"]["60"]
    cell = reporting.summarize_cell(result["hour"], result["eligible_n"])
    assert result["eligible_n"] == 0
    assert cell["valid"] is False
    assert cell["in_window"]["invalid_reasons"] == ["EMPTY_D0", "EMPTY_D9"]


@pytest.mark.parametrize("utc,expected", [
    ("2026-08-22T13:29:59+00:00", False),
    ("2026-08-22T13:30:00+00:00", True),
    ("2026-08-22T19:59:59+00:00", True),
    ("2026-08-22T20:00:00+00:00", False),
    ("2026-01-10T14:30:00+00:00", True),
])
def test_session_boundaries_dst_and_weekends(utc, expected):
    times = np.array([epoch(utc)], dtype=np.int64)
    inside, control = integration.temporal_masks(times)["session"]
    assert bool(inside[0]) is expected
    assert bool(control[0]) is not expected


def test_hour_boundaries():
    start, _ = runner._day_bounds_ms(reporting.DATES[0])
    times = start + np.array([0, 14, 15, 44, 45, 59], dtype=np.int64) * 60_000
    inside, control = integration.temporal_masks(times)["hour"]
    assert inside.tolist() == [True, True, False, False, True, True]
    assert np.all(inside ^ control)


@pytest.mark.parametrize("kind", [
    "length", "wrong_day", "nonfinite", "bad_dtype", "missing",
])
def test_malformed_screen_rejected(kind):
    value = screen()
    if kind == "length":
        value["imbalance"] = value["imbalance"][:-1]
    elif kind == "wrong_day":
        value["sample_trade_time"][0] -= 1
    elif kind == "nonfinite":
        value["return_60s"][0] = np.inf
    elif kind == "bad_dtype":
        value["common_eligible"] = np.ones(20, dtype=np.int64)
    else:
        del value["momentum"]
    with pytest.raises(reporting.ReportError):
        summarize(value)


def test_non_synthetic_declaration_rejected():
    with pytest.raises(reporting.ReportError, match="synthetic-development"):
        integration.summarize_screen(
            screen(), "BTC-USD", reporting.DATES[0],
            input_classification="HISTORICAL"
        )


def test_small_parquet_loader_kernel_and_complete_reporting(tmp_path, monkeypatch):
    attempt = tmp_path / "attempt"
    attempt.mkdir(mode=0o700)
    root = attempt / "synthetic-trades"
    fixture.build_fixture(root, 6000, files_per_partition=2)
    original_read = runner.pq.read_table
    seen = []

    def checked_read(path, *args, **kwargs):
        assert path.resolve().is_relative_to(root.resolve())
        seen.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(runner.pq, "read_table", checked_read)
    monkeypatch.setattr(runner, "CANONICAL_TRADES_ROOT", root)
    partitions = runner._resolve_source_partitions(fixture.TARGET_DATE)
    start, end = runner._day_bounds_ms(fixture.TARGET_DATE)
    counted, _ = runner.count_target_rows(partitions, "BTC-USD", start, end)
    assert counted == 6000
    arrays = runner.load_instrument_day(
        partitions, "BTC-USD", start, end, counted
    )
    runner.validate_day_integrity(arrays[0], arrays[2], arrays[3], start, end)
    order = np.lexsort((arrays[1], arrays[0]))
    loaded = tuple(value[order] for value in arrays)
    kernel.validate_sorted_arrays(*loaded)
    assert np.array_equal(np.sort(loaded[1]), np.arange(6000))
    records = []
    # Explicit synthetic replication: reuse fabricated values, shift their
    # timestamps into each reporting date, and label both fabricated instruments.
    # This is not 48 independently generated/loaded instrument-day corpora.
    for day in reporting.DATES:
        day_start, _ = runner._day_bounds_ms(day)
        times = loaded[0] + (day_start - start)
        for instrument in reporting.INSTRUMENTS:
            result = kernel.compute_screen(times, *loaded[1:])
            records.append(integration.summarize_screen(
                result, instrument, day,
                input_classification="SYNTHETIC_DEVELOPMENT"
            ))
    report = reporting.build_report(
        records, input_classification="SYNTHETIC_DEVELOPMENT"
    )
    assert len(seen) == 12
    assert report["instrument_day_count"] == 48
    assert report["classification"] == "COMPLETE_DESCRIPTIVE"
    assert all(record["horizons"]["60"]["eligible_n"] > 0 for record in records)
    assert len(reporting.encode_report(report)) <= reporting.MAX_REPORT_BYTES
