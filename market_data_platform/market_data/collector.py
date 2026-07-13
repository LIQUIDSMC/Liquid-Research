"""
Market Data Platform — Live Collector (Step 3a)
market_data_platform/market_data/collector.py

Step 3a scope only: connect to Coinbase's live public market_trades
channel for BTC-USD and print raw messages exactly as received. No
parsing, no adapter usage, no storage, no reconnection, no
multi-symbol handling. Each of those is a separate, later step.

Public channel — no authentication required, confirmed directly
from Coinbase's official WebSocket setup guide: "Public channels do
not require authentication, so you can simply send a subscription
message after establishing the WebSocket connection."

Usage:
    python3 -m market_data_platform.market_data.collector
    (Ctrl+C to stop; connection closes gracefully.)
"""

import asyncio
import json
import ssl
import time
import certifi
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from market_data_platform.market_data.adapters.coinbase import parse_market_trades_message, parse_level2_message

COINBASE_WS_URL = "wss://advanced-trade-ws.coinbase.com"

SUBSCRIBE_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD"],
    "channel": "market_trades",
}

LEVEL2_SUBSCRIBE_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD"],
    "channel": "level2",
}

# Explicitly use certifi's certificate bundle. Python's default SSL
# context on this system does not reliably find a valid CA bundle
# (a known macOS framework-Python issue), causing
# SSLCertVerificationError even for legitimately-signed sites.
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class SequenceGapTracker:
    """
    Tracks sequence_num continuity for one connection session's
    lifetime only. Confirmed by live evidence, this session:
    sequence_num is a single counter shared across every channel,
    product, and control message on one WebSocket connection — not
    scoped per channel or per product.

    Sequence continuity is valid only within one observed connection
    session. A new tracker is created for every connection. The
    first sequence observed in a new connection is accepted as the
    baseline, regardless of its value — no continuity is inferred
    across reconnects, since one observed reconnect restarting at 0
    does not establish a guarantee that every future connection will
    behave identically.

    A new SequenceGapTracker instance must be created for every new
    _connect_and_stream() call — never reused across reconnects.
    """

    def __init__(self):
        self.previous_sequence = None

    def check(self, sequence_num) -> None:
        """
        Check one message's sequence_num against the previously
        seen value for this session, and log the result. Never
        raises, never crashes the collector — a malformed or
        unexpected sequence value is logged, not fatal.

        Receives:
            sequence_num: the message's raw "sequence_num" value,
            of unknown type until validated here.

        Returns:
            None. All results are logged directly to console.
        """
        if type(sequence_num) is not int:
            print(f"GAP-TRACKER: malformed sequence_num (not an int): {sequence_num!r}")
            return

        if self.previous_sequence is None:
            self.previous_sequence = sequence_num
            return

        expected = self.previous_sequence + 1

        if sequence_num == expected:
            self.previous_sequence = sequence_num
        elif sequence_num > expected:
            missing_count = sequence_num - expected
            print(
                f"GAP DETECTED: previous={self.previous_sequence}, current={sequence_num}, "
                f"first_missing={expected}, last_missing={sequence_num - 1}, "
                f"missing_count={missing_count}"
            )
            self.previous_sequence = sequence_num
        else:
            print(
                f"DUPLICATE/OUT-OF-ORDER: previous={self.previous_sequence}, "
                f"current={sequence_num} (not advancing tracker)"
            )


async def _connect_and_stream() -> None:
    """
    Perform a single connection attempt: connect, subscribe, and
    stream messages until the connection drops or the process is
    interrupted. May return normally (remote side closed cleanly,
    e.g. code 1000/1001) or raise ConnectionClosed/OSError (an
    abnormal drop). The caller (run()) treats both cases as a
    reason to reconnect.

    timestamp_received is captured immediately upon message
    receipt, at this collector-owned boundary, per the ownership
    principle established during Step 3b design: it is a local
    observation, never derived from the exchange's own timestamp.
    """
    print(f"Connecting to {COINBASE_WS_URL} ...")
    async with connect(
        COINBASE_WS_URL,
        ssl=SSL_CONTEXT,
        max_size=8 * 1024 * 1024,
    ) as websocket:
        await websocket.send(json.dumps(SUBSCRIBE_MESSAGE))
        await websocket.send(json.dumps(LEVEL2_SUBSCRIBE_MESSAGE))
        gap_tracker = SequenceGapTracker()
        print("Connected and subscribed. Printing parsed records (Ctrl+C to stop):\n")
        async for raw_message in websocket:
            timestamp_received = int(time.time() * 1000)
            message = json.loads(raw_message)
            channel = message.get("channel")

            gap_tracker.check(message.get("sequence_num"))

            if channel == "market_trades":
                records = parse_market_trades_message(message, timestamp_received)
                for record in records:
                    print(record)
            elif channel == "l2_data":
                records = parse_level2_message(message, timestamp_received)
                for record in records:
                    print(record)


async def run() -> None:
    """
    Run the collector indefinitely, automatically reconnecting on
    any connection drop — whether the drop raises an exception
    (ConnectionClosed, OSError) or the connection ends cleanly from
    the remote side (_connect_and_stream() simply returns with no
    exception). Both paths are treated identically: log, wait,
    reconnect. No gap detection yet (Step 3f) — a reconnection is
    only proven to happen, not yet proven to be gap-tracked.

    Ctrl+C raises KeyboardInterrupt, which is deliberately NOT
    caught here — it propagates up to __main__'s existing handler
    and exits normally, without triggering a reconnect.

    A short fixed backoff is used between reconnection attempts to
    avoid hammering Coinbase's server if the connection keeps
    failing (e.g. during a real network outage).
    """
    reconnect_delay_seconds = 3

    while True:
        try:
            await _connect_and_stream()
            print("\nConnection ended (remote side closed cleanly).")
        except (ConnectionClosed, OSError) as e:
            print(f"\nConnection lost: {e}")

        print(f"Reconnecting in {reconnect_delay_seconds} seconds...\n")
        await asyncio.sleep(reconnect_delay_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nShutting down (Ctrl+C received). Connection closed.")
