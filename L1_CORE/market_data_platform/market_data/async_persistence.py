"""
LRS-3 F3 — Asynchronous Persistence

Bounded single-writer persistence component for the F3 ownership-transfer
experiment.

This module does not own WebSocket ingestion, parsing, sequence tracking,
canonical schemas, or storage paths. It accepts detached record batches,
persists them from one worker thread, and exposes persistence failure to
the owning collector lifecycle.

F3 v1 intentionally uses one persistence worker.
"""

from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from typing import Callable, Generic, List, Optional, TypeVar


T = TypeVar("T")


@dataclass
class PersistenceBatch(Generic[T]):
    """
    One detached persistence batch.

    records is owned by this batch after ingestion transfers ownership.
    The worker groups records by UTC partition date before calling the
    injected write function.
    """

    records: List[T]
    write_function: Callable[[List[T]], str]
    partition_date_function: Callable[[int], str]
    label: str


class PersistenceWorker:
    """
    Bounded, single-thread persistence worker.

    submit() uses blocking Queue.put(), so queue saturation creates
    explicit backpressure rather than silent loss or unbounded growth.

    Any persistence exception is retained and surfaced to the owner by
    drain_and_stop(). The worker does not silently retry failed writes.
    """

    _STOP = object()

    def __init__(self, max_queue_size: int):
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be greater than zero")

        self._queue = Queue(maxsize=max_queue_size)
        self._thread: Optional[Thread] = None
        self._failure: Optional[BaseException] = None
        self._failure_lock = Lock()
        self._state_lock = Lock()
        self._accepted_count = 0
        self._persisted_count = 0
        self._started = False
        self._stopping = False

    def start(self) -> None:
        if self._started:
            raise RuntimeError("PersistenceWorker already started")

        self._started = True
        self._thread = Thread(
            target=self._run,
            name="lrs-f3-persistence",
            daemon=False,
        )
        self._thread.start()

    def submit(self, batch: PersistenceBatch) -> None:
        if not self._started:
            raise RuntimeError("PersistenceWorker has not been started")
        if self._stopping:
            raise RuntimeError("PersistenceWorker is stopping; new submissions are refused")

        self._raise_if_failed()
        self._queue.put(batch)
        with self._state_lock:
            self._accepted_count += 1
        self._raise_if_failed()

    def drain_and_stop(self) -> None:
        if not self._started:
            raise RuntimeError("PersistenceWorker has not been started")

        if not self._stopping:
            self._stopping = True
            self._queue.put(self._STOP)

        self._queue.join()

        if self._thread is not None:
            self._thread.join()

        self._raise_if_failed()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is self._STOP:
                    return

                try:
                    self._raise_if_failed()
                    self._persist_batch(item)
                except BaseException as exc:
                    self._record_failure(exc)
                else:
                    with self._state_lock:
                        self._persisted_count += 1
            finally:
                self._queue.task_done()

    @property
    def accepted_count(self) -> int:
        with self._state_lock:
            return self._accepted_count

    @property
    def persisted_count(self) -> int:
        with self._state_lock:
            return self._persisted_count

    @property
    def unpersisted_count(self) -> int:
        with self._state_lock:
            return self._accepted_count - self._persisted_count

    def _persist_batch(self, batch: PersistenceBatch) -> None:
        groups = {}

        for record in batch.records:
            date = batch.partition_date_function(record.timestamp_received)
            groups.setdefault(date, []).append(record)

        for date in sorted(groups.keys()):
            self._raise_if_failed()
            batch.write_function(groups[date])

    def _record_failure(self, exc: BaseException) -> None:
        with self._failure_lock:
            if self._failure is None:
                self._failure = exc

    def _raise_if_failed(self) -> None:
        with self._failure_lock:
            failure = self._failure

        if failure is not None:
            raise failure
