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


# F3 NOTE:
# The former cancellation tests in this location manually recreated run()'s
# old synchronous `_flush_all_pending()` finally block. They were removed
# when F3 made persistence worker-owned because that synthetic lifecycle no
# longer represented production behavior.
#
# Cancellation/shutdown behavior is now covered through the real `run()`
# function by:
#   - test_run_shutdown_hands_off_active_buffers_then_drains_worker()
#   - test_run_shutdown_worker_failure_propagates_and_telemetry_still_closes()
#
# Worker-level accepted-work draining and failure propagation are additionally
# covered by test_async_persistence.py.


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
    test_no_production_canonical_path_touched()

    print("\nAll collector integration tests passed, exercising real production functions. No production canonical data was touched at any point.")


def test_async_due_buffer_handoff_submits_detached_batch_without_sync_write():
    from L1_CORE.market_data_platform.market_data.collector import _handoff_if_due

    writes = []

    def writer(records):
        writes.append(list(records))
        return "/fake/should-not-write.parquet"

    buffer = RecordBuffer(
        write_function=writer,
        partition_date_function=storage.partition_date_utc,
        count_threshold=2,
        max_interval_seconds=1000.0,
    )

    buffer.add(
        collector.parse_market_trades_message(
            json.loads(_real_trade_message(0)),
            1720000000000,
        )[0]
    )
    buffer.add(
        collector.parse_market_trades_message(
            json.loads(_real_trade_message(0)),
            1720000000000,
        )[0]
    )

    original_records = buffer.records
    submitted = []

    class FakeWorker:
        def submit(self, batch):
            submitted.append(batch)

    _handoff_if_due(buffer, "trade", FakeWorker())

    assert len(submitted) == 1
    assert submitted[0].records is original_records
    assert buffer.records == []
    assert buffer.records is not original_records
    assert writes == [], "Ingestion handoff must not synchronously persist the detached batch"

    print("PASS: due buffer detaches exact ownership and submits without synchronous persistence")


def test_async_non_due_buffer_is_not_detached_or_submitted():
    from L1_CORE.market_data_platform.market_data.collector import _handoff_if_due

    buffer = RecordBuffer(
        write_function=lambda records: "/fake/not-used.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=100,
        max_interval_seconds=1000.0,
    )

    buffer.add(
        collector.parse_market_trades_message(
            json.loads(_real_trade_message(0)),
            1720000000000,
        )[0]
    )
    original_records = buffer.records
    submitted = []

    class FakeWorker:
        def submit(self, batch):
            submitted.append(batch)

    result = _handoff_if_due(buffer, "trade", FakeWorker())

    assert result is None
    assert submitted == []
    assert buffer.records is original_records

    print("PASS: non-due buffer remains ingestion-owned and is not submitted")


def test_async_handoff_preserves_complete_oversized_message_batch():
    from L1_CORE.market_data_platform.market_data.collector import _handoff_if_due

    buffer = RecordBuffer(
        write_function=lambda records: "/fake/not-used.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=2,
        max_interval_seconds=1000.0,
    )

    template_record = collector.parse_market_trades_message(
        json.loads(_real_trade_message(0)),
        1720000000000,
    )[0]
    complete_message = [template_record for _ in range(5)]
    for record in complete_message:
        buffer.add(record)

    submitted = []

    class FakeWorker:
        def submit(self, batch):
            submitted.append(batch)

    _handoff_if_due(buffer, "trade", FakeWorker())

    assert len(submitted) == 1
    assert submitted[0].records == complete_message
    assert len(submitted[0].records) == 5
    assert buffer.records == []

    print("PASS: collector handoff preserves complete oversized message as one detached batch")


def test_async_handoff_submit_failure_restores_detached_records():
    from L1_CORE.market_data_platform.market_data.collector import _handoff_if_due

    buffer = RecordBuffer(
        write_function=lambda records: "/fake/not-used.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=2,
        max_interval_seconds=1000.0,
    )

    for seq in (0, 1):
        buffer.add(
            collector.parse_market_trades_message(
                json.loads(_real_trade_message(seq)),
                1720000000000,
            )[0]
        )

    original_records = buffer.records

    class RejectingWorker:
        def submit(self, batch):
            raise RuntimeError("Simulated submit failure before worker acceptance")

    try:
        _handoff_if_due(buffer, "trade", RejectingWorker())
    except RuntimeError as exc:
        assert str(exc) == "Simulated submit failure before worker acceptance"
    else:
        raise AssertionError("Expected submit failure to propagate")

    assert buffer.records is original_records
    assert len(buffer.records) == 2

    print("PASS: failed worker submission restores exact detached list and propagates failure")


