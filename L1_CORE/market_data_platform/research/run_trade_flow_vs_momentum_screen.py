"""
Market Data Platform -- Trade-Flow vs Momentum Screen: Single-Day Runner
market_data_platform/research/run_trade_flow_vs_momentum_screen.py

v1 scope: single instrument-day only (--instrument, --date). The
8-day loop is deliberately NOT implemented yet.

Loading: true two-pass (Pass 1 counts exact N via instrument_id
only; Pass 2 allocates once and fills in place).

Decimal handling: price/quantity are Arrow decimal128(18,8) in
canonical storage (confirmed via direct schema inspection). Cast to
float64 at the Arrow level BEFORE any NumPy conversion.

Usage:
    python3 -m L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen \
        --instrument BTC-USD --date 2026-08-22 --output-dir /tmp/screen_results
"""

import argparse
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    compute_screen,
    rank_deciles,
    validate_sorted_arrays,
    HORIZONS,
    SAMPLE_EVERY_NTH,
    LOOKBACK_SECONDS,
)

CANONICAL_TRADES_ROOT = Path("/mnt/lrs001/data/market_data_platform/canonical/trades")
METHODOLOGY_VERSION = "trade_flow_vs_momentum_screen_v1"

REQUIRED_COLUMNS = ["trade_time", "trade_id", "price", "quantity", "is_buyer_maker", "instrument_id"]
MS_PER_DAY = 24 * 60 * 60 * 1000


def _rss_checkpoint(label):
    """
    Prints a high-water-mark RSS checkpoint. ru_maxrss is cumulative
    (never decreases within a process). The authoritative
    whole-process peak is measured externally via /usr/bin/time -v
    wrapping this entire script.
    """
    rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"  [RSS checkpoint: {label}] {rss_kb / 1024:.1f} MiB (high-water mark)")


def _day_bounds_ms(date_str):
    import datetime
    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    start_ms = int(d.timestamp() * 1000)
    end_ms = start_ms + MS_PER_DAY
    return start_ms, end_ms


def _require_no_null_instrument_id(table, file_path):
    """
    Fail-closed check that instrument_id itself contains no nulls in
    this file, BEFORE any instrument filtering happens. A null
    instrument_id would otherwise silently vanish from both the
    match and non-match sides of an equality filter -- Arrow's
    filter semantics do not raise for this, they simply exclude the
    row, which conflicts with the project's no-silent-dropping rule.

    Raises:
        RuntimeError: naming the file and null count.
    """
    null_count = table.column("instrument_id").null_count
    if null_count > 0:
        raise RuntimeError(
            f"{null_count} null instrument_id value(s) found in {file_path}. "
            f"A null instrument identity is a data-integrity defect and must "
            f"not be silently excluded by filtering. Refusing to proceed."
        )


def count_target_rows(files, instrument):
    """
    Pass 1: reads only instrument_id per file, verifies no nulls,
    counts rows matching the target instrument, discards. Establishes
    the exact N for Pass 2 preallocation.
    """
    total = 0
    per_file_counts = []
    for i, f in enumerate(files):
        table = pq.read_table(f, columns=["instrument_id"])
        _require_no_null_instrument_id(table, f)
        mask = pc.equal(table.column("instrument_id"), instrument)
        n = pc.sum(mask).as_py() or 0
        per_file_counts.append((f, n))
        total += n
        del table, mask
        if (i + 1) % 2000 == 0:
            print(f"  Pass 1 (counting): {i + 1}/{len(files)} files scanned, running N={total}")
    return total, per_file_counts


def _check_no_nulls(table, columns, file_path):
    """
    Fail-closed null check across the given columns of one file's
    already-filtered table.

    Raises:
        RuntimeError: naming the file, column, and null count.
    """
    for col in columns:
        null_count = table.column(col).null_count
        if null_count > 0:
            raise RuntimeError(
                f"{null_count} null value(s) found in column '{col}' in file "
                f"{file_path}. Refusing to proceed -- nulls must be resolved "
                f"upstream, not silently coerced during conversion."
            )


