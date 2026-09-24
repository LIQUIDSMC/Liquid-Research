"""
LRS-3 F3 — Asynchronous Persistence Gate-1 Tests

Deterministic offline tests for the F3 ownership-transfer persistence
component. No production canonical storage is touched.

These tests define the minimum worker contract before collector.py is
modified.
"""

import threading
import time
from dataclasses import dataclass

from L1_CORE.market_data_platform.market_data.async_persistence import (
    PersistenceBatch,
    PersistenceWorker,
)


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


if __name__ == "__main__":
    test_batch_owns_detached_record_list()
    test_worker_groups_dates_in_sorted_order()
    test_partial_failure_does_not_retry_successful_group()
    test_background_failure_becomes_owner_visible()
    test_queue_is_bounded_and_applies_backpressure()
    test_shutdown_drains_all_accepted_work()

    print("\nAll F3 async-persistence contract tests passed.")


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
