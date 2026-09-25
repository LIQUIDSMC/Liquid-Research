"""F2 telemetry tests (plain asserts; run as a module)."""
import asyncio
import dataclasses
import io
import json
import os
import tempfile
import time
from threading import Event, Thread
from contextlib import redirect_stdout
from pathlib import Path

from L1_CORE.market_data_platform.market_data import collector, telemetry as T
from L1_CORE.market_data_platform.market_data.buffer import RecordBuffer


def lines(d):
    out = []
    for p in sorted(Path(d).glob("telemetry_*.jsonl")):
        out += [json.loads(x) for x in p.read_text().splitlines()]
    return out


def test_bounds():
    d = tempfile.mkdtemp()
    tel = T.Telemetry(directory=d)
    for i in range(450):
        tel.emit({"type": "x", "i": i})
        assert len(tel._batch) <= T.MAX_RECORDS
    assert len(lines(d)) == 400 and len(tel._batch) == 50
    tel2 = T.Telemetry(directory=tempfile.mkdtemp())
    for i in range(300):
        tel2.emit({"type": "x", "pad": "y" * 1000})
        assert tel2._batch_bytes < T.MAX_BYTES + 2000
    print("bounds OK")


def test_failure_and_disable():
    f = tempfile.NamedTemporaryFile(delete=False)
    tel = T.Telemetry(directory=f.name)
    buf = io.StringIO()
    with redirect_stdout(buf):
        for i in range(600):
            tel.emit({"type": "x", "i": i})
    out = buf.getvalue()
    assert out.count("TELEMETRY-WARNING") >= 1 and "TELEMETRY-DISABLED" in out
    assert tel.enabled is False and tel.dropped > 0
    print("failure/disable OK")


def test_cap():
    old = T.FILE_CAP_BYTES
    T.FILE_CAP_BYTES = 5000
    try:
        d = tempfile.mkdtemp()
        tel = T.Telemetry(directory=d)
        buf = io.StringIO()
        with redirect_stdout(buf):
            for i in range(1000):
                tel.emit({"type": "x", "i": i})
        assert tel.compromised and "TELEMETRY-CAP-REACHED" in buf.getvalue()
        assert sum(p.stat().st_size for p in Path(d).glob("*.jsonl")) <= 5000
    finally:
        T.FILE_CAP_BYTES = old
    print("cap OK")


def test_kill_switch_and_size():
    os.environ["LRS_TELEMETRY"] = "0"
    assert T.Telemetry.from_env().enabled is False
    del os.environ["LRS_TELEMETRY"]
    d = tempfile.mkdtemp()
    tel = T.Telemetry.disabled()
    tel.emit({"type": "x"})
    tel.flush_record("s", "depth", 1, 1, 1, 2, True, 1, None)
    assert not list(Path(d).iterdir())
    tel = T.Telemetry(directory=d)
    tel.flush_record("11111111-2222-3333-4444-555555555555", "depth", 230, 123456,
                     1234567890123456, 1234567990123456, True, 1, None)
    tel.close()
    rec = lines(d)[0]
    size = len(json.dumps(rec, separators=(",", ":"))) + 1
    print("typical flush record bytes:", size)
    assert size < 500
    print("kill switch / size OK")


class Done(Exception):
    pass


class FakeWS:
    def __init__(self, msgs):
        self.msgs = list(msgs)

    async def recv(self):
        if not self.msgs:
            raise Done()
        return self.msgs.pop(0)


def l2(seq, typ, prod, n):
    ups = [{"side": "bid" if i % 2 == 0 else "offer",
            "event_time": "2026-09-20T00:00:00.000000Z",
            "price_level": "%d.00" % (100 + i), "new_quantity": "1.5"} for i in range(n)]
    return json.dumps({"channel": "l2_data", "client_id": "",
                       "timestamp": "2026-09-20T00:00:00.000000000Z", "sequence_num": seq,
                       "events": [{"type": typ, "product_id": prod, "updates": ups}]})


