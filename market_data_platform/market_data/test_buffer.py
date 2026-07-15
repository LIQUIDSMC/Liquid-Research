"""
Market Data Platform — RecordBuffer Test
market_data_platform/market_data/test_buffer.py

Deterministic offline tests for RecordBuffer. No real storage is
touched — write_function and partition_date_function are fake,
injected callables, so these tests run entirely in memory. No real
sleeping — the clock is a fake, injectable, manually-advanced
function.

Run directly: python3 -m market_data_platform.market_data.test_buffer
"""

from dataclasses import dataclass

from market_data_platform.market_data.buffer import RecordBuffer, FlushResult


@dataclass
class FakeRecord:
    """Minimal stand-in record — only needs timestamp_received, per RecordBuffer's actual usage."""
    timestamp_received: int
    label: str = ""


class FakeClock:
    """Manually-advanced fake clock, injected in place of time.monotonic."""

    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeWriter:
    """
    Fake write function. Records every call's arguments. Can be
    configured to raise on a specific call number, to test partial-
    failure behavior deterministically.
    """

    def __init__(self, fail_on_call: int = None):
        self.calls = []
        self.fail_on_call = fail_on_call
        self._call_count = 0

    def __call__(self, records: list) -> str:
        self._call_count += 1
        self.calls.append(list(records))
        if self.fail_on_call is not None and self._call_count == self.fail_on_call:
            raise RuntimeError(f"Simulated write failure on call {self._call_count}")
        return f"/fake/path/batch_{self._call_count}.parquet"


def _fake_partition_date(timestamp_received_ms: int) -> str:
    """Fake partition function: two fixed dates based on a threshold, for deterministic grouping in tests."""
    return "2026-07-14" if timestamp_received_ms < 2_000_000_000_000 else "2026-07-15"


def test_count_triggered_flush():
    clock = FakeClock()
    writer = FakeWriter()
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=3, max_interval_seconds=100.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "a"))
    buf.add(FakeRecord(1_000_000_000_000, "b"))
    assert not buf.is_due_for_flush(), "Should not be due before reaching count threshold"

    buf.add(FakeRecord(1_000_000_000_000, "c"))
    assert buf.is_due_for_flush(), "Should be due once count threshold is reached"

    result = buf.flush()
    assert result.records_persisted == 3
    assert len(result.files_written) == 1
    assert len(writer.calls) == 1
    assert buf.records == []
    print("PASS: count-triggered flush becomes due at the correct threshold and successfully persists")


def test_time_triggered_flush_with_no_new_records():
    clock = FakeClock()
    writer = FakeWriter()
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=10.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "a"))
    assert not buf.is_due_for_flush(), "Should not be due immediately"

    clock.advance(9.0)
    assert not buf.is_due_for_flush(), "Should not be due before the interval elapses"

    clock.advance(1.5)
    assert buf.is_due_for_flush(), "Should be due once the time interval elapses, with no new records added"

    result = buf.flush()
    assert result.records_persisted == 1
    assert len(result.files_written) == 1
    assert len(writer.calls) == 1
    assert buf.records == []
    print("PASS: time-triggered flush becomes due at the correct interval and successfully persists, using injected clock only")


def test_utc_date_grouping_into_multiple_writes():
    clock = FakeClock()
    writer = FakeWriter()
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=1000.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "day1-a"))
    buf.add(FakeRecord(1_000_000_000_000, "day1-b"))
    buf.add(FakeRecord(3_000_000_000_000, "day2-a"))

    result = buf.flush()

    assert len(writer.calls) == 2, f"Expected 2 separate writes (one per date group), got {len(writer.calls)}"
    assert len(writer.calls[0]) == 2, "First write should be the 2 day1 records"
    assert len(writer.calls[1]) == 1, "Second write should be the 1 day2 record"
    assert result.records_persisted == 3
    assert len(result.files_written) == 2
    assert buf.records == [], "Buffer should be fully empty after a fully successful flush"
    print(f"PASS: UTC date grouping produced 2 separate writes: {result}")


def test_buffer_retains_unwritten_records_after_failed_write():
    clock = FakeClock()
    writer = FakeWriter(fail_on_call=2)  # succeed on the first date group, fail on the second
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=1000.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "day1-a"))
    buf.add(FakeRecord(3_000_000_000_000, "day2-a"))

    try:
        buf.flush()
        raise AssertionError("Expected flush() to raise RuntimeError, but it did not.")
    except RuntimeError as e:
        print(f"PASS: flush() correctly propagated the write failure: {e}")

    assert len(buf.records) == 1, f"Expected 1 record retained (the failed day2 group), got {len(buf.records)}"
    assert buf.records[0].label == "day2-a", "The retained record should be the one whose write failed"
    print("PASS: successfully-written date group was removed; failed date group's record remains buffered")


