"""
Market Data Platform -- Threshold-Stability Post-Study Analysis
market_data_platform/research/analyze_threshold_stability.py

Reproducibly derives the two decision-relevant analyses from the
existing threshold_stability_results.json (no corpus rescan, no new
Pi loading):

  1. Common-eligible-date comparison: restricts to exactly the
     target dates eligible at ALL of N=1/3/5/10 for BOTH instruments
     (verified, not assumed -- see find_common_eligible_dates()),
     giving an apples-to-apples comparison of within-window daily-
     P10/P90 dispersion (population std, ddof=0, plus min-max range)
     not confounded by differing eligible-date populations across N.

  2. Pooled-threshold churn: for each instrument and N, the absolute
     change in historical_p10/historical_p90 between CONSECUTIVE
     CALENDAR-DAY targets only (explicitly excluding the Aug09->Aug26
     gap and any other non-1-day jump), reporting mean, median
     (statistics.median -- correct for both odd and even pair
     counts), and max churn.

Fail-closed structural integrity: verifies the source JSON is
exactly the expected 200-record study (25 dates x 2 instruments x 4
N values, no duplicates) before any calculation, verifies BTC-USD
and ETH-USD eligibility never diverges for any date (rather than
assuming the runner's date-level eligibility design always holds),
and verifies the derived common-eligible-date count is exactly 14
before proceeding -- any violation aborts rather than silently
analyzing an unverified or unexpected population.

STABILITY vs. CALIBRATION: this analysis measures how much daily
values disperse within a historical window, and how much the
resulting pooled threshold moves from one target day to the next. It
does NOT measure calibration, responsiveness to genuine regime
change, or optimality -- a stable threshold could be stable because
it is slow to adapt. No N selection or recommendation is made here.

Usage:
    python3 -m L1_CORE.market_data_platform.research.analyze_threshold_stability
"""

import json
import statistics
from datetime import date
from pathlib import Path

RESULTS_PATH = (
    Path(__file__).resolve().parent
    / "results" / "threshold_stability_v1" / "threshold_stability_results.json"
)

INSTRUMENTS = ["BTC-USD", "ETH-USD"]
N_VALUES = [1, 3, 5, 10]
EXPECTED_TOTAL_RECORDS = 200
EXPECTED_TARGET_DATE_COUNT = 25
EXPECTED_COMMON_ELIGIBLE_COUNT = 14


def load_results():
    with open(RESULTS_PATH) as f:
        return json.load(f)


def validate_source_structure(results):
    """
    Fail-closed structural verification of the source study JSON,
    run immediately after loading and before any derived dictionary
    is built or any calculation occurs.
    """
    if len(results) != EXPECTED_TOTAL_RECORDS:
        raise RuntimeError(
            f"FATAL: expected {EXPECTED_TOTAL_RECORDS} total records, got {len(results)}"
        )

    target_dates = set(r["target_date"] for r in results)
    if len(target_dates) != EXPECTED_TARGET_DATE_COUNT:
        raise RuntimeError(
            f"FATAL: expected {EXPECTED_TARGET_DATE_COUNT} unique target dates, "
            f"got {len(target_dates)}"
        )

    instruments_found = set(r["instrument"] for r in results)
    if instruments_found != set(INSTRUMENTS):
        raise RuntimeError(
            f"FATAL: expected instruments {INSTRUMENTS}, got {sorted(instruments_found)}"
        )

    n_found = set(r["n"] for r in results)
    if n_found != set(N_VALUES):
        raise RuntimeError(f"FATAL: expected N values {N_VALUES}, got {sorted(n_found)}")

    seen = set()
    for r in results:
        key = (r["instrument"], r["target_date"], r["n"])
        if key in seen:
            raise RuntimeError(f"FATAL: duplicate record for {key}")
        seen.add(key)
    if len(seen) != EXPECTED_TOTAL_RECORDS:
        raise RuntimeError(
            f"FATAL: expected exactly one record per instrument x date x N "
            f"({EXPECTED_TOTAL_RECORDS}), got {len(seen)}"
        )


def find_common_eligible_dates(results, n_values):
    """
    Returns the sorted list of target dates eligible at ALL of the
    given N values, for BOTH instruments. Verifies -- rather than
    assumes -- that BTC-USD and ETH-USD eligibility never diverges
    for any date; aborts if it ever does, since that would
    contradict the runner's date-level eligibility design and this
    analysis should not silently proceed on an unverified assumption.
    """
    by_target_n = {(r["instrument"], r["target_date"], r["n"]): r for r in results}
    all_targets = sorted(set(r["target_date"] for r in results))

    common_dates = []
    for t in all_targets:
        btc_eligible = {n: by_target_n[("BTC-USD", t, n)]["eligible"] for n in n_values}
        eth_eligible = {n: by_target_n[("ETH-USD", t, n)]["eligible"] for n in n_values}

        if btc_eligible != eth_eligible:
            raise RuntimeError(
                f"FATAL: BTC-USD and ETH-USD eligibility diverge for {t}: "
                f"BTC={btc_eligible}, ETH={eth_eligible}. This contradicts the "
                f"runner's date-level eligibility design -- aborting."
            )

        if all(btc_eligible.values()):
            common_dates.append(t)

    return common_dates