def test_async_count_triggered_handoff_through_stream_messages():
    writes = []

    def forbidden_sync_writer(records):
        writes.append(list(records))
        raise AssertionError("Synchronous persistence must not run on the F3 async stream path")

    trade_buffer = RecordBuffer(
        write_function=forbidden_sync_writer,
        partition_date_function=storage.partition_date_utc,
        count_threshold=2,
        max_interval_seconds=1000.0,
    )
    depth_buffer = RecordBuffer(
        write_function=lambda records: "/fake/depth-not-used.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=1000,
        max_interval_seconds=1000.0,
    )

    submitted = []

    class FakeWorker:
        def submit(self, batch):
            submitted.append(batch)

    fake_ws = FakeWebSocket(
        messages_to_send=[
            _real_trade_message(0),
            _real_trade_message(1),
        ],
        disconnect_after=2,
    )

    async def scenario():
        try:
            await collector._stream_messages(
                fake_ws,
                trade_buffer,
                depth_buffer,
                persistence_worker=FakeWorker(),
            )
        except ConnectionClosed:
            pass

    asyncio.run(scenario())

    assert writes == []
    assert len(submitted) == 1
    assert submitted[0].label == "trade"
    assert len(submitted[0].records) == 2
    assert trade_buffer.records == []

    print("PASS: count-triggered real stream path detaches and submits without synchronous persistence")


def test_async_timeout_triggered_handoff_through_stream_messages():
    writes = []

    def forbidden_sync_writer(records):
        writes.append(list(records))
        raise AssertionError("Timeout path must not synchronously persist when an F3 worker is supplied")

    trade_buffer = RecordBuffer(
        write_function=forbidden_sync_writer,
        partition_date_function=storage.partition_date_utc,
        count_threshold=1000,
        max_interval_seconds=0.05,
    )
    depth_buffer = RecordBuffer(
        write_function=lambda records: "/fake/depth-not-used.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=1000,
        max_interval_seconds=1000.0,
    )

    submitted = []

    class FakeWorker:
        def submit(self, batch):
            submitted.append(batch)

    fake_ws = FakeWebSocket(
        messages_to_send=[_real_trade_message(0)],
    )

    async def scenario():
        task = asyncio.create_task(
            collector._stream_messages(
                fake_ws,
                trade_buffer,
                depth_buffer,
                receive_timeout_seconds=0.01,
                persistence_worker=FakeWorker(),
            )
        )

        await asyncio.sleep(0.08)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(scenario())
    except AssertionError as exc:
        assert "Timeout path must not synchronously persist" in str(exc)
        raise

    assert writes == []
    assert len(submitted) == 1
    assert submitted[0].label == "trade"
    assert len(submitted[0].records) == 1
    assert trade_buffer.records == []

    print("PASS: timeout-triggered real stream path detaches and submits without synchronous persistence")


def test_async_handoff_returns_post_submit_monotonic_anchor():
    from unittest.mock import patch
    from L1_CORE.market_data_platform.market_data.collector import _handoff_if_due

    buffer = RecordBuffer(
        write_function=lambda records: "/fake/not-used.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=1,
        max_interval_seconds=1000.0,
    )

    buffer.add(
        collector.parse_market_trades_message(
            json.loads(_real_trade_message(0)),
            1720000000000,
        )[0]
    )

    submitted = []

    class FakeWorker:
        def submit(self, batch):
            submitted.append(batch)

    expected_anchor = 987654321012345

    with patch(
        "L1_CORE.market_data_platform.market_data.collector.time.monotonic_ns",
        return_value=expected_anchor,
    ):
        result = _handoff_if_due(buffer, "trade", FakeWorker())

    assert len(submitted) == 1
    assert result == expected_anchor, (
        "Successful async handoff must return the post-submit monotonic "
        "timestamp used as the ingestion-loop telemetry anchor"
    )

    print("PASS: successful async handoff returns post-submit monotonic anchor")