def test_successful_group_not_duplicated_on_retry_after_partial_failure():
    clock = FakeClock()
    writer = FakeWriter(fail_on_call=2)
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=1000.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "day1-a"))
    buf.add(FakeRecord(3_000_000_000_000, "day2-a"))

    try:
        buf.flush()
    except RuntimeError:
        pass

    # Retry with a writer that now succeeds.
    buf.write_function = FakeWriter()
    result = buf.flush()

    assert result.records_persisted == 1, (
        f"Expected only the previously-failed day2 record to be persisted on retry "
        f"(day1 was already written and removed), got {result.records_persisted}"
    )
    assert buf.records == []
    print("PASS: retry after partial failure did not re-write the already-successful date group")


def test_last_flush_time_not_reset_on_failure():
    clock = FakeClock()
    writer = FakeWriter(fail_on_call=1)
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=10.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "a"))
    initial_flush_time = buf.last_flush_time

    try:
        buf.flush()
    except RuntimeError:
        pass

    assert buf.last_flush_time == initial_flush_time, "last_flush_time must not change on a failed flush"
    print("PASS: last_flush_time was not reset after a failed flush")


def test_independent_thresholds_between_two_buffers():
    clock = FakeClock()
    trade_writer = FakeWriter()
    depth_writer = FakeWriter()

    trade_buf = RecordBuffer(trade_writer, _fake_partition_date, count_threshold=5, max_interval_seconds=10.0, clock=clock)
    depth_buf = RecordBuffer(depth_writer, _fake_partition_date, count_threshold=200, max_interval_seconds=10.0, clock=clock)

    for _ in range(5):
        trade_buf.add(FakeRecord(1_000_000_000_000))
    for _ in range(5):
        depth_buf.add(FakeRecord(1_000_000_000_000))

    assert trade_buf.is_due_for_flush(), "Trade buffer should be due at its own lower threshold"
    assert not depth_buf.is_due_for_flush(), "Depth buffer should not be due yet at its own higher threshold"
    print("PASS: trade and depth buffers maintain independent thresholds correctly")


def test_buffers_survive_simulated_reconnect():
    # Simulates the reconnect requirement: the same RecordBuffer
    # instance must persist across a simulated reconnect (i.e. no
    # new RecordBuffer is constructed), unlike SequenceGapTracker,
    # which is correctly reconstructed on every reconnect.
    clock = FakeClock()
    writer = FakeWriter()
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=1000.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "before-reconnect"))
    assert len(buf.records) == 1

    # Simulated reconnect: a new SequenceGapTracker would be created
    # here in the real collector, but buf itself is untouched.
    buf.add(FakeRecord(1_000_000_000_000, "after-reconnect"))

    assert len(buf.records) == 2, "Records added before and after a simulated reconnect must both be retained"
    print("PASS: buffer retains records across a simulated reconnect")


def test_pending_records_can_be_flushed_for_shutdown():
    # Proves only that RecordBuffer.flush(), called manually,
    # correctly persists whatever is currently buffered. This does
    # NOT prove that collector.py's task-cancellation / finally
    # path actually invokes this method — collector.py has not yet
    # been modified. The real cancellation-triggers-flush test
    # belongs in the later collector-integration test suite, once
    # that integration exists to test.
    clock = FakeClock()
    writer = FakeWriter()
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=1000.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "pending-at-shutdown"))
    result = buf.flush()

    assert result.records_persisted == 1
    assert buf.records == []
    print("PASS: manually calling flush() persists all pending records (does not test collector.py's actual shutdown path — not yet integrated)")


def test_successful_flush_resets_last_flush_time():
    clock = FakeClock(start=5.0)
    writer = FakeWriter()
    buf = RecordBuffer(writer, _fake_partition_date, count_threshold=1000, max_interval_seconds=10.0, clock=clock)

    buf.add(FakeRecord(1_000_000_000_000, "a"))
    clock.advance(3.0)

    result = buf.flush()

    assert result.records_persisted == 1
    assert buf.records == [], "Buffer should be empty after a fully successful flush"
    assert buf.last_flush_time == clock(), (
        f"last_flush_time should be reset to the current clock value ({clock()}) "
        f"after a successful flush, got {buf.last_flush_time}"
    )
    assert not buf.is_due_for_flush(), "A freshly-flushed, empty buffer should not be due"
    print("PASS: successful flush correctly resets last_flush_time to the current clock value")


if __name__ == "__main__":
    test_count_triggered_flush()
    test_time_triggered_flush_with_no_new_records()
    test_utc_date_grouping_into_multiple_writes()
    test_buffer_retains_unwritten_records_after_failed_write()
    test_successful_group_not_duplicated_on_retry_after_partial_failure()
    test_last_flush_time_not_reset_on_failure()
    test_independent_thresholds_between_two_buffers()
    test_buffers_survive_simulated_reconnect()
    test_pending_records_can_be_flushed_for_shutdown()
    test_successful_flush_resets_last_flush_time()

    print("\nAll RecordBuffer tests passed. No real storage, sleeping, or production data involved.")
