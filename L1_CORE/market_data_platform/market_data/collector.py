"""
Market Data Platform — Live Collector
market_data_platform/market_data/collector.py

Connects to Coinbase's live public market_trades and level2
(l2_data) channels for BTC-USD and ETH-USD, parses messages through
the Coinbase adapter into canonical TradeRecord/DepthLevelRecord
instances, buffers them (RecordBuffer, one per record type), and
persists them to immutable, UTC-date-partitioned Parquet storage
(storage.py) on a count- or time-triggered flush. Automatically
reconnects on any connection drop, tracking sequence_num continuity
per connection session (SequenceGapTracker). Buffered-but-not-yet-
flushed records survive a reconnect; the gap tracker does not.

Persistence is the canonical operation; console output is
secondary and summary-only (not per-record) to avoid flooding the
console on the high-volume depth stream. Persistence failure is
structural and propagates — it is never silently logged and
ignored, including at final shutdown flush.

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
import uuid
import certifi
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from L1_CORE.market_data_platform.market_data.adapters.coinbase import parse_market_trades_message, parse_level2_message, iso8601_to_epoch_millis
from L1_CORE.market_data_platform.market_data.buffer import RecordBuffer
from L1_CORE.market_data_platform.market_data.storage import write_trade_records, write_depth_level_records, partition_date_utc, verify_canonical_root_or_raise
from L1_CORE.market_data_platform.market_data.telemetry import Telemetry

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

# F2 telemetry emission thresholds (preregistered diagnostics, not cutoffs).
LOOP_GAP_EMIT_NS = 500_000_000
BIG_MSG_ROWS = 5000


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


def _flush_all_pending(trade_buffer: RecordBuffer, depth_buffer: RecordBuffer) -> None:
    """
    Flush both buffers unconditionally, regardless of whether their
    normal count/time threshold has been reached. This is the
    single production shutdown-cleanup function — called from
    run()'s finally block on every exit path, including task
    cancellation, so it is the function offline tests must exercise
    (via real cancellation) to honestly prove shutdown behavior.

    Receives:
        trade_buffer, depth_buffer (RecordBuffer): both flushed via
        _flush_if_due_or_nonempty().

    Raises:
        Whatever exception either buffer's flush() raises,
        unmodified — persistence failure at shutdown is structural
        and must propagate, never be silently logged and ignored.
    """
    _flush_if_due_or_nonempty(trade_buffer, "trade")
    _flush_if_due_or_nonempty(depth_buffer, "depth")


def _flush_if_due_or_nonempty(buffer: RecordBuffer, label: str) -> None:
    """
    Flush the given buffer if it holds any records at all,
    regardless of whether the normal count/time threshold has been
    reached. Used only at shutdown, where any remaining buffered
    records must be persisted before the process exits — waiting
    for the normal threshold would risk losing them.

    Receives:
        buffer (RecordBuffer): the buffer to flush, if non-empty.
        label (str): "trade" or "depth", for the summary message.
    """
    if not buffer.records:
        print(f"No pending {label} records to flush.")
        return
    result = buffer.flush()
    print(
        f"Final flush ({label}): {result.records_persisted} record(s) "
        f"persisted across {len(result.files_written)} file(s): {result.files_written}"
    )


def _flush_if_due(buffer: RecordBuffer, label: str, telemetry=None,
                  trigger_session=None, trigger_seq=None):
    """
    Flush the given buffer if it's due (count or time threshold
    reached), printing a summary of what was persisted. Persistence
    failure is structural — this deliberately does not catch any
    exception from buffer.flush(); it propagates up through
    _connect_and_stream() and run(), stopping the collector rather
    than silently continuing as if the failed records were safe.

    Receives:
        buffer (RecordBuffer): the buffer to check and possibly
        flush.
        label (str): "trade" or "depth", for the summary message.
    """
    if not buffer.is_due_for_flush():
        return None
    rows_pending = len(buffer.records)
    t4 = time.monotonic_ns()
    try:
        result = buffer.flush()
    except Exception as exc:
        t5 = time.monotonic_ns()
        if telemetry is not None:
            telemetry.flush_record(trigger_session, label, rows_pending, trigger_seq,
                                   t4, t5, False, None, type(exc).__name__)
        raise
    t5 = time.monotonic_ns()
    print(
        f"Flushed {label} buffer: {result.records_persisted} record(s) "
        f"persisted across {len(result.files_written)} file(s): {result.files_written}"
    )
    if telemetry is not None:
        telemetry.flush_record(trigger_session, label, rows_pending, trigger_seq,
                               t4, t5, True, len(result.files_written), None)
    return t5


async def _stream_messages(
    websocket,
    trade_buffer: RecordBuffer,
    depth_buffer: RecordBuffer,
    receive_timeout_seconds: float = 1.0,
    telemetry=None,
) -> None:
    """
    The real, production message receive loop: waits for a message
    on the given websocket (bounded by receive_timeout_seconds so a
    quiet feed still allows time-based flushing), parses it,
    buffers the resulting canonical records, and flushes each
    buffer when due. Runs until the websocket raises (e.g.
    ConnectionClosed) or the coroutine is cancelled.

    A new SequenceGapTracker is created here, scoped to this one
    call — matching the existing design that gap tracking is not
    valid across a reconnect, while trade_buffer/depth_buffer are
    owned by the caller and persist across calls.

    This function is the single production implementation of the
    receive loop — offline tests invoke it directly (with a fake
    websocket) rather than reimplementing its logic, so tests
    exercise the actual code path the live collector runs.

    Receives:
        websocket: an object with an async .recv() method (a real
        websockets connection, or a fake one in tests).
        trade_buffer, depth_buffer (RecordBuffer): owned by the
        caller, passed through unchanged.
        receive_timeout_seconds (float): how long to wait for a
        message before checking for a due time-based flush.

    Raises:
        Whatever websocket.recv() raises (e.g. ConnectionClosed),
        propagated unchanged so the caller can decide whether to
        reconnect. Also propagates any exception from a buffer
        flush — persistence failure is structural.
    """
    tel = telemetry if telemetry is not None else Telemetry.disabled()
    gap_tracker = SequenceGapTracker()
    session_id = str(uuid.uuid4())
    tel.session_start(session_id)
    prev_t0 = None
    prev_seq = None
    last_seq = None
    prev_end = time.monotonic_ns()
    reason = "returned"

    try:
        while True:
            try:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=receive_timeout_seconds)
            except asyncio.TimeoutError:
                # No message arrived within the timeout — this is the
                # only way a time-based flush can happen during a quiet
                # feed, since a blocking `async for` would never return
                # control here otherwise.
                e1 = _flush_if_due(trade_buffer, "trade", tel, session_id, last_seq)
                e2 = _flush_if_due(depth_buffer, "depth", tel, session_id, last_seq)
                ends = [x for x in (e1, e2) if x is not None]
                if ends:
                    prev_end = max(ends)
                continue

            t0 = time.monotonic_ns()
            wall0 = time.time_ns()
            timestamp_received = int(time.time() * 1000)
            message = json.loads(raw_message)
            t1 = time.monotonic_ns()
            channel = message.get("channel")
            seq = message.get("sequence_num")

            gap_tracker.check(message.get("sequence_num"))

            if prev_t0 is not None and (t0 - prev_t0) >= LOOP_GAP_EMIT_NS:
                tel.loop_gap(session_id, seq, prev_seq, (t0 - prev_t0) / 1e6, prev_end, t0)
            prev_t0, prev_seq, last_seq = t0, seq, seq
            msg_prev_end = prev_end

            big = None
            if channel == "market_trades":
                records = parse_market_trades_message(message, timestamp_received)
                for record in records:
                    trade_buffer.add(record)
                t3 = time.monotonic_ns()
                e = _flush_if_due(trade_buffer, "trade", tel, session_id, seq)
                end = e if e is not None else t3
            elif channel == "l2_data":
                records = parse_level2_message(message, timestamp_received)
                t2 = time.monotonic_ns()
                for record in records:
                    depth_buffer.add(record)
                t3 = time.monotonic_ns()
                if tel.enabled:
                    big = (records, t2, t3)
                e = _flush_if_due(depth_buffer, "depth", tel, session_id, seq)
                end = e if e is not None else t3
            else:
                end = time.monotonic_ns()

            # end (t3 or t5) was captured above, before any telemetry write.
            if big is not None:
                _emit_big_msg(tel, message, big[0], session_id, seq, raw_message,
                              wall0, t0, t1, big[1], big[2], msg_prev_end)
            prev_end = end
    except BaseException as exc:
        reason = type(exc).__name__
        raise
    finally:
        tel.session_end(session_id, reason)


def _emit_big_msg(tel, message, records, session_id, seq, raw_message,
                  wall0, t0, t1, t2, t3, prev_end) -> None:
    # F2 telemetry only: record every snapshot and any message parsing to
    # >= BIG_MSG_ROWS rows. Never raises into the collector.
    try:
        events = [e for e in (message.get("events") or []) if isinstance(e, dict)]
        types = [e.get("type") for e in events]
        if "snapshot" not in types and len(records) < BIG_MSG_ROWS:
            return
        src_ts = message.get("timestamp")
        try:
            lag = wall0 // 1_000_000 - iso8601_to_epoch_millis(src_ts)
        except Exception:
            lag = None
        tel.big_msg(session_id=session_id, seq=seq, channel=message.get("channel"),
                    event_type=",".join(str(t) for t in types),
                    product_id=events[0].get("product_id") if events else None,
                    n_rows=len(records), msg_chars=len(raw_message),
                    source_timestamp=src_ts, recv_wall_ns=wall0,
                    source_timestamp_to_recv_ms=lag,
                    t0=t0, t1=t1, t2=t2, t3=t3, prev_end=prev_end)
    except Exception as exc:
        tel._on_failure(exc)


async def _connect_and_stream(trade_buffer: RecordBuffer, depth_buffer: RecordBuffer, telemetry=None) -> None:
    """
    Perform a single connection attempt: connect, subscribe, and
    stream messages until the connection drops or the process is
    interrupted. May return normally (remote side closed cleanly,
    e.g. code 1000/1001) or raise ConnectionClosed/OSError (an
    abnormal drop). The caller (run()) treats both cases as a
    reason to reconnect.

    trade_buffer and depth_buffer are owned by run() and passed in
    here so buffered records survive a reconnect — this function
    does not construct or reset them.

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
        print("Connected and subscribed. Buffering parsed records for persistence (Ctrl+C to stop):\n")
        await _stream_messages(websocket, trade_buffer, depth_buffer, telemetry=telemetry)