def run_feed(tel):
    written = []

    def w(recs):
        time.sleep(0.05)
        written.append([{k: v for k, v in dataclasses.asdict(r).items()
                         if k != "timestamp_received"} for r in recs])
        return "fake.parquet"

    tb = RecordBuffer(lambda r: "t", lambda ts: "2026-09-20", count_threshold=25)
    db = RecordBuffer(w, lambda ts: "2026-09-20", count_threshold=25)
    feed = [l2(0, "snapshot", "BTC-USD", 30), l2(1, "update", "BTC-USD", 2),
            l2(2, "update", "ETH-USD", 1)]
    try:
        asyncio.run(collector._stream_messages(FakeWS(feed), tb, db, telemetry=tel))
    except Done:
        pass
    return written, len(db.records)


def test_semantic_equivalence_and_records():
    base_written, base_left = run_feed(None)
    d = tempfile.mkdtemp()
    tel = T.Telemetry(directory=d, code_commit="test")
    with_written, with_left = run_feed(tel)
    tel.close()
    assert base_written == with_written and base_left == with_left
    off_written, _ = run_feed(T.Telemetry.disabled())
    assert off_written == base_written
    recs = lines(d)
    types = [r["type"] for r in recs]
    assert types[0] == "session_start" and types[-1] == "session_end"
    assert recs[-1]["reason"] == "Done"
    big = [r for r in recs if r["type"] == "big_msg"]
    assert len(big) == 1 and big[0]["n_rows"] == 30 and big[0]["seq"] == 0
    assert big[0]["event_type"] == "snapshot" and big[0]["source_timestamp"]
    assert big[0]["prev_end"] <= big[0]["t0"] <= big[0]["t1"] <= big[0]["t2"] <= big[0]["t3"]
    fl = [r for r in recs if r["type"] == "flush"]
    assert len(fl) == 1 and fl[0]["trigger_seq"] == 0 and fl[0]["ok"] is True
    assert fl[0]["dur_ms"] >= 40 and fl[0]["t4"] < fl[0]["t5"] and fl[0]["buffer"] == "depth"
    assert not any("telemetry" in k for w in with_written for row in w for k in row)
    print("semantic equivalence / record content OK")


def test_failed_flush_is_recorded_and_reraised():
    def bad_writer(recs):
        raise RuntimeError("forced writer failure")

    def run(tel):
        tb = RecordBuffer(lambda r: "t", lambda ts: "2026-09-20", count_threshold=25)
        db = RecordBuffer(bad_writer, lambda ts: "2026-09-20", count_threshold=25)
        feed = [l2(0, "snapshot", "BTC-USD", 30), l2(1, "update", "BTC-USD", 2)]
        try:
            asyncio.run(collector._stream_messages(FakeWS(feed), tb, db, telemetry=tel))
        except Exception as exc:
            return exc
        return None

    base_exc = run(None)
    d = tempfile.mkdtemp()
    tel = T.Telemetry(directory=d, code_commit="test")
    exc = run(tel)
    tel.close()
    assert isinstance(exc, RuntimeError) and str(exc) == "forced writer failure"
    assert type(base_exc) is type(exc) and str(base_exc) == str(exc)
    recs = lines(d)
    fl = [r for r in recs if r["type"] == "flush"]
    assert len(fl) == 1, fl
    assert fl[0]["ok"] is False and fl[0]["n_files"] is None
    assert fl[0]["exc"] == "RuntimeError" and fl[0]["t4"] < fl[0]["t5"]
    assert fl[0]["trigger_seq"] == 0 and fl[0]["buffer"] == "depth"
    assert recs[-1]["type"] == "session_end" and recs[-1]["reason"] == "RuntimeError"
    print("failed flush recorded and re-raised OK")




