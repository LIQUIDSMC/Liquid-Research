"""
LRS-3 F3 — Asynchronous Persistence Gate-1 Tests

Deterministic offline tests for the F3 ownership-transfer persistence
component. No production canonical storage is touched.

These tests define the minimum worker contract before collector.py is
modified.
"""

import json
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from L1_CORE.market_data_platform.market_data.async_persistence import (
    PersistenceBatch,
    PersistenceWorker,
)
from L1_CORE.market_data_platform.market_data.telemetry import Telemetry


@dataclass
class FakeRecord:
    timestamp_received: int
    label: str = ""


def fake_partition_date(timestamp_received_ms: int) -> str:
    return "2026-07-14" if timestamp_received_ms < 2_000_000_000_000 else "2026-07-15"


class RecordingWriter:
    def __init__(self, fail_on_call=None, block_event=None):
        self.calls = []
        self.fail_on_call = fail_on_call
        self.block_event = block_event
        self.call_count = 0

    def __call__(self, records):
        self.call_count += 1
        self.calls.append(list(records))

        if self.block_event is not None:
            self.block_event.wait(timeout=2.0)

        if self.fail_on_call == self.call_count:
            raise RuntimeError(f"Simulated write failure on call {self.call_count}")

        return f"/fake/batch_{self.call_count}.parquet"


def test_batch_owns_detached_record_list():
    records = [
        FakeRecord(1_000_000_000_000, "a"),
        FakeRecord(1_000_000_000_000, "b"),
    ]

    batch = PersistenceBatch(
        records=records,
        write_function=RecordingWriter(),
        partition_date_function=fake_partition_date,
        label="trade",
    )

    replacement_active_records = []
    replacement_active_records.append(FakeRecord(1_000_000_000_000, "new"))

    assert [r.label for r in batch.records] == ["a", "b"]
    assert [r.label for r in replacement_active_records] == ["new"]

    print("PASS: detached batch ownership is independent from replacement ingestion state")


def test_worker_groups_dates_in_sorted_order():
    writer = RecordingWriter()
    worker = PersistenceWorker(max_queue_size=2)
    worker.start()

    batch = PersistenceBatch(
        records=[
            FakeRecord(3_000_000_000_000, "day2"),
            FakeRecord(1_000_000_000_000, "day1"),
        ],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="trade",
    )

    worker.submit(batch)
    worker.drain_and_stop()

    assert [[r.label for r in call] for call in writer.calls] == [
        ["day1"],
        ["day2"],
    ]

    print("PASS: worker preserves deterministic sorted UTC-date grouping")


def test_partial_failure_does_not_retry_successful_group():
    writer = RecordingWriter(fail_on_call=2)
    worker = PersistenceWorker(max_queue_size=2)
    worker.start()

    batch = PersistenceBatch(
        records=[
            FakeRecord(1_000_000_000_000, "day1"),
            FakeRecord(3_000_000_000_000, "day2"),
        ],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="trade",
    )

    worker.submit(batch)

    try:
        worker.drain_and_stop()
        raise AssertionError("Expected persistence failure")
    except RuntimeError:
        pass

    assert [[r.label for r in call] for call in writer.calls] == [
        ["day1"],
        ["day2"],
    ]

    print("PASS: successful date group was not duplicated after later group failure")


def test_background_failure_becomes_owner_visible():
    writer = RecordingWriter(fail_on_call=1)
    worker = PersistenceWorker(max_queue_size=1)
    worker.start()

    worker.submit(PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "fail")],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="trade",
    ))

    try:
        worker.drain_and_stop()
        raise AssertionError("Expected background persistence failure")
    except RuntimeError as exc:
        assert "Simulated write failure" in str(exc)

    print("PASS: background persistence failure is visible to worker owner")


