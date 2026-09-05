"""
Market Data Platform -- Multi-Partition Loader Integration Fixture
market_data_platform/research/test_multi_partition_loader.py

Exercises the ACTUAL loader functions (count_target_rows,
load_instrument_day, _resolve_source_partitions) against real,
temporary Parquet files written to a temp directory structure
mimicking date=2026-08-21/22/23 partitions -- not merely the pure
is_in_research_day() predicate in isolation.

Run: python3 -m L1_CORE.market_data_platform.research.test_multi_partition_loader
"""
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen as runner_mod
from L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen import (
    is_in_research_day,
    _day_bounds_ms,
    _adjacent_date_str,
    _resolve_source_partitions,
    count_target_rows,
    load_instrument_day,
)

TARGET_DATE = "2026-08-22"
START_MS, END_MS = _day_bounds_ms(TARGET_DATE)


def _write_parquet(path, rows):
    """
    Writes a minimal synthetic Parquet file with the six required
    columns, using the same decimal128(18,8) type for price/quantity
    as real canonical storage (confirmed via direct schema
    inspection earlier), so this fixture exercises the real Arrow
    decimal->float64 cast path, not a shortcut.

    Receives:
        path (Path): output file path.
        rows (list[dict]): each dict has trade_time, trade_id,
        price, quantity, is_buyer_maker, instrument_id.
    """
    schema = pa.schema([
        ("trade_time", pa.int64()),
        ("trade_id", pa.int64()),
        ("price", pa.decimal128(18, 8)),
        ("quantity", pa.decimal128(18, 8)),
        ("is_buyer_maker", pa.bool_()),
        ("instrument_id", pa.string()),
    ])
    table = pa.table({
        "trade_time": pa.array([r["trade_time"] for r in rows], type=pa.int64()),
        "trade_id": pa.array([r["trade_id"] for r in rows], type=pa.int64()),
        "price": pa.array([Decimal(r["price"]) for r in rows], type=pa.decimal128(18, 8)),
        "quantity": pa.array([Decimal(r["quantity"]) for r in rows], type=pa.decimal128(18, 8)),
        "is_buyer_maker": pa.array([r["is_buyer_maker"] for r in rows], type=pa.bool_()),
        "instrument_id": pa.array([r["instrument_id"] for r in rows], type=pa.string()),
    }, schema=schema)
    pq.write_table(table, path)


