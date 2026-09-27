import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from L1_CORE.market_data_platform.research.analyze_f3_gate2 import (
    _distribution,
    load_f3_observations,
    main,
    partition_worker_epochs,
    summarize_gate2,
    validate_and_pair,
)


def handoff(batch_id=1):
    return {
        "type": "f3_persistence_handoff",
        "batch_id": batch_id,
        "label": "depth",
        "rows": 40000,
        "submit_start_ns": 100,
        "accepted_ns": 110,
        "submit_block_ms": 0.00001,
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


def completion(batch_id=1):
    return {
        "type": "f3_persistence_complete",
        "batch_id": batch_id,
        "label": "depth",
        "rows": 40000,
        "submit_start_ns": 100,
        "accepted_ns": 110,
        "worker_start_ns": 120,
        "worker_end_ns": 220,
        "submit_to_worker_start_ms": 0.00002,
        "queue_wait_after_accept_ms": 0.00001,
        "worker_persist_ms": 0.0001,
        "ok": True,
        "exc": None,
        "queue_depth_at_completion": 0,
        "queue_capacity": 2,
        "accepted_count": 1,
        "persisted_count": 1,
        "unpersisted_count": 0,
        "previous_observer_callback_ms": 0.2,
        "previous_observer_event_type": "persistence_handoff",
        "previous_observer_batch_id": batch_id,
    }


def write_jsonl(records):
    directory = Path(tempfile.mkdtemp())
    path = directory / "telemetry_test.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def expect_runtime_error(fn, expected_text):
    try:
        fn()
    except RuntimeError as exc:
        assert expected_text in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected RuntimeError containing {expected_text!r}")


def test_load_filters_unrelated_telemetry():
    path = write_jsonl(
        [
            {"type": "session_start", "session_id": "abc"},
            handoff(),
            {"type": "loop_gap", "gap_ms": 123},
            completion(),
        ]
    )

    observations = load_f3_observations([path])

    assert len(observations) == 2
    assert [record["type"] for record in observations] == [
        "f3_persistence_handoff",
        "f3_persistence_complete",
    ]
    print("PASS: unrelated telemetry is ignored")


def test_valid_pair_passes():
    path = write_jsonl([handoff(), completion()])
    pairs = validate_and_pair(load_f3_observations([path]))

    assert len(pairs) == 1
    assert pairs[0]["batch_id"] == 1
    print("PASS: valid handoff/completion pair passes structural validation")


def test_gate2_summary_preserves_measurement_boundaries():
    h1 = handoff()
    c1 = completion()

    h2 = handoff(batch_id=2)
    h2["submit_start_ns"] = 1_000_000
    h2["accepted_ns"] = 3_000_000
    h2["submit_block_ms"] = 2.0
    h2["queue_depth_before"] = 2
    h2["queue_depth_after_accept"] = 2
    h2["queue_full_at_submit_start"] = True
    h2["accepted_count"] = 2
    h2["persisted_count"] = 0
    h2["unpersisted_count"] = 2
    h2["previous_observer_callback_ms"] = 0.2
    h2["previous_observer_event_type"] = "persistence_complete"
    h2["previous_observer_batch_id"] = 1

    c2 = completion(batch_id=2)
    c2["submit_start_ns"] = 1_000_000
    c2["accepted_ns"] = 3_000_000
    c2["worker_start_ns"] = 8_000_000
    c2["worker_end_ns"] = 18_000_000
    c2["submit_to_worker_start_ms"] = 7.0
    c2["queue_wait_after_accept_ms"] = 5.0
    c2["worker_persist_ms"] = 10.0
    c2["queue_depth_at_completion"] = 1
    c2["accepted_count"] = 2
    c2["persisted_count"] = 2
    c2["unpersisted_count"] = 0
    c2["previous_observer_callback_ms"] = 0.3
    c2["previous_observer_event_type"] = "persistence_handoff"
    c2["previous_observer_batch_id"] = 2

    path = write_jsonl([h1, c1, h2, c2])
    observations = load_f3_observations([path])
    pairs = validate_and_pair(observations)
    summary = summarize_gate2(observations, pairs)

    assert summary["epoch_count"] == 1
    assert summary["paired_batch_count"] == 2
    assert summary["total_rows"] == 80000
    assert summary["batch_counts_by_label"] == {"depth": 2}
    assert summary["queue_capacity"] == 2

    assert summary["submit_block_ms"]["n"] == 2
    assert summary["submit_block_ms"]["max"] == 2.0

    assert summary["queue_wait_after_accept_ms"]["n"] == 2
    assert summary["queue_wait_after_accept_ms"]["max"] == 5.0
    assert summary["queue_wait_unknown_count"] == 0

    assert summary["worker_persist_ms"]["n"] == 2
    assert summary["worker_persist_ms"]["max"] == 10.0

    assert summary["previous_observer_callback_ms"]["n"] == 3
    assert summary["previous_observer_callback_ms"]["max"] == 0.3

    assert summary["queue_full_at_submit_start_count"] == 1
    assert summary["max_observed_queue_depth"] == 2

    assert summary["queue_depth_before_at_capacity_count"] == 1
    assert summary["queue_depth_after_accept_at_capacity_count"] == 1
    assert summary["queue_depth_at_completion_at_capacity_count"] == 0
    assert summary["queue_depth_observations_at_capacity"] == 2

    assert summary["queue_depth_observations_at_capacity"] == (
        summary["queue_depth_before_at_capacity_count"]
        + summary["queue_depth_after_accept_at_capacity_count"]
        + summary["queue_depth_at_completion_at_capacity_count"]
    )

    print("PASS: Gate-2 summary preserves separate measurement families")


def test_gate2_summary_exposes_failed_completion_without_dropping_timing():
    h = handoff()
    c = completion()
    c["ok"] = False
    c["exc"] = "synthetic persistence failure"

    path = write_jsonl([h, c])
    observations = load_f3_observations([path])
    pairs = validate_and_pair(observations)
    summary = summarize_gate2(observations, pairs)

    assert summary["successful_completion_count"] == 0
    assert summary["failed_completion_count"] == 1
    assert summary["failed_completion_batch_ids"] == [
        {"epoch_id": 1, "batch_id": 1}
    ]

    # Failure status is reported separately; the observed worker duration remains
    # part of the descriptive timing population.
    assert summary["worker_persist_ms"]["n"] == 1
    assert summary["worker_persist_ms"]["max"] == c["worker_persist_ms"]

    print("PASS: Gate-2 summary exposes failed completion and preserves timing")


def test_gate2_summary_preserves_unknown_queue_wait():
    h = handoff()
    c = completion()

    # Accepted timestamp may be captured after the worker has already started.
    # The paired identity remains consistent, while queue residence is unknown.
    h["accepted_ns"] = 130
    h["submit_block_ms"] = 0.00003
    c["accepted_ns"] = 130
    c["queue_wait_after_accept_ms"] = None

    path = write_jsonl([h, c])
    observations = load_f3_observations([path])
    pairs = validate_and_pair(observations)
    summary = summarize_gate2(observations, pairs)

    assert summary["queue_wait_after_accept_ms"] == {
        "n": 0,
        "min": None,
        "median": None,
        "p95": None,
        "max": None,
    }
    assert summary["queue_wait_unknown_count"] == 1

    print("PASS: Gate-2 summary preserves unknown queue wait instead of zero")


def test_distribution_percentile_definition_is_deterministic():
    summary = _distribution([1.0, 2.0, 3.0, 4.0, 5.0])

    assert summary["n"] == 5
    assert summary["min"] == 1.0
    assert summary["median"] == 3.0
    assert summary["p95"] == 4.8
    assert summary["max"] == 5.0

    singleton = _distribution([7.0])
    assert singleton == {
        "n": 1,
        "min": 7.0,
        "median": 7.0,
        "p95": 7.0,
        "max": 7.0,
    }

    empty = _distribution([])
    assert empty == {
        "n": 0,
        "min": None,
        "median": None,
        "p95": None,
        "max": None,
    }

    print("PASS: descriptive percentile definition is deterministic")


def test_json_output_is_deterministic_and_matches_summary():
    h = handoff()
    c = completion()
    path = write_jsonl([h, c])

    observations = load_f3_observations([path])
    pairs = validate_and_pair(observations)
    expected = summarize_gate2(observations, pairs)

    outputs = []
    for _ in range(2):
        stream = io.StringIO()
        with redirect_stdout(stream):
            main([path], json_output=True)
        outputs.append(stream.getvalue())

    assert outputs[0] == outputs[1]
    assert outputs[0].endswith("\n")
    assert json.loads(outputs[0]) == expected

    encoded = outputs[0].rstrip("\n")
    assert encoded == json.dumps(
        expected,
        sort_keys=True,
        separators=(",", ":"),
    )

    print("PASS: Gate-2 JSON output is deterministic and matches summary")


def test_missing_completion_fails_closed():
    path = write_jsonl([handoff()])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "unmatched F3 persistence observations",
    )
    print("PASS: missing completion fails closed")


