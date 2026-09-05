"""
Market Data Platform -- Trade-Flow vs Momentum Screen: Single-Day Runner
market_data_platform/research/run_trade_flow_vs_momentum_screen.py

v1 scope: single instrument-day only (--instrument, --date). The
8-day loop is deliberately NOT implemented yet.

REVISION 2: a storage partition (date=YYYY-MM-DD) is NOT the same
thing as a trade_time research day. Direct boundary evidence shows
that rows can cross storage-partition boundaries relative to their
own trade_time, consistent with storage partitioning by receipt
time (this was not independently verified against storage.py's
source -- it is an evidence-based inference, not a confirmed fact).
Observed directly: BTC-USD 2026-08-22 had one row spill into the
2026-08-23 partition, and one row in the 2026-08-22 partition
actually belonged to 2026-08-21. This runner therefore reads the
target date partition PLUS its immediate previous and next date
partitions, and defines the research day purely by the trade_time
interval [start_ms, end_ms) -- never by which partition a row was
physically stored in.

For this frozen 8-date historical study (all interior dates), all
three partitions (prev/target/next) are REQUIRED to exist; a missing
adjacent partition is treated as an inability to verify completeness
and is a hard failure. Edge-of-corpus dates are explicitly out of
scope for this runner.

Loading: two logical passes across the three selected partitions'
files (Pass 1 reads 2 columns, Pass 2 reads all 6 required columns).
Both passes apply the identical is_in_research_day() predicate.
Null instrument_id and null trade_time are rejected on the raw,
unfiltered table immediately after reading -- before either the
instrument filter or the day-range filter, so a null value can never
silently vanish through filtering.

Decimal handling unchanged from v1: price/quantity are Arrow
decimal128(18,8), cast to float64 at the Arrow level before any
NumPy conversion.

Provenance note: for adjacent (prev/next) partitions,
out_of_range_rows will naturally be nearly the entire partition's
target-instrument row count, since almost none of a neighboring
day's trades fall inside the target research day. out_of_range_rows
is accurate accounting, not a "spillover" count -- the meaningful
cross-partition contribution is a partition's in_range_rows.

Usage:
    python3 -m L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen \
        --instrument BTC-USD --date 2026-08-22 --output-dir /tmp/screen_results
"""

import argparse
import datetime
import json
import os
import resource
import subprocess
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
METHODOLOGY_VERSION = "trade_flow_vs_momentum_screen_v2_multi_partition"

REQUIRED_COLUMNS = ["trade_time", "trade_id", "price", "quantity", "is_buyer_maker", "instrument_id"]
MS_PER_DAY = 24 * 60 * 60 * 1000


def _rss_checkpoint(label):
    rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"  [RSS checkpoint: {label}] {rss_kb / 1024:.1f} MiB (high-water mark)")


def _day_bounds_ms(date_str):
    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    start_ms = int(d.timestamp() * 1000)
    end_ms = start_ms + MS_PER_DAY
    return start_ms, end_ms


def _adjacent_date_str(date_str, offset_days):
    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    d2 = d + datetime.timedelta(days=offset_days)
    return d2.strftime("%Y-%m-%d")


def is_in_research_day(trade_time_array, start_ms, end_ms):
    """
    The single, shared research-day inclusion predicate. Called
    identically by both Pass 1 and Pass 2 -- what matters is that
    both call sites use this same function (proven by the loader
    fixture), not merely that they happen to look similar.
    """
    return (trade_time_array >= start_ms) & (trade_time_array < end_ms)


def _resolve_source_partitions(date_str):
    """
    Resolves the three required partition directories (previous,
    target, next). All three must exist for this frozen 8-date
    study -- a missing adjacent partition means completeness cannot
    be verified, which is a hard failure here.

    Raises:
        RuntimeError: if any of the three directories doesn't exist.
    """
    prev_date = _adjacent_date_str(date_str, -1)
    next_date = _adjacent_date_str(date_str, +1)

    partitions = [
        (prev_date, CANONICAL_TRADES_ROOT / f"date={prev_date}"),
        (date_str, CANONICAL_TRADES_ROOT / f"date={date_str}"),
        (next_date, CANONICAL_TRADES_ROOT / f"date={next_date}"),
    ]

    for label, path in partitions:
        if not path.is_dir():
            raise RuntimeError(
                f"Required source partition does not exist: {path} "
                f"(needed to verify completeness of the {date_str} trade_time "
                f"research day). This runner requires all three of "
                f"prev/target/next partitions; edge-of-corpus dates are out "
                f"of scope."
            )

    return partitions


