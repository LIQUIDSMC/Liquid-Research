"""
Market Data Platform — Coinbase Adapter
market_data_platform/market_data/adapters/coinbase.py

Translates Coinbase's wire-format WebSocket messages into the
platform's canonical schema (TradeRecord, DepthLevelRecord). This
is the only module in the platform permitted to contain Coinbase-
specific logic — per zROADMAP.md Scope, everything downstream of
this adapter is venue-agnostic.

Ownership boundary: timestamp_received is not an exchange fact — it
is when the collector actually observed the message locally. The
collector owns this value and supplies it as a parameter; the
adapter never derives it from the exchange's own timestamp.
Collapsing the two would discard real latency information and
misrepresent what "received" means.

Canonical mapping decisions (see design discussion, this session):
  - Coinbase's ISO 8601 timestamp strings are converted to the
    canonical numeric timestamp representation.
  - Coinbase's string trade_id is converted to the canonical int
    type.
  - Coinbase's side field is a deterministic transformation into
    is_buyer_maker, per Coinbase's own documentation: "side...
    refers to the makers side." side == "BUY" means the buyer was
    the maker (is_buyer_maker=True); side == "SELL" means the
    seller was the maker (is_buyer_maker=False).

Message shape confirmed against Coinbase's official Advanced Trade
WebSocket documentation and a real live connection, this session.
"""

from datetime import datetime
from decimal import Decimal
from typing import List

from market_data_platform.market_data.schema import TradeRecord


def iso8601_to_epoch_millis(iso_string: str) -> int:
    """
    Convert an ISO 8601 timestamp string into Unix epoch
    milliseconds, matching the platform's canonical numeric
    timestamp representation. Not Coinbase-specific — pure ISO-8601
    conversion, kept here since only one adapter currently needs it;
    a natural candidate for extraction into a shared utility once a
    second adapter needs the same conversion.

    Receives:
        iso_string (str): e.g. "2026-07-13T00:42:19.992059Z"

    Returns:
        int: Unix epoch milliseconds.
    """
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def parse_market_trades_message(message: dict, timestamp_received: int) -> List[TradeRecord]:
    """
    Parse one Coinbase market_trades message into a list of
    TradeRecord instances — one per trade in the message's events/
    trades arrays, per the Canonical Unit of Observation principle.
    A single message can report multiple trades batched over a
    250ms window.

    Receives:
        message (dict): a decoded Coinbase market_trades message,
        with keys "channel", "timestamp", "sequence_num", "events".
        timestamp_received (int): the collector's own local receipt
        time (Unix epoch milliseconds), supplied by the caller —
        never derived from the exchange's own timestamp.

    Returns:
        List[TradeRecord]

    Raises:
        ValueError: if message["channel"] is not "market_trades".
        KeyError: if a required field is missing.
    """
    if message.get("channel") != "market_trades":
        raise ValueError(
            f"parse_market_trades_message() requires a market_trades "
            f"message, got channel='{message.get('channel')}'."
        )

    event_time = iso8601_to_epoch_millis(message["timestamp"])

    records = []

    for event in message.get("events", []):
        for trade in event.get("trades", []):
            records.append(TradeRecord(
                timestamp_received=timestamp_received,
                event_time=event_time,
                trade_time=iso8601_to_epoch_millis(trade["time"]),
                trade_id=int(trade["trade_id"]),
                price=Decimal(trade["price"]),
                quantity=Decimal(trade["size"]),
                is_buyer_maker=(trade["side"] == "BUY"),
            ))

    return records


if __name__ == "__main__":
    # Smoke test against a real message shape captured from the
    # live Coinbase connection during Step 3a, this session.
    real_message = {
        "channel": "market_trades",
        "timestamp": "2026-07-13T00:42:20.035371636Z",
        "sequence_num": 154,
        "events": [
            {
                "type": "update",
                "trades": [
                    {
                        "product_id": "BTC-USD",
                        "trade_id": "1054922998",
                        "price": "63630.96",
                        "size": "0.00000009",
                        "time": "2026-07-13T00:42:19.992059Z",
                        "side": "BUY",
                    },
                    {
                        "product_id": "BTC-USD",
                        "trade_id": "1054922997",
                        "price": "63630.97",
                        "size": "0.00077797",
                        "time": "2026-07-13T00:42:19.955503Z",
                        "side": "SELL",
                    },
                ],
            }
        ],
    }

    # Simulated local receipt time — in real use, the collector
    # supplies this at the moment the raw message actually arrives.
    fake_timestamp_received = 1783901740000

    records = parse_market_trades_message(real_message, fake_timestamp_received)
    print(f"Parsed {len(records)} TradeRecords from one market_trades message:")
    for r in records:
        print(" ", r)

    assert records[0].price == Decimal("63630.96"), "Price value was not preserved exactly!"
    assert records[0].quantity == Decimal("0.00000009"), "Quantity value was not preserved exactly!"
    assert records[0].is_buyer_maker is True, "BUY side should map to is_buyer_maker=True"
    assert records[1].is_buyer_maker is False, "SELL side should map to is_buyer_maker=False"
    assert records[0].timestamp_received == fake_timestamp_received, "timestamp_received should be the supplied value, not derived"
    print("\nAll precision and mapping checks passed.")

    try:
        parse_market_trades_message({"channel": "level2"}, fake_timestamp_received)
        print("ERROR: wrong channel was not rejected")
    except ValueError as e:
        print("Correctly rejected wrong channel:", e)
