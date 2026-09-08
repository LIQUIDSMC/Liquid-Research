"""
Market Data Platform -- Threshold-Stability Study Runner
market_data_platform/research/run_threshold_stability_study.py

Three phases:
  1. Fresh audit (reuses audit_threshold_reference_dates.py's
     audit_date()/derive_n_eligibility() directly -- no independent
     eligibility logic). A frozen-study integrity assertion then
     compares the fresh eligible target-date SETS (not merely
     counts) against the previously locked matrix -- mechanically
     verified via a direct run of the audit module against the
     canonical Pi dataset (see EXPECTED_ELIGIBLE_TARGET_SETS below) -- and aborts on any
     drift rather than silently studying a different population.
  2. Feature cache: loads each needed audit-PASS date's raw trades
     ONCE per instrument, sorts, extracts compact imbalance vector,
     computes daily P10/P90, releases raw arrays before next date.
  3. Stability study: for each frozen TARGET_DATE x instrument x
     candidate N, records ineligibility with specific failed
     reference dates, or computes pooled historical P10/P90,
     signed day-to-day daily-percentile changes (chronological
     oldest -> newest), dispersion (population std, ddof=0, min/max),
     and an isolated, hindsight-only target-day diagnostic never
     used in threshold formation or N selection.

Purely descriptive: no returns, no outcomes, no trading signals, no
entry/exit/cost logic, no N selection or recommendation anywhere.

Fail-closed: cached vectors are verified (length matches stored
observation_count, finite, non-empty) before use; pooled counts are
cross-checked against the sum of daily counts; any mismatch aborts.

Usage:
    python3 -m L1_CORE.market_data_platform.research.run_threshold_stability_study
"""

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen import (
    _resolve_source_partitions,
    _day_bounds_ms,
    count_target_rows,
    load_instrument_day,
)
from L1_CORE.market_data_platform.research.run_expanded_batch_screen import INSTRUMENTS
from L1_CORE.market_data_platform.research.audit_threshold_reference_dates import (
    TARGET_DATES,
    AUDIT_DATES,
    CANDIDATE_N_VALUES,
    audit_date,
    derive_n_eligibility,
)
from L1_CORE.market_data_platform.research.imbalance_feature import compute_imbalance_only
from L1_CORE.market_data_platform.research.threshold_percentiles import compute_tail_thresholds

RESULTS_DIR = Path(__file__).resolve().parent / "results" / "threshold_stability_v1"

# Frozen-study integrity assertion. Mechanically derived by running
# the committed audit_threshold_reference_dates.py module directly
# against the canonical Pi dataset (not hand-transcribed): exact
# eligible TARGET_DATE sets, not merely counts, since two dates
# could swap while leaving a count unchanged. If a fresh audit run
# disagrees, the underlying data has changed and the study must not
# silently proceed on a different population.
EXPECTED_ELIGIBLE_TARGET_SETS = {
    1: {"2026-07-23", "2026-07-24", "2026-07-25", "2026-07-26", "2026-07-27",
        "2026-07-28", "2026-07-29", "2026-07-30", "2026-07-31", "2026-08-01",
        "2026-08-02", "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06",
        "2026-08-07", "2026-08-08", "2026-08-09", "2026-08-26", "2026-08-27",
        "2026-08-28", "2026-08-29", "2026-08-30"},
    3: {"2026-07-25", "2026-07-26", "2026-07-27", "2026-07-28", "2026-07-29",
        "2026-07-30", "2026-07-31", "2026-08-01", "2026-08-02", "2026-08-03",
        "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-08",
        "2026-08-09", "2026-08-26", "2026-08-27", "2026-08-28", "2026-08-29",
        "2026-08-30"},
    5: {"2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30", "2026-07-31",
        "2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04", "2026-08-05",
        "2026-08-06", "2026-08-07", "2026-08-08", "2026-08-09", "2026-08-26",
        "2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30"},
    10: {"2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04", "2026-08-05",
         "2026-08-06", "2026-08-07", "2026-08-08", "2026-08-09", "2026-08-26",
         "2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30"},
}

# Populated during Phase 2, consumed during Phase 3.
daily_features = {}    # {(instrument, date_str): np.ndarray imbalance vector}
daily_thresholds = {}  # {(instrument, date_str): {"p10":..., "p90":..., "observation_count":...}}


