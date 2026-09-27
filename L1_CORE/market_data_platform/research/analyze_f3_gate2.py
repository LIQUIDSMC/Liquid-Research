"""
F3 Gate-2 Offline Observation Analyzer

Reads one or more collector telemetry JSONL files and extracts the F3
persistence observations required for Gate-2 analysis.

This analyzer is intentionally observational. It does not adjudicate F3,
select queue capacity, impose a performance threshold, modify F2 evidence,
or infer physical-disk, network, trading, or economic performance.

The first validation layer is fail-closed: malformed or internally
inconsistent F3 persistence evidence is rejected before analysis.
"""

import json
import math
import statistics
from pathlib import Path


HANDOFF_TYPE = "f3_persistence_handoff"
COMPLETION_TYPE = "f3_persistence_complete"
F3_TYPES = {HANDOFF_TYPE, COMPLETION_TYPE}

COMMON_REQUIRED_FIELDS = {
    "type",
    "batch_id",
    "label",
    "rows",
    "queue_capacity",
    "accepted_count",
    "persisted_count",
    "unpersisted_count",
    "previous_observer_callback_ms",
    "previous_observer_event_type",
    "previous_observer_batch_id",
}

HANDOFF_REQUIRED_FIELDS = COMMON_REQUIRED_FIELDS | {
    "submit_start_ns",
    "accepted_ns",
    "submit_block_ms",
    "queue_depth_before",
    "queue_depth_after_accept",
    "queue_full_at_submit_start",
}

COMPLETION_REQUIRED_FIELDS = COMMON_REQUIRED_FIELDS | {
    "submit_start_ns",
    "accepted_ns",
    "worker_start_ns",
    "worker_end_ns",
    "submit_to_worker_start_ms",
    "queue_wait_after_accept_ms",
    "worker_persist_ms",
    "ok",
    "exc",
    "queue_depth_at_completion",
}


def load_f3_observations(paths):
    observations = []

    for source in paths:
        path = Path(source)
        with path.open() as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"FATAL: invalid JSON in {path}:{line_number}: {exc}"
                    ) from exc

                if not isinstance(record, dict):
                    raise RuntimeError(
                        f"FATAL: expected JSON object in {path}:{line_number}"
                    )

                if record.get("type") not in F3_TYPES:
                    continue

                copied = dict(record)
                copied["_source_file"] = str(path)
                copied["_source_line"] = line_number
                observations.append(copied)

    return observations


def _require_fields(record, required):
    missing = sorted(required - record.keys())
    if missing:
        raise RuntimeError(
            "FATAL: missing required F3 fields "
            f"{missing} at {record['_source_file']}:{record['_source_line']}"
        )


FROZEN_QUEUE_CAPACITY = 2
DURATION_ABS_TOLERANCE_MS = 1e-9


def _require_nonnegative_int(record, field):
    value = record[field]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(
            f"FATAL: {field} must be a nonnegative integer at "
            f"{record['_source_file']}:{record['_source_line']}; got {value!r}"
        )


def _require_nonnegative_number(record, field, allow_none=False):
    value = record[field]
    if value is None and allow_none:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise RuntimeError(
            f"FATAL: {field} must be a nonnegative number at "
            f"{record['_source_file']}:{record['_source_line']}; got {value!r}"
        )


def _require_duration_match(record, field, expected_ms):
    actual = record[field]
    _require_nonnegative_number(record, field)
    if abs(actual - expected_ms) > DURATION_ABS_TOLERANCE_MS:
        raise RuntimeError(
            f"FATAL: {field} disagrees with source timestamps at "
            f"{record['_source_file']}:{record['_source_line']}; "
            f"reported={actual!r}, expected={expected_ms!r}"
        )