def test_queue_is_bounded_and_applies_backpressure():
    release_writer = threading.Event()
    writer = RecordingWriter(block_event=release_writer)

    worker = PersistenceWorker(max_queue_size=1)
    worker.start()

    def batch(label):
        return PersistenceBatch(
            records=[FakeRecord(1_000_000_000_000, label)],
            write_function=writer,
            partition_date_function=fake_partition_date,
            label="trade",
        )

    worker.submit(batch("first"))
    worker.submit(batch("second"))

    third_completed = threading.Event()

    def submit_third():
        worker.submit(batch("third"))
        third_completed.set()

    submitter = threading.Thread(target=submit_third)
    submitter.start()

    time.sleep(0.05)
    assert not third_completed.is_set(), (
        "Third submission should be backpressured while the bounded queue is saturated"
    )

    release_writer.set()
    submitter.join(timeout=2.0)

    assert third_completed.is_set(), "Backpressured submit should complete once capacity returns"

    worker.drain_and_stop()

    assert sum(len(call) for call in writer.calls) == 3

    print("PASS: bounded queue applies backpressure without silently dropping accepted work")


def test_shutdown_drains_all_accepted_work():
    writer = RecordingWriter()
    worker = PersistenceWorker(max_queue_size=2)
    worker.start()

    for label in ("a", "b", "c"):
        worker.submit(PersistenceBatch(
            records=[FakeRecord(1_000_000_000_000, label)],
            write_function=writer,
            partition_date_function=fake_partition_date,
            label="trade",
        ))

    worker.drain_and_stop()

    persisted = [record.label for call in writer.calls for record in call]
    assert persisted == ["a", "b", "c"]

    print("PASS: shutdown drains all accepted work before success")


def test_failure_preserves_later_accepted_batch_as_unpersisted():
    """
    If one accepted batch fails, later accepted work must not disappear from
    accounting merely because the worker dequeued it after becoming failed.
    """
    release_writer = threading.Event()

    class FailFirstAfterReleaseWriter:
        def __init__(self):
            self.calls = []
            self.call_count = 0

        def __call__(self, records):
            self.call_count += 1
            self.calls.append(list(records))
            if self.call_count == 1:
                release_writer.wait(timeout=2.0)
                raise RuntimeError("Simulated first-batch failure")
            return f"/fake/batch_{self.call_count}.parquet"

    writer = FailFirstAfterReleaseWriter()
    worker = PersistenceWorker(max_queue_size=2)
    worker.start()

    def batch(label):
        return PersistenceBatch(
            records=[FakeRecord(1_000_000_000_000, label)],
            write_function=writer,
            partition_date_function=fake_partition_date,
            label="trade",
        )

    worker.submit(batch("first"))
    worker.submit(batch("second"))

    release_writer.set()

    try:
        worker.drain_and_stop()
        raise AssertionError("Expected persistence failure")
    except RuntimeError:
        pass

    assert worker.unpersisted_count == 2, (
        "Both the failed first batch and the later accepted-but-unwritten "
        "second batch must remain explicitly accounted as unpersisted"
    )

    print("PASS: failure preserves explicit accounting for all accepted-but-unpersisted work")


def test_blocked_submit_is_released_by_worker_failure():
    """
    A producer blocked by bounded-queue backpressure must eventually observe
    worker failure rather than remaining blocked indefinitely.
    """
    writer_entered = threading.Event()
    allow_failure = threading.Event()

    class BlockingFailWriter:
        def __call__(self, records):
            writer_entered.set()
            allow_failure.wait(timeout=2.0)
            raise RuntimeError("Simulated blocked-writer failure")

    writer = BlockingFailWriter()
    worker = PersistenceWorker(max_queue_size=1)
    worker.start()

    def batch(label):
        return PersistenceBatch(
            records=[FakeRecord(1_000_000_000_000, label)],
            write_function=writer,
            partition_date_function=fake_partition_date,
            label="trade",
        )

    worker.submit(batch("first"))
    assert writer_entered.wait(timeout=2.0), "Worker never entered the first write"

    worker.submit(batch("second"))

    outcome = {"exception": None}
    submit_finished = threading.Event()

    def submit_third():
        try:
            worker.submit(batch("third"))
        except BaseException as exc:
            outcome["exception"] = exc
        finally:
            submit_finished.set()

    submitter = threading.Thread(target=submit_third)
    submitter.start()

    time.sleep(0.05)
    assert not submit_finished.is_set(), "Third submit should initially be backpressured"

    allow_failure.set()

    submitter.join(timeout=2.0)

    assert submit_finished.is_set(), (
        "Blocked submit remained stranded after persistence worker failure"
    )
    assert isinstance(outcome["exception"], RuntimeError), (
        "Blocked submit must surface the persistence failure"
    )

    try:
        worker.drain_and_stop()
    except RuntimeError:
        pass

    print("PASS: blocked producer is released and observes worker failure")