def test_connect_and_stream_forwards_exact_persistence_worker():
    trade_buffer = RecordBuffer(
        write_function=lambda records: "/fake/trade.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=1000,
        max_interval_seconds=1000.0,
    )
    depth_buffer = RecordBuffer(
        write_function=lambda records: "/fake/depth.parquet",
        partition_date_function=storage.partition_date_utc,
        count_threshold=1000,
        max_interval_seconds=1000.0,
    )

    class FakeWorker:
        pass

    worker = FakeWorker()
    observed = {}

    class FakeWebSocket:
        async def send(self, message):
            pass

    class FakeConnectContext:
        async def __aenter__(self):
            return FakeWebSocket()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def fake_connect(*args, **kwargs):
        observed["connect_called"] = True
        return FakeConnectContext()

    async def fake_stream_messages(
        websocket,
        received_trade_buffer,
        received_depth_buffer,
        receive_timeout_seconds=1.0,
        telemetry=None,
        persistence_worker=None,
    ):
        observed["trade_buffer"] = received_trade_buffer
        observed["depth_buffer"] = received_depth_buffer
        observed["persistence_worker"] = persistence_worker

    original_connect = collector.connect
    original_stream_messages = collector._stream_messages

    collector.connect = fake_connect
    collector._stream_messages = fake_stream_messages

    try:
        asyncio.run(
            collector._connect_and_stream(
                trade_buffer,
                depth_buffer,
                persistence_worker=worker,
            )
        )
    finally:
        collector.connect = original_connect
        collector._stream_messages = original_stream_messages

    assert observed.get("connect_called") is True
    assert observed.get("trade_buffer") is trade_buffer
    assert observed.get("depth_buffer") is depth_buffer
    assert observed.get("persistence_worker") is worker, (
        "_connect_and_stream() must forward the exact worker object "
        "it receives into _stream_messages()"
    )

    print("PASS: _connect_and_stream forwards the exact persistence worker object")


def test_run_owns_one_persistence_worker_across_reconnects():
    observed = {
        "workers_created": [],
        "workers_started": [],
        "connection_workers": [],
    }

    class StopAfterTwoConnections(BaseException):
        pass

    class FakePersistenceWorker:
        def __init__(self, max_queue_size):
            self.max_queue_size = max_queue_size
            observed["workers_created"].append(self)

        def start(self):
            observed["workers_started"].append(self)

        def drain_and_stop(self):
            pass

    async def fake_connect_and_stream(
        trade_buffer,
        depth_buffer,
        telemetry=None,
        persistence_worker=None,
    ):
        observed["connection_workers"].append(persistence_worker)
        if len(observed["connection_workers"]) >= 2:
            raise StopAfterTwoConnections()

    async def fake_sleep(seconds):
        return None

    class FakeTelemetry:
        def close(self):
            pass

    original_worker = getattr(collector, "PersistenceWorker", None)
    had_worker = hasattr(collector, "PersistenceWorker")
    original_connect = collector._connect_and_stream
    original_sleep = collector.asyncio.sleep
    original_telemetry_from_env = collector.Telemetry.from_env
    original_verify = collector.verify_canonical_root_or_raise
    original_flush_all = collector._flush_all_pending

    collector.PersistenceWorker = FakePersistenceWorker
    collector._connect_and_stream = fake_connect_and_stream
    collector.asyncio.sleep = fake_sleep
    collector.Telemetry.from_env = staticmethod(lambda: FakeTelemetry())
    collector.verify_canonical_root_or_raise = lambda: None
    collector._flush_all_pending = lambda trade_buffer, depth_buffer: None

    try:
        try:
            asyncio.run(collector.run())
        except StopAfterTwoConnections:
            pass
    finally:
        if had_worker:
            collector.PersistenceWorker = original_worker
        else:
            delattr(collector, "PersistenceWorker")
        collector._connect_and_stream = original_connect
        collector.asyncio.sleep = original_sleep
        collector.Telemetry.from_env = original_telemetry_from_env
        collector.verify_canonical_root_or_raise = original_verify
        collector._flush_all_pending = original_flush_all

    assert len(observed["workers_created"]) == 1, (
        "run() must construct exactly one PersistenceWorker for its entire lifetime"
    )
    assert len(observed["workers_started"]) == 1, (
        "run() must start its PersistenceWorker exactly once"
    )
    assert observed["workers_started"][0] is observed["workers_created"][0]

    assert len(observed["connection_workers"]) == 2
    assert observed["connection_workers"][0] is observed["workers_created"][0], (
        "first connection attempt must receive run()'s worker"
    )
    assert observed["connection_workers"][1] is observed["workers_created"][0], (
        "reconnect must receive the exact same worker object"
    )

    assert observed["workers_created"][0].max_queue_size == 2, (
        "run() must use the frozen F3 v1 persistence queue capacity of 2"
    )

    print(
        "PASS: run owns one started PersistenceWorker and preserves "
        "its exact identity across reconnects"
    )