def _validate_observer_provenance(record):
    values = (
        record["previous_observer_callback_ms"],
        record["previous_observer_event_type"],
        record["previous_observer_batch_id"],
    )
    none_count = sum(value is None for value in values)
    if none_count not in (0, 3):
        raise RuntimeError(
            "FATAL: previous-observer provenance must be entirely null or entirely "
            f"populated at {record['_source_file']}:{record['_source_line']}"
        )

    if none_count == 0:
        _require_nonnegative_number(record, "previous_observer_callback_ms")
        if record["previous_observer_event_type"] not in (
            "persistence_handoff",
            "persistence_complete",
        ):
            raise RuntimeError(
                "FATAL: invalid previous_observer_event_type at "
                f"{record['_source_file']}:{record['_source_line']}"
            )
        if (
            isinstance(record["previous_observer_batch_id"], bool)
            or not isinstance(record["previous_observer_batch_id"], int)
            or record["previous_observer_batch_id"] < 0
        ):
            raise RuntimeError(
                "FATAL: previous_observer_batch_id must be a nonnegative integer at "
                f"{record['_source_file']}:{record['_source_line']}"
            )


def _validate_record_structure(record):
    for field in (
        "batch_id",
        "rows",
        "queue_capacity",
        "accepted_count",
        "persisted_count",
        "unpersisted_count",
    ):
        _require_nonnegative_int(record, field)

    if record["rows"] == 0:
        raise RuntimeError(
            f"FATAL: rows must be positive for batch_id={record['batch_id']}"
        )

    if record["queue_capacity"] != FROZEN_QUEUE_CAPACITY:
        raise RuntimeError(
            f"FATAL: expected frozen F3 queue_capacity={FROZEN_QUEUE_CAPACITY}, "
            f"got {record['queue_capacity']!r} for batch_id={record['batch_id']}"
        )

    if not isinstance(record["label"], str) or not record["label"]:
        raise RuntimeError(
            f"FATAL: label must be a non-empty string for batch_id={record['batch_id']}"
        )

    _validate_observer_provenance(record)

    if record["type"] == HANDOFF_TYPE:
        for field in (
            "submit_start_ns",
            "accepted_ns",
            "queue_depth_before",
            "queue_depth_after_accept",
        ):
            _require_nonnegative_int(record, field)

        if not isinstance(record["queue_full_at_submit_start"], bool):
            raise RuntimeError(
                "FATAL: queue_full_at_submit_start must be boolean for "
                f"batch_id={record['batch_id']}"
            )

        if record["submit_start_ns"] > record["accepted_ns"]:
            raise RuntimeError(
                f"FATAL: submit timestamps out of order for batch_id={record['batch_id']}"
            )

        for field in ("queue_depth_before", "queue_depth_after_accept"):
            if record[field] > record["queue_capacity"]:
                raise RuntimeError(
                    f"FATAL: {field} exceeds queue capacity for "
                    f"batch_id={record['batch_id']}"
                )

        expected_submit_ms = (
            record["accepted_ns"] - record["submit_start_ns"]
        ) / 1e6
        _require_duration_match(record, "submit_block_ms", expected_submit_ms)

    elif record["type"] == COMPLETION_TYPE:
        for field in (
            "submit_start_ns",
            "accepted_ns",
            "worker_start_ns",
            "worker_end_ns",
            "queue_depth_at_completion",
        ):
            _require_nonnegative_int(record, field)

        if record["submit_start_ns"] > record["accepted_ns"]:
            raise RuntimeError(
                f"FATAL: submit timestamps out of order for batch_id={record['batch_id']}"
            )

        if record["worker_start_ns"] > record["worker_end_ns"]:
            raise RuntimeError(
                f"FATAL: worker timestamps out of order for batch_id={record['batch_id']}"
            )

        if record["queue_depth_at_completion"] > record["queue_capacity"]:
            raise RuntimeError(
                "FATAL: queue_depth_at_completion exceeds queue capacity for "
                f"batch_id={record['batch_id']}"
            )

        expected_submit_to_worker_ms = (
            record["worker_start_ns"] - record["submit_start_ns"]
        ) / 1e6
        if expected_submit_to_worker_ms < 0:
            raise RuntimeError(
                "FATAL: worker_start_ns precedes submit_start_ns for "
                f"batch_id={record['batch_id']}"
            )
        _require_duration_match(
            record,
            "submit_to_worker_start_ms",
            expected_submit_to_worker_ms,
        )

        expected_worker_ms = (
            record["worker_end_ns"] - record["worker_start_ns"]
        ) / 1e6
        _require_duration_match(record, "worker_persist_ms", expected_worker_ms)

        # The worker may start after queue.put() but before the submitting thread
        # records accepted_ns. In that accepted-timestamp race, the implementation
        # intentionally emits queue_wait_after_accept_ms=None.
        if record["worker_start_ns"] >= record["accepted_ns"]:
            expected_queue_wait_ms = (
                record["worker_start_ns"] - record["accepted_ns"]
            ) / 1e6
            if record["queue_wait_after_accept_ms"] is None:
                raise RuntimeError(
                    "FATAL: queue_wait_after_accept_ms unexpectedly null without "
                    f"accepted-timestamp race for batch_id={record['batch_id']}"
                )
            _require_duration_match(
                record,
                "queue_wait_after_accept_ms",
                expected_queue_wait_ms,
            )
        else:
            if record["queue_wait_after_accept_ms"] is not None:
                raise RuntimeError(
                    "FATAL: queue_wait_after_accept_ms must be null when worker start "
                    f"precedes accepted timestamp for batch_id={record['batch_id']}"
                )

        if not isinstance(record["ok"], bool):
            raise RuntimeError(
                f"FATAL: ok must be boolean for batch_id={record['batch_id']}"
            )

        if record["ok"] and record["exc"] is not None:
            raise RuntimeError(
                f"FATAL: successful completion carries exc for batch_id={record['batch_id']}"
            )
        if not record["ok"] and record["exc"] is None:
            raise RuntimeError(
                f"FATAL: failed completion lacks exc for batch_id={record['batch_id']}"
            )


