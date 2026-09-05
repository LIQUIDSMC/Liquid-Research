"""
Market Data Platform -- Read-Only Completeness Audit
market_data_platform/research/run_completeness_audit.py

Structural/coverage-only audit for the proposed 56-instrument-day
expanded validation matrix. Inspects ONLY instrument_id and
trade_time -- never price, quantity, is_buyer_maker, imbalance,
deciles, forward returns, or any signal outcome.

For each candidate calendar date, verifies:
  - prev/target/next storage partitions all exist
  - file counts and zero-byte file counts per partition
  - EXHAUSTIVE null counts for instrument_id and trade_time,
    scanned ONCE per file (not once per instrument -- BTC-USD and
    ETH-USD research-day counts are both derived from the same
    single read of each file, roughly halving physical I/O versus
    scanning every file separately per instrument)
  - research-day row count per instrument: rows satisfying
    start_ms <= trade_time < end_ms, counted across ALL THREE
    partitions combined (not target-partition-only)

ZERO-BYTE FILES ARE A GLOBAL ABORT, NOT A PER-DATE FAILURE. The
known historical zero-byte trade files were already identified,
documented, and removed during the instrument-identity incident.
Any zero-byte trade file found now is therefore UNEXPECTED evidence
of a potential current integrity problem -- the audit stops
immediately, prints the exact offending file path(s), and exits
nonzero. It does NOT silently exclude the affected date and
continue; a new zero-byte file must be investigated before the
validation matrix can be frozen at all.

Any other predeclared failure (missing partition, any null
instrument_id/trade_time, zero research-day rows for either
instrument) excludes that calendar date for BOTH instruments as a
matched pair -- never one instrument alone.

Memory-safe: reads only two columns per file, processes one file at
a time, never materializes a full instrument-day's rows in memory.

Usage:
    python3 -m L1_CORE.market_data_platform.research.run_completeness_audit
"""

import datetime
import sys
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

CANONICAL_TRADES_ROOT = Path("/mnt/lrs001/data/market_data_platform/canonical/trades")
INSTRUMENTS = ["BTC-USD", "ETH-USD"]
MS_PER_DAY = 24 * 60 * 60 * 1000

BLOCK_A = [f"2026-07-{d:02d}" for d in range(22, 32)] + [f"2026-08-{d:02d}" for d in range(1, 10)]
BLOCK_B = [f"2026-08-{d:02d}" for d in range(26, 32)] + [f"2026-09-{d:02d}" for d in range(1, 4)]
CANDIDATE_DATES = BLOCK_A + BLOCK_B


def _day_bounds_ms(date_str):
    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    start_ms = int(d.timestamp() * 1000)
    return start_ms, start_ms + MS_PER_DAY


def _adjacent_date_str(date_str, offset_days):
    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    return (d + datetime.timedelta(days=offset_days)).strftime("%Y-%m-%d")


def audit_partition_structure(date_str):
    """
    Checks whether prev/target/next partition directories exist,
    and returns per-partition file/zero-byte counts and the exact
    paths of any zero-byte files found (for the global-abort report).
    """
    prev_date = _adjacent_date_str(date_str, -1)
    next_date = _adjacent_date_str(date_str, +1)
    labels = [prev_date, date_str, next_date]

    result = {}
    for label in labels:
        path = CANONICAL_TRADES_ROOT / f"date={label}"
        if not path.is_dir():
            result[label] = {
                "exists": False, "path": str(path),
                "file_count": 0, "zero_byte_files": [],
            }
            continue

        files = list(path.glob("*.parquet"))
        zero_byte_files = [str(f) for f in files if f.stat().st_size == 0]
        result[label] = {
            "exists": True,
            "path": str(path),
            "file_count": len(files),
            "zero_byte_files": zero_byte_files,
        }
    return result


def audit_instrument_day(date_str, partition_structure):
    """
    Exhaustively scans instrument_id and trade_time ONCE per file
    across every non-zero-byte file in the prev/target/next
    partitions for this calendar date, deriving BOTH BTC-USD and
    ETH-USD counts from the same single read -- not one pass per
    instrument.

    Returns:
        dict keyed by instrument, each with:
        null_instrument_id_count, null_trade_time_count (shared
        across both instruments since these are raw, unfiltered
        counts), instrument_rows_total, research_day_rows_total,
        per_partition_research_day_rows, files_scanned.
    """
    start_ms, end_ms = _day_bounds_ms(date_str)

    shared_null_instrument_id_count = 0
    shared_null_trade_time_count = 0
    files_scanned = 0

    per_instrument = {
        instr: {
            "instrument_rows_total": 0,
            "research_day_rows_total": 0,
            "per_partition_research_day_rows": {},
        }
        for instr in INSTRUMENTS
    }

    for label, stats in partition_structure.items():
        if not stats["exists"]:
            continue

        partition_dir = Path(stats["path"])
        partition_running = {instr: 0 for instr in INSTRUMENTS}

        for f in sorted(partition_dir.glob("*.parquet")):
            if f.stat().st_size == 0:
                continue  # zero-byte files trigger a global abort before this function is ever called

            table = pq.read_table(f, columns=["instrument_id", "trade_time"])
            files_scanned += 1

            shared_null_instrument_id_count += table.column("instrument_id").null_count
            shared_null_trade_time_count += table.column("trade_time").null_count

            for instrument in INSTRUMENTS:
                instrument_mask = pc.equal(table.column("instrument_id"), instrument)
                filtered = table.filter(instrument_mask)
                n_instrument = filtered.num_rows
                per_instrument[instrument]["instrument_rows_total"] += n_instrument

                if n_instrument > 0:
                    tt = filtered.column("trade_time").to_numpy()
                    in_range = (tt >= start_ms) & (tt < end_ms)
                    n_in_range = int(in_range.sum())
                    per_instrument[instrument]["research_day_rows_total"] += n_in_range
                    partition_running[instrument] += n_in_range

                del instrument_mask, filtered

            del table

        for instrument in INSTRUMENTS:
            per_instrument[instrument]["per_partition_research_day_rows"][label] = partition_running[instrument]

    for instrument in INSTRUMENTS:
        per_instrument[instrument]["null_instrument_id_count"] = shared_null_instrument_id_count
        per_instrument[instrument]["null_trade_time_count"] = shared_null_trade_time_count
        per_instrument[instrument]["files_scanned"] = files_scanned

    return per_instrument


