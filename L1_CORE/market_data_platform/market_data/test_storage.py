"""
Market Data Platform — Persistent Storage Test
market_data_platform/market_data/test_storage.py

Deterministic offline test of storage.py, entirely isolated from
the real production canonical directory. Every write in this test
occurs inside a temporary directory, created and destroyed by
tempfile.TemporaryDirectory() — never inside
data/market_data_platform/canonical/.

storage's module-level path constants (CANONICAL_ROOT, TRADES_DIR,
DEPTH_LEVELS_DIR) are patched on the storage module object itself
for the duration of each test, then restored — the storage module
is imported as a module, not by importing its constants by value,
so patching the module's attributes actually affects what the
write/read functions use internally.

Run directly: python3 -m market_data_platform.market_data.test_storage
"""

import os
import tempfile
from decimal import Decimal

from L1_CORE.market_data_platform.market_data.schema import TradeRecord, DepthLevelRecord
from L1_CORE.market_data_platform.market_data import storage


def _make_trade_record(trade_id: int, timestamp_received: int) -> TradeRecord:
    return TradeRecord(
        timestamp_received=timestamp_received,
        event_time=timestamp_received,
        trade_time=timestamp_received,
        trade_id=trade_id,
        price=Decimal("63630.96"),
        quantity=Decimal("0.00000009"),
        is_buyer_maker=True,
        instrument_id="BTC-USD",
    )


def _make_depth_record(timestamp_received: int) -> DepthLevelRecord:
    return DepthLevelRecord(
        timestamp_received=timestamp_received,
        event_time=timestamp_received,
        transaction_time=timestamp_received,
        first_update_id=None,
        final_update_id=None,
        previous_final_update_id=None,
        side="bid",
        price=Decimal("10"),
        quantity=Decimal("0"),
        instrument_id="BTC-USD",
    )


class _IsolatedStorageRoot:
    """
    Context manager that patches storage's module-level path
    constants to point inside a temporary directory for the
    duration of a test, and restores the originals afterward.
    Guarantees no test write can ever reach the real production
    canonical directory, regardless of what storage.py's constants
    are set to at import time.
    """

    def __enter__(self):
        self._tmpdir_ctx = tempfile.TemporaryDirectory()
        self.tmp_root = self._tmpdir_ctx.__enter__()

        self._original_canonical_root = storage.CANONICAL_ROOT
        self._original_trades_dir = storage.TRADES_DIR
        self._original_depth_levels_dir = storage.DEPTH_LEVELS_DIR

        storage.CANONICAL_ROOT = os.path.join(self.tmp_root, "canonical")
        storage.TRADES_DIR = os.path.join(storage.CANONICAL_ROOT, "trades")
        storage.DEPTH_LEVELS_DIR = os.path.join(storage.CANONICAL_ROOT, "depth_levels")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        storage.CANONICAL_ROOT = self._original_canonical_root
        storage.TRADES_DIR = self._original_trades_dir
        storage.DEPTH_LEVELS_DIR = self._original_depth_levels_dir
        self._tmpdir_ctx.__exit__(exc_type, exc_val, exc_tb)


def test_trade_records_write_and_roundtrip():
    with _IsolatedStorageRoot() as iso:
        ts = 1784030400000  # 2026-07-14 12:00:00 UTC
        records = [_make_trade_record(1, ts), _make_trade_record(2, ts)]

        filepath = storage.write_trade_records(records)
        assert filepath.startswith(iso.tmp_root), f"Write escaped temp root: {filepath}"
        assert os.path.exists(filepath)
        assert "date=2026-07-14" in filepath

        read_back = storage.read_trade_records(filepath)
        assert len(read_back) == 2
        assert read_back[0] == records[0]
        assert read_back[1] == records[1]
        print(f"PASS: TradeRecord batch written and round-tripped exactly (isolated): {filepath}")


def test_depth_records_write_and_roundtrip():
    with _IsolatedStorageRoot() as iso:
        ts = 1784030400000
        records = [_make_depth_record(ts)]

        filepath = storage.write_depth_level_records(records)
        assert filepath.startswith(iso.tmp_root), f"Write escaped temp root: {filepath}"
        assert os.path.exists(filepath)
        assert "date=2026-07-14" in filepath

        read_back = storage.read_depth_level_records(filepath)
        assert len(read_back) == 1
        assert read_back[0] == records[0]
        assert read_back[0].first_update_id is None, "None must round-trip as None, not fabricated"
        print(f"PASS: DepthLevelRecord written and round-tripped exactly, None preserved (isolated): {filepath}")


