"""
Market Data Platform -- Sequential Batch Orchestrator
market_data_platform/research/run_batch_screen.py

Pure orchestration. Does NOT import or modify any kernel, loader,
feature, sampling, horizon, or decile logic -- it only invokes the
already-validated single-day runner
(run_trade_flow_vs_momentum_screen.py) as a subprocess, once per
instrument-day, strictly sequentially. Never runs two children
concurrently -- the single-day runner's peak RSS (~237MiB, measured
directly on real BTC-USD 2026-08-22 data) leaves headroom for one
child at a time on this Pi (~905MiB RAM), but concurrent runs would
not.

Frozen matrix (hard-coded, not configurable via CLI -- this batch
runner exists for exactly this one 8-date screen, not as a general
tool). BTC-USD 2026-08-22 is intentionally re-run here even though
it was already completed successfully in isolation, so all 8 results
come from one uniform batch execution/provenance.

    BTC-USD: 2026-08-10, 2026-08-18, 2026-08-22, 2026-08-25
    ETH-USD: 2026-08-10, 2026-08-18, 2026-08-22, 2026-08-25

Fail-closed: if any child exits nonzero, the batch stops immediately
and reports exactly which instrument-day failed. Already-completed
instrument-days' results and logs remain on disk.

Note: results/logs are written under /tmp, which is not durable
across a reboot. Copy the final JSONs/logs to persistent storage
before treating them as retained research evidence.

Usage:
    python3 -m L1_CORE.market_data_platform.research.run_batch_screen
"""

import subprocess
import sys
import time
from pathlib import Path

FROZEN_MATRIX = [
    ("BTC-USD", "2026-08-10"),
    ("BTC-USD", "2026-08-18"),
    ("BTC-USD", "2026-08-22"),
    ("BTC-USD", "2026-08-25"),
    ("ETH-USD", "2026-08-10"),
    ("ETH-USD", "2026-08-18"),
    ("ETH-USD", "2026-08-22"),
    ("ETH-USD", "2026-08-25"),
]

OUTPUT_DIR = "/tmp/screen_results"
LOG_DIR = "/tmp/screen_results/logs"


def run_one(instrument, date_str, index, total):
    """
    Runs exactly one instrument-day via the existing single-day
    runner, wrapped in /usr/bin/time -v, writing a dedicated log
    file. Blocks until the child fully exits before returning --
    no concurrency of any kind.

    Returns:
        (success: bool, elapsed_seconds: float, log_path: str)
    """
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
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    total = len(FROZEN_MATRIX)

    print(f"===== BATCH SCREEN: {total} instrument-days, strictly sequential =====")

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