def check_for_zero_byte_files_or_abort(date_str, partition_structure):
    """
    Global abort check. Any zero-byte trade file discovered is
    unexpected (the known historical ones were already removed) and
    requires investigation before the matrix can be frozen -- this
    is not a per-date failure, it stops the entire audit run.
    """
    all_zero_byte = []
    for label, stats in partition_structure.items():
        all_zero_byte.extend(stats["zero_byte_files"])

    if all_zero_byte:
        print(f"\n===== AUDIT ABORTED: UNEXPECTED ZERO-BYTE FILE(S) FOUND =====", file=sys.stderr)
        print(f"While auditing calendar date {date_str}:", file=sys.stderr)
        for path in all_zero_byte:
            print(f"  {path}", file=sys.stderr)
        print(f"\nThe known historical zero-byte trade files were already identified, "
              f"documented, and removed during the instrument-identity incident. Any "
              f"zero-byte file found now is unexpected and requires investigation "
              f"before the validation matrix can be frozen. Not excluding this date "
              f"automatically -- stopping entirely.", file=sys.stderr)
        sys.exit(1)


def evaluate_date(date_str):
    partition_structure = audit_partition_structure(date_str)

    missing_partitions = [label for label, s in partition_structure.items() if not s["exists"]]
    if missing_partitions:
        return {
            "date": date_str, "passed": False,
            "reason": f"missing required partition(s): {missing_partitions}",
        }

    check_for_zero_byte_files_or_abort(date_str, partition_structure)

    per_instrument = audit_instrument_day(date_str, partition_structure)

    failure_reasons = []
    for instrument in INSTRUMENTS:
        r = per_instrument[instrument]
        if r["null_instrument_id_count"] > 0:
            failure_reasons.append(f"{instrument}: {r['null_instrument_id_count']} null instrument_id")
        if r["null_trade_time_count"] > 0:
            failure_reasons.append(f"{instrument}: {r['null_trade_time_count']} null trade_time")
        if r["research_day_rows_total"] == 0:
            failure_reasons.append(f"{instrument}: zero research-day rows")

    passed = len(failure_reasons) == 0

    return {
        "date": date_str,
        "passed": passed,
        "reason": "; ".join(failure_reasons) if failure_reasons else None,
        "per_instrument": per_instrument,
    }


def main():
    print(f"===== COMPLETENESS AUDIT: {len(CANDIDATE_DATES)} candidate calendar dates =====")
    print("(Structural/coverage only -- no price, quantity, signal, or outcome data inspected)")
    print("(Zero-byte file discovery aborts the entire run -- see module docstring)\n")

    results = []
    for i, date_str in enumerate(CANDIDATE_DATES, start=1):
        print(f"[{i}/{len(CANDIDATE_DATES)}] Auditing {date_str}...")
        result = evaluate_date(date_str)
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status}" + (f" -- {result['reason']}" if result["reason"] else ""))

    passed_dates = [r["date"] for r in results if r["passed"]]
    failed_dates = [(r["date"], r["reason"]) for r in results if not r["passed"]]

    print(f"\n===== SUMMARY =====")
    print(f"Total candidate dates: {len(CANDIDATE_DATES)}")
    print(f"Passed (both instruments): {len(passed_dates)}")
    print(f"Failed (excluded as matched pair): {len(failed_dates)}")
    if failed_dates:
        print("\nFailed dates and reasons:")
        for date_str, reason in failed_dates:
            print(f"  {date_str}: {reason}")

    print(f"\nFinal validated matrix: {len(passed_dates)} dates x {len(INSTRUMENTS)} instruments "
          f"= {len(passed_dates) * len(INSTRUMENTS)} instrument-days")
    print("\nPassed dates:")
    for d in passed_dates:
        print(f"  {d}")


if __name__ == "__main__":
    main()
