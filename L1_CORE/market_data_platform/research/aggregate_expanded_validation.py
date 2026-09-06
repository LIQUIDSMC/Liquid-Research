"""
Market Data Platform -- Expanded Validation Aggregator (50 instrument-days)
market_data_platform/research/aggregate_expanded_validation.py

Reads the 50 existing per-instrument-day JSON results (produced by
run_expanded_batch_screen.py / run_trade_flow_vs_momentum_screen.py)
and mechanically evaluates the frozen promotion gate for trade-flow
imbalance. Does NOT re-run any Parquet loading or the kernel.

Momentum is present in the source JSONs and is structurally
validated here (a malformed momentum block still aborts), but is
NEVER used in any gate or statistic in this script -- this
expanded-validation decision is scored on imbalance only.

UNITS: every D9-D0 value used anywhere in this script is basis
points (bp), taken directly from the source JSON's d9_minus_d0_bp
field -- never derived by converting d9_minus_d0_raw.

Fail-closed: imports FROZEN_MATRIX directly from
run_expanded_batch_screen.py (single canonical matrix definition,
never reconstructed independently here) and requires exactly those
50 (instrument, date) pairs -- no missing, duplicate, or unexpected
result files.

Structural validation confirmed against real runner output and
source (summarize_feature_deciles() in
run_trade_flow_vs_momentum_screen.py): decile n=0 legitimately
produces mean_return_bp=None; n>0 requires a finite number. Both
directions of this relationship are validated, not merely typed.

Promotion gate (9 individually-reported checks, ALL required for
overall PASS):
  1-4. Sign consistency >= 33/50 at 5s, 15s, 30s, 60s
  5. Combined median D9-D0 > 0 at all four horizons
  6. BTC median D9-D0 > 0 at all four horizons (independently)
  7. ETH median D9-D0 > 0 at all four horizons (independently)
  8. For every horizon and every one of the 50 possible
     single-observation omissions, the mean of the remaining 49
     D9-D0 values must be >= 0.
  9. 60s combined median D9-D0 >= +0.10 bp

Diagnostics (reported, never gating): unweighted mean/median,
BTC/ETH split, 10%-per-tail trimmed mean, full D0-D9 aggregate
mean/median shape, max absolute LOO shift and its instrument-day,
Spearman rank correlation (decile index vs. aggregate decile
return) via a local, deterministic tie-aware implementation --
explicitly diagnostic, never a gate.

No causal, cost, or tradability language anywhere in this script's
output.

Usage:
    python3 -m L1_CORE.market_data_platform.research.aggregate_expanded_validation \
        --results-dir /tmp/expanded_screen_results
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from L1_CORE.market_data_platform.research.run_expanded_batch_screen import FROZEN_MATRIX

HORIZONS = [5, 15, 30, 60]
FEATURES = ["imbalance", "momentum"]  # both validated structurally; only imbalance is scored
SIGN_CONSISTENCY_THRESHOLD = 33  # ceil(0.65 * 50)
SIXTY_S_MEDIAN_FLOOR_BP = 0.10

EXPECTED_MATRIX = set(FROZEN_MATRIX)


def load_all_results(results_dir):
    results_dir = Path(results_dir)
    files = sorted(results_dir.glob("*.json"))

    loaded = []
    seen_pairs = []
    for f in files:
        with open(f) as fh:
            data = json.load(fh)

        # Parse the EXPECTED identity from the filename itself
        # ("{instrument}_{date}.json"), not from the JSON content --
        # otherwise a swapped/misnamed file could pass identity
        # validation trivially by comparing content against itself.
        stem = f.stem  # e.g. "BTC-USD_2026-07-22"
        if "_" not in stem:
            _fail(f, f"filename does not match expected '{{instrument}}_{{date}}.json' pattern")
        filename_instrument, filename_date = stem.split("_", 1)
        pair = (filename_instrument, filename_date)

        seen_pairs.append(pair)
        loaded.append((pair, data, f))

    seen_set = set(seen_pairs)
    duplicates = [p for p in seen_set if seen_pairs.count(p) > 1]
    missing = EXPECTED_MATRIX - seen_set
    unexpected = seen_set - EXPECTED_MATRIX

    problems = []
    if duplicates:
        problems.append(f"DUPLICATE (instrument, date) pairs: {duplicates}")
    if missing:
        problems.append(f"MISSING pairs: {sorted(missing)}")
    if unexpected:
        problems.append(f"UNEXPECTED pairs not in frozen matrix: {sorted(unexpected)}")

    if problems:
        print("===== FROZEN MATRIX VALIDATION FAILED =====", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(f"\nExpected exactly {len(EXPECTED_MATRIX)} pairs.", file=sys.stderr)
        print(f"Found {len(seen_pairs)} files in {results_dir}.", file=sys.stderr)
        sys.exit(1)

    for pair, data, f in loaded:
        validate_result_structure(pair, data, f)

    print(f"Loaded and validated exactly {len(loaded)} frozen instrument-day results "
          f"from {results_dir}\n")

    return [data for (_, data, _) in loaded]


def validate_result_structure(expected_pair, data, f):
    """
    expected_pair is derived from the FILENAME, not from the JSON
    content -- this makes the instrument/date check below a genuine
    filename<->content consistency check, not a tautological
    comparison of the JSON against itself.
    """
    filename_instrument, filename_date = expected_pair

    if not isinstance(data, dict):
        _fail(f, f"top-level JSON content is not an object: {type(data).__name__}")

    internal_instrument = data.get("instrument")
    internal_date = data.get("date")
    if internal_instrument != filename_instrument or internal_date != filename_date:
        _fail(f, f"internal instrument/date ({internal_instrument!r}, {internal_date!r}) "
                 f"does not match filename-derived identity "
                 f"({filename_instrument!r}, {filename_date!r})")

    horizon_container = data.get("results_by_horizon")
    if not isinstance(horizon_container, dict):
        _fail(f, f"'results_by_horizon' is not an object: {type(horizon_container).__name__}")

    expected_horizon_keys = {str(h) for h in HORIZONS}
    actual_horizon_keys = set(horizon_container.keys())
    if actual_horizon_keys != expected_horizon_keys:
        _fail(f, f"results_by_horizon keys must be exactly {sorted(expected_horizon_keys)}, "
                 f"got {sorted(actual_horizon_keys)}")

    for h in HORIZONS:
        h_key = str(h)
        horizon_data = horizon_container[h_key]
        if not isinstance(horizon_data, dict):
            _fail(f, f"horizon {h_key}: value is not an object: {type(horizon_data).__name__}")

        expected_feature_keys = set(FEATURES) | {"n"}
        actual_feature_keys = set(horizon_data.keys())
        if actual_feature_keys != expected_feature_keys:
            _fail(f, f"horizon {h_key}: keys must be exactly {sorted(expected_feature_keys)}, "
                     f"got {sorted(actual_feature_keys)}")

        n = horizon_data.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            _fail(f, f"horizon {h_key}: 'n' is not a nonnegative integer: {n!r}")

        for feat in FEATURES:
            feat_data = horizon_data[feat]
            if not isinstance(feat_data, dict):
                _fail(f, f"horizon {h_key}, {feat}: value is not an object: {type(feat_data).__name__}")

            d9_d0 = feat_data.get("d9_minus_d0_bp")
            if (not isinstance(d9_d0, (int, float)) or isinstance(d9_d0, bool)
                    or not math.isfinite(d9_d0)):
                _fail(f, f"horizon {h_key}, {feat}: d9_minus_d0_bp is not a finite number: {d9_d0!r}")

            decile_summary = feat_data.get("decile_summary")
            if not isinstance(decile_summary, list) or len(decile_summary) != 10:
                _fail(f, f"horizon {h_key}, {feat}: decile_summary does not have exactly 10 entries")

            seen_deciles = set()
            for entry in decile_summary:
                if not isinstance(entry, dict):
                    _fail(f, f"horizon {h_key}, {feat}: decile_summary entry is not an object: "
                             f"{type(entry).__name__}")
                d = entry.get("decile")
                if not isinstance(d, int) or isinstance(d, bool) or d not in range(10) or d in seen_deciles:
                    _fail(f, f"horizon {h_key}, {feat}: invalid or duplicate decile identity: {d!r}")
                seen_deciles.add(d)

                entry_n = entry.get("n")
                if not isinstance(entry_n, int) or isinstance(entry_n, bool) or entry_n < 0:
                    _fail(f, f"horizon {h_key}, {feat}, decile {d}: invalid n: {entry_n!r}")

                mean_ret = entry.get("mean_return_bp")
                # Confirmed runner semantics (summarize_feature_deciles):
                # n=0 -> mean_return_bp is None; n>0 -> finite numeric.
                if entry_n == 0:
                    if mean_ret is not None:
                        _fail(f, f"horizon {h_key}, {feat}, decile {d}: n=0 requires "
                                 f"mean_return_bp=None, got {mean_ret!r}")
                else:
                    if (not isinstance(mean_ret, (int, float)) or isinstance(mean_ret, bool)
                            or not math.isfinite(mean_ret)):
                        _fail(f, f"horizon {h_key}, {feat}, decile {d}: n>0 requires finite "
                                 f"numeric mean_return_bp, got {mean_ret!r}")

            if seen_deciles != set(range(10)):
                _fail(f, f"horizon {h_key}, {feat}: decile_summary does not cover exactly 0-9")


def _fail(f, message):
    print("===== MALFORMED RESULT FILE =====", file=sys.stderr)
    print(f"  File: {f}", file=sys.stderr)
    print(f"  Problem: {message}", file=sys.stderr)
    sys.exit(1)


def build_imbalance_table(all_results):
    table = {h: [] for h in HORIZONS}
    for r in all_results:
        instrument = r["instrument"]
        date = r["date"]
        for h in HORIZONS:
            val = r["results_by_horizon"][str(h)]["imbalance"]["d9_minus_d0_bp"]
            table[h].append((instrument, date, val))
    return table


def trimmed_mean(values, trim_fraction=0.10):
    k = math.floor(trim_fraction * len(values))
    sorted_values = sorted(values)
    trimmed = sorted_values[k:len(sorted_values) - k] if k > 0 else sorted_values
    return statistics.mean(trimmed)


def spearman_rank_correlation(x, y):
    def rank(values):
        sorted_idx = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(sorted_idx):
            j = i
            while j + 1 < len(sorted_idx) and values[sorted_idx[j + 1]] == values[sorted_idx[i]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[sorted_idx[k]] = avg_rank
            i = j + 1
        return ranks

    rx = rank(x)
    ry = rank(y)
    n = len(x)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_rx = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_ry = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    if std_rx == 0 or std_ry == 0:
        return float("nan")
    return cov / (std_rx * std_ry)


def evaluate_gates(table):
    gates = {}

    for h in HORIZONS:
        values = [v for (_, _, v) in table[h]]
        positive_count = sum(1 for v in values if v > 0)
        gates[f"sign_consistency_{h}s (>={SIGN_CONSISTENCY_THRESHOLD}/{len(values)})"] = (
            positive_count >= SIGN_CONSISTENCY_THRESHOLD
        )

    combined_medians = {h: statistics.median([v for (_, _, v) in table[h]]) for h in HORIZONS}
    gates["combined_median_positive_all_horizons"] = all(combined_medians[h] > 0 for h in HORIZONS)

    btc_medians = {h: statistics.median([v for (i, _, v) in table[h] if i == "BTC-USD"]) for h in HORIZONS}
    gates["btc_median_positive_all_horizons"] = all(btc_medians[h] > 0 for h in HORIZONS)

    eth_medians = {h: statistics.median([v for (i, _, v) in table[h] if i == "ETH-USD"]) for h in HORIZONS}
    gates["eth_median_positive_all_horizons"] = all(eth_medians[h] > 0 for h in HORIZONS)

    loo_ok = True
    for h in HORIZONS:
        values = [v for (_, _, v) in table[h]]
        for i in range(len(values)):
            remaining_mean = statistics.mean(values[:i] + values[i + 1:])
            if remaining_mean < 0:
                loo_ok = False
    gates["loo_49obs_mean_never_negative"] = loo_ok

    gates[f"60s_median_at_least_{SIXTY_S_MEDIAN_FLOOR_BP}bp"] = (
        combined_medians[60] >= SIXTY_S_MEDIAN_FLOOR_BP
    )

    overall_pass = all(gates.values())
    return gates, overall_pass, combined_medians, btc_medians, eth_medians


def print_gate_table(gates, overall_pass):
    print("===== PROMOTION GATE TABLE =====\n")
    print(f"{'Gate':<55}{'Result':>10}")
    for gate_name, passed in gates.items():
        print(f"{gate_name:<55}{'PASS' if passed else 'FAIL':>10}")
    print(f"{'':<55}{'':>10}")
    print(f"{'OVERALL':<55}{'PASS' if overall_pass else 'FAIL':>10}")
    print()


def print_diagnostics(table, all_results):
    print("===== DIAGNOSTICS (reported, non-gating) =====\n")

    for h in HORIZONS:
        values = [v for (_, _, v) in table[h]]
        btc_values = [v for (i, _, v) in table[h] if i == "BTC-USD"]
        eth_values = [v for (i, _, v) in table[h] if i == "ETH-USD"]

        mean_v = statistics.mean(values)
        median_v = statistics.median(values)
        trimmed_v = trimmed_mean(values, 0.10)

        print(f"--- Horizon {h}s ---")
        print(f"  Combined: mean={mean_v:+.4f}bp median={median_v:+.4f}bp "
              f"trimmed_mean(10%/tail)={trimmed_v:+.4f}bp")
        print(f"  BTC: mean={statistics.mean(btc_values):+.4f}bp median={statistics.median(btc_values):+.4f}bp")
        print(f"  ETH: mean={statistics.mean(eth_values):+.4f}bp median={statistics.median(eth_values):+.4f}bp")

        max_shift = 0.0
        max_shift_entry = None
        for i, (instrument, date, val) in enumerate(table[h]):
            remaining_mean = statistics.mean([v for j, (_, _, v) in enumerate(table[h]) if j != i])
            shift = abs(remaining_mean - mean_v)
            if shift > max_shift:
                max_shift = shift
                max_shift_entry = (instrument, date, val)
        print(f"  Max absolute LOO shift: {max_shift:.4f}bp (excluding {max_shift_entry[0]} "
              f"{max_shift_entry[1]}, its value: {max_shift_entry[2]:+.4f}bp)")
        print()

    print("--- Full aggregate D0-D9 decile shape (unweighted mean/median across all 50 instrument-days) ---")
    for h in HORIZONS:
        decile_means = {d: [] for d in range(10)}
        for r in all_results:
            deciles = r["results_by_horizon"][str(h)]["imbalance"]["decile_summary"]
            for entry in deciles:
                if entry["n"] > 0:
                    decile_means[entry["decile"]].append(entry["mean_return_bp"])

        agg_means = [statistics.mean(decile_means[d]) if decile_means[d] else float("nan") for d in range(10)]
        agg_medians = [statistics.median(decile_means[d]) if decile_means[d] else float("nan") for d in range(10)]

        mean_str = " ".join(f"D{d}:{agg_means[d]:+.3f}" for d in range(10))
        median_str = " ".join(f"D{d}:{agg_medians[d]:+.3f}" for d in range(10))
        print(f"  {h}s mean:   {mean_str}")
        print(f"  {h}s median: {median_str}")

        valid_deciles = [d for d in range(10) if not math.isnan(agg_means[d])]
        if len(valid_deciles) >= 3:
            rho = spearman_rank_correlation(valid_deciles, [agg_means[d] for d in valid_deciles])
            print(f"  {h}s Spearman rho (decile index vs. mean return) [DIAGNOSTIC ONLY]: {rho:.4f}")
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    args = parser.parse_args()

    all_results = load_all_results(args.results_dir)
    table = build_imbalance_table(all_results)

    gates, overall_pass, combined_medians, btc_medians, eth_medians = evaluate_gates(table)

    print_gate_table(gates, overall_pass)
    print_diagnostics(table, all_results)


if __name__ == "__main__":
    main()