def load_instrument_day(files, instrument, expected_n, rss_checkpoint_fn=None):
    """
    Pass 2: allocates the five target arrays once, fills them by
    reading each file's required columns, verifying no null
    instrument_id, filtering to instrument, verifying the filter
    result, checking for nulls in the remaining columns, casting
    price/quantity to float64 at the Arrow level, and copying
    directly into the correct output slice.

    Receives:
        rss_checkpoint_fn (callable, optional): called with a label
        string immediately after the five np.empty() calls. This is
        a LIFECYCLE checkpoint, not a measurement of the arrays'
        eventual resident cost -- np.empty() reserves virtual
        address space, but those pages are typically not yet
        physically resident, so ru_maxrss may show little or no
        increase here. The after_loading checkpoint (in run())
        captures the RSS impact once the arrays are actually
        populated with data.

    Raises:
        RuntimeError: on any null instrument_id, any null value in
        the required columns, any post-filter instrument mismatch,
        any chunk that would overflow the preallocated arrays, a
        final row-count mismatch against expected_n, or any
        unexpected resulting dtype.
    """
    trade_time = np.empty(expected_n, dtype=np.int64)
    trade_id = np.empty(expected_n, dtype=np.int64)
    price = np.empty(expected_n, dtype=np.float64)
    quantity = np.empty(expected_n, dtype=np.float64)
    is_buyer_maker = np.empty(expected_n, dtype=np.bool_)

    if rss_checkpoint_fn is not None:
        rss_checkpoint_fn("after_preallocation (virtual reservation; see docstring)")

    offset = 0
    for i, f in enumerate(files):
        table = pq.read_table(f, columns=REQUIRED_COLUMNS)
        _require_no_null_instrument_id(table, f)

        mask = pc.equal(table.column("instrument_id"), instrument)
        filtered = table.filter(mask)
        n_chunk = filtered.num_rows

        if n_chunk == 0:
            del table, mask, filtered
            continue

        distinct_instruments = pc.unique(filtered.column("instrument_id")).to_pylist()
        if distinct_instruments != [instrument]:
            raise RuntimeError(
                f"Post-filter instrument check failed in {f}: expected only "
                f"'{instrument}', found {distinct_instruments}. Refusing to proceed."
            )

        _check_no_nulls(filtered, ["trade_time", "trade_id", "price", "quantity", "is_buyer_maker"], f)

        end = offset + n_chunk
        if end > expected_n:
            raise RuntimeError(
                f"Pass 2 chunk from {f} would write past the preallocated array "
                f"bound: offset={offset}, chunk={n_chunk}, expected_n={expected_n}. "
                f"Pass 1/Pass 2 disagree on row counts -- refusing to proceed "
                f"rather than risk a silent partial write or opaque broadcast error."
            )

        tt_chunk = filtered.column("trade_time").to_numpy()
        tid_chunk = filtered.column("trade_id").to_numpy()
        price_chunk = filtered.column("price").cast(pa.float64()).to_numpy()
        qty_chunk = filtered.column("quantity").cast(pa.float64()).to_numpy()
        maker_chunk = filtered.column("is_buyer_maker").to_numpy()

        trade_time[offset:end] = tt_chunk
        trade_id[offset:end] = tid_chunk
        price[offset:end] = price_chunk
        quantity[offset:end] = qty_chunk
        is_buyer_maker[offset:end] = maker_chunk
        offset = end

        del table, mask, filtered, tt_chunk, tid_chunk, price_chunk, qty_chunk, maker_chunk

        if (i + 1) % 2000 == 0:
            print(f"  Pass 2 (loading): {i + 1}/{len(files)} files processed, offset={offset}")

    if offset != expected_n:
        raise RuntimeError(
            f"Pass 1/Pass 2 row-count mismatch: Pass 1 counted {expected_n}, "
            f"Pass 2 wrote {offset}. Refusing to proceed with inconsistent data."
        )

    for name, arr, expected_dtype in [
        ("trade_time", trade_time, np.int64),
        ("trade_id", trade_id, np.int64),
        ("price", price, np.float64),
        ("quantity", quantity, np.float64),
        ("is_buyer_maker", is_buyer_maker, np.bool_),
    ]:
        if arr.dtype != expected_dtype:
            raise RuntimeError(f"{name} has dtype {arr.dtype}, expected {expected_dtype}")

    return trade_time, trade_id, price, quantity, is_buyer_maker