def test_gate2_observations_correlate_handoff_and_completion():
    observations = []
    writer = RecordingWriter()
    worker = PersistenceWorker(
        max_queue_size=2,
        observation_callback=observations.append,
    )
    worker.start()

    batch = PersistenceBatch(
        records=[
            FakeRecord(1_000_000_000_000, "a"),
            FakeRecord(1_000_000_000_000, "b"),
        ],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="trade",
    )

    worker.submit(batch)
    worker.drain_and_stop()

    handoffs = [r for r in observations if r["type"] == "persistence_handoff"]
    completions = [r for r in observations if r["type"] == "persistence_complete"]

    assert len(handoffs) == 1
    assert len(completions) == 1

    handoff = handoffs[0]
    completion = completions[0]

    assert handoff["batch_id"] == completion["batch_id"] == batch.batch_id
    assert handoff["label"] == completion["label"] == "trade"
    assert handoff["rows"] == completion["rows"] == 2

    assert handoff["submit_start_ns"] <= handoff["accepted_ns"]
    assert handoff["submit_block_ms"] >= 0
    assert handoff["queue_capacity"] == 2

    assert completion["submit_start_ns"] == handoff["submit_start_ns"]
    assert completion["worker_start_ns"] >= completion["submit_start_ns"]
    assert completion["worker_end_ns"] >= completion["worker_start_ns"]
    assert completion["submit_to_worker_start_ms"] >= 0
    assert completion["worker_persist_ms"] >= 0
    assert completion["ok"] is True
    assert completion["exc"] is None

    if completion["accepted_ns"] is None:
        assert completion["queue_wait_after_accept_ms"] is None
    else:
        assert completion["queue_wait_after_accept_ms"] >= 0

    print("PASS: Gate-2 handoff/completion observations correlate by batch identity")


def test_gate2_fast_consumer_does_not_require_accepted_timestamp():
    observations = []
    worker = PersistenceWorker(
        max_queue_size=2,
        observation_callback=observations.append,
    )
    worker.start()

    for i in range(200):
        worker.submit(PersistenceBatch(
            records=[FakeRecord(1_000_000_000_000, str(i))],
            write_function=lambda records: "/fake/fast.parquet",
            partition_date_function=fake_partition_date,
            label="trade",
        ))

    worker.drain_and_stop()

    completions = [r for r in observations if r["type"] == "persistence_complete"]
    assert len(completions) == 200

    ids = [r["batch_id"] for r in completions]
    assert all(batch_id is not None for batch_id in ids)
    assert len(set(ids)) == 200

    for rec in completions:
        assert rec["submit_start_ns"] is not None
        assert rec["submit_to_worker_start_ms"] >= 0
        assert rec["worker_persist_ms"] >= 0
        if rec["accepted_ns"] is None:
            assert rec["queue_wait_after_accept_ms"] is None
        else:
            assert rec["queue_wait_after_accept_ms"] >= 0

    print("PASS: fast consumer preserves deterministic identity and honest timing uncertainty")


