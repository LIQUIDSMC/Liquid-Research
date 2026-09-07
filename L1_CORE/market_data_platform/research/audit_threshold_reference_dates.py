"""
Market Data Platform -- Threshold-Study Reference-Date Availability/
Reconstruction Eligibility Audit
market_data_platform/research/audit_threshold_reference_dates.py

NARROW, ACCURATE SCOPE: this audits whether each candidate UTC date's
required three partitions RESOLVE and whether BTC-USD/ETH-USD have a
RECONSTRUCTABLE trade_time population under the already-validated
multi-partition semantics (_resolve_source_partitions(),
count_target_rows()). "PASS" means reconstructable under this
operational standard -- it does NOT independently prove the absence
of a silent collector outage or zero intraday collection gaps. This
is an availability/reconstruction eligibility audit, not a
collection-completeness audit.

Separate from and does not modify run_completeness_audit.py, which
has its own frozen scientific purpose and fixed 28-date candidate
matrix. This script exists specifically to determine N=1/3/5/10
threshold-history eligibility for the threshold-stability study,
using only the existing, already-validated primitives:
  - _resolve_source_partitions() (unmodified)
  - _day_bounds_ms() (unmodified)
  - count_target_rows() (unmodified)

TARGET_DATES vs. AUDIT_DATES (two explicitly separate universes):
  - TARGET_DATES: imported directly from run_expanded_batch_screen.py
    (FROZEN_DATES) -- the exact frozen 25 expanded-validation dates.
    Never redefined here, to avoid any drift between the two scripts.
  - AUDIT_DATES: mechanically derived as every TARGET_DATE plus its
    up-to-10-preceding-calendar-dates (needed as potential N=1..10
    references for any target). Includes genuine reference-only
    dates (e.g. between Aug 10-25) that were never expanded-
    validation targets themselves.

N eligibility is derived ONLY for TARGET_DATES. Reference-only dates
are audited (to determine target eligibility) but never themselves
promoted into eligibility output.

N eligibility rule (frozen): N = the immediately preceding N
calendar UTC dates that PASS this audit's reconstruction standard.
No skipping, substitution, or backfilling. If any required prior
date fails this audit, that target/N combination is ineligible --
and the specific failing date(s) are reported, not just a bare
pass/fail.

No loader or kernel modification. No outcome/return computation
anywhere in this script.

Usage:
    python3 -m L1_CORE.market_data_platform.research.audit_threshold_reference_dates
"""

import datetime

from L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen import (
    _resolve_source_partitions,
    _day_bounds_ms,
    count_target_rows,
)
from L1_CORE.market_data_platform.research.run_expanded_batch_screen import (
    FROZEN_DATES,
    INSTRUMENTS,
)

MAX_N = 10
CANDIDATE_N_VALUES = [1, 3, 5, 10]

TARGET_DATES = FROZEN_DATES  # exactly the frozen 25, imported directly -- never redefined


def _build_audit_dates(target_dates, max_n):
    """
    Mechanically derives the full set of dates that must be audited:
    every target date itself, plus every date up to max_n calendar
    days before each target (potential reference dates for any N).
    """
    audit_dates = set()
    for target in target_dates:
        d = datetime.datetime.strptime(target, "%Y-%m-%d").date()
        audit_dates.add(target)
        for k in range(1, max_n + 1):
            audit_dates.add((d - datetime.timedelta(days=k)).strftime("%Y-%m-%d"))
    return sorted(audit_dates)


AUDIT_DATES = _build_audit_dates(TARGET_DATES, MAX_N)


def audit_date(date_str):
    """
    For one calendar date, resolves the required 3 partitions and
    reconstructs the trade_time-defined population for each
    instrument via the existing, unmodified primitives.

    Returns:
        dict: date, passed (bool), reason (str or None),
        per_instrument (dict of instrument -> in_range_rows).
    """
    start_ms, end_ms = _day_bounds_ms(date_str)

    try:
        partitions = _resolve_source_partitions(date_str)
    except RuntimeError as e:
        return {"date": date_str, "passed": False, "reason": str(e), "per_instrument": {}}

    per_instrument = {}
    for instrument in INSTRUMENTS:
        n_total, _ = count_target_rows(partitions, instrument, start_ms, end_ms)
        per_instrument[instrument] = n_total

        if n_total == 0:
            return {
                "date": date_str, "passed": False,
                "reason": f"{instrument}: zero reconstructed in-range rows",
                "per_instrument": per_instrument,
            }

    return {"date": date_str, "passed": True, "reason": None, "per_instrument": per_instrument}


def derive_n_eligibility(audit_results, target_dates, n_values):
    """
    Derives N-eligibility ONLY for target_dates (the frozen 25).
    For each target and each N, checks whether the target itself
    passed AND every one of the immediately preceding N calendar
    dates also passed this audit's reconstruction standard -- strict,
    no skipping/backfilling. Reports the SPECIFIC failing date(s),
    not merely a boolean.

    Returns:
        dict: {target_date: {n: {"eligible": bool, "failed_dates": [...]}}}
    """
    results_by_date = {r["date"]: r["passed"] for r in audit_results}

    eligibility = {}
    for date_str in target_dates:
        target_passed = results_by_date.get(date_str, False)

        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        eligibility[date_str] = {}

        for n in n_values:
            if not target_passed:
                eligibility[date_str][n] = {"eligible": False, "failed_dates": [f"{date_str} (target itself)"]}
                continue

            required_dates = [(d - datetime.timedelta(days=k)).strftime("%Y-%m-%d") for k in range(1, n + 1)]
            failed_dates = [rd for rd in required_dates if not results_by_date.get(rd, False)]
            eligibility[date_str][n] = {
                "eligible": len(failed_dates) == 0,
                "failed_dates": failed_dates,
            }

    return eligibility


def main():
    print(f"===== THRESHOLD REFERENCE-DATE AVAILABILITY/RECONSTRUCTION AUDIT =====")
    print(f"Target dates (frozen 25, imported from run_expanded_batch_screen.py): {len(TARGET_DATES)}")
    print(f"Total audit dates (targets + up to {MAX_N}-day history): {len(AUDIT_DATES)}\n")

    audit_results = []
    for i, date_str in enumerate(AUDIT_DATES, start=1):
        print(f"[{i}/{len(AUDIT_DATES)}] Auditing {date_str}...")
        result = audit_date(date_str)
        audit_results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status}" + (f" -- {result['reason']}" if result["reason"] else ""))

    print(f"\n===== N-ELIGIBILITY (frozen 25 targets only; strict, immediately preceding "
          f"calendar dates that PASS this audit) =====\n")
    eligibility = derive_n_eligibility(audit_results, TARGET_DATES, CANDIDATE_N_VALUES)

    for date_str in TARGET_DATES:
        target_passed = next(r["passed"] for r in audit_results if r["date"] == date_str)
        print(f"{date_str}  target_PASS={target_passed}")
        for n in CANDIDATE_N_VALUES:
            e = eligibility[date_str][n]
            if e["eligible"]:
                print(f"  N={n:<3} YES")
            else:
                print(f"  N={n:<3} NO   required date(s) failed: {', '.join(e['failed_dates'])}")
        print()


if __name__ == "__main__":
    main()