def test_duplicate_handoff_fails_closed():
    first = handoff()
    duplicate = handoff()
    duplicate["previous_observer_callback_ms"] = 0.1
    duplicate["previous_observer_event_type"] = "persistence_handoff"
    duplicate["previous_observer_batch_id"] = first["batch_id"]

    done = completion()
    done["previous_observer_callback_ms"] = 0.1
    done["previous_observer_event_type"] = "persistence_handoff"
    done["previous_observer_batch_id"] = duplicate["batch_id"]

    path = write_jsonl([first, duplicate, done])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "duplicate f3_persistence_handoff",
    )
    print("PASS: duplicate handoff within one worker epoch fails closed")


def test_missing_entire_batch_id_fails_closed():
    first_handoff = handoff()

    first_completion = completion()
    first_completion["previous_observer_callback_ms"] = 0.1
    first_completion["previous_observer_event_type"] = "persistence_handoff"
    first_completion["previous_observer_batch_id"] = 1

    third_handoff = handoff()
    third_handoff["batch_id"] = 3
    third_handoff["accepted_count"] = 3
    third_handoff["persisted_count"] = 2
    third_handoff["unpersisted_count"] = 1
    third_handoff["previous_observer_callback_ms"] = 0.1
    third_handoff["previous_observer_event_type"] = "persistence_complete"
    third_handoff["previous_observer_batch_id"] = 1

    third_completion = completion()
    third_completion["batch_id"] = 3
    third_completion["accepted_count"] = 3
    third_completion["persisted_count"] = 3
    third_completion["unpersisted_count"] = 0
    third_completion["previous_observer_callback_ms"] = 0.1
    third_completion["previous_observer_event_type"] = "persistence_handoff"
    third_completion["previous_observer_batch_id"] = 3

    path = write_jsonl([
        first_handoff,
        first_completion,
        third_handoff,
        third_completion,
    ])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "non-contiguous batch IDs",
    )
    print("PASS: entirely missing batch_id within one worker epoch fails closed")