def run_fresh_audit():
    """
    Phase 1. Re-runs audit_date() over the full AUDIT_DATES universe,
    derives N-eligibility for TARGET_DATES, then asserts the fresh
    eligible target-date SETS match the previously locked, evidence-
    verified matrix exactly -- aborting if the underlying data has
    changed.
    """
    print(f"===== PHASE 1: FRESH AUDIT ({len(AUDIT_DATES)} dates) =====\n")
    audit_results = []
    for i, date_str in enumerate(AUDIT_DATES, start=1):
        print(f"[AUDIT {i}/{len(AUDIT_DATES)}] {date_str}...")
        result = audit_date(date_str)
        audit_results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status}" + (f" -- {result['reason']}" if result["reason"] else ""))

    audit_results_by_date = {r["date"]: r for r in audit_results}
    eligibility = derive_n_eligibility(audit_results, TARGET_DATES, CANDIDATE_N_VALUES)

    print("\n===== FROZEN-STUDY INTEGRITY ASSERTION =====")
    for n in CANDIDATE_N_VALUES:
        fresh_eligible_set = {t for t in TARGET_DATES if eligibility[t][n]["eligible"]}
        expected_set = EXPECTED_ELIGIBLE_TARGET_SETS[n]
        if fresh_eligible_set != expected_set:
            missing = expected_set - fresh_eligible_set
            unexpected = fresh_eligible_set - expected_set
            raise RuntimeError(
                f"FATAL: fresh audit eligibility for N={n} does not match the locked, "
                f"evidence-verified matrix. Missing (expected eligible, now not): "
                f"{sorted(missing)}. Unexpected (now eligible, not previously): "
                f"{sorted(unexpected)}. Underlying data has changed since the matrix was "
                f"locked -- aborting rather than silently studying a different population."
            )
        print(f"  N={n}: {len(fresh_eligible_set)} eligible targets -- MATCHES locked matrix")

    print()
    return audit_results_by_date, eligibility


def determine_needed_dates(eligibility):
    needed = set(TARGET_DATES)
    for target in TARGET_DATES:
        d = date.fromisoformat(target)
        for n in CANDIDATE_N_VALUES:
            if eligibility[target][n]["eligible"]:
                for k in range(1, n + 1):
                    needed.add((d - timedelta(days=k)).isoformat())
    return sorted(needed)


def extract_and_cache_features(needed_dates, audit_results_by_date):
    total = len(INSTRUMENTS) * len(needed_dates)
    counter = 0

    print(f"===== PHASE 2: FEATURE EXTRACTION ({total} instrument-days) =====\n")

    for instrument in INSTRUMENTS:
        for date_str in needed_dates:
            counter += 1
            print(f"[FEATURE {counter}/{total}] {instrument} {date_str} ...")

            audit_result = audit_results_by_date.get(date_str)
            if audit_result is None or not audit_result["passed"]:
                print(f"  SKIPPED -- date did not pass the fresh audit")
                continue

            partitions = _resolve_source_partitions(date_str)
            start_ms, end_ms = _day_bounds_ms(date_str)
            n_target, _ = count_target_rows(partitions, instrument, start_ms, end_ms)

            if n_target == 0:
                raise RuntimeError(
                    f"FATAL: {instrument} {date_str} passed the audit but produced zero "
                    f"in-range rows on reload. Aborting -- audit/runner disagreement must "
                    f"be investigated before proceeding."
                )

            trade_time, trade_id, price, quantity, is_buyer_maker = load_instrument_day(
                partitions, instrument, start_ms, end_ms, n_target
            )

            order = np.lexsort((trade_id, trade_time))
            trade_time = trade_time[order]
            trade_id = trade_id[order]
            quantity = quantity[order]
            is_buyer_maker = is_buyer_maker[order]
            del price, order

            result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
            imbalance_vector = result["imbalance"]
            del trade_time, trade_id, quantity, is_buyer_maker, result

            daily_threshold = compute_tail_thresholds(imbalance_vector)

            daily_features[(instrument, date_str)] = imbalance_vector
            daily_thresholds[(instrument, date_str)] = daily_threshold

            print(f"  cached: n_samples={len(imbalance_vector)}, "
                  f"daily_p10={daily_threshold['p10']:.4f}, daily_p90={daily_threshold['p90']:.4f}")

    print()