def analyze_common_eligible_dispersion(results, common_dates):
    """
    Analysis 1: within-window daily dispersion, restricted to the
    common-eligible date population, per instrument and N.
    """
    by_target_n = {(r["instrument"], r["target_date"], r["n"]): r for r in results}

    output = {}
    for instrument in INSTRUMENTS:
        output[instrument] = {}
        for n in N_VALUES:
            p10_stds, p90_stds, p10_ranges, p90_ranges = [], [], [], []
            hist_p10s, hist_p90s = [], []

            for target in common_dates:
                r = by_target_n[(instrument, target, n)]
                p10_stds.append(r["dispersion"]["p10_std_across_daily"])
                p90_stds.append(r["dispersion"]["p90_std_across_daily"])
                p10_ranges.append(r["dispersion"]["p10_max"] - r["dispersion"]["p10_min"])
                p90_ranges.append(r["dispersion"]["p90_max"] - r["dispersion"]["p90_min"])
                hist_p10s.append(r["historical_p10"])
                hist_p90s.append(r["historical_p90"])

            output[instrument][str(n)] = {
                "mean_p10_std_across_daily": statistics.mean(p10_stds),
                "mean_p90_std_across_daily": statistics.mean(p90_stds),
                "mean_p10_range": statistics.mean(p10_ranges),
                "mean_p90_range": statistics.mean(p90_ranges),
                "mean_historical_p10": statistics.mean(hist_p10s),
                "mean_historical_p90": statistics.mean(hist_p90s),
            }

    return output


def analyze_pooled_threshold_churn(results):
    """
    Analysis 2: consecutive-calendar-day pooled-threshold churn, per
    instrument and N. Only compares target pairs exactly 1 calendar
    day apart -- explicitly excludes the Aug09->Aug26 gap and any
    other non-consecutive jump.
    """
    by_target_n = {}
    for r in results:
        if r["eligible"]:
            by_target_n[(r["instrument"], r["target_date"], r["n"])] = r

    output = {}
    for instrument in INSTRUMENTS:
        output[instrument] = {}
        for n in N_VALUES:
            eligible_targets = sorted(
                t for (i, t, nn) in by_target_n.keys() if i == instrument and nn == n
            )

            p10_changes, p90_changes = [], []
            for i in range(1, len(eligible_targets)):
                prev_date = date.fromisoformat(eligible_targets[i - 1])
                curr_date = date.fromisoformat(eligible_targets[i])
                if (curr_date - prev_date).days != 1:
                    continue

                prev_r = by_target_n[(instrument, eligible_targets[i - 1], n)]
                curr_r = by_target_n[(instrument, eligible_targets[i], n)]

                p10_changes.append(abs(curr_r["historical_p10"] - prev_r["historical_p10"]))
                p90_changes.append(abs(curr_r["historical_p90"] - prev_r["historical_p90"]))

            if p10_changes:
                output[instrument][str(n)] = {
                    "consecutive_pairs": len(p10_changes),
                    "p10_mean_abs_change": statistics.mean(p10_changes),
                    "p10_median_abs_change": statistics.median(p10_changes),
                    "p10_max_abs_change": max(p10_changes),
                    "p90_mean_abs_change": statistics.mean(p90_changes),
                    "p90_median_abs_change": statistics.median(p90_changes),
                    "p90_max_abs_change": max(p90_changes),
                }
            else:
                output[instrument][str(n)] = {"consecutive_pairs": 0}

    return output


def main():
    results = load_results()
    validate_source_structure(results)

    common_dates = find_common_eligible_dates(results, N_VALUES)
    if len(common_dates) != EXPECTED_COMMON_ELIGIBLE_COUNT:
        raise RuntimeError(
            f"FATAL: expected exactly {EXPECTED_COMMON_ELIGIBLE_COUNT} common-eligible "
            f"dates, got {len(common_dates)}. This may indicate a different study "
            f"population than previously analyzed -- aborting."
        )

    dispersion_analysis = analyze_common_eligible_dispersion(results, common_dates)
    churn_analysis = analyze_pooled_threshold_churn(results)

    output = {
        "source_file": str(RESULTS_PATH),
        "common_eligible_dates": common_dates,
        "common_eligible_date_count": len(common_dates),
        "note": (
            "STABILITY vs. CALIBRATION: this analysis measures within-window daily "
            "dispersion and pooled-threshold churn between consecutive calendar-day "
            "targets. It does NOT measure calibration, responsiveness to genuine "
            "regime change, or optimality. No N selection or recommendation is made."
        ),
        "within_window_dispersion_common_eligible": dispersion_analysis,
        "pooled_threshold_churn_consecutive_days": churn_analysis,
    }

    output_dir = RESULTS_PATH.parent
    output_path = output_dir / "threshold_stability_post_analysis.json"

    if output_path.exists():
        raise RuntimeError(f"FATAL: refusing to overwrite existing analysis file: {output_path}")

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"===== ANALYSIS COMPLETE =====")
    print(f"Common eligible dates: {len(common_dates)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
