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
import time
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
    batch_id: Optional[int] = None
    submit_start_ns: Optional[int] = None
    accepted_ns: Optional[int] = None


class PersistenceWorker:
    """
    Bounded, single-thread persistence worker.

    submit() uses blocking Queue.put(), so queue saturation creates
    explicit backpressure rather than silent loss or unbounded growth.

    Any persistence exception is retained and surfaced to the owner by
    drain_and_stop(). The worker does not silently retry failed writes.
    """

    _STOP = object()

    def __init__(self, max_queue_size: int, observation_callback=None):
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be greater than zero")

        self._queue = Queue(maxsize=max_queue_size)
        self._max_queue_size = max_queue_size
        self._observation_callback = observation_callback
        self._thread: Optional[Thread] = None
        self._failure: Optional[BaseException] = None
        self._failure_lock = Lock()
        self._state_lock = Lock()
        self._observation_lock = Lock()
        self._accepted_count = 0
        self._persisted_count = 0
        self._next_batch_id = 1
        self._last_observer_callback_ms: Optional[float] = None
        self._last_observer_event_type: Optional[str] = None
        self._last_observer_batch_id: Optional[int] = None
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

        submit_start_ns = time.monotonic_ns()
        queue_depth_before = self._queue.qsize()
        queue_full_at_submit_start = self._queue.full()

        with self._state_lock:
            batch.batch_id = self._next_batch_id
            self._next_batch_id += 1
            batch.submit_start_ns = submit_start_ns

        self._queue.put(batch)
        accepted_ns = time.monotonic_ns()

        with self._state_lock:
            batch.accepted_ns = accepted_ns
            self._accepted_count += 1
            accepted_count = self._accepted_count
            persisted_count = self._persisted_count

        self._observe({
            "type": "persistence_handoff",
            "batch_id": batch.batch_id,
            "label": batch.label,
            "rows": len(batch.records),
            "submit_start_ns": submit_start_ns,
            "accepted_ns": accepted_ns,
            "submit_block_ms": (accepted_ns - submit_start_ns) / 1e6,
            "queue_depth_before": queue_depth_before,
            "queue_depth_after_accept": self._queue.qsize(),
            "queue_capacity": self._max_queue_size,
            "queue_full_at_submit_start": queue_full_at_submit_start,
            "accepted_count": accepted_count,
            "persisted_count": persisted_count,
            "unpersisted_count": accepted_count - persisted_count,
        })

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

                worker_start_ns = time.monotonic_ns()
                try:
                    self._raise_if_failed()
                    self._persist_batch(item)
                except BaseException as exc:
                    worker_end_ns = time.monotonic_ns()
                    self._record_failure(exc)
                    self._observe_worker_result(
                        item, worker_start_ns, worker_end_ns, False, exc
                    )
                else:
                    worker_end_ns = time.monotonic_ns()
                    with self._state_lock:
                        self._persisted_count += 1
                    self._observe_worker_result(
                        item, worker_start_ns, worker_end_ns, True, None
                    )
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

    def _observe_worker_result(
        self,
        batch: PersistenceBatch,
        worker_start_ns: int,
        worker_end_ns: int,
        ok: bool,
        exc: Optional[BaseException],
    ) -> None:
        with self._state_lock:
            accepted_count = self._accepted_count
            persisted_count = self._persisted_count

        accepted_ns = batch.accepted_ns
        submit_start_ns = batch.submit_start_ns
        submit_to_worker_start_ms = (
            (worker_start_ns - submit_start_ns) / 1e6
            if submit_start_ns is not None
            else None
        )
        queue_wait_after_accept_ms = (
            max(0, worker_start_ns - accepted_ns) / 1e6
            if accepted_ns is not None
            else None
        )

        self._observe({
            "type": "persistence_complete",
            "batch_id": batch.batch_id,
            "label": batch.label,
            "rows": len(batch.records),
            "submit_start_ns": submit_start_ns,
            "accepted_ns": accepted_ns,
            "worker_start_ns": worker_start_ns,
            "worker_end_ns": worker_end_ns,
            "submit_to_worker_start_ms": submit_to_worker_start_ms,
            "queue_wait_after_accept_ms": queue_wait_after_accept_ms,
            "worker_persist_ms": (worker_end_ns - worker_start_ns) / 1e6,
            "ok": ok,
            "exc": None if exc is None else type(exc).__name__,
            "queue_depth_at_completion": self._queue.qsize(),
            "queue_capacity": self._max_queue_size,
            "accepted_count": accepted_count,
            "persisted_count": persisted_count,
            "unpersisted_count": accepted_count - persisted_count,
        })

    def _observe(self, record) -> None:
        callback = self._observation_callback
        if callback is None:
            return

        # submit() and the persistence worker can call _observe() from
        # different threads. Serialize the full observer transaction so
        # callback ordering and "last observer" attribution are deterministic.
        with self._observation_lock:
            with self._state_lock:
                previous_callback_ms = self._last_observer_callback_ms
                previous_event_type = self._last_observer_event_type
                previous_batch_id = self._last_observer_batch_id

            observed_record = dict(record)
            observed_record["previous_observer_callback_ms"] = previous_callback_ms
            observed_record["previous_observer_event_type"] = previous_event_type
            observed_record["previous_observer_batch_id"] = previous_batch_id

            observer_start_ns = time.monotonic_ns()
            try:
                callback(observed_record)
            except Exception:
                # F3 performance observation is non-structural. Observation failure
                # must never become canonical persistence failure.
                pass
            finally:
                observer_end_ns = time.monotonic_ns()
                with self._state_lock:
                    self._last_observer_callback_ms = (
                        observer_end_ns - observer_start_ns
                    ) / 1e6
                    self._last_observer_event_type = record.get("type")
                    self._last_observer_batch_id = record.get("batch_id")

    @property
    def last_observer_measurement(self):
        with self._state_lock:
            return {
                "callback_ms": self._last_observer_callback_ms,
                "event_type": self._last_observer_event_type,
                "batch_id": self._last_observer_batch_id,
            }

    def _record_failure(self, exc: BaseException) -> None:
        with self._failure_lock:
            if self._failure is None:
                self._failure = exc

    def _raise_if_failed(self) -> None:
        with self._failure_lock:
            failure = self._failure

        if failure is not None:
            raise failure