def validate_day_integrity(trade_time, price, quantity, date_str):
    if not np.isfinite(price).all():
        bad = (~np.isfinite(price)).sum()
        raise RuntimeError(f"{bad} non-finite price value(s) found. Refusing to proceed.")
    if not np.isfinite(quantity).all():
        bad = (~np.isfinite(quantity)).sum()
        raise RuntimeError(f"{bad} non-finite quantity value(s) found. Refusing to proceed.")
    if (price <= 0).any():
        bad = (price <= 0).sum()
        raise RuntimeError(f"{bad} non-positive price value(s) found. Refusing to proceed.")
    if (quantity <= 0).any():
        bad = (quantity <= 0).sum()
        raise RuntimeError(f"{bad} non-positive quantity value(s) found. Refusing to proceed.")

    start_ms, end_ms = _day_bounds_ms(date_str)
    out_of_range = (trade_time < start_ms) | (trade_time >= end_ms)
    if out_of_range.any():
        bad_count = out_of_range.sum()
        bad_times = trade_time[out_of_range]
        raise RuntimeError(
            f"{bad_count} row(s) have trade_time outside the requested UTC date "
            f"{date_str} [{start_ms}, {end_ms}). "
            f"Offending min={bad_times.min()}, max={bad_times.max()}. Refusing to proceed."
        )


def build_comparative_population(result, horizon):
    return_col = f"return_{horizon}s"
    mask = result["common_eligible"] & ~np.isnan(result[return_col])

    return {
        "mask": mask,
        "n": int(mask.sum()),
        "sample_trade_time": result["sample_trade_time"][mask],
        "sample_trade_id": result["sample_trade_id"][mask],
        "imbalance": result["imbalance"][mask],
        "momentum": result["momentum"][mask],
        "return": result[return_col][mask],
    }


def summarize_feature_deciles(feature_values, returns, trade_time, trade_id):
    deciles = rank_deciles(feature_values, trade_time, trade_id)

    decile_summary = []
    decile_means = {}
    for d in range(10):
        in_decile = deciles == d
        n = int(in_decile.sum())
        mean_ret = float(np.mean(returns[in_decile])) if n > 0 else None
        mean_ret_bp = mean_ret * 10000 if mean_ret is not None else None
        decile_summary.append({
            "decile": d,
            "n": n,
            "mean_return": mean_ret,
            "mean_return_bp": mean_ret_bp,
        })
        decile_means[d] = mean_ret

    d9 = decile_means.get(9)
    d0 = decile_means.get(0)
    if d9 is not None and d0 is not None:
        spread_raw = d9 - d0
        spread_bp = spread_raw * 10000
    else:
        spread_raw = None
        spread_bp = None

    return {
        "decile_summary": decile_summary,
        "d9_minus_d0_raw": spread_raw,
        "d9_minus_d0_bp": spread_bp,
    }