def test_run_shutdown_hands_off_active_buffers_then_drains_worker():
    events = []

    class StopCollector(BaseException):
        pass

    class FakePersistenceWorker:
        instance = None

        def __init__(self, max_queue_size):
            self.max_queue_size = max_queue_size
            self.submitted = []
            FakePersistenceWorker.instance = self

        def start(self):
            events.append("worker_start")

        def submit(self, batch):
            self.submitted.append(batch)
            events.append(f"submit:{batch.label}")

        def drain_and_stop(self):
            events.append("drain_and_stop")

    class FakeTelemetry:
        def close(self):
            events.append("telemetry_close")

    async def fake_connect_and_stream(
        trade_buffer,
        depth_buffer,
        telemetry=None,
        persistence_worker=None,
    ):
        trade_buffer.add(object())
        depth_buffer.add(object())
        raise StopCollector()

    def forbidden_sync_final_flush(trade_buffer, depth_buffer):
        raise AssertionError(
            "F3 shutdown must not use legacy synchronous _flush_all_pending()"
        )

    original_worker = collector.PersistenceWorker
    original_connect = collector._connect_and_stream
    original_telemetry_from_env = collector.Telemetry.from_env
    original_verify = collector.verify_canonical_root_or_raise
    original_flush_all = collector._flush_all_pending

    collector.PersistenceWorker = FakePersistenceWorker
    collector._connect_and_stream = fake_connect_and_stream
    collector.Telemetry.from_env = staticmethod(lambda: FakeTelemetry())
    collector.verify_canonical_root_or_raise = lambda: None
    collector._flush_all_pending = forbidden_sync_final_flush

    try:
        try:
            asyncio.run(collector.run())
        except StopCollector:
            pass
    finally:
        collector.PersistenceWorker = original_worker
        collector._connect_and_stream = original_connect
        collector.Telemetry.from_env = original_telemetry_from_env
        collector.verify_canonical_root_or_raise = original_verify
        collector._flush_all_pending = original_flush_all

    worker = FakePersistenceWorker.instance
    assert worker is not None

    assert events == [
        "worker_start",
        "submit:trade",
        "submit:depth",
        "drain_and_stop",
        "telemetry_close",
    ], (
        "F3 shutdown must transfer remaining active trade/depth work "
        "to the worker, drain accepted persistence work, stop/join the "
        "worker, and only then close telemetry; observed events: "
        f"{events}"
    )

    assert len(worker.submitted) == 2
    assert worker.submitted[0].label == "trade"
    assert worker.submitted[1].label == "depth"

    print(
        "PASS: F3 shutdown hands off active buffers before draining "
        "and stopping the persistence worker"
    )


def test_run_shutdown_worker_failure_propagates_and_telemetry_still_closes():
    events = []

    class StopCollector(BaseException):
        pass

    shutdown_failure = RuntimeError("Simulated F3 shutdown persistence failure")

    class FakePersistenceWorker:
        instance = None

        def __init__(self, max_queue_size):
            self.max_queue_size = max_queue_size
            self.submitted = []
            FakePersistenceWorker.instance = self

        def start(self):
            events.append("worker_start")

        def submit(self, batch):
            self.submitted.append(batch)
            events.append(f"submit:{batch.label}")

        def drain_and_stop(self):
            events.append("drain_and_stop")
            raise shutdown_failure

    class FakeTelemetry:
        def close(self):
            events.append("telemetry_close")

    async def fake_connect_and_stream(
        trade_buffer,
        depth_buffer,
        telemetry=None,
        persistence_worker=None,
    ):
        trade_buffer.add(object())
        depth_buffer.add(object())
        raise StopCollector()

    original_worker = collector.PersistenceWorker
    original_connect = collector._connect_and_stream
    original_telemetry_from_env = collector.Telemetry.from_env
    original_verify = collector.verify_canonical_root_or_raise

    collector.PersistenceWorker = FakePersistenceWorker
    collector._connect_and_stream = fake_connect_and_stream
    collector.Telemetry.from_env = staticmethod(lambda: FakeTelemetry())
    collector.verify_canonical_root_or_raise = lambda: None

    caught = None

    try:
        try:
            asyncio.run(collector.run())
        except RuntimeError as exc:
            caught = exc
        except StopCollector:
            raise AssertionError(
                "F3 shutdown worker failure was masked by the original collector exit"
            )
    finally:
        collector.PersistenceWorker = original_worker
        collector._connect_and_stream = original_connect
        collector.Telemetry.from_env = original_telemetry_from_env
        collector.verify_canonical_root_or_raise = original_verify

    assert caught is shutdown_failure, (
        "run() must propagate the exact persistence-worker shutdown failure"
    )

    assert events == [
        "worker_start",
        "submit:trade",
        "submit:depth",
        "drain_and_stop",
        "telemetry_close",
    ], (
        "worker failure must occur after remaining buffers are accepted, "
        "and telemetry must still close after that failure; observed: "
        f"{events}"
    )

    worker = FakePersistenceWorker.instance
    assert worker is not None
    assert len(worker.submitted) == 2

    print(
        "PASS: F3 shutdown persistence failure propagates fail-closed "
        "while telemetry still closes"
    )


