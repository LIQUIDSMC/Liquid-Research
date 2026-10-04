"""
LRS-3 Candidate D — D0 Time-Conditioning Feasibility Diagnostic

Candidate-selection diagnostic only.

Controlling predeclaration:
    /tmp/lrs3_candidate_d_d0_predeclared_20261004.txt

Frozen predeclaration SHA256:
    9fce77d46174cd22be28bcae5d244de45cb404222f74e5c30539cb90f78c68f5

D0 is NOT H2.
D0 is NOT a strategy test.
D0 is NOT an execution, cost, or profitability test.

Implementation invariant:
    For each instrument-day, compute_screen() runs on the complete
    instrument-day. For each horizon, build_comparative_population()
    then constructs the complete horizon-specific eligible population.
    rank_deciles() assigns deciles across that complete population.
    Only AFTER those whole-day decile assignments are frozen are
    observations partitioned into D0-HOUR or D0-SESSION.

The candidate H2 market-outcome clean reserve beginning 2026-09-04
is prohibited. This analyzer hard-rejects any matrix date on or after
that boundary.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    HORIZONS,
    LOOKBACK_SECONDS,
    SAMPLE_EVERY_NTH,
    compute_screen,
    rank_deciles,
    validate_sorted_arrays,
)

from L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen import (
    CANONICAL_TRADES_ROOT,
    _day_bounds_ms,
    _resolve_source_partitions,
    build_comparative_population,
    count_target_rows,
    load_instrument_day,
    validate_day_integrity,
)


PREDECLARATION_PATH = Path(
    "/tmp/lrs3_candidate_d_d0_predeclared_20261004.txt"
)
PREDECLARATION_SHA256 = (
    "9fce77d46174cd22be28bcae5d244de45cb404222f74e5c30539cb90f78c68f5"
)

SEALED_RESERVE_START = dt.date(2026, 9, 4)

BLOCK_A_DATES = (
    [f"2026-07-{day:02d}" for day in range(22, 32)]
    + [f"2026-08-{day:02d}" for day in range(1, 10)]
)

BLOCK_B_DATES = [
    "2026-08-26",
    "2026-08-27",
    "2026-08-28",
    "2026-08-29",
    "2026-08-30",
    "2026-09-03",
]

FROZEN_DATES = BLOCK_A_DATES + BLOCK_B_DATES
INSTRUMENTS = ["BTC-USD", "ETH-USD"]

# Date-paired execution order, identical in population to the frozen
# expanded-validation matrix.
FROZEN_MATRIX = [
    (instrument, date_str)
    for date_str in FROZEN_DATES
    for instrument in INSTRUMENTS
]

PRIMARY_HORIZON = 60
SECONDARY_HORIZONS = [5, 15, 30]

SIGN_CONSISTENCY_THRESHOLD = 33

NY_TZ = ZoneInfo("America/New_York")

DEFAULT_OUTPUT_DIR = Path("/tmp/lrs3_candidate_d_d0_results")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_predeclaration() -> None:
    if not PREDECLARATION_PATH.is_file():
        raise RuntimeError(
            f"Frozen D0 predeclaration is missing: {PREDECLARATION_PATH}"
        )

    actual = sha256_file(PREDECLARATION_PATH)
    if actual != PREDECLARATION_SHA256:
        raise RuntimeError(
            "Frozen D0 predeclaration SHA256 mismatch. "
            f"expected={PREDECLARATION_SHA256} actual={actual}. "
            "Refusing to proceed."
        )


def verify_frozen_matrix() -> None:
    if len(FROZEN_DATES) != 25:
        raise RuntimeError(
            f"Expected exactly 25 frozen dates, found {len(FROZEN_DATES)}."
        )

    if len(FROZEN_MATRIX) != 50:
        raise RuntimeError(
            f"Expected exactly 50 instrument-days, found {len(FROZEN_MATRIX)}."
        )

    if len(set(FROZEN_DATES)) != len(FROZEN_DATES):
        raise RuntimeError("Duplicate date found in frozen D0 matrix.")

    if len(set(FROZEN_MATRIX)) != len(FROZEN_MATRIX):
        raise RuntimeError("Duplicate instrument-day found in frozen D0 matrix.")

    expected_instruments = {"BTC-USD", "ETH-USD"}
    if set(INSTRUMENTS) != expected_instruments:
        raise RuntimeError(
            f"Unexpected instrument set: {INSTRUMENTS}. Refusing to proceed."
        )

    for instrument, date_str in FROZEN_MATRIX:
        if instrument not in expected_instruments:
            raise RuntimeError(
                f"Unauthorized instrument in D0 matrix: {instrument}"
            )

        parsed = dt.date.fromisoformat(date_str)

        # Positive hard boundary: sealed-reserve dates are forbidden,
        # not merely absent from the current list.
        if parsed >= SEALED_RESERVE_START:
            raise RuntimeError(
                "SEALED RESERVE VIOLATION: "
                f"{instrument} {date_str} is on/after "
                f"{SEALED_RESERVE_START.isoformat()}."
            )


def prepare_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise RuntimeError(
                f"Output path exists and is not a directory: {output_dir}"
            )

        if any(output_dir.iterdir()):
            raise RuntimeError(
                f"Output directory already exists and is non-empty: {output_dir}. "
                "Refusing to mix or overwrite D0 evidence."
            )
    else:
        output_dir.mkdir(parents=True, exist_ok=False)


def get_git_sha() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def load_complete_instrument_day(
    instrument: str,
    date_str: str,
):
    """
    Reuse the frozen multi-partition loader contract.

    The research day is defined by trade_time UTC boundaries. Previous,
    target, and next storage partitions are resolved by the existing runner.
    """
    parsed = dt.date.fromisoformat(date_str)
    if parsed >= SEALED_RESERVE_START:
        raise RuntimeError(
            f"SEALED RESERVE VIOLATION before load: {instrument} {date_str}"
        )

    start_ms, end_ms = _day_bounds_ms(date_str)
    partitions = _resolve_source_partitions(date_str)

    n_target, partition_stats = count_target_rows(
        partitions,
        instrument,
        start_ms,
        end_ms,
    )

    if n_target == 0:
        raise RuntimeError(
            f"Zero in-range rows for {instrument} {date_str}."
        )

    trade_time, trade_id, price, quantity, is_buyer_maker = (
        load_instrument_day(
            partitions,
            instrument,
            start_ms,
            end_ms,
            n_target,
        )
    )

    validate_day_integrity(
        trade_time,
        price,
        quantity,
        start_ms,
        end_ms,
    )

    order = np.lexsort((trade_id, trade_time))

    trade_time = trade_time[order]
    trade_id = trade_id[order]
    price = price[order]
    quantity = quantity[order]
    is_buyer_maker = is_buyer_maker[order]

    validate_sorted_arrays(
        trade_time,
        trade_id,
        price,
        quantity,
        is_buyer_maker,
    )

    return (
        trade_time,
        trade_id,
        price,
        quantity,
        is_buyer_maker,
        partition_stats,
    )


def hour_masks(sample_trade_time: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    D0-HOUR:
      IN      minute [45,60) or [0,15)
      CONTROL minute [15,45)

    sample_trade_time is epoch milliseconds.
    """
    minute_of_hour = (
        (sample_trade_time // (60 * 1000)) % 60
    ).astype(np.int64)

    in_window = (minute_of_hour >= 45) | (minute_of_hour < 15)
    control = (minute_of_hour >= 15) & (minute_of_hour < 45)

    if np.any(in_window & control):
        raise RuntimeError("D0-HOUR masks overlap.")

    if not np.all(in_window | control):
        raise RuntimeError("D0-HOUR masks are not exhaustive.")

    return in_window, control


def session_masks(
    sample_trade_time: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    D0-SESSION:
      IN      09:30 <= America/New_York local time < 16:00
      CONTROL all other observations.

    Uses timezone-aware conversion via zoneinfo.
    """
    in_window = np.zeros(len(sample_trade_time), dtype=bool)

    session_start_minutes = 9 * 60 + 30
    session_end_minutes = 16 * 60

    for i, epoch_ms in enumerate(sample_trade_time):
        utc_dt = dt.datetime.fromtimestamp(
            int(epoch_ms) / 1000.0,
            tz=dt.timezone.utc,
        )
        ny_dt = utc_dt.astimezone(NY_TZ)
        local_minutes = ny_dt.hour * 60 + ny_dt.minute

        in_window[i] = (
            session_start_minutes
            <= local_minutes
            < session_end_minutes
        )

    control = ~in_window

    if np.any(in_window & control):
        raise RuntimeError("D0-SESSION masks overlap.")

    if not np.all(in_window | control):
        raise RuntimeError("D0-SESSION masks are not exhaustive.")

    return in_window, control


def partition_edge(
    deciles: np.ndarray,
    returns: np.ndarray,
    partition_mask: np.ndarray,
) -> dict:
    """
    Calculate D9-D0 within one already-partitioned subset.

    IMPORTANT: deciles were assigned BEFORE this function is called,
    across the complete horizon-eligible instrument-day population.
    """
    d0_mask = partition_mask & (deciles == 0)
    d9_mask = partition_mask & (deciles == 9)

    n_d0 = int(d0_mask.sum())
    n_d9 = int(d9_mask.sum())

    if n_d0 == 0 or n_d9 == 0:
        return {
            "valid": False,
            "n_d0": n_d0,
            "n_d9": n_d9,
            "d0_mean_return": None,
            "d9_mean_return": None,
            "edge_bp": None,
        }

    d0_mean = float(np.mean(returns[d0_mask]))
    d9_mean = float(np.mean(returns[d9_mask]))
    edge_bp = float((d9_mean - d0_mean) * 10000.0)

    return {
        "valid": True,
        "n_d0": n_d0,
        "n_d9": n_d9,
        "d0_mean_return": d0_mean,
        "d9_mean_return": d9_mean,
        "edge_bp": edge_bp,
    }


def evaluate_mechanism(
    deciles: np.ndarray,
    returns: np.ndarray,
    in_mask: np.ndarray,
    control_mask: np.ndarray,
) -> dict:
    in_result = partition_edge(deciles, returns, in_mask)
    control_result = partition_edge(deciles, returns, control_mask)

    valid = bool(in_result["valid"] and control_result["valid"])

    if not valid:
        delta_bp = None
    else:
        delta_bp = float(
            in_result["edge_bp"] - control_result["edge_bp"]
        )

    return {
        "valid": valid,
        "in_window": in_result,
        "control": control_result,
        "delta_bp": delta_bp,
    }


def analyze_instrument_day(
    instrument: str,
    date_str: str,
) -> dict:
    (
        trade_time,
        trade_id,
        price,
        quantity,
        is_buyer_maker,
        partition_stats,
    ) = load_complete_instrument_day(instrument, date_str)

    # Full instrument-day kernel execution occurs before ANY temporal split.
    screen = compute_screen(
        trade_time,
        trade_id,
        price,
        quantity,
        is_buyer_maker,
    )

    horizon_results = {}

    for horizon in HORIZONS:
        # CRITICAL:
        # Build the complete horizon-specific eligible population first.
        # This applies:
        #   common_eligible & ~np.isnan(return_h)
        # before any temporal partitioning.
        pop = build_comparative_population(screen, horizon)

        if pop["n"] <= 0:
            raise RuntimeError(
                f"Zero comparative observations for "
                f"{instrument} {date_str} horizon={horizon}s."
            )

        # Whole-day deciles are assigned once for this horizon.
        deciles = rank_deciles(
            pop["imbalance"],
            pop["sample_trade_time"],
            pop["sample_trade_id"],
        )

        if len(deciles) != pop["n"]:
            raise RuntimeError(
                f"Decile length mismatch for "
                f"{instrument} {date_str} horizon={horizon}s."
            )

        if np.any((deciles < 0) | (deciles > 9)):
            raise RuntimeError(
                f"Invalid decile assignment for "
                f"{instrument} {date_str} horizon={horizon}s."
            )

        # ONLY AFTER whole-day ranking do temporal masks get constructed.
        hour_in, hour_control = hour_masks(pop["sample_trade_time"])
        session_in, session_control = session_masks(
            pop["sample_trade_time"]
        )

        hour_result = evaluate_mechanism(
            deciles,
            pop["return"],
            hour_in,
            hour_control,
        )

        session_result = evaluate_mechanism(
            deciles,
            pop["return"],
            session_in,
            session_control,
        )

        horizon_results[str(horizon)] = {
            "eligible_n": int(pop["n"]),
            "hour": hour_result,
            "session": session_result,
        }

    return {
        "instrument": instrument,
        "date": date_str,
        "total_in_range_rows": int(len(trade_time)),
        "source_partitions": partition_stats,
        "horizons": horizon_results,
    }


def finite_stats(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=np.float64)

    if len(arr) == 0:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }

    if not np.isfinite(arr).all():
        raise RuntimeError("Non-finite value encountered in D0 aggregation.")

    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def aggregate_mechanism(
    instrument_days: list[dict],
    mechanism: str,
    horizon: int,
) -> dict:
    rows = []

    for record in instrument_days:
        result = record["horizons"][str(horizon)][mechanism]

        rows.append({
            "instrument": record["instrument"],
            "date": record["date"],
            "valid": bool(result["valid"]),
            "delta_bp": result["delta_bp"],
            "in_edge_bp": result["in_window"]["edge_bp"],
            "control_edge_bp": result["control"]["edge_bp"],
            "in_n_d0": result["in_window"]["n_d0"],
            "in_n_d9": result["in_window"]["n_d9"],
            "control_n_d0": result["control"]["n_d0"],
            "control_n_d9": result["control"]["n_d9"],
        })

    valid_rows = [row for row in rows if row["valid"]]

    deltas = [float(row["delta_bp"]) for row in valid_rows]
    btc_deltas = [
        float(row["delta_bp"])
        for row in valid_rows
        if row["instrument"] == "BTC-USD"
    ]
    eth_deltas = [
        float(row["delta_bp"])
        for row in valid_rows
        if row["instrument"] == "ETH-USD"
    ]

    in_edges = [
        float(row["in_edge_bp"])
        for row in valid_rows
    ]
    control_edges = [
        float(row["control_edge_bp"])
        for row in valid_rows
    ]

    positive_count = int(sum(value > 0 for value in deltas))

    summary = {
        "mechanism": mechanism,
        "horizon_s": horizon,
        "total_instrument_days": len(rows),
        "valid_instrument_days": len(valid_rows),
        "invalid_instrument_days": len(rows) - len(valid_rows),
        "positive_delta_count": positive_count,
        "delta_bp": finite_stats(deltas),
        "btc_delta_bp": finite_stats(btc_deltas),
        "eth_delta_bp": finite_stats(eth_deltas),
        "in_window_edge_bp": finite_stats(in_edges),
        "control_edge_bp": finite_stats(control_edges),
        "instrument_days": rows,
    }

    return summary


def evaluate_primary_gates(summary: dict) -> dict:
    """
    Apply the frozen five-gate rule at 60 seconds.

    Any structurally invalid instrument-day causes the mechanism to fail
    closed because the frozen gates are defined across all 50 days.
    """
    rows = summary["instrument_days"]
    valid_rows = [row for row in rows if row["valid"]]

    structural_complete = len(valid_rows) == 50

    if not structural_complete:
        return {
            "structural_complete": False,
            "gate_1_sign_consistency": False,
            "gate_2_combined_median": False,
            "gate_3_btc_median": False,
            "gate_4_eth_median": False,
            "gate_5_leave_one_out_mean": False,
            "positive_delta_count": summary["positive_delta_count"],
            "combined_median_delta_bp": None,
            "btc_median_delta_bp": None,
            "eth_median_delta_bp": None,
            "minimum_leave_one_out_mean_delta_bp": None,
            "pass": False,
            "decision": "FAIL / PARK",
            "reason": (
                "One or more instrument-days were structurally invalid; "
                "frozen D0 rule requires fail-closed treatment."
            ),
        }

    deltas = np.asarray(
        [float(row["delta_bp"]) for row in rows],
        dtype=np.float64,
    )

    btc = np.asarray(
        [
            float(row["delta_bp"])
            for row in rows
            if row["instrument"] == "BTC-USD"
        ],
        dtype=np.float64,
    )

    eth = np.asarray(
        [
            float(row["delta_bp"])
            for row in rows
            if row["instrument"] == "ETH-USD"
        ],
        dtype=np.float64,
    )

    if len(deltas) != 50 or len(btc) != 25 or len(eth) != 25:
        raise RuntimeError(
            "Primary D0 aggregation population mismatch."
        )

    positive_count = int(np.sum(deltas > 0))

    combined_median = float(np.median(deltas))
    btc_median = float(np.median(btc))
    eth_median = float(np.median(eth))

    loo_means = np.asarray(
        [
            np.mean(np.delete(deltas, i))
            for i in range(len(deltas))
        ],
        dtype=np.float64,
    )

    minimum_loo_mean = float(np.min(loo_means))

    gate_1 = positive_count >= SIGN_CONSISTENCY_THRESHOLD
    gate_2 = combined_median > 0
    gate_3 = btc_median > 0
    gate_4 = eth_median > 0
    gate_5 = bool(np.all(loo_means >= 0))

    passed = bool(
        gate_1
        and gate_2
        and gate_3
        and gate_4
        and gate_5
    )

    return {
        "structural_complete": True,
        "gate_1_sign_consistency": bool(gate_1),
        "gate_2_combined_median": bool(gate_2),
        "gate_3_btc_median": bool(gate_3),
        "gate_4_eth_median": bool(gate_4),
        "gate_5_leave_one_out_mean": bool(gate_5),
        "positive_delta_count": positive_count,
        "combined_median_delta_bp": combined_median,
        "btc_median_delta_bp": btc_median,
        "eth_median_delta_bp": eth_median,
        "minimum_leave_one_out_mean_delta_bp": minimum_loo_mean,
        "pass": passed,
        "decision": (
            "PASS / FURTHER INVESTIGATION"
            if passed
            else "FAIL / PARK"
        ),
        "reason": (
            "All five frozen primary gates passed."
            if passed
            else "At least one frozen primary gate failed."
        ),
    }


def build_aggregate(instrument_days: list[dict]) -> dict:
    mechanisms = ["hour", "session"]

    output = {
        "primary_horizon_s": PRIMARY_HORIZON,
        "secondary_horizons_s": SECONDARY_HORIZONS,
        "mechanisms": {},
    }

    for mechanism in mechanisms:
        by_horizon = {}

        for horizon in HORIZONS:
            summary = aggregate_mechanism(
                instrument_days,
                mechanism,
                horizon,
            )

            if horizon == PRIMARY_HORIZON:
                summary["primary_gates"] = evaluate_primary_gates(summary)
            else:
                summary["primary_gates"] = None

            by_horizon[str(horizon)] = summary

        output["mechanisms"][mechanism] = by_horizon

    return output


def write_json_atomic(path: Path, payload: dict) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_path, path)


def print_primary_result(aggregate: dict) -> None:
    print("\n===== D0 PRIMARY RESULT — 60s =====")

    for mechanism in ["hour", "session"]:
        summary = aggregate["mechanisms"][mechanism][
            str(PRIMARY_HORIZON)
        ]
        gates = summary["primary_gates"]

        print(f"\n{mechanism.upper()}")
        print(
            f"  valid instrument-days: "
            f"{summary['valid_instrument_days']}/50"
        )
        print(
            f"  positive delta count: "
            f"{summary['positive_delta_count']}/50"
        )
        print(
            f"  gate1 sign consistency: "
            f"{gates['gate_1_sign_consistency']}"
        )
        print(
            f"  gate2 combined median > 0: "
            f"{gates['gate_2_combined_median']}"
        )
        print(
            f"  gate3 BTC median > 0: "
            f"{gates['gate_3_btc_median']}"
        )
        print(
            f"  gate4 ETH median > 0: "
            f"{gates['gate_4_eth_median']}"
        )
        print(
            f"  gate5 all LOO means >= 0: "
            f"{gates['gate_5_leave_one_out_mean']}"
        )
        print(f"  DECISION: {gates['decision']}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "LRS-3 Candidate D D0 time-conditioning feasibility diagnostic"
        )
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=(
            "New/fresh D0 evidence directory. Existing non-empty "
            "directories are refused."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    print("===== LRS-3 CANDIDATE D — D0 =====")
    print("Verifying frozen predeclaration...")
    verify_predeclaration()
    print(
        f"PREDECLARATION SHA256 PASS: {PREDECLARATION_SHA256}"
    )

    print("Verifying frozen research matrix and sealed-reserve boundary...")
    verify_frozen_matrix()
    print("FROZEN MATRIX PASS: 25 dates x 2 instruments = 50")
    print(
        "SEALED RESERVE HARD BOUNDARY PASS: "
        "no date >= 2026-09-04"
    )

    if HORIZONS != [5, 15, 30, 60]:
        raise RuntimeError(
            f"Frozen kernel horizons changed unexpectedly: {HORIZONS}"
        )

    if SAMPLE_EVERY_NTH != 20:
        raise RuntimeError(
            "Frozen kernel SAMPLE_EVERY_NTH changed unexpectedly: "
            f"{SAMPLE_EVERY_NTH}"
        )

    if LOOKBACK_SECONDS != 10.0:
        raise RuntimeError(
            "Frozen kernel LOOKBACK_SECONDS changed unexpectedly: "
            f"{LOOKBACK_SECONDS}"
        )

    print(f"Canonical trades root: {CANONICAL_TRADES_ROOT}")

    # Output directory is established only after all frozen controls pass.
    prepare_output_dir(output_dir)

    repo_sha = get_git_sha()

    run_manifest = {
        "diagnostic": "LRS3_Candidate_D_D0_Time_Conditioning",
        "predeclaration_path": str(PREDECLARATION_PATH),
        "predeclaration_sha256": PREDECLARATION_SHA256,
        "repo_git_sha": repo_sha,
        "canonical_trades_root": str(CANONICAL_TRADES_ROOT),
        "sealed_reserve_start": SEALED_RESERVE_START.isoformat(),
        "sealed_reserve_queried": False,
        "frozen_dates": FROZEN_DATES,
        "instruments": INSTRUMENTS,
        "instrument_day_count": len(FROZEN_MATRIX),
        "lookback_seconds": LOOKBACK_SECONDS,
        "sample_every_nth": SAMPLE_EVERY_NTH,
        "horizons_s": HORIZONS,
        "primary_horizon_s": PRIMARY_HORIZON,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    write_json_atomic(
        output_dir / "run_manifest.json",
        run_manifest,
    )

    instrument_days = []

    total = len(FROZEN_MATRIX)
    for index, (instrument, date_str) in enumerate(
        FROZEN_MATRIX,
        start=1,
    ):
        print(
            f"\n===== {index}/{total}: "
            f"{instrument} {date_str} ====="
        )

        t0 = time.time()
        record = analyze_instrument_day(instrument, date_str)
        record["elapsed_seconds"] = float(time.time() - t0)

        instrument_days.append(record)

        print(
            f"COMPLETE: {instrument} {date_str} "
            f"in {record['elapsed_seconds']:.1f}s"
        )

    if len(instrument_days) != 50:
        raise RuntimeError(
            f"Expected 50 completed instrument-days, "
            f"found {len(instrument_days)}."
        )

    aggregate = build_aggregate(instrument_days)

    evidence = {
        "manifest": run_manifest,
        "instrument_days": instrument_days,
        "aggregate": aggregate,
        "completed_utc": dt.datetime.now(
            dt.timezone.utc
        ).isoformat(),
    }

    write_json_atomic(
        output_dir / "d0_results.json",
        evidence,
    )

    print_primary_result(aggregate)

    print("\n===== D0 BOUNDARY =====")
    print("sealed_reserve_queried=NO")
    print("D0 is candidate-selection evidence only.")
    print("No H2 conclusion is authorized by this analyzer.")


if __name__ == "__main__":
    main()