def test_pair_identity_mismatch_fails_closed():
    bad_completion = completion()
    bad_completion["rows"] = 39999
    path = write_jsonl([handoff(), bad_completion])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "disagrees on rows",
    )
    print("PASS: paired identity mismatch fails closed")


def test_accounting_mismatch_fails_closed():
    bad_completion = completion()
    bad_completion["unpersisted_count"] = 1
    path = write_jsonl([handoff(), bad_completion])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "inconsistent completion unpersisted_count",
    )
    print("PASS: accounting mismatch fails closed")


def test_missing_required_field_fails_closed():
    bad = handoff()
    del bad["submit_block_ms"]
    path = write_jsonl([bad, completion()])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "missing required F3 fields",
    )
    print("PASS: missing required field fails closed")


def test_timestamp_duration_mismatch_fails_closed():
    bad = handoff()
    bad["submit_block_ms"] = 99.0
    path = write_jsonl([bad, completion()])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "submit_block_ms disagrees with source timestamps",
    )
    print("PASS: timestamp/duration mismatch fails closed")


def test_queue_capacity_mismatch_fails_closed():
    bad_handoff = handoff()
    bad_completion = completion()
    bad_handoff["queue_capacity"] = 3
    bad_completion["queue_capacity"] = 3
    path = write_jsonl([bad_handoff, bad_completion])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "expected frozen F3 queue_capacity=2",
    )
    print("PASS: queue-capacity mismatch fails closed")


def test_queue_depth_over_capacity_fails_closed():
    bad = handoff()
    bad["queue_depth_after_accept"] = 3
    path = write_jsonl([bad, completion()])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "queue_depth_after_accept exceeds queue capacity",
    )
    print("PASS: queue depth over capacity fails closed")


def test_worker_timestamp_order_fails_closed():
    bad = completion()
    bad["worker_start_ns"] = 300
    bad["worker_end_ns"] = 220
    path = write_jsonl([handoff(), bad])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "worker timestamps out of order",
    )
    print("PASS: impossible worker timestamp order fails closed")


def test_accepted_timestamp_race_allows_null_queue_wait():
    raced = completion()
    raced["accepted_ns"] = 130
    raced["worker_start_ns"] = 120
    raced["submit_to_worker_start_ms"] = 0.00002
    raced["queue_wait_after_accept_ms"] = None

    raced_handoff = handoff()
    raced_handoff["accepted_ns"] = 130
    raced_handoff["submit_block_ms"] = 0.00003

    path = write_jsonl([raced_handoff, raced])
    pairs = validate_and_pair(load_f3_observations([path]))

    assert len(pairs) == 1
    print("PASS: accepted-timestamp race preserves unknown queue wait")


def test_nonrace_null_queue_wait_fails_closed():
    bad = completion()
    bad["queue_wait_after_accept_ms"] = None
    path = write_jsonl([handoff(), bad])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "queue_wait_after_accept_ms unexpectedly null",
    )
    print("PASS: unexplained null queue wait fails closed")


def test_partial_observer_provenance_fails_closed():
    bad = handoff()
    bad["previous_observer_callback_ms"] = 0.1
    path = write_jsonl([bad, completion()])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "previous-observer provenance must be entirely null or entirely populated",
    )
    print("PASS: partial observer provenance fails closed")