def test_gate2_saturated_submit_measures_blocking_and_queue_snapshot():
    observations = []
    writer_entered = threading.Event()
    release_writer = threading.Event()

    class BlockingWriter:
        def __call__(self, records):
            writer_entered.set()
            release_writer.wait(timeout=2.0)
            return "/fake/blocking.parquet"

    writer = BlockingWriter()
    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=observations.append,
    )
    worker.start()

    def batch(label):
        return PersistenceBatch(
            records=[FakeRecord(1_000_000_000_000, label)],
            write_function=writer,
            partition_date_function=fake_partition_date,
            label="trade",
        )

    worker.submit(batch("first"))
    assert writer_entered.wait(timeout=2.0)

    worker.submit(batch("second"))

    submit_finished = threading.Event()

    def submit_third():
        worker.submit(batch("third"))
        submit_finished.set()

    submitter = threading.Thread(target=submit_third)
    submitter.start()

    time.sleep(0.05)
    assert not submit_finished.is_set()

    release_writer.set()
    submitter.join(timeout=2.0)
    assert submit_finished.is_set()

    worker.drain_and_stop()

    third = next(
        r for r in observations
        if r["type"] == "persistence_handoff" and r["batch_id"] == 3
    )

    assert third["queue_full_at_submit_start"] is True
    assert third["queue_depth_before"] == 1
    assert third["submit_block_ms"] >= 25.0

    print("PASS: saturated submission exposes queue-full snapshot and measured blocking")


def test_gate2_worker_failure_emits_failed_completion():
    observations = []
    writer = RecordingWriter(fail_on_call=1)
    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=observations.append,
    )
    worker.start()

    worker.submit(PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "fail")],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="depth",
    ))

    try:
        worker.drain_and_stop()
        raise AssertionError("Expected persistence failure")
    except RuntimeError:
        pass

    failed = [
        r for r in observations
        if r["type"] == "persistence_complete" and r["ok"] is False
    ]

    assert len(failed) == 1
    assert failed[0]["batch_id"] is not None
    assert failed[0]["label"] == "depth"
    assert failed[0]["exc"] == "RuntimeError"
    assert failed[0]["worker_persist_ms"] >= 0

    print("PASS: persistence failure produces correlated failed Gate-2 completion")


def test_gate2_real_submit_and_worker_completion_observers_are_serialized():
    completion_entered = threading.Event()
    release_completion = threading.Event()
    second_handoff_entered = threading.Event()
    second_submit_finished = threading.Event()
    calls = []
    calls_lock = threading.Lock()

    def blocking_observer(record):
        event_type = record["type"]
        batch_id = record["batch_id"]

        with calls_lock:
            calls.append(("enter", event_type, batch_id))

        if event_type == "persistence_complete" and batch_id == 1:
            completion_entered.set()
            release_completion.wait(timeout=2.0)
        elif event_type == "persistence_handoff" and batch_id == 2:
            second_handoff_entered.set()

        with calls_lock:
            calls.append(("exit", event_type, batch_id))

    worker = PersistenceWorker(
        max_queue_size=2,
        observation_callback=blocking_observer,
    )
    worker.start()

    first = PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "first")],
        write_function=lambda records: "/fake/first.parquet",
        partition_date_function=fake_partition_date,
        label="trade",
    )

    worker.submit(first)

    assert completion_entered.wait(timeout=2.0), (
        "Worker never entered the real batch-1 completion observer"
    )

    second = PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "second")],
        write_function=lambda records: "/fake/second.parquet",
        partition_date_function=fake_partition_date,
        label="trade",
    )

    def submit_second():
        worker.submit(second)
        second_submit_finished.set()

    submitter = threading.Thread(target=submit_second)
    submitter.start()

    deadline = time.monotonic() + 2.0
    while second.accepted_ns is None and time.monotonic() < deadline:
        time.sleep(0.001)

    assert second.accepted_ns is not None, (
        "Batch 2 was not accepted into the real bounded queue"
    )

    assert not second_handoff_entered.wait(timeout=0.05), (
        "Real submit() handoff observer entered while the worker completion "
        "observer still owned the observation lock"
    )
    assert not second_submit_finished.is_set(), (
        "submit() returned before its serialized handoff observation completed"
    )

    release_completion.set()

    submitter.join(timeout=2.0)
    assert not submitter.is_alive()
    assert second_submit_finished.is_set()
    assert second_handoff_entered.is_set()

    worker.drain_and_stop()

    with calls_lock:
        first_completion_exit = calls.index(
            ("exit", "persistence_complete", 1)
        )
        second_handoff_enter = calls.index(
            ("enter", "persistence_handoff", 2)
        )

    assert first_completion_exit < second_handoff_enter

    assert worker.accepted_count == 2
    assert worker.persisted_count == 2
    assert worker.unpersisted_count == 0

    print(
        "PASS: real submit() and worker completion observations serialize "
        "across ingestion and persistence threads"
    )