def get_git_sha():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def run(instrument, date_str, output_dir):
    t_start = time.time()
    print(f"===== {instrument} {date_str} =====")

    date_dir = CANONICAL_TRADES_ROOT / f"date={date_str}"
    if not date_dir.is_dir():
        raise RuntimeError(f"Date partition does not exist: {date_dir}")

    files = sorted(date_dir.glob("*.parquet"))
    if not files:
        raise RuntimeError(f"No Parquet files found in {date_dir}")
    print(f"Discovered {len(files)} files in {date_dir}")

    print("Pass 1: counting target-instrument rows...")
    n_target, per_file_counts = count_target_rows(files, instrument)
    if n_target == 0:
        raise RuntimeError(f"Zero rows found for instrument {instrument} on {date_str}.")
    print(f"Pass 1 complete: N={n_target}")
    _rss_checkpoint("after_pass1_counting")

    print("Pass 2: preallocating arrays and loading...")
    trade_time, trade_id, price, quantity, is_buyer_maker = load_instrument_day(
        files, instrument, n_target, rss_checkpoint_fn=_rss_checkpoint
    )
    print(f"Pass 2 complete: loaded {len(trade_time)} rows")
    _rss_checkpoint("after_loading")

    print("Validating day integrity (finite/positive values, UTC date range)...")
    validate_day_integrity(trade_time, price, quantity, date_str)
    print("Integrity validation passed.")

    print("Sorting by (trade_time, trade_id)...")
    _rss_checkpoint("before_sort")
    order = np.lexsort((trade_id, trade_time))
    _rss_checkpoint("after_order_created")

    trade_time = trade_time[order]
    trade_id_sorted = trade_id[order]
    del trade_id
    trade_id = trade_id_sorted
    price = price[order]
    quantity = quantity[order]
    is_buyer_maker = is_buyer_maker[order]
    del order
    _rss_checkpoint("after_sorted_arrays")

    validate_sorted_arrays(trade_time, trade_id, price, quantity, is_buyer_maker)
    print("Sort validated.")

    print("Running kernel (compute_screen)...")
    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    print(f"Kernel complete: {len(result['sample_trade_time'])} sampled observations")
    _rss_checkpoint("after_compute_screen")

    print("Summarizing per-horizon comparative deciles...")
    horizon_results = {}
    for h in HORIZONS:
        pop = build_comparative_population(result, h)
        imbalance_summary = summarize_feature_deciles(
            pop["imbalance"], pop["return"], pop["sample_trade_time"], pop["sample_trade_id"]
        )
        momentum_summary = summarize_feature_deciles(
            pop["momentum"], pop["return"], pop["sample_trade_time"], pop["sample_trade_id"]
        )
        horizon_results[h] = {
            "n": pop["n"],
            "imbalance": imbalance_summary,
            "momentum": momentum_summary,
        }
        print(f"  Horizon {h}s: n={pop['n']} "
              f"imbalance_D9-D0_bp={imbalance_summary['d9_minus_d0_bp']} "
              f"momentum_D9-D0_bp={momentum_summary['d9_minus_d0_bp']}")
    _rss_checkpoint("after_summarization")

    elapsed = time.time() - t_start

    output = {
        "methodology": METHODOLOGY_VERSION,
        "instrument": instrument,
        "date": date_str,
        "source_root": str(CANONICAL_TRADES_ROOT),
        "source_file_count": len(files),
        "source_rows_target_instrument": n_target,
        "sample_every_nth": SAMPLE_EVERY_NTH,
        "lookback_s": LOOKBACK_SECONDS,
        "horizons_s": HORIZONS,
        "git_sha": get_git_sha(),
        "elapsed_seconds": elapsed,
        "results_by_horizon": {str(h): v for h, v in horizon_results.items()},
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / f"{instrument}_{date_str}.json"
    tmp_path = output_dir / f"{instrument}_{date_str}.json.tmp"

    with open(tmp_path, "w") as f:
        json.dump(output, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp_path, final_path)

    print(f"\nCOMPLETE ({elapsed:.1f}s). Result written to {final_path}")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    run(args.instrument, args.date, args.output_dir)


if __name__ == "__main__":
    main()