def validate_cached_feature(instrument, date_str):
    key = (instrument, date_str)

    if key not in daily_features or key not in daily_thresholds:
        raise RuntimeError(
            f"FATAL: no cached feature/threshold found for {instrument} {date_str}. Aborting."
        )

    vector = daily_features[key]
    stored_count = daily_thresholds[key]["observation_count"]

    if len(vector) != stored_count:
        raise RuntimeError(
            f"FATAL: cached vector length ({len(vector)}) != stored observation_count "
            f"({stored_count}) for {instrument} {date_str}. Aborting."
        )
    if len(vector) == 0:
        raise RuntimeError(f"FATAL: cached vector for {instrument} {date_str} is empty. Aborting.")
    if not np.isfinite(vector).all():
        raise RuntimeError(
            f"FATAL: cached vector for {instrument} {date_str} contains non-finite values. Aborting."
        )


def run_stability_study(audit_results_by_date, eligibility):
    print(f"===== PHASE 3: STABILITY STUDY =====\n")

    results = []

    for target in TARGET_DATES:
        target_passed = audit_results_by_date[target]["passed"]

        for instrument in INSTRUMENTS:
            for n in CANDIDATE_N_VALUES:
                e = eligibility[target][n]

                if not e["eligible"]:
                    results.append({
                        "instrument": instrument,
                        "target_date": target,
                        "n": n,
                        "eligible": False,
                        "failed_reference_dates": e["failed_dates"],
                    })
                    continue

                d = date.fromisoformat(target)
                reference_dates = sorted(
                    (d - timedelta(days=k)).isoformat() for k in range(1, n + 1)
                )  # ISO date strings sort chronologically oldest -> newest

                pooled_list = []
                per_reference_day = []
                day_to_day_changes = []
                prior = None
                expected_count = 0

                for ref_date in reference_dates:
                    validate_cached_feature(instrument, ref_date)
                    vec = daily_features[(instrument, ref_date)]
                    dth = daily_thresholds[(instrument, ref_date)]
                    expected_count += dth["observation_count"]

                    pooled_list.append(vec)
                    per_reference_day.append({
                        "date": ref_date,
                        "daily_p10": dth["p10"],
                        "daily_p90": dth["p90"],
                        "daily_observation_count": dth["observation_count"],
                    })

                    if prior is not None:
                        day_to_day_changes.append({
                            "from": prior["date"],
                            "to": ref_date,
                            "p10_change": dth["p10"] - prior["p10"],
                            "p90_change": dth["p90"] - prior["p90"],
                        })
                    prior = {"date": ref_date, "p10": dth["p10"], "p90": dth["p90"]}

                pooled = np.concatenate(pooled_list)
                if len(pooled) != expected_count:
                    raise RuntimeError(
                        f"FATAL: pooled length ({len(pooled)}) != sum of daily observation_counts "
                        f"({expected_count}) for {instrument} {target} N={n}. Aborting."
                    )

                historical = compute_tail_thresholds(pooled)
                if historical["observation_count"] != expected_count:
                    raise RuntimeError(
                        f"FATAL: historical observation_count ({historical['observation_count']}) "
                        f"!= expected ({expected_count}) for {instrument} {target} N={n}. Aborting."
                    )

                p10_values = [r["daily_p10"] for r in per_reference_day]
                p90_values = [r["daily_p90"] for r in per_reference_day]
                dispersion = {
                    "p10_std_across_daily": float(np.std(p10_values, ddof=0)),
                    "p90_std_across_daily": float(np.std(p90_values, ddof=0)),
                    "p10_min": float(min(p10_values)),
                    "p10_max": float(max(p10_values)),
                    "p90_min": float(min(p90_values)),
                    "p90_max": float(max(p90_values)),
                }

                target_diag = None
                if target_passed:
                    validate_cached_feature(instrument, target)
                    target_dth = daily_thresholds[(instrument, target)]
                    target_diag = {
                        "target_day_p10": target_dth["p10"],
                        "target_day_p90": target_dth["p90"],
                        "target_day_observation_count": target_dth["observation_count"],
                        "note": (
                            "DIAGNOSTIC ONLY. Computed from the target day's own full-day "
                            "imbalance population, AFTER the historical threshold above was "
                            "already finalized from strictly prior reference days. Never used "
                            "in threshold formation or N selection."
                        ),
                    }

                results.append({
                    "instrument": instrument,
                    "target_date": target,
                    "n": n,
                    "eligible": True,
                    "reference_dates": reference_dates,
                    "historical_p10": historical["p10"],
                    "historical_p90": historical["p90"],
                    "historical_observation_count": historical["observation_count"],
                    "per_reference_day": per_reference_day,
                    "day_to_day_changes": day_to_day_changes,
                    "dispersion": dispersion,
                    "target_day_diagnostic_only": target_diag,
                })

    print(f"Stability study complete: {len(results)} target x instrument x N records\n")
    return results


