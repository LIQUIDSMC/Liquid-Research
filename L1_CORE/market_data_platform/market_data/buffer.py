"""
Market Data Platform — Record Buffer
market_data_platform/market_data/buffer.py

Bounded in-memory buffering layer between parsed canonical records
and persistent storage. Exists because the live depth feed produces
extremely high message volume — writing one UUID Parquet file per
incoming message would create a severe small-file problem. Records
are accumulated and flushed together, either when a count threshold
is reached or when a maximum time interval has elapsed since the
last successful flush.

Flush semantics: buffered records are grouped by UTC calendar date
(storage.py's write functions correctly reject cross-date batches).
Date groups are written in deterministic sorted-date order. After
each individual date group writes successfully, only that group is
removed from the buffer. If a later group fails, all unwritten
groups (including the failed one) are preserved and the exception
propagates — persistence failure is structural, never silently
retried or masked. last_flush_time is reset only when the buffer
becomes fully empty after a completely successful flush; a failed
or partially-failed flush does not reset the timer, so a stalled
buffer does not silently wait another full interval before the
caller notices the failure.

This module has no import-time dependency on storage.py — both the
write function and the partition-date function are injected at
construction, keeping RecordBuffer independently testable and
decoupled from storage's internals.

The buffer never calls time.monotonic() directly — a clock function
is injected at construction, so timed-flush behavior can be tested
deterministically without real sleeping.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Generic, List, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class FlushResult:
    """
    Result of one RecordBuffer.flush() call, reflecting only what
    was actually, successfully written during that call.
    """
    records_persisted: int
    files_written: List[str] = field(default_factory=list)


class RecordBuffer(Generic[T]):
    """
    Accumulates canonical records of one type (TradeRecord or
    DepthLevelRecord) and flushes them to persistent storage in
    UTC-date-grouped batches, either on a count threshold or a time
    threshold — whichever is reached first.

    Fields:
        write_function (Callable[[List[T]], str]): e.g.
            storage.write_trade_records — injected so this class is
            type-agnostic and independently testable.
        partition_date_function (Callable[[int], str]): e.g.
            storage.partition_date_utc — injected so RecordBuffer
            has no import-time dependency on storage.py.
        count_threshold (int): flush when len(records) reaches this.
            This is a minimum flush trigger, not a maximum batch
            size: the check runs once per completed message, and
            one exchange message can add many canonical records at
            once (per the Canonical Unit of Observation principle).
            Confirmed by real operational evidence: Coinbase's
            initial level2 snapshot for one product can add tens of
            thousands of DepthLevelRecord instances in a single
            add() call, well past this threshold, before the next
            flush check even runs. This is expected, correct
            behavior, not a bug — the buffer is never artificially
            split mid-message to force a smaller file.
        max_interval_seconds (float): flush when this many seconds
            have elapsed since the last successful full flush.
        clock (Callable[[], float]): defaults to time.monotonic.
            Injectable so tests can supply a controlled fake clock
            instead of sleeping.
    """

    def __init__(
        self,
        write_function: Callable[[List[T]], str],
        partition_date_function: Callable[[int], str],
        count_threshold: int = 200,
        max_interval_seconds: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.write_function = write_function
        self.partition_date_function = partition_date_function
        self.count_threshold = count_threshold
        self.max_interval_seconds = max_interval_seconds
        self._clock = clock

        self.records: List[T] = []
        initial_time = self._clock()
        self.last_flush_time: float = initial_time
        self.last_handoff_time: float = initial_time

    def add(self, record: T) -> None:
        """Append one canonical record to the buffer."""
        self.records.append(record)

    def is_due_for_flush(self) -> bool:
        """
        True if either the count threshold or the time threshold
        has been reached. An empty buffer is never due for flush,
        regardless of elapsed time.
        """
        if not self.records:
            return False
        if len(self.records) >= self.count_threshold:
            return True
        if self._clock() - self.last_flush_time >= self.max_interval_seconds:
            return True
        return False

    def is_due_for_handoff(self) -> bool:
        """
        True if the active ingestion buffer is ready for asynchronous
        ownership transfer.

        Count semantics match the existing flush threshold. Time semantics
        use the independent handoff clock rather than the successful
        persistence clock.
        """
        if not self.records:
            return False

        if len(self.records) >= self.count_threshold:
            return True

        if self._clock() - self.last_handoff_time >= self.max_interval_seconds:
            return True

        return False

    def detach_for_persistence(self) -> List[T]:
        """
        Transfer ownership of the entire active record list.

        The exact list object becomes detached persistence work and ingestion
        immediately receives a fresh list. The nominal count threshold never
        splits the already-accepted active batch.

        This advances only the asynchronous handoff clock. It does not claim
        successful persistence and therefore does not modify last_flush_time.
        """
        detached = self.records
        self.records = []
        self.last_handoff_time = self._clock()
        return detached

    def flush(self) -> FlushResult:
        """
        Group buffered records by UTC date and write each group,
        in sorted-date order. Only successfully-written groups are
        removed from the buffer. If a write fails partway through,
        all unwritten groups (including the one that failed)
        remain in the buffer, and the exception propagates —
        persistence failure is structural, not silently retried.

        last_flush_time is reset only if the buffer is fully empty
        after this call (i.e. every date group wrote successfully).

        Returns:
            FlushResult: reflects only what was actually,
            successfully written during this call.

        Raises:
            Whatever exception the underlying write_function raises
            for the failing date group, unmodified. Already-written
            groups remain correctly removed from the buffer even
            though the exception prevents a FlushResult from being
            returned.
        """
        if not self.records:
            return FlushResult(records_persisted=0, files_written=[])

        groups: dict = {}
        for record in self.records:
            date = self.partition_date_function(record.timestamp_received)
            groups.setdefault(date, []).append(record)

        records_persisted = 0
        files_written: List[str] = []

        for date in sorted(groups.keys()):
            group_records = groups[date]
            filepath = self.write_function(group_records)

            files_written.append(filepath)
            records_persisted += len(group_records)

            # Remove this successfully-written date group from the
            # buffer immediately, before attempting the next group.
            # If a later group's write raises, this group is
            # already safely removed and cannot be duplicated on a
            # future retry — only groups not yet reached (or the
            # one that just failed) remain buffered.
            self.records = [
                record for record in self.records
                if self.partition_date_function(record.timestamp_received) != date
            ]

        if not self.records:
            self.last_flush_time = self._clock()

        return FlushResult(records_persisted=records_persisted, files_written=files_written)
