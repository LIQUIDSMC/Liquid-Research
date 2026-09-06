"""
Market Data Platform -- Expanded Validation Batch Orchestrator
market_data_platform/research/run_expanded_batch_screen.py

Pure orchestration, identical pattern to run_batch_screen.py (the
original 8-day screen), reused unchanged. Does NOT import or modify
any kernel, loader, feature, sampling, horizon, or decile logic --
only invokes the existing, already-validated single-day runner
(run_trade_flow_vs_momentum_screen.py) as a subprocess, once per
instrument-day, strictly sequentially. Never runs two children
concurrently.

FROZEN MATRIX (locked after the read-only completeness audit,
run_completeness_audit.py, which found 25/28 candidate dates pass):

  Block A: 2026-07-22 through 2026-08-09 (19 dates)
  Block B retained: 2026-08-26, 27, 28, 29, 30, 2026-09-03 (6 dates)
  Excluded (no backfill): 2026-08-31, 2026-09-01, 2026-09-02
    -- reason: required date=2026-09-01 storage partition is absent.
    The CAUSE of that absence is not established here; it remains a
    separate, unproven operational question and does not change this
    validation matrix.

  25 dates x 2 instruments (BTC-USD, ETH-USD) = 50 instrument-days.
  Execution order is date-paired (BTC then ETH for each date, in
  date order) purely for operational clarity on interruption/resume
  -- this does not alter the frozen sample or methodology.

Frozen promotion gate (documented here for provenance, evaluated
separately by the aggregation script, not by this orchestrator):
  - sign consistency >= 33/50 at each of 5s/15s/30s/60s (ceil(0.65*50))
  - combined median D9-D0 > 0 at all four horizons
  - BTC median > 0 and ETH median > 0 independently at all horizons
  - removing any single instrument-day must not flip combined mean
    negative at any horizon
  - 60s median D9-D0 >= +0.10 bp
  - decile shape / trimmed mean / influential-date diagnostics
    reported, not hard gates

Fail-closed evidence directory: refuses to start if OUTPUT_DIR
already exists and is non-empty, so every validation run produces an
unambiguous, uncontaminated evidence set. Does not auto-clean --
deletion would destroy provenance; a pre-existing non-empty
directory must be moved/renamed manually before re-running.

Usage:
    python3 -m L1_CORE.market_data_platform.research.run_expanded_batch_screen
"""

import subprocess
import sys
import time
from pathlib import Path

BLOCK_A_DATES = [f"2026-07-{d:02d}" for d in range(22, 32)] + [f"2026-08-{d:02d}" for d in range(1, 10)]
BLOCK_B_DATES = ["2026-08-26", "2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30", "2026-09-03"]
FROZEN_DATES = BLOCK_A_DATES + BLOCK_B_DATES  # 25 dates

INSTRUMENTS = ["BTC-USD", "ETH-USD"]

# Date-paired execution order (BTC then ETH per date, in date order),
# for operational clarity on interruption/resume -- does not alter
# the frozen sample or methodology.
FROZEN_MATRIX = [(instrument, date_str) for date_str in FROZEN_DATES for instrument in INSTRUMENTS]

OUTPUT_DIR = "/tmp/expanded_screen_results"
LOG_DIR = "/tmp/expanded_screen_results/logs"


def run_one(instrument, date_str, index, total):
    log_path = f"{LOG_DIR}/{instrument}_{date_str}.log"
    print(f"\n===== RUN {index}/{total}: {instrument} {date_str} =====")
    print(f"  Log: {log_path}")

    cmd = [
        "/usr/bin/time", "-v",
        sys.executable, "-m",
        "L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen",
        "--instrument", instrument,
        "--date", date_str,
        "--output-dir", OUTPUT_DIR,
    ]

    t_start = time.time()
    with open(log_path, "w") as log_file:
        result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    elapsed = time.time() - t_start

    success = result.returncode == 0
    status = "COMPLETED" if success else f"FAILED (exit {result.returncode})"
    print(f"  {status} in {elapsed:.1f}s")

    return success, elapsed, log_path


def main():
    output_path = Path(OUTPUT_DIR)

    if output_path.exists() and any(output_path.iterdir()):
        print(
            f"ERROR: output directory already exists and is non-empty: {OUTPUT_DIR}\n"
            f"Refusing to mix or overwrite validation evidence. Move or rename it "
            f"manually before re-running this validation.",
            file=sys.stderr,
        )
        sys.exit(1)

    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    total = len(FROZEN_MATRIX)

    print(f"===== EXPANDED BATCH SCREEN: {total} instrument-days, strictly sequential =====")
    print(f"({len(FROZEN_DATES)} dates x {len(INSTRUMENTS)} instruments)\n")

    results = []
    for i, (instrument, date_str) in enumerate(FROZEN_MATRIX, start=1):
        success, elapsed, log_path = run_one(instrument, date_str, i, total)
        results.append({
            "instrument": instrument, "date": date_str,
            "success": success, "elapsed_seconds": elapsed, "log_path": log_path,
        })

        if not success:
            print(f"\n===== BATCH STOPPED: {instrument} {date_str} failed. "
                  f"See {log_path} for details. =====")
            print(f"Completed before failure: {i - 1}/{total}")
            sys.exit(1)

    print(f"\n===== BATCH COMPLETE: all {total} instrument-days succeeded =====")
    for r in results:
        print(f"  {r['instrument']} {r['date']}: {r['elapsed_seconds']:.1f}s")


if __name__ == "__main__":
    main()