def build_summary(results):
    """
    Mechanical counts and descriptive aggregate diagnostics only. No
    N selection, no recommendation, no winner. Instrument-separated
    throughout -- BTC and ETH are never blended into a shared
    aggregate, per the frozen instrument-separation rule.
    """
    eligibility_counts_by_n = {n: 0 for n in CANDIDATE_N_VALUES}
    seen_targets_per_n = {n: set() for n in CANDIDATE_N_VALUES}

    per_instrument_and_n = {
        instr: {n: {"historical_p10": [], "historical_p90": [],
                     "p10_std_across_daily": [], "p90_std_across_daily": []}
                for n in CANDIDATE_N_VALUES}
        for instr in INSTRUMENTS
    }

    for r in results:
        n = r["n"]
        if r["eligible"]:
            if r["target_date"] not in seen_targets_per_n[n]:
                eligibility_counts_by_n[n] += 1
                seen_targets_per_n[n].add(r["target_date"])

            instr_stats = per_instrument_and_n[r["instrument"]][n]
            instr_stats["historical_p10"].append(r["historical_p10"])
            instr_stats["historical_p90"].append(r["historical_p90"])
            instr_stats["p10_std_across_daily"].append(r["dispersion"]["p10_std_across_daily"])
            instr_stats["p90_std_across_daily"].append(r["dispersion"]["p90_std_across_daily"])

    aggregate_by_instrument_and_n = {}
    for instr in INSTRUMENTS:
        aggregate_by_instrument_and_n[instr] = {}
        for n in CANDIDATE_N_VALUES:
            stats = per_instrument_and_n[instr][n]
            if len(stats["historical_p10"]) > 0:
                aggregate_by_instrument_and_n[instr][str(n)] = {
                    "eligible_count": len(stats["historical_p10"]),
                    "mean_historical_p10": float(np.mean(stats["historical_p10"])),
                    "mean_historical_p90": float(np.mean(stats["historical_p90"])),
                    "mean_p10_std_across_daily": float(np.mean(stats["p10_std_across_daily"])),
                    "mean_p90_std_across_daily": float(np.mean(stats["p90_std_across_daily"])),
                }
            else:
                aggregate_by_instrument_and_n[instr][str(n)] = {"eligible_count": 0}

    return {
        "target_dates_total": len(TARGET_DATES),
        "instruments": INSTRUMENTS,
        "candidate_n_values": CANDIDATE_N_VALUES,
        "eligibility_counts_by_n": {str(n): c for n, c in eligibility_counts_by_n.items()},
        "aggregate_by_instrument_and_n": aggregate_by_instrument_and_n,
        "note": "Descriptive counts and instrument-separated aggregate diagnostics only. "
                "No N selection, recommendation, or winner is made anywhere in this summary. "
                "BTC-USD and ETH-USD are never blended.",
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    audit_results_by_date, eligibility = run_fresh_audit()
    needed_dates = determine_needed_dates(eligibility)
    extract_and_cache_features(needed_dates, audit_results_by_date)
    results = run_stability_study(audit_results_by_date, eligibility)
    summary = build_summary(results)

    results_path = RESULTS_DIR / "threshold_stability_results.json"
    summary_path = RESULTS_DIR / "threshold_stability_summary.json"

    for output_path in (results_path, summary_path):
        if output_path.exists():
            raise RuntimeError(
                f"FATAL: refusing to overwrite existing evidence file: {output_path}"
            )

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"===== COMPLETE =====")
    print(f"Results: {results_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