def _require_no_null_raw(table, file_path):
    """
    Fail-closed check on the RAW, unfiltered table: instrument_id
    and trade_time must have zero nulls before any filtering.
    """
    for col in ("instrument_id", "trade_time"):
        null_count = table.column(col).null_count
        if null_count > 0:
            raise RuntimeError(
                f"{null_count} null value(s) found in raw column '{col}' in "
                f"file {file_path}, before any filtering. Refusing to proceed."
            )


def _check_no_nulls_post_filter(table, columns, file_path):
    for col in columns:
        null_count = table.column(col).null_count
        if null_count > 0:
            raise RuntimeError(
                f"{null_count} null value(s) found in column '{col}' in file "
                f"{file_path} (post-filter). Refusing to proceed."
            )


def count_target_rows(partitions, instrument, start_ms, end_ms):
    """
    Pass 1: for each of the three partitions, for each file, reads
    only [instrument_id, trade_time], rejects raw nulls, filters to
    the target instrument, applies is_in_research_day(), and counts.
    """
    total_n = 0
    per_partition_stats = []

    for date_label, date_dir in partitions:
        files = sorted(date_dir.glob("*.parquet"))
        target_instrument_rows = 0
        in_range_rows = 0

        for i, f in enumerate(files):
            table = pq.read_table(f, columns=["instrument_id", "trade_time"])
            _require_no_null_raw(table, f)

            instrument_mask = pc.equal(table.column("instrument_id"), instrument)
            filtered = table.filter(instrument_mask)
            n_instrument = filtered.num_rows
            target_instrument_rows += n_instrument

            if n_instrument > 0:
                tt = filtered.column("trade_time").to_numpy()
                in_range_mask = is_in_research_day(tt, start_ms, end_ms)
                in_range_rows += int(in_range_mask.sum())

            del table, instrument_mask, filtered

            if (i + 1) % 3000 == 0:
                print(f"  Pass 1 [{date_label}]: {i + 1}/{len(files)} files scanned")

        out_of_range_rows = target_instrument_rows - in_range_rows
        per_partition_stats.append({
            "date": date_label,
            "file_count": len(files),
            "target_instrument_rows": target_instrument_rows,
            "in_range_rows": in_range_rows,
            "out_of_range_rows": out_of_range_rows,
        })
        total_n += in_range_rows
        print(f"  Pass 1 [{date_label}] complete: target_instrument_rows="
              f"{target_instrument_rows}, in_range_rows={in_range_rows}")

    return total_n, per_partition_stats


