"""
Market Data Platform — Binance Adapter
platform/market_data/adapters/binance.py

Translates Binance's wire-format WebSocket messages into the
platform's canonical schema (DepthLevelRecord, TradeRecord). This
is the only module in the platform permitted to contain Binance-
specific logic — per zROADMAP.md Scope, everything downstream of
this adapter is venue-agnostic.

Validation boundary: this adapter performs Binance-specific
structural validation (correct message type, required fields
present) before constructing canonical records. The schema classes
(DepthLevelRecord, TradeRecord) enforce platform-wide invariants
only (non-negative price/quantity, Decimal type, valid side) — they
have no knowledge of Binance's message shape and never validate
against it.

This module performs parsing and normalization only. No
networking, no storage.

Message shapes confirmed against Binance's official WebSocket
Streams documentation (developers.binance.com), not assumed.
"""

import time
from decimal import Decimal
from typing import List

from L1_CORE.market_data_platform.market_data.schema import DepthLevelRecord, TradeRecord


def parse_depth_update(message: dict) -> List[DepthLevelRecord]:
    """
    Parse one Binance depthUpdate message into a list of
    DepthLevelRecord instances — one per price level reported in
    the message's "b" (bids) and "a" (asks) arrays, per the
    Canonical Unit of Observation principle (a message may report
    many indivisible facts; each becomes its own record).

    Receives:
        message (dict): a decoded Binance depthUpdate message, with
        keys "e", "E", "T" (optional), "U", "u", "pu" (optional),
        "b", "a".

    Returns:
        List[DepthLevelRecord]: one record per price level change
        in the message, all sharing the same U/u/pu context.

    Raises:
        ValueError: if message["e"] is not "depthUpdate".
        KeyError: if a required field is missing from the message.
    """
    if message.get("e") != "depthUpdate":
        raise ValueError(
            f"parse_depth_update() requires a depthUpdate message, "
            f"got e='{message.get('e')}'."
        )

    timestamp_received = int(time.time() * 1000)
    event_time = message["E"]
    transaction_time = message["T"] if "T" in message else None
    first_update_id = message["U"]
    final_update_id = message["u"]
    previous_final_update_id = message["pu"] if "pu" in message else None

    instrument_id = message.get("s")
    if not instrument_id:
        raise ValueError(
            f"parse_depth_update() received a message with missing "
            f"or empty symbol ('s'): {message!r}"
        )

    records = []

    for price_str, quantity_str in message.get("b", []):
        records.append(DepthLevelRecord(
            timestamp_received=timestamp_received,
            event_time=event_time,
            transaction_time=transaction_time,
            first_update_id=first_update_id,
            final_update_id=final_update_id,
            previous_final_update_id=previous_final_update_id,
            side="bid",
            price=Decimal(price_str),
            quantity=Decimal(quantity_str),
            instrument_id=instrument_id,
        ))

    for price_str, quantity_str in message.get("a", []):
        records.append(DepthLevelRecord(
            timestamp_received=timestamp_received,
            event_time=event_time,
            transaction_time=transaction_time,
            first_update_id=first_update_id,
            final_update_id=final_update_id,
            previous_final_update_id=previous_final_update_id,
            side="ask",
            price=Decimal(price_str),
            quantity=Decimal(quantity_str),
            instrument_id=instrument_id,
        ))

    return records


def parse_trade(message: dict) -> TradeRecord:
    """
    Parse one Binance trade message into a single TradeRecord.

    Receives:
        message (dict): a decoded Binance trade message, with keys
        "e", "E", "T" (optional), "t", "p", "q", "m".

    Returns:
        TradeRecord

    Raises:
        ValueError: if message["e"] is not "trade".
        KeyError: if a required field is missing.
    """
    if message.get("e") != "trade":
        raise ValueError(
            f"parse_trade() requires a trade message, "
            f"got e='{message.get('e')}'."
        )

    timestamp_received = int(time.time() * 1000)

    instrument_id = message.get("s")
    if not instrument_id:
        raise ValueError(
            f"parse_trade() received a message with missing or empty "
            f"symbol ('s'): {message!r}"
        )

    return TradeRecord(
        timestamp_received=timestamp_received,
        event_time=message["E"],
        trade_time=message["T"] if "T" in message else None,
        trade_id=message["t"],
        instrument_id=instrument_id,
        price=Decimal(message["p"]),
        quantity=Decimal(message["q"]),
        is_buyer_maker=message["m"],
    )


if __name__ == "__main__":
    # Smoke test against real, known message shapes confirmed from
    # Binance's official WebSocket documentation — not invented.

    real_depth_update = {
        "e": "depthUpdate",
        "E": 1672515782136,
        "s": "BNBBTC",
        "U": 157,
        "u": 160,
        "pu": 149,
        "b": [["0.0024", "10"]],
        "a": [["0.0026", "100"]],
    }
    depth_records = parse_depth_update(real_depth_update)
    print(f"Parsed {len(depth_records)} DepthLevelRecords from one depthUpdate message:")
    for r in depth_records:
        print(" ", r)

    real_trade = {
        "e": "trade",
        "E": 1773110023891,
        "T": 1773110023877,
        "m": False,
        "p": "8.40000000",
        "q": "0.97915700",
        "s": "ALPHA_116USDT",
        "t": 19911650,
    }
    trade_record = parse_trade(real_trade)
    print("\nParsed TradeRecord:")
    print(" ", trade_record)

    # Confirm exact decimal preservation — the entire point of the
    # Numeric Precision principle.
    assert str(depth_records[0].price) == "0.0024", "Price precision was not preserved exactly!"
    assert str(trade_record.quantity) == "0.97915700", "Quantity precision was not preserved exactly!"
    print("\nPrecision check passed: Decimal values match transmitted strings exactly.")

    # Confirm message-type validation rejects the wrong type.
    try:
        parse_depth_update(real_trade)
        print("ERROR: parse_depth_update() accepted a trade message")
    except ValueError as e:
        print("Correctly rejected wrong message type:", e)

    try:
        parse_trade(real_depth_update)
        print("ERROR: parse_trade() accepted a depthUpdate message")
    except ValueError as e:
        print("Correctly rejected wrong message type:", e)