def test_run_task_cancellation_drains_worker_before_exit():
    events = []

    class FakePersistenceWorker:
        instance = None

        def __init__(self, max_queue_size):
            self.max_queue_size = max_queue_size
            self.submitted = []
            FakePersistenceWorker.instance = self

        def start(self):
            events.append("worker_start")

        def submit(self, batch):
            self.submitted.append(batch)
            events.append(f"submit:{batch.label}")

        def drain_and_stop(self):
            events.append("drain_and_stop")

    class FakeTelemetry:
        def close(self):
            events.append("telemetry_close")

    entered_stream = asyncio.Event()

    async def fake_connect_and_stream(
        trade_buffer,
        depth_buffer,
        telemetry=None,
        persistence_worker=None,
    ):
        trade_buffer.add(object())
        depth_buffer.add(object())
        entered_stream.set()

        # Remain inside the production run() lifecycle until the task
        # itself is genuinely cancelled.
        await asyncio.Event().wait()

    async def exercise():
        task = asyncio.create_task(collector.run())

        await asyncio.wait_for(entered_stream.wait(), timeout=1.0)

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            events.append("cancelled_propagated")
        else:
            raise AssertionError(
                "run() must propagate task cancellation after F3 shutdown cleanup"
            )

    original_worker = collector.PersistenceWorker
    original_connect = collector._connect_and_stream
    original_telemetry_from_env = collector.Telemetry.from_env
    original_verify = collector.verify_canonical_root_or_raise

    collector.PersistenceWorker = FakePersistenceWorker
    collector._connect_and_stream = fake_connect_and_stream
    collector.Telemetry.from_env = staticmethod(lambda: FakeTelemetry())
    collector.verify_canonical_root_or_raise = lambda: None

    try:
        asyncio.run(exercise())
    finally:
        collector.PersistenceWorker = original_worker
        collector._connect_and_stream = original_connect
        collector.Telemetry.from_env = original_telemetry_from_env
        collector.verify_canonical_root_or_raise = original_verify

    worker = FakePersistenceWorker.instance
    assert worker is not None

    assert events == [
        "worker_start",
        "submit:trade",
        "submit:depth",
        "drain_and_stop",
        "telemetry_close",
        "cancelled_propagated",
    ], (
        "real task cancellation must enter run()'s F3 finally lifecycle, "
        "hand off remaining work, drain/stop the worker, close telemetry, "
        "and then propagate cancellation; observed: "
        f"{events}"
    )

    assert len(worker.submitted) == 2
    assert worker.submitted[0].label == "trade"
    assert worker.submitted[1].label == "depth"

    print(
        "PASS: genuine run() task cancellation drains F3 persistence "
        "before cancellation propagates"
    )