def load_instrument_day(partitions, instrument, start_ms, end_ms, expected_n, rss_checkpoint_fn=None):
    """
    Pass 2: allocates the five target arrays once, then for each
    partition, for each file: reads all required columns, rejects
    raw nulls, filters to instrument, applies is_in_research_day(),
    verifies the post-filter instrument set, checks remaining
    columns for nulls, casts price/quantity to float64 at the Arrow
    level, and copies into the correct output slice.
    """
    trade_time = np.empty(expected_n, dtype=np.int64)
    trade_id = np.empty(expected_n, dtype=np.int64)
    price = np.empty(expected_n, dtype=np.float64)
    quantity = np.empty(expected_n, dtype=np.float64)
    is_buyer_maker = np.empty(expected_n, dtype=np.bool_)

    if rss_checkpoint_fn is not None:
        rss_checkpoint_fn("after_preallocation (virtual reservation; see docstring)")

    offset = 0
    for date_label, date_dir in partitions:
        files = sorted(date_dir.glob("*.parquet"))

        for i, f in enumerate(files):
            table = pq.read_table(f, columns=REQUIRED_COLUMNS)
            _require_no_null_raw(table, f)

            instrument_mask = pc.equal(table.column("instrument_id"), instrument)
            instrument_filtered = table.filter(instrument_mask)

            if instrument_filtered.num_rows == 0:
                del table, instrument_mask, instrument_filtered
                continue

            tt_all = instrument_filtered.column("trade_time").to_numpy()
            day_mask = is_in_research_day(tt_all, start_ms, end_ms)
            n_chunk = int(day_mask.sum())

            if n_chunk == 0:
                del table, instrument_mask, instrument_filtered, tt_all, day_mask
                continue

            filtered = instrument_filtered.filter(pa.array(day_mask))

            distinct_instruments = pc.unique(filtered.column("instrument_id")).to_pylist()
            if distinct_instruments != [instrument]:
                raise RuntimeError(
                    f"Post-filter instrument check failed in {f} ({date_label}): "
                    f"expected only '{instrument}', found {distinct_instruments}. "
                    f"Refusing to proceed."
                )

            _check_no_nulls_post_filter(
                filtered, ["trade_id", "price", "quantity", "is_buyer_maker"], f
            )

            end = offset + n_chunk
            if end > expected_n:
                raise RuntimeError(
                    f"Pass 2 chunk from {f} ({date_label}) would write past the "
                    f"preallocated array bound: offset={offset}, chunk={n_chunk}, "
                    f"expected_n={expected_n}. Pass 1/Pass 2 disagree -- refusing "
                    f"to proceed."
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

            del (table, instrument_mask, instrument_filtered, tt_all, day_mask, filtered,
                 tt_chunk, tid_chunk, price_chunk, qty_chunk, maker_chunk)

            if (i + 1) % 3000 == 0:
                print(f"  Pass 2 [{date_label}]: {i + 1}/{len(files)} files processed, offset={offset}")

        print(f"  Pass 2 [{date_label}] complete, running offset={offset}")

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


def validate_day_integrity(trade_time, price, quantity, start_ms, end_ms):
    """
    Post-load integrity assertions. The UTC range check should now
    NEVER fire -- if it does, that indicates a bug in the new
    loader, not an expected data-boundary artifact.
    """
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

    out_of_range = ~is_in_research_day(trade_time, start_ms, end_ms)
    if out_of_range.any():
        bad_count = out_of_range.sum()
        bad_times = trade_time[out_of_range]
        raise RuntimeError(
            f"INTERNAL INVARIANT VIOLATION: {bad_count} row(s) passed the loader "
            f"but are outside [{start_ms}, {end_ms}). This should be impossible "
            f"with the multi-partition loader -- offending min={bad_times.min()}, "
            f"max={bad_times.max()}. This indicates a loader bug."
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
    print(f"===== {instrument} {date_str} (multi-partition, trade_time-defined day) =====")

    start_ms, end_ms = _day_bounds_ms(date_str)
    partitions = _resolve_source_partitions(date_str)
    print(f"Source partitions required and present: {[label for label, _ in partitions]}")

    print("Pass 1: counting in-range target-instrument rows across all 3 partitions...")
    n_target, per_partition_stats = count_target_rows(partitions, instrument, start_ms, end_ms)
    if n_target == 0:
        raise RuntimeError(f"Zero in-range rows found for {instrument} on {date_str}.")
    print(f"Pass 1 complete: total in-range N={n_target}")
    _rss_checkpoint("after_pass1_counting")

    print("Pass 2: preallocating arrays and loading across all 3 partitions...")
    trade_time, trade_id, price, quantity, is_buyer_maker = load_instrument_day(
        partitions, instrument, start_ms, end_ms, n_target, rss_checkpoint_fn=_rss_checkpoint
    )
    print(f"Pass 2 complete: loaded {len(trade_time)} rows")
    _rss_checkpoint("after_loading")

    print("Validating day integrity (finite/positive values, UTC in-range invariant)...")
    validate_day_integrity(trade_time, price, quantity, start_ms, end_ms)
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
        "source_partitions": per_partition_stats,
        "total_in_range_rows": n_target,
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