async def run() -> None:
    """
    Run the collector indefinitely, automatically reconnecting on
    any connection drop — whether the drop raises an exception
    (ConnectionClosed, OSError) or the connection ends cleanly from
    the remote side (_connect_and_stream() simply returns with no
    exception). Both paths are treated identically: log, wait,
    reconnect.

    Owns the two RecordBuffer instances (trade, depth) for the
    entire lifetime of the process — constructed once, here, before
    the reconnect loop begins, and passed into _connect_and_stream()
    on every call so buffered-but-not-yet-flushed records survive a
    reconnect. This is deliberately different from
    SequenceGapTracker, which is correctly reconstructed fresh on
    every reconnect inside _connect_and_stream() itself.

    Ctrl+C raises KeyboardInterrupt, which is deliberately NOT
    caught here — it propagates up to __main__'s existing handler
    and exits normally, without triggering a reconnect.

    A short fixed backoff is used between reconnection attempts to
    avoid hammering Coinbase's server if the connection keeps
    failing (e.g. during a real network outage).
    """
    # Startup guard against the 2026-08-24/25 storage-path divergence
    # incident (see STORAGE_PATH_DIVERGENCE_INCIDENT.md): fail loudly,
    # before any writes happen, if the canonical storage path is not
    # what it's expected to be, rather than silently writing to the
    # wrong location for days.
    verify_canonical_root_or_raise()

    reconnect_delay_seconds = 3

    telemetry = Telemetry.from_env()

    trade_buffer = RecordBuffer(
        write_function=write_trade_records,
        partition_date_function=partition_date_utc,
    )
    depth_buffer = RecordBuffer(
        write_function=write_depth_level_records,
        partition_date_function=partition_date_utc,
    )

    try:
        while True:
            try:
                await _connect_and_stream(trade_buffer, depth_buffer, telemetry)
                print("\nConnection ended (remote side closed cleanly).")
            except (ConnectionClosed, OSError) as e:
                print(f"\nConnection lost: {e}")

            print(f"Reconnecting in {reconnect_delay_seconds} seconds...\n")
            await asyncio.sleep(reconnect_delay_seconds)
    finally:
        # Runs on every exit from the while loop above, including
        # task cancellation (Ctrl+C, via asyncio.run()'s handling).
        # Parquet writes are synchronous, so this cannot be
        # interrupted mid-write by cancellation — it runs to
        # completion as ordinary code once entered.
        print("\nFlushing remaining buffered records before shutdown...")
        try:
            _flush_all_pending(trade_buffer, depth_buffer)
        except Exception as e:
            print(f"ERROR: final shutdown flush failed: {e}")
            raise
        finally:
            telemetry.close()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nShutting down (Ctrl+C received). All buffered records flushed successfully.")
    # Any other exception (e.g. a final-flush persistence failure,
    # re-raised deliberately in run()'s finally block) is NOT caught
    # here — it propagates and crashes the process with a real
    # traceback. This is intentional: persistence failure at
    # shutdown must never be reported as a clean, successful exit.
