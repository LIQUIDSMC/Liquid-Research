"""
Market Data Platform — Persistent Canonical Storage
market_data_platform/market_data/storage.py

Writes canonical TradeRecord and DepthLevelRecord objects to
immutable, date-partitioned Parquet files, using the decimal128(18,
8) representation proven in test_parquet_roundtrip.py.

Partition key: timestamp_received (UTC calendar date), not any
exchange-reported timestamp. timestamp_received is always
collector-owned, always present (never Optional in the schema),
and never a placeholder value — unlike exchange-reported timestamps
(e.g. Coinbase's transaction_time, observed as 0/epoch-placeholder
in real live data). Partitioning on collector-owned data keeps
partition correctness independent of any single venue's data
quality.

Two separate datasets (trades/, depth_levels/), not one combined
sparse table — kept as an explicit design choice, not required or
forbidden by the roadmap's "date-partitioned Parquet" language.

Each write produces exactly one new, uniquely-named file
(date=YYYY-MM-DD/<uuid4>.parquet). No file is ever modified or
overwritten after being written, per the Governing Design
Principle.
"""

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

import pyarrow as pa
import pyarrow.parquet as pq

from L1_CORE.market_data_platform.market_data.schema import TradeRecord, DepthLevelRecord

CANONICAL_ROOT = "L1_CORE/market_data_platform/data/canonical"
TRADES_DIR = os.path.join(CANONICAL_ROOT, "trades")
DEPTH_LEVELS_DIR = os.path.join(CANONICAL_ROOT, "depth_levels")

# Proven safe for real observed values in test_parquet_roundtrip.py.
# Not claimed universally sufficient for every possible future venue.
DECIMAL_PRECISION = 18
DECIMAL_SCALE = 8
DECIMAL_TYPE = pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE)

TRADE_SCHEMA = pa.schema([
    ("timestamp_received", pa.int64()),
    ("event_time", pa.int64()),
    ("trade_time", pa.int64()),
    ("trade_id", pa.int64()),
    ("price", DECIMAL_TYPE),
    ("quantity", DECIMAL_TYPE),
    ("is_buyer_maker", pa.bool_()),
])

DEPTH_LEVEL_SCHEMA = pa.schema([
    ("timestamp_received", pa.int64()),
    ("event_time", pa.int64()),
    ("transaction_time", pa.int64()),
    ("first_update_id", pa.int64()),
    ("final_update_id", pa.int64()),
    ("previous_final_update_id", pa.int64()),
    ("side", pa.string()),
    ("price", DECIMAL_TYPE),
    ("quantity", DECIMAL_TYPE),
])