def test_concurrent_emit_is_serialized():
    d = tempfile.mkdtemp()
    tel = T.Telemetry(directory=d)

    n_threads = 4
    per_thread = 500

    def producer(producer_id):
        for i in range(per_thread):
            tel.emit({
                "type": "concurrency_probe",
                "producer": producer_id,
                "i": i,
            })

    threads = [
        Thread(target=producer, args=(producer_id,))
        for producer_id in range(n_threads)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    tel.close()

    recs = [
        r for r in lines(d)
        if r["type"] == "concurrency_probe"
    ]

    expected = {
        (producer_id, i)
        for producer_id in range(n_threads)
        for i in range(per_thread)
    }
    actual = [
        (r["producer"], r["i"])
        for r in recs
    ]

    assert len(actual) == n_threads * per_thread
    assert len(set(actual)) == len(actual)
    assert set(actual) == expected

    assert tel.dropped == 0
    assert tel.compromised is False
    assert tel.enabled is True
    assert tel._batch == []
    assert tel._batch_bytes == 0

    print("concurrent telemetry emission serialized without loss or duplication")




def test_take_emit_ms_uses_telemetry_lock():
    tel = T.Telemetry(directory=tempfile.mkdtemp())
    tel._emit_ms = 12.5

    entered = Event()
    completed = Event()
    result = []

    def consumer():
        entered.set()
        result.append(tel.take_emit_ms())
        completed.set()

    with tel._lock:
        thread = Thread(target=consumer)
        thread.start()

        assert entered.wait(timeout=1.0)
        assert not completed.wait(timeout=0.05), (
            "take_emit_ms() completed while another thread owned telemetry lock"
        )
        assert tel._emit_ms == 12.5

    assert completed.wait(timeout=1.0)
    thread.join(timeout=1.0)
    assert not thread.is_alive()

    assert result == [12.5]
    assert tel._emit_ms is None

    print("take_emit_ms serialized by telemetry lock")


def test_f3_persistence_bridge():
    d = tempfile.mkdtemp()
    tel = T.Telemetry(directory=d)

    handoff = {
        "type": "persistence_handoff",
        "batch_id": 17,
        "label": "trade",
        "rows": 25,
        "submit_start_ns": 100,
        "accepted_ns": 200,
        "submit_block_ms": 0.0001,
        "queue_depth_before": 0,
        "queue_depth_after_accept": 1,
        "queue_capacity": 2,
        "queue_full_at_submit_start": False,
        "accepted_count": 1,
        "persisted_count": 0,
        "unpersisted_count": 1,
        "previous_observer_callback_ms": None,
        "previous_observer_event_type": None,
        "previous_observer_batch_id": None,
    }
    original_handoff = dict(handoff)

    completion = {
        "type": "persistence_complete",
        "batch_id": 17,
        "label": "trade",
        "rows": 25,
        "submit_start_ns": 100,
        "accepted_ns": 200,
        "worker_start_ns": 300,
        "worker_end_ns": 400,
        "submit_to_worker_start_ms": 0.0002,
        "queue_wait_after_accept_ms": 0.0001,
        "worker_persist_ms": 0.0001,
        "ok": True,
        "exc": None,
        "queue_depth_at_completion": 0,
        "queue_capacity": 2,
        "accepted_count": 1,
        "persisted_count": 1,
        "unpersisted_count": 0,
        "previous_observer_callback_ms": 1.25,
        "previous_observer_event_type": "persistence_handoff",
        "previous_observer_batch_id": 17,
    }
    original_completion = dict(completion)

    tel.f3_persistence(handoff)
    tel.f3_persistence(completion)
    tel.f3_persistence({"type": "not_an_f3_persistence_event", "batch_id": 99})
    tel.close()

    assert handoff == original_handoff
    assert completion == original_completion

    recs = lines(d)
    assert len(recs) == 2

    h, c = recs
    assert h["type"] == "f3_persistence_handoff"
    assert c["type"] == "f3_persistence_complete"
    assert h["batch_id"] == c["batch_id"] == 17
    assert h["label"] == c["label"] == "trade"
    assert h["rows"] == c["rows"] == 25
    assert isinstance(h["wall_ns"], int) and h["wall_ns"] > 0
    assert isinstance(c["wall_ns"], int) and c["wall_ns"] > 0

    assert h["previous_observer_callback_ms"] is None
    assert h["previous_observer_event_type"] is None
    assert h["previous_observer_batch_id"] is None

    assert c["previous_observer_callback_ms"] == 1.25
    assert c["previous_observer_event_type"] == "persistence_handoff"
    assert c["previous_observer_batch_id"] == 17

    for key, value in original_handoff.items():
        if key != "type":
            assert h[key] == value

    for key, value in original_completion.items():
        if key != "type":
            assert c[key] == value

    print("F3 persistence bridge preserves observations and namespaces event types")


if __name__ == "__main__":
    test_bounds()
    test_failure_and_disable()
    test_cap()
    test_kill_switch_and_size()
    test_semantic_equivalence_and_records()
    test_failed_flush_is_recorded_and_reraised()
    test_concurrent_emit_is_serialized()
    test_take_emit_ms_uses_telemetry_lock()
    test_f3_persistence_bridge()
    print("ALL F2 + THREAD-SAFETY + F3 BRIDGE TESTS PASSED")
