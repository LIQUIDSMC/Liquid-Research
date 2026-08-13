"""
Market Data Platform — Collector Integration Test
market_data_platform/market_data/test_collector_integration.py

Offline integration tests for collector.py, invoking the real
production functions directly (_stream_messages, _flush_all_pending)
rather than reimplementing their logic — these tests exercise the
actual code path the live collector runs. Uses a fake WebSocket (no
real network) and storage functions patched to write into an
isolated temporary directory (no production canonical path is ever
touched).

Run directly: python3 -m market_data_platform.market_data.test_collector_integration
"""

import asyncio
import json
import os
import tempfile
from decimal import Decimal

from websockets.exceptions import ConnectionClosed

from L1_CORE.market_data_platform.market_data import collector
from L1_CORE.market_data_platform.market_data import storage
from L1_CORE.market_data_platform.market_data.buffer import RecordBuffer


class FakeWebSocket:
    """
    Fake WebSocket exposing only .recv(), matching what
    _stream_messages() actually uses. Returns queued messages in
    order; once exhausted, either raises ConnectionClosed
    (disconnect_after reached) or sleeps indefinitely to simulate a
    quiet feed (letting asyncio.wait_for's own timeout fire, or
    letting an external cancellation interrupt it).
    """

    def __init__(self, messages_to_send=None, disconnect_after=None):
        self._queue = list(messages_to_send or [])
        self._disconnect_after = disconnect_after
        self._recv_count = 0

    async def recv(self):
        self._recv_count += 1
        if self._disconnect_after is not None and self._recv_count > self._disconnect_after:
            raise ConnectionClosed(None, None)
        if self._queue:
            return self._queue.pop(0)
        await asyncio.sleep(100)


def _real_trade_message(sequence_num: int = 0) -> str:
    return json.dumps({
        "channel": "market_trades",
        "timestamp": "2026-07-14T00:00:00.000000Z",
        "sequence_num": sequence_num,
        "events": [{
            "type": "update",
            "trades": [{
                "product_id": "BTC-USD",
                "trade_id": "1",
                "price": "63630.96",
                "size": "0.00000009",
                "time": "2026-07-14T00:00:00.000000Z",
                "side": "BUY",
            }],
        }],
    })


def _real_depth_message(sequence_num: int = 0) -> str:
    return json.dumps({
        "channel": "l2_data",
        "client_id": "",
        "timestamp": "2026-07-14T00:00:00.000000Z",
        "sequence_num": sequence_num,
        "events": [{
            "type": "snapshot",
            "product_id": "BTC-USD",
            "updates": [{
                "side": "bid",
                "event_time": "2026-07-14T00:00:00.000000Z",
                "price_level": "21921.73",
                "new_quantity": "0.06317902",
            }],
        }],
    })