def test_gate2_observer_callbacks_are_serialized():
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    calls = []
    calls_lock = threading.Lock()

    def blocking_observer(record):
        with calls_lock:
            calls.append(("enter", record["batch_id"]))

        if record["batch_id"] == 101:
            first_entered.set()
            release_first.wait(timeout=2.0)
        else:
            second_entered.set()

        with calls_lock:
            calls.append(("exit", record["batch_id"]))

    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=blocking_observer,
    )

    first = {
        "type": "persistence_handoff",
        "batch_id": 101,
    }
    second = {
        "type": "persistence_complete",
        "batch_id": 202,
    }

    t1 = threading.Thread(target=worker._observe, args=(first,))
    t2 = threading.Thread(target=worker._observe, args=(second,))

    t1.start()
    assert first_entered.wait(timeout=2.0)

    t2.start()

    assert not second_entered.wait(timeout=0.05), (
        "Concurrent _observe() callbacks overlapped; previous-observer "
        "provenance cannot be deterministic without serialization"
    )

    release_first.set()

    t1.join(timeout=2.0)
    t2.join(timeout=2.0)

    assert not t1.is_alive()
    assert not t2.is_alive()
    assert calls == [
        ("enter", 101),
        ("exit", 101),
        ("enter", 202),
        ("exit", 202),
    ]

    print("PASS: observer callbacks are serialized across calling threads")


def test_gate2_real_worker_to_telemetry_jsonl_preserves_observer_provenance():
    telemetry_dir = tempfile.mkdtemp()
    telemetry = Telemetry(directory=telemetry_dir)
    writer = RecordingWriter()

    worker = PersistenceWorker(
        max_queue_size=2,
        observation_callback=telemetry.f3_persistence,
    )
    worker.start()

    batches = []
    for label in ("first", "second"):
        batch = PersistenceBatch(
            records=[
                FakeRecord(
                    1_000_000_000_000,
                    label,
                )
            ],
            write_function=writer,
            partition_date_function=fake_partition_date,
            label="trade",
        )
        batches.append(batch)
        worker.submit(batch)

    worker.drain_and_stop()
    telemetry.close()

    records = []
    for path in sorted(
        Path(telemetry_dir).glob("telemetry_*.jsonl")
    ):
        records.extend(
            json.loads(line)
            for line in path.read_text().splitlines()
        )

    observations = [
        record
        for record in records
        if record["type"] in (
            "f3_persistence_handoff",
            "f3_persistence_complete",
        )
    ]

    assert len(observations) == 4, (
        "Two real batches must produce two handoff and two completion "
        "observations in persisted telemetry"
    )

    assert {
        record["batch_id"]
        for record in observations
    } == {
        batches[0].batch_id,
        batches[1].batch_id,
    }

    first = observations[0]
    assert first["previous_observer_callback_ms"] is None
    assert first["previous_observer_event_type"] is None
    assert first["previous_observer_batch_id"] is None

    for previous, current in zip(observations, observations[1:]):
        previous_type = previous["type"].removeprefix("f3_")

        assert current["previous_observer_callback_ms"] is not None
        assert current["previous_observer_callback_ms"] >= 0.0
        assert current["previous_observer_event_type"] == previous_type
        assert (
            current["previous_observer_batch_id"]
            == previous["batch_id"]
        )

    final_measurement = worker.last_observer_measurement

    assert final_measurement["callback_ms"] is not None
    assert final_measurement["callback_ms"] >= 0.0
    assert final_measurement["event_type"] == (
        observations[-1]["type"].removeprefix("f3_")
    )
    assert final_measurement["batch_id"] == observations[-1]["batch_id"]

    assert worker.accepted_count == 2
    assert worker.persisted_count == 2
    assert worker.unpersisted_count == 0
    assert sum(len(call) for call in writer.calls) == 2

    print(
        "PASS: real PersistenceWorker -> Telemetry -> JSONL seam "
        "preserves measured serialized observer provenance"
    )