def _build_temp_corpus():
    """
    Builds a temporary directory with date=2026-08-21/22/23
    partitions, each containing one Parquet file with a deliberate
    mix of rows designed to exercise every case from the design
    review: prev-day spill-in, next-day spill-in, wrong-instrument
    exclusion, wrong-day-within-target-partition exclusion, and
    exact end_ms boundary exclusion.

    Returns:
        (temp_root: Path, expected: dict) -- expected contains the
        exact hand-calculated ground truth this fixture asserts
        against.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="lrs_loader_fixture_"))

    prev_dir = temp_root / "date=2026-08-21"
    target_dir = temp_root / f"date={TARGET_DATE}"
    next_dir = temp_root / "date=2026-08-23"
    for d in (prev_dir, target_dir, next_dir):
        d.mkdir(parents=True)

    # PREV partition (2026-08-21):
    #   trade_id 1: before Aug22 -> excluded
    #   trade_id 2: trade_time genuinely INSIDE Aug22 (>= START_MS),
    #     but physically stored in the 2026-08-21 partition file --
    #     this is the real spill-in case: a trade whose own
    #     trade_time belongs to the target day, stored in the
    #     PREVIOUS day's partition (the mirror image of the real
    #     observed Aug-22/Aug-23 case, included here for symmetry
    #     even though only the Aug-23-side spill-in was directly
    #     observed in real data).
    #   trade_id 3: also inside Aug22, stored in prev partition -> included
    _write_parquet(prev_dir / "file1.parquet", [
        {"trade_time": START_MS - 5000, "trade_id": 1, "price": "100.00000000",
         "quantity": "1.00000000", "is_buyer_maker": False, "instrument_id": "BTC-USD"},
        {"trade_time": START_MS + 50, "trade_id": 2, "price": "100.01000000",
         "quantity": "1.00000000", "is_buyer_maker": True, "instrument_id": "BTC-USD"},
        {"trade_time": START_MS + 100, "trade_id": 3, "price": "100.02000000",
         "quantity": "2.00000000", "is_buyer_maker": False, "instrument_id": "BTC-USD"},
    ])

    # TARGET partition (2026-08-22):
    #   trade_id 10: before Aug22 (wrong-day-within-target-partition) -> excluded
    #   trade_id 11, 12: inside Aug22 -> included
    #   trade_id 13: ETH-USD inside Aug22 -> excluded by instrument
    _write_parquet(target_dir / "file1.parquet", [
        {"trade_time": START_MS - 50, "trade_id": 10, "price": "99.99000000",
         "quantity": "1.00000000", "is_buyer_maker": True, "instrument_id": "BTC-USD"},
        {"trade_time": START_MS + 1000, "trade_id": 11, "price": "100.10000000",
         "quantity": "3.00000000", "is_buyer_maker": False, "instrument_id": "BTC-USD"},
        {"trade_time": START_MS + 2000, "trade_id": 12, "price": "100.20000000",
         "quantity": "4.00000000", "is_buyer_maker": True, "instrument_id": "BTC-USD"},
        {"trade_time": START_MS + 1500, "trade_id": 13, "price": "2500.00000000",
         "quantity": "1.00000000", "is_buyer_maker": False, "instrument_id": "ETH-USD"},
    ])

    # NEXT partition (2026-08-23):
    #   trade_id 20: inside Aug22 (spill-in, real observed case, critical) -> included
    #   trade_id 21: exactly at end_ms (midnight of Aug23) -> excluded (half-open interval)
    #   trade_id 22: well inside Aug23 -> excluded
    _write_parquet(next_dir / "file1.parquet", [
        {"trade_time": END_MS - 43, "trade_id": 20, "price": "100.30000000",
         "quantity": "5.00000000", "is_buyer_maker": True, "instrument_id": "BTC-USD"},
        {"trade_time": END_MS, "trade_id": 21, "price": "100.31000000",
         "quantity": "1.00000000", "is_buyer_maker": False, "instrument_id": "BTC-USD"},
        {"trade_time": END_MS + 5000, "trade_id": 22, "price": "100.40000000",
         "quantity": "1.00000000", "is_buyer_maker": True, "instrument_id": "BTC-USD"},
    ])

    expected = {
        "prev": {"target_instrument_rows": 3, "in_range_rows": 2},   # id 2, id 3 (id 1 is before Aug22)
        "target": {"target_instrument_rows": 3, "in_range_rows": 2},  # id 11, 12 (id 13 is ETH, id 10 wrong day)
        "next": {"target_instrument_rows": 3, "in_range_rows": 1},    # id 20 only
        "total_in_range": 5,  # ids 2, 3, 11, 12, 20
        "expected_trade_ids": {2, 3, 11, 12, 20},
    }

    return temp_root, expected


def test_full_loader_pipeline_against_synthetic_corpus():
    """
    The core integration test: builds a real temporary 3-partition
    corpus, patches CANONICAL_TRADES_ROOT to point at it, and calls
    the ACTUAL count_target_rows() and load_instrument_day()
    functions -- not a reimplementation, not the bare predicate.
    """
    temp_root, expected = _build_temp_corpus()
    original_root = runner_mod.CANONICAL_TRADES_ROOT

    try:
        runner_mod.CANONICAL_TRADES_ROOT = temp_root

        partitions = _resolve_source_partitions(TARGET_DATE)
        assert len(partitions) == 3, f"expected 3 partitions, got {len(partitions)}"

        n_target, per_partition_stats = count_target_rows(partitions, "BTC-USD", START_MS, END_MS)

        assert n_target == expected["total_in_range"], (
            f"Pass 1 total mismatch: expected {expected['total_in_range']}, got {n_target}"
        )

        stats_by_date = {s["date"]: s for s in per_partition_stats}
        assert stats_by_date["2026-08-21"]["target_instrument_rows"] == expected["prev"]["target_instrument_rows"]
        assert stats_by_date["2026-08-21"]["in_range_rows"] == expected["prev"]["in_range_rows"]
        assert stats_by_date["2026-08-22"]["target_instrument_rows"] == expected["target"]["target_instrument_rows"]
        assert stats_by_date["2026-08-22"]["in_range_rows"] == expected["target"]["in_range_rows"]
        assert stats_by_date["2026-08-23"]["target_instrument_rows"] == expected["next"]["target_instrument_rows"]
        assert stats_by_date["2026-08-23"]["in_range_rows"] == expected["next"]["in_range_rows"]

        trade_time, trade_id, price, quantity, is_buyer_maker = load_instrument_day(
            partitions, "BTC-USD", START_MS, END_MS, n_target
        )

        assert len(trade_time) == expected["total_in_range"], (
            f"Pass 2 loaded row count mismatch: expected {expected['total_in_range']}, got {len(trade_time)}"
        )

        loaded_ids = set(trade_id.tolist())
        assert loaded_ids == expected["expected_trade_ids"], (
            f"loaded trade_id set mismatch: expected {expected['expected_trade_ids']}, got {loaded_ids}"
        )

        # Every loaded row must genuinely be in [START_MS, END_MS).
        in_range_check = is_in_research_day(trade_time, START_MS, END_MS)
        assert in_range_check.all(), (
            f"some loaded rows are outside the target research day: {trade_time[~in_range_check]}"
        )

        # ETH-USD row (id 13) must be absent -- confirms instrument
        # filtering happened correctly in the real loader.
        assert 13 not in loaded_ids, "ETH-USD row leaked into BTC-USD loaded results"

        # Wrong-day rows must be absent.
        assert 1 not in loaded_ids, "prev-partition wrong-day row (id 1) incorrectly included"
        assert 10 not in loaded_ids, "target-partition wrong-day row (id 10) incorrectly included"
        assert 21 not in loaded_ids, "exact end_ms row (id 21) incorrectly included"
        assert 22 not in loaded_ids, "next-partition wrong-day row (id 22) incorrectly included"

        # Confirm the critical spill-in rows ARE present -- both the
        # prev-partition spill-in (ids 2, 3) and the next-partition
        # spill-in (id 20, the case actually observed in real data).
        assert 2 in loaded_ids, "prev-partition spill-in row (id 2) missing"
        assert 3 in loaded_ids, "prev-partition spill-in row (id 3) missing"
        assert 20 in loaded_ids, "next-partition spill-in row (id 20) missing -- this matches the real observed case"

        # Confirm the price cast (decimal128 -> float64) worked correctly.
        assert price.dtype == np.float64
        idx_of_20 = list(trade_id).index(20)
        assert abs(price[idx_of_20] - 100.30) < 1e-9, f"price cast mismatch for spill-in row: {price[idx_of_20]}"

        print("PASS: full loader pipeline (real Parquet files, real 3-partition structure, "
              "actual count_target_rows/load_instrument_day) correctly includes both spill-in rows, "
              "excludes wrong-day and wrong-instrument rows, and matches exact expected trade_id set")

    finally:
        runner_mod.CANONICAL_TRADES_ROOT = original_root
        shutil.rmtree(temp_root, ignore_errors=True)


def test_missing_adjacent_partition_raises():
    """
    Fail-closed requirement: if the previous or next partition
    directory doesn't exist, _resolve_source_partitions() must
    raise, not silently proceed with incomplete coverage.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="lrs_loader_fixture_missing_"))
    original_root = runner_mod.CANONICAL_TRADES_ROOT

    try:
        runner_mod.CANONICAL_TRADES_ROOT = temp_root
        # Only create the target partition, deliberately omit prev/next.
        (temp_root / f"date={TARGET_DATE}").mkdir(parents=True)

        try:
            _resolve_source_partitions(TARGET_DATE)
            raise AssertionError("Expected RuntimeError for missing adjacent partitions")
        except RuntimeError as e:
            assert "does not exist" in str(e)

        print("PASS: missing adjacent partition correctly raises RuntimeError")
    finally:
        runner_mod.CANONICAL_TRADES_ROOT = original_root
        shutil.rmtree(temp_root, ignore_errors=True)


