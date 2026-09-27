"""
F3 Gate-2 Primary Population Preparation

Validates complete worker-epoch F3 telemetry with the frozen G2-8A
validate_and_pair() contract, then selects an inclusive primary batch range
only after structural validation succeeds.

This helper does not determine the production endpoint N, inspect timestamps to
choose N, alter the frozen analyzer, or adjudicate Gate-2.
"""

import json
from pathlib import Path

from L1_CORE.market_data_platform.research.analyze_f3_gate2 import (
    load_f3_observations,
    summarize_gate2,
    validate_and_pair,
)


def select_primary_population(observations, pairs, start_batch_id, end_batch_id):
    if (
        isinstance(start_batch_id, bool)
        or not isinstance(start_batch_id, int)
        or start_batch_id < 1
    ):
        raise RuntimeError("FATAL: start_batch_id must be a positive integer")

    if (
        isinstance(end_batch_id, bool)
        or not isinstance(end_batch_id, int)
        or end_batch_id < start_batch_id
    ):
        raise RuntimeError(
            "FATAL: end_batch_id must be an integer >= start_batch_id"
        )

    epoch_ids = {pair["epoch_id"] for pair in pairs}
    if len(epoch_ids) != 1:
        raise RuntimeError(
            "FATAL: primary selection requires exactly one validated worker epoch"
        )

    epoch_id = next(iter(epoch_ids))

    primary_pairs = [
        pair
        for pair in pairs
        if pair["epoch_id"] == epoch_id
        and start_batch_id <= pair["batch_id"] <= end_batch_id
    ]

    expected_ids = list(range(start_batch_id, end_batch_id + 1))
    actual_ids = [pair["batch_id"] for pair in primary_pairs]

    if actual_ids != expected_ids:
        raise RuntimeError(
            "FATAL: validated primary range is incomplete; "
            f"expected={expected_ids}, got={actual_ids}"
        )

    primary_ids = set(actual_ids)
    primary_observations = [
        record
        for record in observations
        if record["batch_id"] in primary_ids
    ]

    expected_observation_count = 2 * len(primary_pairs)
    if len(primary_observations) != expected_observation_count:
        raise RuntimeError(
            "FATAL: primary observation selection is inconsistent with "
            "validated handoff/completion pairs"
        )

    return primary_observations, primary_pairs


def prepare_primary(paths, start_batch_id, end_batch_id):
    observations = load_f3_observations(paths)

    # Structural validation always occurs on the complete supplied epoch first.
    pairs = validate_and_pair(observations)

    primary_observations, primary_pairs = select_primary_population(
        observations,
        pairs,
        start_batch_id,
        end_batch_id,
    )

    return summarize_gate2(primary_observations, primary_pairs)


def main(paths, start_batch_id, end_batch_id):
    summary = prepare_primary(paths, start_batch_id, end_batch_id)
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Validate complete F3 worker-epoch telemetry, then summarize an "
            "inclusive post-validation primary batch range."
        )
    )
    parser.add_argument(
        "telemetry",
        nargs="+",
        type=Path,
        help="Complete worker-epoch telemetry JSONL file(s).",
    )
    parser.add_argument(
        "--start-batch",
        type=int,
        required=True,
        help="Inclusive primary start batch_id.",
    )
    parser.add_argument(
        "--end-batch",
        type=int,
        required=True,
        help="Inclusive primary end batch_id N.",
    )

    args = parser.parse_args()
    main(args.telemetry, args.start_batch, args.end_batch)
