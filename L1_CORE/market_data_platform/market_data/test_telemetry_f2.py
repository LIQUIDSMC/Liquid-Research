"""F2 telemetry tests (plain asserts; run as a module)."""
import asyncio
import dataclasses
import io
import json
import os
import tempfile
import time
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


if __name__ == "__main__":
    test_bounds()
    test_failure_and_disable()
    test_cap()
    test_kill_switch_and_size()
    test_semantic_equivalence_and_records()
    test_failed_flush_is_recorded_and_reraised()
    print("ALL F2 TESTS PASSED")
