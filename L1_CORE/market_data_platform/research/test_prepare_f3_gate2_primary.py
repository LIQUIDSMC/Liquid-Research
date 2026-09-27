import json
import tempfile
from pathlib import Path

from L1_CORE.market_data_platform.research.analyze_f3_gate2 import (
    load_f3_observations,
    validate_and_pair,
)
from L1_CORE.market_data_platform.research.prepare_f3_gate2_primary import (
    prepare_primary,
    select_primary_population,
)


def handoff(batch_id, previous=None):
    record = {
        "type": "f3_persistence_handoff",
        "batch_id": batch_id,
        "label": "depth",
        "rows": 100 * batch_id,
        "submit_start_ns": batch_id * 10_000_000,
        "accepted_ns": batch_id * 10_000_000 + batch_id * 1_000_000,
        "submit_block_ms": float(batch_id),
        "queue_depth_before": 0,
        "queue_depth_after_accept": 1,
        "queue_capacity": 2,
        "queue_full_at_submit_start": False,
        "accepted_count": batch_id,
        "persisted_count": batch_id - 1,
        "unpersisted_count": 1,
        "previous_observer_callback_ms": None,
        "previous_observer_event_type": None,
        "previous_observer_batch_id": None,
    }
    set_previous(record, previous)
    return record


def completion(batch_id, previous):
    start = batch_id * 10_000_000
    accepted = start + batch_id * 1_000_000
    worker_start = accepted + batch_id * 2_000_000
    worker_end = worker_start + batch_id * 10_000_000
    record = {
        "type": "f3_persistence_complete",
        "batch_id": batch_id,
        "label": "depth",
        "rows": 100 * batch_id,
        "submit_start_ns": start,
        "accepted_ns": accepted,
        "worker_start_ns": worker_start,
        "worker_end_ns": worker_end,
        "submit_to_worker_start_ms": float(batch_id) * 3.0,
        "queue_wait_after_accept_ms": float(batch_id) * 2.0,
        "worker_persist_ms": float(batch_id) * 10.0,
        "ok": True,
        "exc": None,
        "queue_depth_at_completion": 0,
        "queue_capacity": 2,
        "accepted_count": batch_id,
        "persisted_count": batch_id,
        "unpersisted_count": 0,
        "previous_observer_callback_ms": None,
        "previous_observer_event_type": None,
        "previous_observer_batch_id": None,
    }
    set_previous(record, previous)
    return record


def set_previous(record, previous):
    if previous is not None:
        record["previous_observer_callback_ms"] = 0.1 * previous["batch_id"]
        record["previous_observer_event_type"] = previous["type"].removeprefix("f3_")
        record["previous_observer_batch_id"] = previous["batch_id"]


def epoch_records(count=5):
    records = []
    previous = None

    for batch_id in range(1, count + 1):
        h = handoff(batch_id, previous)
        records.append(h)
        previous = h

        c = completion(batch_id, previous)
        records.append(c)
        previous = c

    return records


def write_jsonl(records):
    directory = Path(tempfile.mkdtemp())
    path = directory / "synthetic_f3.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def expect_runtime_error(fn, expected):
    try:
        fn()
    except RuntimeError as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected RuntimeError containing {expected!r}")


def test_primary_range_selected_only_after_complete_epoch_validation():
    path = write_jsonl(epoch_records(5))
    observations = load_f3_observations([path])
    pairs = validate_and_pair(observations)

    primary_observations, primary_pairs = select_primary_population(
        observations, pairs, 3, 5
    )

    assert [pair["batch_id"] for pair in primary_pairs] == [3, 4, 5]
    assert {record["batch_id"] for record in primary_observations} == {3, 4, 5}
    assert len(primary_observations) == 6


def test_primary_summary_excludes_pre_protocol_performance_values():
    path = write_jsonl(epoch_records(5))
    summary = prepare_primary([path], 3, 5)

    assert summary["paired_batch_count"] == 3
    assert summary["total_rows"] == 300 + 400 + 500

    # Batch 1/2 values must not leak into primary distributions.
    assert summary["submit_block_ms"]["min"] == 3.0
    assert summary["worker_persist_ms"]["min"] == 30.0

    # Observer provenance is also filtered to primary observations.
    assert summary["previous_observer_callback_ms"]["n"] == 6


def test_cropped_mid_epoch_input_still_fails_closed():
    records = [
        record for record in epoch_records(5)
        if 3 <= record["batch_id"] <= 5
    ]
    path = write_jsonl(records)

    expect_runtime_error(
        lambda: prepare_primary([path], 3, 5),
        "mid-epoch fragment",
    )


def test_missing_requested_end_batch_fails_closed():
    path = write_jsonl(epoch_records(4))

    expect_runtime_error(
        lambda: prepare_primary([path], 3, 5),
        "validated primary range is incomplete",
    )


def test_invalid_primary_bounds_fail_closed():
    path = write_jsonl(epoch_records(5))
    observations = load_f3_observations([path])
    pairs = validate_and_pair(observations)

    expect_runtime_error(
        lambda: select_primary_population(observations, pairs, 0, 5),
        "start_batch_id must be a positive integer",
    )
    expect_runtime_error(
        lambda: select_primary_population(observations, pairs, 5, 4),
        "end_batch_id must be an integer >= start_batch_id",
    )


def run_all():
    tests = [
        test_primary_range_selected_only_after_complete_epoch_validation,
        test_primary_summary_excludes_pre_protocol_performance_values,
        test_cropped_mid_epoch_input_still_fails_closed,
        test_missing_requested_end_batch_fails_closed,
        test_invalid_primary_bounds_fail_closed,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"ALL ITEM-2 SYNTHETIC TESTS PASSED ({len(tests)}/{len(tests)})")


if __name__ == "__main__":
    run_all()