def test_raw_null_trade_time_raises_before_filtering():
    """
    Fail-closed requirement: a null trade_time in the raw table must
    raise immediately (via _require_no_null_raw), before either the
    instrument filter or the day-range filter runs -- otherwise the
    null row could silently vanish through filtering.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="lrs_loader_fixture_nulltime_"))
    original_root = runner_mod.CANONICAL_TRADES_ROOT

    try:
        runner_mod.CANONICAL_TRADES_ROOT = temp_root
        prev_dir = temp_root / "date=2026-08-21"
        target_dir = temp_root / f"date={TARGET_DATE}"
        next_dir = temp_root / "date=2026-08-23"
        for d in (prev_dir, target_dir, next_dir):
            d.mkdir(parents=True)

        # Write a target-partition file with a null trade_time.
        schema = pa.schema([
            ("trade_time", pa.int64()),
            ("trade_id", pa.int64()),
            ("price", pa.decimal128(18, 8)),
            ("quantity", pa.decimal128(18, 8)),
            ("is_buyer_maker", pa.bool_()),
            ("instrument_id", pa.string()),
        ])
        table = pa.table({
            "trade_time": pa.array([None, START_MS + 100], type=pa.int64()),
            "trade_id": pa.array([1, 2], type=pa.int64()),
            "price": pa.array([Decimal("100.0"), Decimal("100.0")], type=pa.decimal128(18, 8)),
            "quantity": pa.array([Decimal("1.0"), Decimal("1.0")], type=pa.decimal128(18, 8)),
            "is_buyer_maker": pa.array([False, False], type=pa.bool_()),
            "instrument_id": pa.array(["BTC-USD", "BTC-USD"], type=pa.string()),
        }, schema=schema)
        pq.write_table(table, target_dir / "file1.parquet")

        # prev/next need at least a valid file to reach the target
        # partition's null during Pass 1's iteration -- but since
        # partitions are processed prev/target/next in order, an
        # empty prev partition (zero files) is fine.

        partitions = _resolve_source_partitions(TARGET_DATE)

        try:
            count_target_rows(partitions, "BTC-USD", START_MS, END_MS)
            raise AssertionError("Expected RuntimeError for null trade_time")
        except RuntimeError as e:
            assert "trade_time" in str(e)

        print("PASS: raw null trade_time correctly raises RuntimeError before filtering")
    finally:
        runner_mod.CANONICAL_TRADES_ROOT = original_root
        shutil.rmtree(temp_root, ignore_errors=True)


def test_day_bounds_are_exactly_24_hours():
    start_ms, end_ms = _day_bounds_ms(TARGET_DATE)
    assert end_ms - start_ms == 86_400_000
    print("PASS: day bounds span exactly 24 hours")


def test_adjacent_date_str_prev_and_next():
    assert _adjacent_date_str(TARGET_DATE, -1) == "2026-08-21"
    assert _adjacent_date_str(TARGET_DATE, +1) == "2026-08-23"
    print("PASS: adjacent date calculation correct for prev/next")


def test_adjacent_date_str_crosses_month_boundary():
    assert _adjacent_date_str("2026-09-01", -1) == "2026-08-31"
    assert _adjacent_date_str("2026-08-31", +1) == "2026-09-01"
    print("PASS: adjacent date calculation correctly crosses month boundaries")


if __name__ == "__main__":
    test_day_bounds_are_exactly_24_hours()
    test_adjacent_date_str_prev_and_next()
    test_adjacent_date_str_crosses_month_boundary()
    test_full_loader_pipeline_against_synthetic_corpus()
    test_missing_adjacent_partition_raises()
    test_raw_null_trade_time_raises_before_filtering()
    print("\nALL TESTS PASSED")