def test_two_writes_produce_distinct_files():
    with _IsolatedStorageRoot() as iso:
        ts = 1784030400000
        records = [_make_trade_record(1, ts)]

        filepath_one = storage.write_trade_records(records)
        filepath_two = storage.write_trade_records(records)

        assert filepath_one.startswith(iso.tmp_root) and filepath_two.startswith(iso.tmp_root)
        assert filepath_one != filepath_two, "Two separate writes must never produce the same filename"
        assert os.path.exists(filepath_one), "First write's file must still exist after second write"
        assert os.path.exists(filepath_two), "Second write's file must exist"
        print(f"PASS: two writes produced distinct files, neither overwritten (isolated):\n  {filepath_one}\n  {filepath_two}")


def test_partition_date_uses_timestamp_received_not_local_clock():
    with _IsolatedStorageRoot() as iso:
        # 2020-01-01 00:00:00 UTC, deliberately far from today's real
        # date, to prove partitioning uses the record's own
        # timestamp_received, not the machine's current local calendar
        # date.
        ts = 1577836800000
        records = [_make_trade_record(1, ts)]

        filepath = storage.write_trade_records(records)
        assert filepath.startswith(iso.tmp_root)
        assert "date=2020-01-01" in filepath, f"Expected date=2020-01-01 partition, got: {filepath}"
        print(f"PASS: partition date correctly derived from timestamp_received, not local clock (isolated): {filepath}")


def test_empty_batch_rejected_for_trades():
    with _IsolatedStorageRoot():
        try:
            storage.write_trade_records([])
        except ValueError as e:
            print(f"PASS: empty trade batch correctly rejected: {e}")
        else:
            raise AssertionError("Expected write_trade_records([]) to raise ValueError, but it did not.")


def test_empty_batch_rejected_for_depth_levels():
    with _IsolatedStorageRoot():
        try:
            storage.write_depth_level_records([])
        except ValueError as e:
            print(f"PASS: empty depth batch correctly rejected: {e}")
        else:
            raise AssertionError("Expected write_depth_level_records([]) to raise ValueError, but it did not.")


def test_cross_date_batch_rejected_for_trades():
    with _IsolatedStorageRoot():
        ts_day_one = 1784030400000    # 2026-07-14
        ts_day_two = 1784116800000    # 2026-07-15
        records = [_make_trade_record(1, ts_day_one), _make_trade_record(2, ts_day_two)]

        try:
            storage.write_trade_records(records)
        except ValueError as e:
            print(f"PASS: cross-date trade batch correctly rejected: {e}")
        else:
            raise AssertionError("Expected a cross-date trade batch to raise ValueError, but it did not.")


def test_cross_date_batch_rejected_for_depth_levels():
    with _IsolatedStorageRoot():
        ts_day_one = 1784030400000
        ts_day_two = 1784116800000
        records = [_make_depth_record(ts_day_one), _make_depth_record(ts_day_two)]

        try:
            storage.write_depth_level_records(records)
        except ValueError as e:
            print(f"PASS: cross-date depth batch correctly rejected: {e}")
        else:
            raise AssertionError("Expected a cross-date depth batch to raise ValueError, but it did not.")


def test_written_arrow_schema_matches_declared_schema():
    with _IsolatedStorageRoot():
        ts = 1784030400000

        trade_filepath = storage.write_trade_records([_make_trade_record(1, ts)])
        import pyarrow.parquet as pq
        trade_schema_read = pq.ParquetFile(trade_filepath).schema_arrow
        assert trade_schema_read.equals(storage.TRADE_SCHEMA), (
            f"Written trade schema does not match declared TRADE_SCHEMA.\n"
            f"Written:   {trade_schema_read}\n"
            f"Declared:  {storage.TRADE_SCHEMA}"
        )
        print("PASS: written trade file's physical Arrow schema matches declared TRADE_SCHEMA exactly")

        depth_filepath = storage.write_depth_level_records([_make_depth_record(ts)])
        depth_schema_read = pq.ParquetFile(depth_filepath).schema_arrow
        assert depth_schema_read.equals(storage.DEPTH_LEVEL_SCHEMA), (
            f"Written depth schema does not match declared DEPTH_LEVEL_SCHEMA.\n"
            f"Written:   {depth_schema_read}\n"
            f"Declared:  {storage.DEPTH_LEVEL_SCHEMA}"
        )
        print("PASS: written depth file's physical Arrow schema matches declared DEPTH_LEVEL_SCHEMA exactly")


if __name__ == "__main__":
    test_trade_records_write_and_roundtrip()
    test_depth_records_write_and_roundtrip()
    test_two_writes_produce_distinct_files()
    test_partition_date_uses_timestamp_received_not_local_clock()
    test_empty_batch_rejected_for_trades()
    test_empty_batch_rejected_for_depth_levels()
    test_cross_date_batch_rejected_for_trades()
    test_cross_date_batch_rejected_for_depth_levels()
    test_written_arrow_schema_matches_declared_schema()

    print("\nAll storage tests passed. No production canonical data was touched at any point.")