class _IsolatedProductionPath:
    """
    Patches storage's module-level path constants to an isolated
    temporary directory, so any real write_trade_records/
    write_depth_level_records call made through the real production
    code path never touches data/market_data_platform/canonical/.
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


def _walk_files(directory):
    found = []
    if os.path.exists(directory):
        for root, _, files in os.walk(directory):
            found.extend(files)
    return found


def test_count_triggered_persistence_through_stream_messages():
    with _IsolatedProductionPath() as iso:
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=2, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        fake_ws = FakeWebSocket(messages_to_send=[_real_trade_message(0), _real_trade_message(1)], disconnect_after=2)

        try:
            asyncio.run(collector._stream_messages(fake_ws, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
        except ConnectionClosed:
            pass

        assert trade_buffer.records == [], "Trade buffer should have flushed at count_threshold=2"
        assert len(_walk_files(os.path.join(iso.tmp_root, "canonical", "trades"))) == 1
        print("PASS: count-triggered persistence through the real _stream_messages() production function")


def test_timeout_triggered_persistence_during_silence():
    with _IsolatedProductionPath() as iso:
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=0.05)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        fake_ws = FakeWebSocket(messages_to_send=[_real_trade_message(0)])

        async def run_briefly():
            task = asyncio.create_task(collector._stream_messages(fake_ws, trade_buffer, depth_buffer, receive_timeout_seconds=0.02))
            await asyncio.sleep(0.15)  # long enough for the message to arrive and the interval to elapse during silence
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_briefly())

        assert trade_buffer.records == [], "Trade buffer should have flushed due to elapsed time during a quiet feed, via the real production loop"
        print("PASS: true timeout-triggered persistence during simulated feed silence, through the real production loop")


def test_parsed_records_enter_correct_buffer():
    with _IsolatedProductionPath():
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        fake_ws = FakeWebSocket(messages_to_send=[_real_trade_message(0), _real_depth_message(1)], disconnect_after=2)

        try:
            asyncio.run(collector._stream_messages(fake_ws, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
        except ConnectionClosed:
            pass

        assert len(trade_buffer.records) == 1
        assert len(depth_buffer.records) == 1
        assert trade_buffer.records[0].price == Decimal("63630.96")
        assert depth_buffer.records[0].price == Decimal("21921.73")
        print("PASS: parsed trade and depth records enter their correct, separate buffers, through the real production loop")


def test_persistence_errors_propagate_through_stream_messages():
    with _IsolatedProductionPath():
        def failing_writer(records):
            raise RuntimeError("Simulated persistence failure")

        trade_buffer = RecordBuffer(failing_writer, storage.partition_date_utc, count_threshold=1, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        fake_ws = FakeWebSocket(messages_to_send=[_real_trade_message(0)])

        try:
            asyncio.run(collector._stream_messages(fake_ws, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
            raise AssertionError("Expected persistence failure to propagate, but it did not.")
        except RuntimeError as e:
            print(f"PASS: persistence error correctly propagated out of the real _stream_messages(): {e}")


def test_network_closure_is_reconnectable():
    with _IsolatedProductionPath():
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        fake_ws = FakeWebSocket(messages_to_send=[_real_trade_message(0)], disconnect_after=1)

        try:
            asyncio.run(collector._stream_messages(fake_ws, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
            raise AssertionError("Expected ConnectionClosed to propagate, but it did not.")
        except ConnectionClosed:
            print("PASS: ConnectionClosed propagates out of the real _stream_messages(), enabling reconnection at the run() level")


def test_buffers_survive_simulated_reconnect():
    with _IsolatedProductionPath():
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)

        fake_ws_one = FakeWebSocket(messages_to_send=[_real_trade_message(0)], disconnect_after=1)
        try:
            asyncio.run(collector._stream_messages(fake_ws_one, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
        except ConnectionClosed:
            pass
        assert len(trade_buffer.records) == 1

        # Simulated reconnect: same buffer objects passed to a fresh
        # _stream_messages() call, exactly as run() does through
        # _connect_and_stream().
        fake_ws_two = FakeWebSocket(messages_to_send=[_real_trade_message(1)], disconnect_after=1)
        try:
            asyncio.run(collector._stream_messages(fake_ws_two, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
        except ConnectionClosed:
            pass

        assert len(trade_buffer.records) == 2, "Records from before and after a simulated reconnect must both be retained"
        print("PASS: buffers survive a simulated reconnect, using the real _stream_messages() production function")


def test_real_cancellation_triggers_finally_flush():
    """
    Genuine asyncio task cancellation test: starts a coroutine that
    owns preloaded buffers and calls _flush_all_pending() in its own
    finally block (mirroring run()'s real structure), cancels the
    running task, and confirms the finally path executed and
    persisted the pending records.
    """
    with _IsolatedProductionPath() as iso:
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)

        # Preload a record directly, simulating one already buffered
        # before cancellation occurs.
        preloaded = collector.parse_market_trades_message(json.loads(_real_trade_message(0)), 1720000000000)[0]
        trade_buffer.add(preloaded)

        async def cancellable_coroutine():
            try:
                await asyncio.sleep(100)  # simulates run()'s reconnect loop, blocked until cancelled
            finally:
                collector._flush_all_pending(trade_buffer, depth_buffer)

        async def run_and_cancel():
            task = asyncio.create_task(cancellable_coroutine())
            await asyncio.sleep(0.02)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_and_cancel())

        assert trade_buffer.records == [], "Pending record should have been flushed by the real cancellation-triggered finally path"
        assert len(_walk_files(os.path.join(iso.tmp_root, "canonical", "trades"))) == 1
        print("PASS: real asyncio task cancellation executed the finally path, which called _flush_all_pending() and persisted the pending record")


def test_final_flush_failure_propagates_through_cancellation():
    """
    Same real-cancellation structure as above, but with a failing
    writer, proving a final-flush failure at the real cancellation
    path is not swallowed — it propagates out of the finally block.
    """
    def failing_writer(records):
        raise RuntimeError("Simulated final-flush failure")

    trade_buffer = RecordBuffer(failing_writer, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)
    depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1000, max_interval_seconds=1000.0)

    preloaded = collector.parse_market_trades_message(json.loads(_real_trade_message(0)), 1720000000000)[0]
    trade_buffer.add(preloaded)

    caught = {"exception": None}

    async def cancellable_coroutine():
        try:
            await asyncio.sleep(100)
        finally:
            collector._flush_all_pending(trade_buffer, depth_buffer)

    async def run_and_cancel():
        task = asyncio.create_task(cancellable_coroutine())
        await asyncio.sleep(0.02)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except RuntimeError as e:
            caught["exception"] = e

    asyncio.run(run_and_cancel())

    assert caught["exception"] is not None, "Expected the final-flush RuntimeError to propagate through the cancelled task, but it did not."
    print(f"PASS: final-flush failure correctly propagated through the real cancellation path: {caught['exception']}")


def test_no_production_canonical_path_touched():
    real_production_path = "L1_CORE/market_data_platform/data/canonical"
    files_before = _walk_files(real_production_path)

    with _IsolatedProductionPath():
        trade_buffer = RecordBuffer(storage.write_trade_records, storage.partition_date_utc, count_threshold=1, max_interval_seconds=1000.0)
        depth_buffer = RecordBuffer(storage.write_depth_level_records, storage.partition_date_utc, count_threshold=1, max_interval_seconds=1000.0)
        fake_ws = FakeWebSocket(messages_to_send=[_real_trade_message(0), _real_depth_message(1)], disconnect_after=2)
        try:
            asyncio.run(collector._stream_messages(fake_ws, trade_buffer, depth_buffer, receive_timeout_seconds=0.05))
        except ConnectionClosed:
            pass

    files_after = _walk_files(real_production_path)
    assert files_before == files_after, "Real production canonical directory was touched during isolated tests!"
    print("PASS: no file was added to the real production canonical directory at any point")


if __name__ == "__main__":
    test_count_triggered_persistence_through_stream_messages()
    test_timeout_triggered_persistence_during_silence()
    test_parsed_records_enter_correct_buffer()
    test_persistence_errors_propagate_through_stream_messages()
    test_network_closure_is_reconnectable()
    test_buffers_survive_simulated_reconnect()
    test_real_cancellation_triggers_finally_flush()
    test_final_flush_failure_propagates_through_cancellation()
    test_no_production_canonical_path_touched()

    print("\nAll collector integration tests passed, exercising real production functions. No production canonical data was touched at any point.")