def set_previous(record, previous):
    record["previous_observer_callback_ms"] = 0.1
    record["previous_observer_event_type"] = previous["type"].removeprefix("f3_")
    record["previous_observer_batch_id"] = previous["batch_id"]
    return record


def test_two_worker_epochs_can_reuse_batch_id():
    first_handoff = handoff(1)
    first_completion = set_previous(completion(1), first_handoff)

    second_handoff = handoff(1)
    second_handoff["submit_start_ns"] = 1000
    second_handoff["accepted_ns"] = 1010
    second_completion = completion(1)
    second_completion["submit_start_ns"] = 1000
    second_completion["accepted_ns"] = 1010
    second_completion["worker_start_ns"] = 1020
    second_completion["worker_end_ns"] = 1120
    second_completion = set_previous(second_completion, second_handoff)

    path = write_jsonl(
        [
            first_handoff,
            first_completion,
            second_handoff,
            second_completion,
        ]
    )

    observations = load_f3_observations([path])
    epochs = partition_worker_epochs(observations)
    pairs = validate_and_pair(observations)

    assert len(epochs) == 2
    assert len(pairs) == 2
    assert [(pair["epoch_id"], pair["batch_id"]) for pair in pairs] == [
        (1, 1),
        (2, 1),
    ]
    print("PASS: batch_id reuse across worker epochs cannot cross-pair")


def test_broken_provenance_chain_fails_closed():
    first_handoff = handoff(1)
    first_completion = completion(1)
    first_completion["previous_observer_event_type"] = "persistence_complete"
    first_completion["previous_observer_batch_id"] = 999

    path = write_jsonl([first_handoff, first_completion])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "broken F3 previous-observer provenance chain",
    )
    print("PASS: broken previous-observer provenance chain fails closed")


def test_mid_epoch_fragment_fails_closed():
    first_handoff = handoff(1)
    fragment = set_previous(completion(1), first_handoff)
    path = write_jsonl([fragment])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "mid-epoch fragment",
    )
    print("PASS: mid-epoch fragment fails closed")


def test_epoch_must_restart_at_batch_one():
    bad_start = handoff(7)
    bad_completion = set_previous(completion(7), bad_start)
    path = write_jsonl([bad_start, bad_completion])

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "does not restart at batch_id=1",
    )
    print("PASS: worker epoch must restart at batch_id=1")


def test_second_epoch_must_restart_at_batch_one():
    first_handoff = handoff(1)
    first_completion = set_previous(completion(1), first_handoff)

    bad_start = handoff(2)
    bad_completion = completion(2)
    bad_completion = set_previous(bad_completion, bad_start)

    path = write_jsonl(
        [first_handoff, first_completion, bad_start, bad_completion]
    )

    expect_runtime_error(
        lambda: validate_and_pair(load_f3_observations([path])),
        "worker epoch 2 does not restart at batch_id=1",
    )
    print("PASS: later worker epoch must restart at batch_id=1")


def test_invalid_json_fails_closed():
    directory = Path(tempfile.mkdtemp())
    path = directory / "telemetry_bad.jsonl"
    path.write_text('{"type":"f3_persistence_handoff"\n')

    expect_runtime_error(
        lambda: load_f3_observations([path]),
        "invalid JSON",
    )
    print("PASS: invalid JSON fails closed")


if __name__ == "__main__":
    test_load_filters_unrelated_telemetry()
    test_valid_pair_passes()
    test_gate2_summary_preserves_measurement_boundaries()
    test_gate2_summary_exposes_failed_completion_without_dropping_timing()
    test_gate2_summary_preserves_unknown_queue_wait()
    test_distribution_percentile_definition_is_deterministic()
    test_json_output_is_deterministic_and_matches_summary()
    test_missing_completion_fails_closed()
    test_duplicate_handoff_fails_closed()
    test_missing_entire_batch_id_fails_closed()
    test_pair_identity_mismatch_fails_closed()
    test_accounting_mismatch_fails_closed()
    test_missing_required_field_fails_closed()
    test_timestamp_duration_mismatch_fails_closed()
    test_queue_capacity_mismatch_fails_closed()
    test_queue_depth_over_capacity_fails_closed()
    test_worker_timestamp_order_fails_closed()
    test_accepted_timestamp_race_allows_null_queue_wait()
    test_nonrace_null_queue_wait_fails_closed()
    test_partial_observer_provenance_fails_closed()
    test_two_worker_epochs_can_reuse_batch_id()
    test_broken_provenance_chain_fails_closed()
    test_mid_epoch_fragment_fails_closed()
    test_epoch_must_restart_at_batch_one()
    test_second_epoch_must_restart_at_batch_one()
    test_invalid_json_fails_closed()

    print()
    print("All F3 Gate-2 analyzer structural tests passed.")