def partition_date_utc(timestamp_received_ms: int) -> str:
    """
    Compute the UTC calendar date (YYYY-MM-DD) for a given
    timestamp_received value, used as the partition key. Always
    UTC, never the local machine's calendar date, so partitioning
    is deterministic regardless of where the collector runs.

    Receives:
        timestamp_received_ms (int): Unix epoch milliseconds.

    Returns:
        str: date in YYYY-MM-DD format.
    """
    dt = datetime.fromtimestamp(timestamp_received_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _write_partitioned_parquet(table: pa.Table, base_dir: str, partition_date: str) -> str:
    """
    Write one Arrow table to a new, uniquely-named file within a
    date-partitioned directory. Never overwrites an existing file —
    the UUID filename guarantees collision safety even across
    multiple writes within the same partition date.

    Receives:
        table (pa.Table): the data to write.
        base_dir (str): TRADES_DIR or DEPTH_LEVELS_DIR.
        partition_date (str): YYYY-MM-DD.

    Returns:
        str: the full path the file was written to.
    """
    partition_dir = os.path.join(base_dir, f"date={partition_date}")
    os.makedirs(partition_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.parquet"
    filepath = os.path.join(partition_dir, filename)

    try:
        with open(filepath, "xb") as sink:
            pq.write_table(table, sink)
    except FileExistsError as e:
        raise RuntimeError(
            f"Refusing to overwrite existing canonical file: {filepath}"
        ) from e

    return filepath


def write_trade_records(records: List[TradeRecord]) -> str:
    """
    Write a batch of TradeRecord objects to immutable, date-
    partitioned Parquet storage. All records in one call must share
    the same UTC calendar date for timestamp_received — a batch
    should be pre-grouped by the caller if it spans a date boundary.

    Receives:
        records (List[TradeRecord]): non-empty list of records to
        write, all from the same UTC calendar date.

    Returns:
        str: the full path the file was written to.

    Raises:
        ValueError: if records is empty, or if records span more
        than one UTC calendar date.
    """
    if not records:
        raise ValueError("write_trade_records() requires at least one record.")

    partition_dates = {partition_date_utc(r.timestamp_received) for r in records}
    if len(partition_dates) > 1:
        raise ValueError(
            f"write_trade_records() received records spanning multiple "
            f"UTC dates ({sorted(partition_dates)}); caller must pre-group "
            f"by date before calling."
        )
    partition_date = partition_dates.pop()

    rows = [{
        "timestamp_received": r.timestamp_received,
        "event_time": r.event_time,
        "trade_time": r.trade_time,
        "trade_id": r.trade_id,
        "price": r.price,
        "quantity": r.quantity,
        "is_buyer_maker": r.is_buyer_maker,
    } for r in records]

    table = pa.Table.from_pylist(rows, schema=TRADE_SCHEMA)
    return _write_partitioned_parquet(table, TRADES_DIR, partition_date)


def write_depth_level_records(records: List[DepthLevelRecord]) -> str:
    """
    Write a batch of DepthLevelRecord objects to immutable, date-
    partitioned Parquet storage. Same single-date constraint as
    write_trade_records().

    Receives:
        records (List[DepthLevelRecord]): non-empty list of records
        to write, all from the same UTC calendar date.

    Returns:
        str: the full path the file was written to.

    Raises:
        ValueError: if records is empty, or if records span more
        than one UTC calendar date.
    """
    if not records:
        raise ValueError("write_depth_level_records() requires at least one record.")

    partition_dates = {partition_date_utc(r.timestamp_received) for r in records}
    if len(partition_dates) > 1:
        raise ValueError(
            f"write_depth_level_records() received records spanning multiple "
            f"UTC dates ({sorted(partition_dates)}); caller must pre-group "
            f"by date before calling."
        )
    partition_date = partition_dates.pop()

    rows = [{
        "timestamp_received": r.timestamp_received,
        "event_time": r.event_time,
        "transaction_time": r.transaction_time,
        "first_update_id": r.first_update_id,
        "final_update_id": r.final_update_id,
        "previous_final_update_id": r.previous_final_update_id,
        "side": r.side,
        "price": r.price,
        "quantity": r.quantity,
    } for r in records]

    table = pa.Table.from_pylist(rows, schema=DEPTH_LEVEL_SCHEMA)
    return _write_partitioned_parquet(table, DEPTH_LEVELS_DIR, partition_date)


def read_trade_records(filepath: str) -> List[TradeRecord]:
    """
    Read one trade Parquet file back into a list of TradeRecord
    objects. Uses ParquetFile(...).read() rather than
    pq.read_table(), since this reads one physical file, not a
    partitioned dataset — pq.read_table() defaults to Hive
    partition discovery and could inject a synthetic column from
    the containing date=YYYY-MM-DD/ directory name.
    """
    table = pq.ParquetFile(filepath).read()
    return [
        TradeRecord(
            timestamp_received=row["timestamp_received"],
            event_time=row["event_time"],
            trade_time=row["trade_time"],
            trade_id=row["trade_id"],
            price=Decimal(row["price"]),
            quantity=Decimal(row["quantity"]),
            is_buyer_maker=row["is_buyer_maker"],
        )
        for row in table.to_pylist()
    ]


def read_depth_level_records(filepath: str) -> List[DepthLevelRecord]:
    """
    Read one depth Parquet file back into a list of
    DepthLevelRecord objects. Same single-file reading rationale as
    read_trade_records() above.
    """
    table = pq.ParquetFile(filepath).read()
    return [
        DepthLevelRecord(
            timestamp_received=row["timestamp_received"],
            event_time=row["event_time"],
            transaction_time=row["transaction_time"],
            first_update_id=row["first_update_id"],
            final_update_id=row["final_update_id"],
            previous_final_update_id=row["previous_final_update_id"],
            side=row["side"],
            price=Decimal(row["price"]),
            quantity=Decimal(row["quantity"]),
        )
        for row in table.to_pylist()
    ]