def _previous_provenance_is_null(record):
    return (
        record["previous_observer_callback_ms"] is None
        and record["previous_observer_event_type"] is None
        and record["previous_observer_batch_id"] is None
    )


def partition_worker_epochs(observations):
    """
    Partition persisted F3 observations into PersistenceWorker lifetimes.

    Persisted JSONL order is authoritative for this reconstruction. Within one
    worker lifetime, every observation after the first must identify the
    immediately previous serialized observation through previous-observer
    provenance. A fully-null provenance triplet starts a new worker epoch.

    Mid-epoch fragments and broken provenance chains fail closed rather than
    guessing worker identity.
    """
    if not observations:
        raise RuntimeError("FATAL: no F3 persistence observations found")

    epochs = []
    current = []
    previous = None

    for record in observations:
        event_type = record["type"]

        if event_type == HANDOFF_TYPE:
            _require_fields(record, HANDOFF_REQUIRED_FIELDS)
        elif event_type == COMPLETION_TYPE:
            _require_fields(record, COMPLETION_REQUIRED_FIELDS)
        else:
            raise RuntimeError(f"FATAL: unexpected F3 event type {event_type!r}")

        _validate_record_structure(record)

        starts_epoch = _previous_provenance_is_null(record)

        if previous is None:
            if not starts_epoch:
                raise RuntimeError(
                    "FATAL: first supplied F3 observation is a mid-epoch fragment; "
                    "previous serialized observation is missing"
                )
            current = [record]
            epochs.append(current)
            previous = record
            continue

        if starts_epoch:
            current = [record]
            epochs.append(current)
            previous = record
            continue

        expected_type = previous["type"].removeprefix("f3_")
        expected_batch_id = previous["batch_id"]

        if (
            record["previous_observer_event_type"] != expected_type
            or record["previous_observer_batch_id"] != expected_batch_id
        ):
            raise RuntimeError(
                "FATAL: broken F3 previous-observer provenance chain at "
                f"{record['_source_file']}:{record['_source_line']}; "
                f"expected previous=({expected_type!r}, {expected_batch_id!r}), "
                "got previous=("
                f"{record['previous_observer_event_type']!r}, "
                f"{record['previous_observer_batch_id']!r})"
            )

        current.append(record)
        previous = record

    return epochs


