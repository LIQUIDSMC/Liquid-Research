"""
Market Data Platform — Parquet Round-Trip Precision Test
market_data_platform/market_data/test_parquet_roundtrip.py

Proves, before any storage-writing code is built into the
collector, whether PyArrow's native decimal128 type can serve as
the canonical on-disk numeric representation for TradeRecord and
DepthLevelRecord, per the roadmap's Numeric Precision principle:
canonical numeric values must preserve the exact mathematical
decimal value reported by the exchange — not any particular textual
or byte-level formatting.

An explicit Arrow schema is declared up front. Nothing is inferred
from example rows. Multiple real-world scales are tested
(63630.96, 0.00000009, 10, 0) against one fixed (precision, scale)
bound, to prove that bound is genuinely safe rather than assumed.

Run directly: python3 -m market_data_platform.market_data.test_parquet_roundtrip
"""

import os
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq

from market_data_platform.market_data.schema import TradeRecord, DepthLevelRecord

TEST_OUTPUT_PATH = "/tmp/test_canonical_roundtrip.parquet"

# Candidate precision/scale bound under test. 18 total digits, 8 of
# them after the decimal point — chosen based on real values
# observed in live Coinbase traffic this session (finest observed
# decimal precision: quantities like 0.00000009, 8 decimal places;
# largest observed magnitude: prices in the tens of thousands with
# 2 decimal places). This test proves only that these specific
# representative values fit and round-trip exactly under this
# bound, plus documents the failure boundary for values outside it
# — it does not prove the bound is universally safe for every
# value any venue could ever transmit.
DECIMAL_PRECISION = 18
DECIMAL_SCALE = 8

DECIMAL_TYPE = pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE)

# Explicit combined schema for both record types' shared numeric
# fields, declared up front — nothing inferred from example rows.
ARROW_SCHEMA = pa.schema([
    ("record_type", pa.string()),
    ("timestamp_received", pa.int64()),
    ("event_time", pa.int64()),
    ("trade_time", pa.int64()),
    ("trade_id", pa.int64()),
    ("transaction_time", pa.int64()),
    ("first_update_id", pa.int64()),
    ("final_update_id", pa.int64()),
    ("previous_final_update_id", pa.int64()),
    ("side", pa.string()),
    ("price", DECIMAL_TYPE),
    ("quantity", DECIMAL_TYPE),
    ("is_buyer_maker", pa.bool_()),
])


def _trade_record_to_row(record: TradeRecord) -> dict:
    return {
        "record_type": "trade",
        "timestamp_received": record.timestamp_received,
        "event_time": record.event_time,
        "trade_time": record.trade_time,
        "trade_id": record.trade_id,
        "transaction_time": None,
        "first_update_id": None,
        "final_update_id": None,
        "previous_final_update_id": None,
        "side": None,
        "price": record.price,
        "quantity": record.quantity,
        "is_buyer_maker": record.is_buyer_maker,
    }


def _depth_record_to_row(record: DepthLevelRecord) -> dict:
    return {
        "record_type": "depth",
        "timestamp_received": record.timestamp_received,
        "event_time": record.event_time,
        "trade_time": None,
        "trade_id": None,
        "transaction_time": record.transaction_time,
        "first_update_id": record.first_update_id,
        "final_update_id": record.final_update_id,
        "previous_final_update_id": record.previous_final_update_id,
        "side": record.side,
        "price": record.price,
        "quantity": record.quantity,
        "is_buyer_maker": None,
    }