def test_gate2_previous_observer_provenance_tracks_completed_serial_order():
    seen = []

    def observer(record):
        seen.append(dict(record))
        time.sleep(0.015)

    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=observer,
    )

    first_source = {
        "type": "persistence_handoff",
        "batch_id": 101,
    }
    second_source = {
        "type": "persistence_complete",
        "batch_id": 101,
    }

    worker._observe(first_source)

    assert first_source == {
        "type": "persistence_handoff",
        "batch_id": 101,
    }
    assert seen[0]["previous_observer_callback_ms"] is None
    assert seen[0]["previous_observer_event_type"] is None
    assert seen[0]["previous_observer_batch_id"] is None

    first_measurement = worker.last_observer_measurement

    assert first_measurement["callback_ms"] >= 10.0
    assert first_measurement["event_type"] == "persistence_handoff"
    assert first_measurement["batch_id"] == 101

    worker._observe(second_source)

    assert second_source == {
        "type": "persistence_complete",
        "batch_id": 101,
    }
    assert (
        seen[1]["previous_observer_callback_ms"]
        == first_measurement["callback_ms"]
    )
    assert (
        seen[1]["previous_observer_event_type"]
        == "persistence_handoff"
    )
    assert seen[1]["previous_observer_batch_id"] == 101

    final_measurement = worker.last_observer_measurement

    assert final_measurement["callback_ms"] >= 10.0
    assert final_measurement["event_type"] == "persistence_complete"
    assert final_measurement["batch_id"] == 101

    print(
        "PASS: previous-observer provenance tracks the previous completed "
        "serialized callback without mutating source records"
    )


def test_gate2_failed_observer_becomes_previous_completed_provenance():
    seen = []

    def failing_observer(record):
        seen.append(dict(record))
        time.sleep(0.015)
        raise RuntimeError("Simulated observation failure")

    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=failing_observer,
    )

    worker._observe({
        "type": "persistence_handoff",
        "batch_id": 201,
    })

    first_measurement = worker.last_observer_measurement

    assert first_measurement["callback_ms"] >= 10.0
    assert first_measurement["event_type"] == "persistence_handoff"
    assert first_measurement["batch_id"] == 201

    worker._observe({
        "type": "persistence_complete",
        "batch_id": 201,
    })

    assert (
        seen[1]["previous_observer_callback_ms"]
        == first_measurement["callback_ms"]
    )
    assert (
        seen[1]["previous_observer_event_type"]
        == "persistence_handoff"
    )
    assert seen[1]["previous_observer_batch_id"] == 201

    print(
        "PASS: failed observer remains previous completed provenance "
        "without becoming structural"
    )


