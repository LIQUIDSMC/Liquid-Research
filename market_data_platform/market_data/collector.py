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

from market_data_platform.market_data.adapters.coinbase import parse_market_trades_message

COINBASE_WS_URL = "wss://advanced-trade-ws.coinbase.com"

SUBSCRIBE_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD"],
    "channel": "market_trades",
}

# Explicitly use certifi's certificate bundle. Python's default SSL
# context on this system does not reliably find a valid CA bundle
# (a known macOS framework-Python issue), causing
# SSLCertVerificationError even for legitimately-signed sites.
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


async def run() -> None:
    """
    Connect to Coinbase's public market_trades channel for BTC-USD,
    parse each real message through the adapter into TradeRecord
    instances, and print the resulting canonical records. No
    storage, no reconnection — proves the adapter works against
    real, live traffic, not just the embedded fixture example.

    timestamp_received is captured immediately upon message
    receipt, at this collector-owned boundary, per the ownership
    principle established during Step 3b design: it is a local
    observation, never derived from the exchange's own timestamp.
    """
    print(f"Connecting to {COINBASE_WS_URL} ...")
    async with connect(COINBASE_WS_URL, ssl=SSL_CONTEXT) as websocket:
        await websocket.send(json.dumps(SUBSCRIBE_MESSAGE))
        print("Connected and subscribed. Printing parsed records (Ctrl+C to stop):\n")
        async for raw_message in websocket:
            timestamp_received = int(time.time() * 1000)
            message = json.loads(raw_message)
            if message.get("channel") != "market_trades":
                continue
            records = parse_market_trades_message(message, timestamp_received)
            for record in records:
                print(record)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nShutting down (Ctrl+C received). Connection closed.")