def test_native_decimal_roundtrip():
    """
    Write one TradeRecord and one DepthLevelRecord, covering
    multiple real-world Decimal scales, to Parquet using an
    explicit decimal128 schema. Read back, reconstruct canonical
    records, and assert exact Decimal equality — not textual
    equality — for every numeric field. Also assert the actual
    on-disk Arrow column type matches what was declared, so a
    silent schema-inference drift can never pass unnoticed.
    """
    trade = TradeRecord(
        timestamp_received=1783901740000,
        event_time=1783903340035,
        trade_time=1783903339992,
        trade_id=1054922998,
        price=Decimal("63630.96"),       # 2 decimal places
        quantity=Decimal("0.00000009"),  # 8 decimal places, smallest scale observed live
        is_buyer_maker=True,
    )

    depth = DepthLevelRecord(
        timestamp_received=1783901740001,
        event_time=1783903340036,
        transaction_time=1783903340010,
        first_update_id=None,
        final_update_id=None,
        previous_final_update_id=None,
        side="bid",
        price=Decimal("10"),   # whole number, 0 decimal places
        quantity=Decimal("0"), # exact zero, tests the "level removed" case
    )

    rows = [_trade_record_to_row(trade), _depth_record_to_row(depth)]
    table = pa.Table.from_pylist(rows, schema=ARROW_SCHEMA)

    pq.write_table(table, TEST_OUTPUT_PATH)

    table_read = pq.read_table(TEST_OUTPUT_PATH)

    # Assert the on-disk column types are exactly what was declared
    # — not inferred, not silently widened or narrowed.
    read_schema = table_read.schema
    price_type = read_schema.field("price").type
    quantity_type = read_schema.field("quantity").type
    assert price_type == DECIMAL_TYPE, f"price column type drifted: expected {DECIMAL_TYPE}, got {price_type}"
    assert quantity_type == DECIMAL_TYPE, f"quantity column type drifted: expected {DECIMAL_TYPE}, got {quantity_type}"
    print(f"PASS: on-disk price/quantity columns are exactly decimal128(precision={DECIMAL_PRECISION}, scale={DECIMAL_SCALE})")

    rows_read = table_read.to_pylist()
    trade_row = next(r for r in rows_read if r["record_type"] == "trade")
    depth_row = next(r for r in rows_read if r["record_type"] == "depth")

    reconstructed_trade = TradeRecord(
        timestamp_received=trade_row["timestamp_received"],
        event_time=trade_row["event_time"],
        trade_time=trade_row["trade_time"],
        trade_id=trade_row["trade_id"],
        price=Decimal(trade_row["price"]),
        quantity=Decimal(trade_row["quantity"]),
        is_buyer_maker=trade_row["is_buyer_maker"],
    )

    reconstructed_depth = DepthLevelRecord(
        timestamp_received=depth_row["timestamp_received"],
        event_time=depth_row["event_time"],
        transaction_time=depth_row["transaction_time"],
        first_update_id=depth_row["first_update_id"],
        final_update_id=depth_row["final_update_id"],
        previous_final_update_id=depth_row["previous_final_update_id"],
        side=depth_row["side"],
        price=Decimal(depth_row["price"]),
        quantity=Decimal(depth_row["quantity"]),
    )

    assert reconstructed_trade.price == trade.price, f"Trade price drifted: {trade.price} -> {reconstructed_trade.price}"
    assert reconstructed_trade.quantity == trade.quantity, f"Trade quantity drifted: {trade.quantity} -> {reconstructed_trade.quantity}"
    assert reconstructed_trade == trade, "TradeRecord did not round-trip identically"
    print(f"PASS: TradeRecord round-trips exactly (price={trade.price}, quantity={trade.quantity})")

    assert reconstructed_depth.price == depth.price, f"Depth price drifted: {depth.price} -> {reconstructed_depth.price}"
    assert reconstructed_depth.quantity == depth.quantity, f"Depth quantity drifted: {depth.quantity} -> {reconstructed_depth.quantity}"
    assert reconstructed_depth == depth, "DepthLevelRecord did not round-trip identically"
    assert reconstructed_depth.first_update_id is None, "None fields must round-trip as None, not fabricated"
    print(f"PASS: DepthLevelRecord round-trips exactly (price={depth.price}, quantity={depth.quantity}, first_update_id=None preserved)")

    os.remove(TEST_OUTPUT_PATH)


def test_scale_boundary_rejects_too_fine_precision():
    """
    Prove the declared failure boundary: a value requiring more
    decimal places than DECIMAL_SCALE must fail clearly, not
    silently round. This documents the boundary rather than
    assuming the chosen scale is universally sufficient.
    """
    too_fine = Decimal("0.000000001")  # requires scale 9; bound is scale 8

    try:
        pa.array([too_fine], type=DECIMAL_TYPE)
    except (pa.ArrowException, ValueError) as e:
        print(
            "PASS: value requiring finer precision than declared "
            f"scale correctly rejected: {e}"
        )
    else:
        raise AssertionError(
            f"Expected pyarrow to reject {too_fine} "
            f"(requires scale 9, bound is scale {DECIMAL_SCALE}), "
            "but it did not raise."
        )


def test_precision_boundary_rejects_too_large_magnitude():
    """
    Prove the declared failure boundary: a value exceeding the
    declared total precision must fail clearly, not silently
    truncate.
    """
    too_large = Decimal("12345678901.00000000")  # 19 total digits at scale 8; bound is precision 18

    try:
        pa.array([too_large], type=DECIMAL_TYPE)
    except (pa.ArrowException, ValueError) as e:
        print(
            "PASS: value exceeding declared precision correctly "
            f"rejected: {e}"
        )
    else:
        raise AssertionError(
            f"Expected pyarrow to reject {too_large} "
            f"(exceeds precision {DECIMAL_PRECISION} at scale "
            f"{DECIMAL_SCALE}), but it did not raise."
        )


if __name__ == "__main__":
    test_native_decimal_roundtrip()
    test_scale_boundary_rejects_too_fine_precision()
    test_precision_boundary_rejects_too_large_magnitude()
    print("\nNative decimal128 Parquet round-trip and boundary tests passed.")