def test_sequence_tracker_is_session_scoped_across_stream_reconnects():
    created_trackers = []

    class RecordingTracker:
        def __init__(self):
            self.sequences = []
            created_trackers.append(self)

        def check(self, sequence_num):
            self.sequences.append(sequence_num)

    class FakeWebSocket:
        def __init__(self, messages):
            self.messages = list(messages)

        async def recv(self):
            if self.messages:
                return self.messages.pop(0)
            raise StopStream()

    class StopStream(BaseException):
        pass

    def raw_message(sequence_num):
        return json.dumps({
            "channel": "subscriptions",
            "sequence_num": sequence_num,
            "events": [],
        })

    async def one_session(sequence_num):
        websocket = FakeWebSocket([raw_message(sequence_num)])

        trade_buffer = RecordBuffer(
            write_function=lambda records: None,
            partition_date_function=storage.partition_date_utc,
            count_threshold=100,
            max_interval_seconds=60.0,
        )
        depth_buffer = RecordBuffer(
            write_function=lambda records: None,
            partition_date_function=storage.partition_date_utc,
            count_threshold=100,
            max_interval_seconds=60.0,
        )

        try:
            await collector._stream_messages(
                websocket,
                trade_buffer,
                depth_buffer,
                receive_timeout_seconds=1.0,
            )
        except StopStream:
            pass

    original_tracker = collector.SequenceGapTracker
    collector.SequenceGapTracker = RecordingTracker

    try:
        asyncio.run(one_session(900))
        asyncio.run(one_session(3))
    finally:
        collector.SequenceGapTracker = original_tracker

    assert len(created_trackers) == 2, (
        "each _stream_messages() connection session must construct "
        "a fresh SequenceGapTracker"
    )

    assert created_trackers[0] is not created_trackers[1]
    assert created_trackers[0].sequences == [900]
    assert created_trackers[1].sequences == [3]

    print(
        "PASS: sequence tracking is session-scoped; reconnect creates "
        "a fresh tracker and accepts an independent first sequence"
    )


def test_run_shutdown_drains_worker_even_if_second_handoff_fails():
    events = []

    class FakeTelemetry:
        def close(self):
            events.append("telemetry_close")

    class FakePersistenceWorker:
        instance = None

        def __init__(self, max_queue_size):
            self.submitted = []
            FakePersistenceWorker.instance = self

        def start(self):
            events.append("worker_start")

        def submit(self, batch):
            events.append(f"submit:{batch.label}")
            if batch.label == "depth":
                raise RuntimeError("Simulated depth shutdown handoff failure")
            self.submitted.append(batch)

        def drain_and_stop(self):
            events.append("drain_and_stop")

    async def fake_connect_and_stream(
        trade_buffer,
        depth_buffer,
        telemetry=None,
        persistence_worker=None,
    ):
        trade_buffer.records.append(object())
        depth_buffer.records.append(object())
        raise asyncio.CancelledError()

    async def exercise():
        try:
            await collector.run()
        except RuntimeError as exc:
            assert str(exc) == "Simulated depth shutdown handoff failure"
            events.append("handoff_failure_propagated")
        except asyncio.CancelledError:
            raise AssertionError(
                "depth handoff failure must replace clean cancellation exit "
                "because shutdown persistence failure is structural"
            )
        else:
            raise AssertionError(
                "expected structural depth shutdown handoff failure"
            )

    original_worker = collector.PersistenceWorker
    original_connect = collector._connect_and_stream
    original_telemetry_from_env = collector.Telemetry.from_env
    original_verify = collector.verify_canonical_root_or_raise

    collector.PersistenceWorker = FakePersistenceWorker
    collector._connect_and_stream = fake_connect_and_stream
    collector.Telemetry.from_env = staticmethod(lambda: FakeTelemetry())
    collector.verify_canonical_root_or_raise = lambda: None

    try:
        asyncio.run(exercise())
    finally:
        collector.PersistenceWorker = original_worker
        collector._connect_and_stream = original_connect
        collector.Telemetry.from_env = original_telemetry_from_env
        collector.verify_canonical_root_or_raise = original_verify

    worker = FakePersistenceWorker.instance
    assert worker is not None

    assert "submit:trade" in events
    assert "submit:depth" in events

    assert "drain_and_stop" in events, (
        "accepted trade shutdown work must still be drained/stopped when "
        "the later depth handoff fails; observed events: "
        f"{events}"
    )

    assert events[-2:] == [
        "telemetry_close",
        "handoff_failure_propagated",
    ], (
        "telemetry must close before the structural handoff failure "
        f"propagates; observed events: {events}"
    )

    assert len(worker.submitted) == 1
    assert worker.submitted[0].label == "trade"

    print(
        "PASS: accepted shutdown work is drained even when a later "
        "shutdown handoff fails structurally"
    )