def validate_and_pair(observations):
    epochs = partition_worker_epochs(observations)
    pairs = []

    for epoch_id, epoch in enumerate(epochs, start=1):
        handoffs = {}
        completions = {}

        if epoch[0]["batch_id"] != 1:
            raise RuntimeError(
                f"FATAL: worker epoch {epoch_id} does not restart at batch_id=1; "
                f"got batch_id={epoch[0]['batch_id']!r}"
            )

        for record in epoch:
            event_type = record["type"]
            batch_id = record["batch_id"]

            if event_type == HANDOFF_TYPE:
                target = handoffs
            elif event_type == COMPLETION_TYPE:
                target = completions
            else:
                raise RuntimeError(
                    f"FATAL: unexpected F3 event type {event_type!r}"
                )

            if batch_id in target:
                raise RuntimeError(
                    f"FATAL: duplicate {event_type} for "
                    f"epoch_id={epoch_id}, batch_id={batch_id}"
                )

            target[batch_id] = record

        handoff_ids = set(handoffs)
        completion_ids = set(completions)

        if handoff_ids != completion_ids:
            missing_completion = sorted(handoff_ids - completion_ids)
            missing_handoff = sorted(completion_ids - handoff_ids)
            raise RuntimeError(
                "FATAL: unmatched F3 persistence observations in "
                f"epoch_id={epoch_id}: "
                f"missing_completion={missing_completion}, "
                f"missing_handoff={missing_handoff}"
            )

        if handoff_ids:
            expected_batch_ids = set(range(1, max(handoff_ids) + 1))
            if handoff_ids != expected_batch_ids:
                missing_batch_ids = sorted(expected_batch_ids - handoff_ids)
                raise RuntimeError(
                    f"FATAL: worker epoch {epoch_id} has non-contiguous batch IDs; "
                    f"missing batch_id(s)={missing_batch_ids}"
                )

        for batch_id in sorted(handoff_ids):
            handoff = handoffs[batch_id]
            completion = completions[batch_id]

            for field in (
                "label",
                "rows",
                "submit_start_ns",
                "accepted_ns",
                "queue_capacity",
            ):
                if handoff[field] != completion[field]:
                    raise RuntimeError(
                        f"FATAL: epoch_id={epoch_id}, batch_id={batch_id} "
                        f"disagrees on {field}: "
                        f"handoff={handoff[field]!r}, "
                        f"completion={completion[field]!r}"
                    )

            if handoff["accepted_count"] < handoff["persisted_count"]:
                raise RuntimeError(
                    "FATAL: impossible handoff accounting for "
                    f"epoch_id={epoch_id}, batch_id={batch_id}"
                )

            if completion["accepted_count"] < completion["persisted_count"]:
                raise RuntimeError(
                    "FATAL: impossible completion accounting for "
                    f"epoch_id={epoch_id}, batch_id={batch_id}"
                )

            if (
                handoff["unpersisted_count"]
                != handoff["accepted_count"] - handoff["persisted_count"]
            ):
                raise RuntimeError(
                    "FATAL: inconsistent handoff unpersisted_count for "
                    f"epoch_id={epoch_id}, batch_id={batch_id}"
                )

            if (
                completion["unpersisted_count"]
                != completion["accepted_count"] - completion["persisted_count"]
            ):
                raise RuntimeError(
                    "FATAL: inconsistent completion unpersisted_count for "
                    f"epoch_id={epoch_id}, batch_id={batch_id}"
                )

            pairs.append(
                {
                    "epoch_id": epoch_id,
                    "batch_id": batch_id,
                    "handoff": handoff,
                    "completion": completion,
                }
            )

    return pairs


def _percentile(values, percentile):
    if not values:
        return None

    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _distribution(values):
    if not values:
        return {
            "n": 0,
            "min": None,
            "median": None,
            "p95": None,
            "max": None,
        }

    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "p95": _percentile(values, 0.95),
        "max": max(values),
    }