def test_gate2_observer_timing_is_measured_and_attributed():
    callback_records = []

    def slow_observer(record):
        callback_records.append(dict(record))
        time.sleep(0.03)

    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=slow_observer,
    )

    initial = worker.last_observer_measurement
    assert initial == {
        "callback_ms": None,
        "event_type": None,
        "batch_id": None,
    }

    worker.start()

    batch = PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "timed")],
        write_function=lambda records: "/fake/timed.parquet",
        partition_date_function=fake_partition_date,
        label="trade",
    )

    worker.submit(batch)
    worker.drain_and_stop()

    final = worker.last_observer_measurement

    assert final["callback_ms"] >= 20.0
    assert final["event_type"] == "persistence_complete"
    assert final["batch_id"] == batch.batch_id

    completion = [
        r for r in callback_records
        if r["type"] == "persistence_complete"
    ]
    assert len(completion) == 1
    assert completion[0]["batch_id"] == batch.batch_id

    print(
        "PASS: observer callback duration is measured and final "
        "completion attribution survives shutdown"
    )


def test_gate2_failed_observer_is_still_timed_without_becoming_structural():
    seen = []

    def failing_observer(record):
        seen.append(dict(record))
        time.sleep(0.02)
        raise RuntimeError("Simulated observation failure")

    writer = RecordingWriter()
    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=failing_observer,
    )
    worker.start()

    batch = PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "safe")],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="depth",
    )

    worker.submit(batch)
    worker.drain_and_stop()

    final = worker.last_observer_measurement

    assert final["callback_ms"] >= 10.0
    assert final["event_type"] == "persistence_complete"
    assert final["batch_id"] == batch.batch_id

    assert worker.accepted_count == 1
    assert worker.persisted_count == 1
    assert worker.unpersisted_count == 0
    assert sum(len(call) for call in writer.calls) == 1

    assert any(
        r["type"] == "persistence_complete"
        and r["batch_id"] == batch.batch_id
        for r in seen
    )

    print(
        "PASS: failed observer is timed and attributed without "
        "becoming canonical persistence failure"
    )


def test_gate2_observation_failure_is_non_structural():
    writer = RecordingWriter()

    def broken_observer(record):
        raise RuntimeError("Simulated telemetry failure")

    worker = PersistenceWorker(
        max_queue_size=1,
        observation_callback=broken_observer,
    )
    worker.start()

    worker.submit(PersistenceBatch(
        records=[FakeRecord(1_000_000_000_000, "safe")],
        write_function=writer,
        partition_date_function=fake_partition_date,
        label="trade",
    ))

    worker.drain_and_stop()

    assert worker.accepted_count == 1
    assert worker.persisted_count == 1
    assert worker.unpersisted_count == 0
    assert sum(len(call) for call in writer.calls) == 1

    print("PASS: observation failure cannot become canonical persistence failure")


if __name__ == "__main__":
    test_batch_owns_detached_record_list()
    test_worker_groups_dates_in_sorted_order()
    test_partial_failure_does_not_retry_successful_group()
    test_background_failure_becomes_owner_visible()
    test_queue_is_bounded_and_applies_backpressure()
    test_shutdown_drains_all_accepted_work()
    test_failure_preserves_later_accepted_batch_as_unpersisted()
    test_blocked_submit_is_released_by_worker_failure()

    test_gate2_observations_correlate_handoff_and_completion()
    test_gate2_fast_consumer_does_not_require_accepted_timestamp()
    test_gate2_saturated_submit_measures_blocking_and_queue_snapshot()
    test_gate2_worker_failure_emits_failed_completion()
    test_gate2_real_submit_and_worker_completion_observers_are_serialized()
    test_gate2_observer_callbacks_are_serialized()
    test_gate2_real_worker_to_telemetry_jsonl_preserves_observer_provenance()
    test_gate2_previous_observer_provenance_tracks_completed_serial_order()
    test_gate2_failed_observer_becomes_previous_completed_provenance()
    test_gate2_observer_timing_is_measured_and_attributed()
    test_gate2_failed_observer_is_still_timed_without_becoming_structural()
    test_gate2_observation_failure_is_non_structural()

    print("\nAll F3 async-persistence Gate-1 + Gate-2 instrumentation tests passed.")
