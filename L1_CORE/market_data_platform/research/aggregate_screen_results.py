"""
Market Data Platform -- Aggregate Analysis of the 8-Date Frozen Screen
market_data_platform/research/aggregate_screen_results.py

Reads the 8 existing per-instrument-day JSON results (already
produced by run_trade_flow_vs_momentum_screen.py / run_batch_screen.py)
and computes the predefined aggregate statistics. Does NOT re-run any
Parquet loading or the compute_screen() kernel -- pure post-hoc
analysis of already-computed results.

Fail-closed on dataset identity: this script requires EXACTLY the
frozen 8 (instrument, date) pairs -- no more, no less, no duplicates.
A missing frozen date, an unexpected extra file, or a duplicate
(instrument, date) all cause an immediate hard failure before any
statistics are computed, since a silently-wrong input set would make
every downstream number meaningless.

Reports, for BOTH imbalance and momentum, at every horizon (5/15/30/60s):
  - D9-D0 per instrument-day
  - n per instrument-day
  - full decile shape per instrument-day
  - unweighted mean, median, min, max of D9-D0 across the 8 days
    (explicitly UNWEIGHTED -- each instrument-day counts once,
    regardless of its sample size, so high-volume days do not
    silently dominate the aggregate)
  - BTC-only and ETH-only sub-summaries
  - sign consistency (count of positive D9-D0 out of 8)
  - leave-one-date-out sensitivity AT EVERY HORIZON (5/15/30/60s),
    not only 60s
  - explicit quantification of ETH-USD 2026-08-22's influence

This is a research screen report only -- no promotion thresholds,
no strategy selection, no costs/sizing/execution logic.

Usage:
    python3 -m L1_CORE.market_data_platform.research.aggregate_screen_results \
        --results-dir /tmp/screen_results
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

HORIZONS = [5, 15, 30, 60]
FEATURES = ["imbalance", "momentum"]

FROZEN_MATRIX = {
    ("BTC-USD", "2026-08-10"), ("BTC-USD", "2026-08-18"),
    ("BTC-USD", "2026-08-22"), ("BTC-USD", "2026-08-25"),
    ("ETH-USD", "2026-08-10"), ("ETH-USD", "2026-08-18"),
    ("ETH-USD", "2026-08-22"), ("ETH-USD", "2026-08-25"),
}


def load_all_results(results_dir):
    """
    Loads all *.json files in results_dir and fail-closed validates
    that the set of (instrument, date) pairs found is EXACTLY the
    frozen 8-pair matrix -- no missing dates, no unexpected extra
    files, no duplicates.

    Raises:
        SystemExit: with a clear, specific message on any mismatch
        (missing, extra, or duplicate), before any statistics are
        computed.
    """
    results_dir = Path(results_dir)
    files = sorted(results_dir.glob("*.json"))

    loaded = []
    seen_pairs = []
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        pair = (data["instrument"], data["date"])
        seen_pairs.append(pair)
        loaded.append((pair, data, f))

    seen_set = set(seen_pairs)
    duplicates = [p for p in seen_set if seen_pairs.count(p) > 1]

    missing = FROZEN_MATRIX - seen_set
    unexpected = seen_set - FROZEN_MATRIX

    problems = []
    if duplicates:
        problems.append(f"DUPLICATE (instrument, date) pairs found: {duplicates}")
    if missing:
        problems.append(f"MISSING frozen (instrument, date) pairs: {sorted(missing)}")
    if unexpected:
        problems.append(f"UNEXPECTED (instrument, date) pairs not in frozen matrix: {sorted(unexpected)}")

    if problems:
        print("===== FROZEN DATASET VALIDATION FAILED =====", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(f"\nExpected exactly these {len(FROZEN_MATRIX)} pairs:", file=sys.stderr)
        for pair in sorted(FROZEN_MATRIX):
            print(f"  {pair}", file=sys.stderr)
        print(f"\nFound {len(seen_pairs)} files in {results_dir}: {sorted(seen_pairs)}", file=sys.stderr)
        sys.exit(1)

    validate_result_structure(loaded)

    return [data for (_, data, _) in loaded]


def validate_result_structure(loaded):
    """
    Confirms each loaded result contains results_by_horizon for
    every frozen horizon, and imbalance/momentum with a numeric
    d9_minus_d0_bp and a decile_summary for each -- fails clearly,
    naming the exact file and field, rather than raising a bare
    KeyError deep inside aggregation.
    """
    for pair, data, f in loaded:
        if "results_by_horizon" not in data:
            _fail_structure(f, "missing top-level 'results_by_horizon'")

        for h in HORIZONS:
            h_key = str(h)
            if h_key not in data["results_by_horizon"]:
                _fail_structure(f, f"missing horizon '{h_key}' in results_by_horizon")

            horizon_data = data["results_by_horizon"][h_key]
            if "n" not in horizon_data:
                _fail_structure(f, f"missing 'n' for horizon {h_key}")

            for feat in FEATURES:
                if feat not in horizon_data:
                    _fail_structure(f, f"missing feature '{feat}' for horizon {h_key}")
                feat_data = horizon_data[feat]
                if "d9_minus_d0_bp" not in feat_data or feat_data["d9_minus_d0_bp"] is None:
                    _fail_structure(f, f"missing or null d9_minus_d0_bp for {feat} at horizon {h_key}")
                if "decile_summary" not in feat_data:
                    _fail_structure(f, f"missing decile_summary for {feat} at horizon {h_key}")


def _fail_structure(f, message):
    print(f"===== MALFORMED RESULT FILE =====", file=sys.stderr)
    print(f"  File: {f}", file=sys.stderr)
    print(f"  Problem: {message}", file=sys.stderr)
    sys.exit(1)


def build_d9_d0_table(all_results):
    table = {feat: {h: [] for h in HORIZONS} for feat in FEATURES}
    for r in all_results:
        instrument = r["instrument"]
        date = r["date"]
        for h in HORIZONS:
            horizon_data = r["results_by_horizon"][str(h)]
            n = horizon_data["n"]
            for feat in FEATURES:
                d9_d0_bp = horizon_data[feat]["d9_minus_d0_bp"]
                table[feat][h].append((instrument, date, d9_d0_bp, n))
    return table


def print_per_day_table(table):
    print("===== D9-D0 (BASIS POINTS) PER INSTRUMENT-DAY, ALL HORIZONS =====\n")
    for feat in FEATURES:
        print(f"--- FEATURE: {feat} ---")
        header = f"{'Instrument':<10}{'Date':<12}"
        for h in HORIZONS:
            header += f"{'n(' + str(h) + 's)':>10}{'D9-D0(' + str(h) + 's)':>14}"
        print(header)
        rows_by_key = {}
        for h in HORIZONS:
            for instrument, date, val, n in table[feat][h]:
                key = (instrument, date)
                rows_by_key.setdefault(key, {})[h] = (val, n)
        for (instrument, date), horizon_vals in sorted(rows_by_key.items()):
            row = f"{instrument:<10}{date:<12}"
            for h in HORIZONS:
                val, n = horizon_vals[h]
                row += f"{n:>10}{val:>14.4f}"
            print(row)
        print()


def compute_unweighted_stats(values):
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "n_days": len(values),
    }


def print_aggregate_stats(table):
    print("===== UNWEIGHTED AGGREGATE STATISTICS (ALL 8 DAYS) =====")
    print("(Each instrument-day counts once, regardless of its own sample size n)\n")
    for feat in FEATURES:
        print(f"--- FEATURE: {feat} ---")
        for h in HORIZONS:
            values = [v for (_, _, v, _) in table[feat][h]]
            stats = compute_unweighted_stats(values)
            positive_count = sum(1 for v in values if v > 0)
            print(f"  {h}s: mean={stats['mean']:+.4f}bp median={stats['median']:+.4f}bp "
                  f"min={stats['min']:+.4f}bp max={stats['max']:+.4f}bp "
                  f"sign_consistency={positive_count}/{stats['n_days']}")
        print()


def print_instrument_split(table):
    print("===== BTC-ONLY vs ETH-ONLY (UNWEIGHTED) =====\n")
    for feat in FEATURES:
        print(f"--- FEATURE: {feat} ---")
        for h in HORIZONS:
            btc_values = [v for (instr, _, v, _) in table[feat][h] if instr == "BTC-USD"]
            eth_values = [v for (instr, _, v, _) in table[feat][h] if instr == "ETH-USD"]
            btc_stats = compute_unweighted_stats(btc_values)
            eth_stats = compute_unweighted_stats(eth_values)
            print(f"  {h}s: BTC mean={btc_stats['mean']:+.4f}bp (n_days={btc_stats['n_days']}) | "
                  f"ETH mean={eth_stats['mean']:+.4f}bp (n_days={eth_stats['n_days']})")
        print()


def print_leave_one_out(table):
    print("===== LEAVE-ONE-DATE-OUT SENSITIVITY (ALL HORIZONS, unweighted mean) =====\n")
    for feat in FEATURES:
        print(f"--- FEATURE: {feat} ---")
        for h in HORIZONS:
            entries = table[feat][h]
            full_mean = statistics.mean([v for (_, _, v, _) in entries])
            print(f"  Horizon {h}s -- full 8-day mean: {full_mean:+.4f}bp")
            for i, (instrument, date, val, n) in enumerate(entries):
                remaining = [v for j, (_, _, v, _) in enumerate(entries) if j != i]
                remaining_mean = statistics.mean(remaining)
                shift = remaining_mean - full_mean
                print(f"    Excluding {instrument} {date} (its value: {val:+.4f}bp): "
                      f"mean becomes {remaining_mean:+.4f}bp (shift: {shift:+.4f}bp)")
            print()


def quantify_eth_aug22_influence(table):
    print("===== EXPLICIT ETH-USD 2026-08-22 INFLUENCE QUANTIFICATION =====\n")
    for feat in FEATURES:
        print(f"--- FEATURE: {feat} ---")
        for h in HORIZONS:
            entries = table[feat][h]
            eth_aug22_val = next(v for (instr, date, v, _) in entries if instr == "ETH-USD" and date == "2026-08-22")
            all_values = [v for (_, _, v, _) in entries]
            full_mean = statistics.mean(all_values)
            without = [v for (instr, date, v, _) in entries if not (instr == "ETH-USD" and date == "2026-08-22")]
            mean_without = statistics.mean(without)
            print(f"  {h}s: ETH-USD 2026-08-22 value={eth_aug22_val:+.4f}bp | "
                  f"full mean={full_mean:+.4f}bp | mean excluding this date={mean_without:+.4f}bp | "
                  f"shift caused by this single date={full_mean - mean_without:+.4f}bp")
        print()


def print_decile_shapes(all_results):
    print("===== FULL DECILE SHAPES (ALL INSTRUMENT-DAYS, ALL HORIZONS) =====\n")
    for r in sorted(all_results, key=lambda r: (r["instrument"], r["date"])):
        instrument = r["instrument"]
        date = r["date"]
        print(f"--- {instrument} {date} ---")
        for h in HORIZONS:
            horizon_data = r["results_by_horizon"][str(h)]
            for feat in FEATURES:
                deciles = horizon_data[feat]["decile_summary"]
                decile_str = " ".join(
                    f"D{d['decile']}:{d['mean_return_bp']:+.2f}" if d['mean_return_bp'] is not None else f"D{d['decile']}:NA"
                    for d in deciles
                )
                print(f"  {feat} {h}s: {decile_str}")
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    args = parser.parse_args()

    all_results = load_all_results(args.results_dir)
    print(f"Loaded and validated exactly {len(all_results)} frozen instrument-day result files "
          f"from {args.results_dir}\n")

    table = build_d9_d0_table(all_results)

    print_per_day_table(table)
    print_aggregate_stats(table)
    print_instrument_split(table)
    print_leave_one_out(table)
    quantify_eth_aug22_influence(table)
    print_decile_shapes(all_results)


if __name__ == "__main__":
    main()