def summarize_gate2(observations, pairs):
    submit_block = []
    queue_wait = []
    worker_persist = []
    observer_callback = []

    queue_depth_before = []
    queue_depth_after_accept = []
    queue_depth_at_completion = []

    queue_full_count = 0
    queue_wait_unknown_count = 0
    successful_completion_count = 0
    failed_completion_count = 0
    failed_completion_batch_ids = []
    total_rows = 0
    labels = {}
    epoch_ids = set()

    for pair in pairs:
        epoch_ids.add(pair["epoch_id"])
        handoff = pair["handoff"]
        completion = pair["completion"]

        total_rows += handoff["rows"]
        labels[handoff["label"]] = labels.get(handoff["label"], 0) + 1

        submit_block.append(handoff["submit_block_ms"])
        worker_persist.append(completion["worker_persist_ms"])

        if completion["queue_wait_after_accept_ms"] is None:
            queue_wait_unknown_count += 1
        else:
            queue_wait.append(completion["queue_wait_after_accept_ms"])

        queue_depth_before.append(handoff["queue_depth_before"])
        queue_depth_after_accept.append(handoff["queue_depth_after_accept"])
        queue_depth_at_completion.append(completion["queue_depth_at_completion"])

        if handoff["queue_full_at_submit_start"]:
            queue_full_count += 1

        if completion["ok"]:
            successful_completion_count += 1
        else:
            failed_completion_count += 1
            failed_completion_batch_ids.append(
                {
                    "epoch_id": pair["epoch_id"],
                    "batch_id": pair["batch_id"],
                }
            )

    for record in observations:
        value = record["previous_observer_callback_ms"]
        if value is not None:
            observer_callback.append(value)

    queue_capacity_values = {
        pair["handoff"]["queue_capacity"]
        for pair in pairs
    }
    queue_capacity = (
        next(iter(queue_capacity_values))
        if len(queue_capacity_values) == 1
        else None
    )

    depth_values = (
        queue_depth_before
        + queue_depth_after_accept
        + queue_depth_at_completion
    )
    max_observed_queue_depth = max(depth_values) if depth_values else None

    queue_depth_before_at_capacity_count = 0
    queue_depth_after_accept_at_capacity_count = 0
    queue_depth_at_completion_at_capacity_count = 0

    if queue_capacity is not None:
        queue_depth_before_at_capacity_count = sum(
            depth == queue_capacity for depth in queue_depth_before
        )
        queue_depth_after_accept_at_capacity_count = sum(
            depth == queue_capacity for depth in queue_depth_after_accept
        )
        queue_depth_at_completion_at_capacity_count = sum(
            depth == queue_capacity for depth in queue_depth_at_completion
        )

    observations_at_capacity = (
        queue_depth_before_at_capacity_count
        + queue_depth_after_accept_at_capacity_count
        + queue_depth_at_completion_at_capacity_count
    )

    return {
        "epoch_count": len(epoch_ids),
        "paired_batch_count": len(pairs),
        "total_rows": total_rows,
        "batch_counts_by_label": dict(sorted(labels.items())),
        "queue_capacity": queue_capacity,
        "submit_block_ms": _distribution(submit_block),
        "queue_wait_after_accept_ms": _distribution(queue_wait),
        "queue_wait_unknown_count": queue_wait_unknown_count,
        "worker_persist_ms": _distribution(worker_persist),
        "successful_completion_count": successful_completion_count,
        "failed_completion_count": failed_completion_count,
        "failed_completion_batch_ids": failed_completion_batch_ids,
        "previous_observer_callback_ms": _distribution(observer_callback),
        "queue_full_at_submit_start_count": queue_full_count,
        "queue_depth_before": _distribution(queue_depth_before),
        "queue_depth_after_accept": _distribution(queue_depth_after_accept),
        "queue_depth_at_completion": _distribution(queue_depth_at_completion),
        "max_observed_queue_depth": max_observed_queue_depth,
        "queue_depth_before_at_capacity_count": (
            queue_depth_before_at_capacity_count
        ),
        "queue_depth_after_accept_at_capacity_count": (
            queue_depth_after_accept_at_capacity_count
        ),
        "queue_depth_at_completion_at_capacity_count": (
            queue_depth_at_completion_at_capacity_count
        ),
        "queue_depth_observations_at_capacity": observations_at_capacity,
    }


def main(paths, json_output=False):
    observations = load_f3_observations(paths)
    pairs = validate_and_pair(observations)
    summary = summarize_gate2(observations, pairs)

    if json_output:
        print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
        return

    print("===== F3 GATE-2 STRUCTURAL VALIDATION PASS =====")
    print(f"F3 observations: {len(observations)}")
    print(f"Paired persistence batches: {len(pairs)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate F3 Gate-2 persistence telemetry."
    )
    parser.add_argument(
        "telemetry",
        nargs="+",
        help="One or more telemetry JSONL files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit deterministic Gate-2 descriptive summary JSON.",
    )
    args = parser.parse_args()
    main(args.telemetry, json_output=args.json_output)
