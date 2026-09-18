"""
L1_CORE/market_data_platform/research/causal_fixed_horizon_gross_edge_v2_eth_replication.py

Experiment 1v2: ETH Post-Entry Gross-Edge Replication Test.

Question (frozen before execution): Does the post-causal-entry ETH
directional effect observed on the Aug27 DISCOVERY population
reproduce across nine previously unexamined N10-eligible ETH
instrument-days spanning the early- and late-August threshold
ENVIRONMENTS (observed threshold clustering, NOT independently shown
to correspond to distinct market conditions -- "environment", not
"regime"), particularly at the prospectively retained 15s and 30s
horizons?

FROZEN before code was written:
  Instrument:            ETH-USD only.
  Replication dates:     exactly the 9 below (selection rule stated
                          before outcomes seen: within each available
                          N10-eligible ETH date cluster, select
                          alternating/spread dates covering the
                          temporal span, plus available late-cluster
                          endpoints, excluding discovery date Aug27).
  Discovery date Aug27:  EXCLUDED from all replication aggregates.
  N:                     10, unchanged.
  Thresholds:            exact pre-existing causal N10 threshold-
                          stability values per date, NOT recalculated.
  Entry:                 exact Delta=0 NEW entry methodology (from
                          the audited causal_fixed_horizon_gross_edge_v1.py,
                          which remains unmodified). 100% Delta=0
                          entry availability is REQUIRED per date --
                          a structural hard-fail, not a soft warning,
                          since partial availability would make the
                          replication denominator chronology-dependent.
  Horizons:              5s/15s/30s/60s, unchanged. 15s/30s PRIMARY
                          CONFIRMATORY. 5s/60s secondary/reference.
  Directions:            ALL actionable signals evaluated. LONG and
                          SHORT reported separately at every level,
                          including the primary per-day/cross-day
                          table -- NOT a long-only filter.
  Excluded entirely:     fees, spread, slippage, stops, targets,
                          sizing, threshold optimization, horizon
                          optimization, parameter tuning.
  Missing/failed dates:  remain visible; NEVER silently substituted.
  Structural failure:    is NOT economic failure -- reported and
                          excluded from pooled/cross-day aggregates,
                          never discarded silently or backfilled.

GATE 7 (exit-horizon coverage) IS FULLY EMPIRICAL AND FAIL-CLOSED:
  Stage A: extend validated physical chronology (by receipt time) to
  resolve the Delta=0 NEW entries. Must reach 100% entry availability
  or the date is a STRUCTURAL FAILURE.
  Stage B: once entry_time is known for every entry, compute the
  REAL required exchange-time target (max(entry_time) + 60s) and
  continue the SAME validated chronology stream, extending by
  receipt time in fixed increments, until that exchange-time target
  is empirically covered OR the validated 14-day forward discovery
  universe is demonstrably exhausted (no arbitrary iteration cap --
  the loop bound is the discovery universe itself, not a guessed
  retry count). If Stage B coverage is not achieved, the date is a
  STRUCTURAL FAILURE -- exit construction does not proceed on an
  unproven coverage claim.

PRIMARY EVIDENCE STANDARD (addresses pseudoreplication):
  Each INSTRUMENT-DAY is one replication unit. The primary per-day
  and cross-day tables report ALL / LONG / SHORT separately at 15s
  and 30s (5s/60s as secondary reference). Cross-day summaries:
  mean-of-day-means, median-of-day-means, mean-of-day-medians, and
  positive-day count, computed separately for ALL/LONG/SHORT.
  Signal-level POOLED statistics (all days combined, plus EARLY vs
  LATE threshold-environment splits) are computed from the per-signal
  .npz artifacts and reported as SECONDARY evidence, explicitly
  labeled as such, since pooling lets one large day dominate.

  No success threshold ("pooled mean > 0") is declared anywhere in
  this script. It reports evidence for human interpretation.

Reuses the exact validated reconstruction/dedup/K5/F-R-A and
Delta=0/fixed-horizon-exit machinery from
causal_fixed_horizon_gross_edge_v1.py (copied, not imported -- that
script executes its full experiment at module load and its own
results/commit remain untouched).

Canonical storage read-only. No frozen-kernel changes.
"""

import heapq
import gc
import json
import sys
sys.path.insert(0, '/mnt/lrs001/liquid-research-l0l4')
import numpy as np
import pyarrow.parquet as pq
import pyarrow.compute as pc
from pathlib import Path
from datetime import datetime, timedelta, timezone

from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    compute_screen, validate_sorted_arrays, SAMPLE_EVERY_NTH, LOOKBACK_SECONDS
)

MAX_K = 200
MAX_X_MS = 2000
K_POLICY = 5
MAX_FORWARD_DAYS_SEARCH = 14
LOOKBACK_MS = int(LOOKBACK_SECONDS * 1000)
SEARCH_WINDOW_DAYS = 2
SAFETY_MARGIN_MS = 60_000

HORIZONS_MS = [5_000, 15_000, 30_000, 60_000]
PRIMARY_CONFIRMATORY_HORIZONS_MS = [15_000, 30_000]
HORIZON_MAX_MS = max(HORIZONS_MS)

INSTRUMENT = "ETH-USD"

EARLY_THRESHOLD_ENVIRONMENT_DATES = [
    "2026-08-01", "2026-08-03", "2026-08-05", "2026-08-07", "2026-08-09",
]
LATE_THRESHOLD_ENVIRONMENT_DATES = [
    "2026-08-26", "2026-08-28", "2026-08-29", "2026-08-30",
]
REPLICATION_DATES = EARLY_THRESHOLD_ENVIRONMENT_DATES + LATE_THRESHOLD_ENVIRONMENT_DATES
DISCOVERY_DATE_EXCLUDED = "2026-08-27"

root = Path("/mnt/lrs001/data/market_data_platform/canonical/trades")

OUTPUT_DIR = Path("/tmp/causal_fixed_horizon_gross_edge_v2_eth_replication_results")
if OUTPUT_DIR.exists():
    raise RuntimeError(
        f"FATAL: output directory already exists: {OUTPUT_DIR}. "
        f"Refusing to overwrite or mix evidence from another run."
    )
OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

THRESHOLD_ARTIFACT = Path(
    "L1_CORE/market_data_platform/research/results/"
    "threshold_stability_v1/threshold_stability_results.json"
)

def load_frozen_eth_n10_thresholds(dates):
    data = json.loads(THRESHOLD_ARTIFACT.read_text())
    thresholds = {}
    missing = []
    for d in dates:
        rec = next(
            (x for x in data
             if isinstance(x, dict)
             and x.get("instrument") == "ETH-USD"
             and x.get("target_date") == d
             and x.get("n") == 10
             and x.get("eligible") is True),
            None
        )
        if rec is None:
            missing.append(d)
            continue
        thresholds[d] = {"p10": rec["historical_p10"], "p90": rec["historical_p90"],
                          "obs": rec["historical_observation_count"]}
    if missing:
        raise RuntimeError(
            f"FATAL: required frozen N10 ETH-USD threshold missing/ineligible for "
            f"dates: {missing}. No skipping, no substitution -- aborting."
        )
    return thresholds

CAUSAL_N10_THRESHOLDS = load_frozen_eth_n10_thresholds(REPLICATION_DATES)

print("===== FROZEN N10 THRESHOLDS LOADED (not recalculated) =====")
for d in REPLICATION_DATES:
    t = CAUSAL_N10_THRESHOLDS[d]
    print(f"  {d}: P10={t['p10']:.6f} P90={t['p90']:.6f} obs={t['obs']}")
print()


# ============================================================
# Reconstruction machinery -- copied from the audited v1
# (SHA-256 51eb33cb...9afa, committed 8ad2edd). Not modified.
# ============================================================

def date_bounds_ms(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(d.timestamp() * 1000), int((d + timedelta(days=1)).timestamp() * 1000)


def search_window_labels(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return [(d + timedelta(days=offset)).isoformat()
            for offset in range(-SEARCH_WINDOW_DAYS, SEARCH_WINDOW_DAYS + 1)]


def find_contributing_files(instrument, date_str, start_ms, end_ms):
    contributing = []
    for label in search_window_labels(date_str):
        partition_dir = root / f"date={label}"
        if not partition_dir.exists():
            continue
        for f in sorted(partition_dir.glob("*.parquet")):
            table = pq.read_table(f, columns=["instrument_id", "trade_time"])
            mask = pc.and_(
                pc.equal(table.column("instrument_id"), instrument),
                pc.and_(pc.greater_equal(table.column("trade_time"), start_ms), pc.less(table.column("trade_time"), end_ms)),
            )
            if table.filter(mask).num_rows > 0:
                contributing.append(f)
    return contributing


def derive_receipt_range_order(instrument, date_str, contributing_files, start_ms, end_ms):
    records = []
    for f in contributing_files:
        table = pq.read_table(f, columns=["instrument_id", "trade_time", "timestamp_received"])
        mask = pc.and_(
            pc.equal(table.column("instrument_id"), instrument),
            pc.and_(pc.greater_equal(table.column("trade_time"), start_ms), pc.less(table.column("trade_time"), end_ms)),
        )
        filtered = table.filter(mask)
        tr = filtered.column("timestamp_received").to_numpy()
        n = len(tr)
        if n > 1 and not bool((np.diff(tr) >= 0).all()):
            raise RuntimeError(f"STRUCTURAL FAIL: {f} not internally receipt-monotonic (target-filtered).")
        records.append({"path": f, "first_received": int(tr[0]), "last_received": int(tr[-1])})

    by_first = sorted(records, key=lambda r: r["first_received"])
    firsts = [r["first_received"] for r in by_first]
    if len(set(firsts)) != len(firsts):
        raise RuntimeError("STRUCTURAL FAIL: target-filtered Gate A -- duplicate first_received.")
    for i in range(1, len(by_first)):
        if by_first[i-1]["last_received"] > by_first[i]["first_received"]:
            raise RuntimeError("STRUCTURAL FAIL: target-filtered Gate A -- adjacent overlap.")
        if by_first[i-1]["last_received"] == by_first[i]["first_received"]:
            raise RuntimeError("STRUCTURAL FAIL: target-filtered Gate A -- exact tie boundary.")
    running_max = -1
    for r in by_first:
        if r["first_received"] < running_max:
            raise RuntimeError("STRUCTURAL FAIL: target-filtered Gate A -- global overlap.")
        running_max = max(running_max, r["last_received"])

    return [r["path"] for r in by_first]


def derive_physical_file_chronology(instrument, file_paths):
    records = []
    for f in file_paths:
        table = pq.read_table(f, columns=["instrument_id", "timestamp_received"])
        mask = pc.equal(table.column("instrument_id"), instrument)
        filtered = table.filter(mask)
        if filtered.num_rows == 0:
            continue
        tr = filtered.column("timestamp_received").to_numpy()
        n = len(tr)
        if n > 1 and not bool((np.diff(tr) >= 0).all()):
            raise RuntimeError(f"STRUCTURAL FAIL: {f} not internally receipt-monotonic (physical, complete stream).")
        records.append({"path": f, "first_received": int(tr[0]), "last_received": int(tr[-1])})

    by_first = sorted(records, key=lambda r: r["first_received"])
    firsts = [r["first_received"] for r in by_first]
    if len(set(firsts)) != len(firsts):
        raise RuntimeError("STRUCTURAL FAIL: physical chronology Gate A -- duplicate first_received.")
    for i in range(1, len(by_first)):
        if by_first[i-1]["last_received"] > by_first[i]["first_received"]:
            raise RuntimeError("STRUCTURAL FAIL: physical chronology Gate A -- adjacent overlap.")
        if by_first[i-1]["last_received"] == by_first[i]["first_received"]:
            raise RuntimeError("STRUCTURAL FAIL: physical chronology Gate A -- exact tie boundary.")
    running_max = -1
    for r in by_first:
        if r["first_received"] < running_max:
            raise RuntimeError("STRUCTURAL FAIL: physical chronology Gate A -- global overlap (chronology ambiguity at boundary).")
        running_max = max(running_max, r["last_received"])

    physical_file_order = [r["path"] for r in by_first]
    return physical_file_order, {f: i for i, f in enumerate(physical_file_order)}


def reconstruct_population(instrument, date_str):
    start_ms, end_ms = date_bounds_ms(date_str)
    contributing = find_contributing_files(instrument, date_str, start_ms, end_ms)
    if not contributing:
        raise RuntimeError(f"STRUCTURAL FAIL: no contributing files for {instrument} {date_str}")

    file_paths = derive_receipt_range_order(instrument, date_str, contributing, start_ms, end_ms)

    tt_list, tid_list, tr_list, price_list, qty_list, maker_list, fidx_list, rord_list = [], [], [], [], [], [], [], []
    for file_idx, f in enumerate(file_paths):
        table = pq.read_table(f, columns=["instrument_id", "trade_time", "trade_id", "timestamp_received", "price", "quantity", "is_buyer_maker"])
        trade_time_col = table.column("trade_time")
        target_mask = pc.and_(
            pc.equal(table.column("instrument_id"), instrument),
            pc.and_(pc.greater_equal(trade_time_col, start_ms), pc.less(trade_time_col, end_ms)),
        )
        target_mask_np = target_mask.to_numpy(zero_copy_only=False)
        target_positions = np.where(target_mask_np)[0]
        if len(target_positions) == 0:
            continue
        filtered = table.filter(target_mask)
        n_chunk = filtered.num_rows
        tt_list.append(filtered.column("trade_time").to_numpy())
        tid_list.append(filtered.column("trade_id").to_numpy())
        tr_list.append(filtered.column("timestamp_received").to_numpy())
        price_list.append(filtered.column("price").cast("float64").to_numpy())
        qty_list.append(filtered.column("quantity").cast("float64").to_numpy())
        maker_list.append(filtered.column("is_buyer_maker").to_numpy())
        fidx_list.append(np.full(n_chunk, file_idx, dtype=np.int32))
        rord_list.append(target_positions.astype(np.int64))

    raw_tt = np.concatenate(tt_list); raw_tid = np.concatenate(tid_list); raw_tr = np.concatenate(tr_list)
    raw_price = np.concatenate(price_list); raw_qty = np.concatenate(qty_list); raw_maker = np.concatenate(maker_list)
    raw_fidx = np.concatenate(fidx_list); raw_rord = np.concatenate(rord_list)

    n_raw = len(raw_tid)

    sort_idx = np.argsort(raw_tid, kind="stable")
    sorted_tid = raw_tid[sort_idx]
    unique_ids, first_pos, counts = np.unique(sorted_tid, return_index=True, return_counts=True)
    dupe_mask = counts > 1
    n_groups = int(dupe_mask.sum())

    role = np.zeros(n_raw, dtype=np.int8)
    if dupe_mask.any():
        for gi in np.where(dupe_mask)[0]:
            s, e = first_pos[gi], first_pos[gi] + counts[gi]
            group_rows = sort_idx[s:e]
            group_tt = raw_tt[group_rows]; group_price = raw_price[group_rows]
            group_qty = raw_qty[group_rows]; group_maker = raw_maker[group_rows]
            if len(set(group_tt.tolist())) > 1 or len(set(group_price.tolist())) > 1 or \
               len(set(group_qty.tolist())) > 1 or len(set(group_maker.tolist())) > 1:
                raise RuntimeError(f"STRUCTURAL FAIL: economic conflict for trade_id={unique_ids[gi]}")
            group_tr = raw_tr[group_rows]
            min_mask = group_tr == group_tr.min()
            if int(min_mask.sum()) > 1:
                raise RuntimeError(f"STRUCTURAL FAIL: tied minimum receipt for trade_id={unique_ids[gi]}")
            keep_local = int(np.argmax(min_mask))
            for local_i, row in enumerate(group_rows):
                if local_i != keep_local:
                    role[row] = 1

    n_discarded = int((role == 1).sum())
    n_target = int((role == 0).sum())
    if n_target != n_raw - n_discarded:
        raise RuntimeError(
            f"STRUCTURAL FAIL: self-consistency check failed for {instrument} {date_str}: "
            f"deduped={n_target} != raw({n_raw}) - excess({n_discarded})."
        )

    retain_mask = role == 0
    target_tt = raw_tt[retain_mask]; target_tid = raw_tid[retain_mask]
    target_price = raw_price[retain_mask]; target_qty = raw_qty[retain_mask]; target_maker = raw_maker[retain_mask]

    canon_sort = np.lexsort((target_tid, target_tt))
    canon_tt = target_tt[canon_sort]; canon_tid = target_tid[canon_sort]
    canon_price = target_price[canon_sort]; canon_qty = target_qty[canon_sort]; canon_maker = target_maker[canon_sort]
    N_TARGET = len(canon_tid)
    if len(np.unique(canon_tid)) != N_TARGET:
        raise RuntimeError(f"STRUCTURAL FAIL: duplicate trade_id survives dedup for {instrument} {date_str}")

    validate_sorted_arrays(canon_tt, canon_tid, canon_price, canon_qty, canon_maker)
    kernel_result = compute_screen(canon_tt, canon_tid, canon_price, canon_qty, canon_maker)

    physical_file_order, physical_order_lookup = derive_physical_file_chronology(instrument, file_paths)

    retained_positions = np.where(retain_mask)[0]
    retained_physical_file_pos = np.array([
        physical_order_lookup[file_paths[int(raw_fidx[p])]] for p in retained_positions
    ], dtype=np.int64)
    retained_physical_rord = raw_rord[retained_positions]

    physical_order_check = np.lexsort((retained_physical_rord, retained_physical_file_pos))
    final_pos = retained_positions[physical_order_check[-1]]
    final_file_idx = int(raw_fidx[final_pos])
    final_row_ordinal = int(raw_rord[final_pos])
    final_file = file_paths[final_file_idx]

    assert_table = pq.read_table(final_file, columns=["instrument_id", "trade_time", "trade_id"])
    if assert_table.column("instrument_id")[final_row_ordinal].as_py() != instrument:
        raise RuntimeError("STRUCTURAL FAIL: boundary instrument mismatch.")
    reread_tt = int(assert_table.column("trade_time")[final_row_ordinal].as_py())
    if not (start_ms <= reread_tt < end_ms):
        raise RuntimeError("STRUCTURAL FAIL: boundary trade_time outside target window.")
    if int(assert_table.column("trade_id")[final_row_ordinal].as_py()) != int(raw_tid[final_pos]):
        raise RuntimeError("STRUCTURAL FAIL: boundary trade_id provenance mismatch.")

    boundary_file = final_file
    boundary_row_ordinal = final_row_ordinal
    bf_table = pq.read_table(boundary_file, columns=["timestamp_received"])
    boundary_receipt = int(bf_table.column("timestamp_received")[boundary_row_ordinal].as_py())

    return {
        "raw_tt": raw_tt, "raw_tid": raw_tid, "raw_tr": raw_tr, "raw_price": raw_price, "role": role,
        "canon_tt": canon_tt, "canon_tid": canon_tid, "N_TARGET": N_TARGET,
        "kernel_result": kernel_result, "file_paths": file_paths,
        "boundary_file": boundary_file, "boundary_row_ordinal": boundary_row_ordinal,
        "boundary_receipt": boundary_receipt, "start_ms": start_ms, "end_ms": end_ms,
        "evidence": {"raw": n_raw, "groups": n_groups, "excess": n_discarded, "deduped": n_target},
    }


def scan_partition_for_receipt_ranges(partition_dir, instrument, boundary_partition_dir, boundary_receipt, boundary_file):
    records = []
    if not partition_dir.exists():
        return records
    for f in sorted(partition_dir.glob("*.parquet")):
        table = pq.read_table(f, columns=["instrument_id", "timestamp_received"])
        mask = pc.equal(table.column("instrument_id"), instrument)
        filtered = table.filter(mask)
        n = filtered.num_rows
        if n == 0:
            continue
        tr = filtered.column("timestamp_received").to_numpy()
        first_received = int(tr[0]); last_received = int(tr[-1])
        if partition_dir == boundary_partition_dir and f != boundary_file and last_received < boundary_receipt:
            continue
        internally_monotonic = bool((np.diff(tr) >= 0).all()) if n > 1 else True
        records.append({"path": f, "first_received": first_received, "last_received": last_received,
                         "row_count": n, "internally_monotonic": internally_monotonic})
    return records


def build_200_context(instrument, boundary_file, boundary_row_ordinal, boundary_receipt, start_ms, end_ms):
    boundary_partition_dir = boundary_file.parent
    boundary_partition_date = datetime.strptime(boundary_partition_dir.name.replace("date=", ""), "%Y-%m-%d").date()

    records_200 = scan_partition_for_receipt_ranges(boundary_partition_dir, instrument, boundary_partition_dir, boundary_receipt, boundary_file)
    for offset in range(1, MAX_FORWARD_DAYS_SEARCH + 1):
        next_date = (boundary_partition_date + timedelta(days=offset)).isoformat()
        records_200.extend(scan_partition_for_receipt_ranges(root / f"date={next_date}", instrument, boundary_partition_dir, boundary_receipt, boundary_file))

    by_first_200 = sorted(records_200, key=lambda r: r["first_received"])
    final_idx_200 = next(i for i, r in enumerate(by_first_200) if r["path"] == boundary_file)

    for i in range(final_idx_200):
        if by_first_200[i]["last_received"] >= boundary_receipt:
            raise RuntimeError("STRUCTURAL FAIL: pre-boundary crossing/ambiguity (200-arrival context).")

    validated_prefix_200 = []
    running_max_last = -1
    exact_arrivals = 0; exact_span = 0; sufficiency_reached = False

    for i in range(final_idx_200, len(by_first_200)):
        r = by_first_200[i]
        if not r["internally_monotonic"]:
            raise RuntimeError(f"STRUCTURAL FAIL: {r['path']} not monotonic.")
        if validated_prefix_200 and r["first_received"] <= running_max_last:
            raise RuntimeError(f"STRUCTURAL FAIL: context ambiguity at position {len(validated_prefix_200)}.")
        validated_prefix_200.append(r)
        running_max_last = max(running_max_last, r["last_received"])

        if r["path"] == boundary_file:
            table = pq.read_table(r["path"], columns=["instrument_id", "trade_time", "timestamp_received"])
            n_post, last_post_tr = 0, None
            for row_ord in range(boundary_row_ordinal + 1, table.num_rows):
                if table.column("instrument_id")[row_ord].as_py() != instrument:
                    continue
                n_post += 1
                last_post_tr = int(table.column("timestamp_received")[row_ord].as_py())
            if n_post > 0:
                exact_arrivals += n_post
                exact_span = max(exact_span, last_post_tr - boundary_receipt)
        else:
            exact_arrivals += r["row_count"]
            exact_span = max(exact_span, r["last_received"] - boundary_receipt)

        if exact_arrivals >= MAX_K and exact_span >= MAX_X_MS:
            sufficiency_reached = True
            break

    if not sufficiency_reached:
        raise RuntimeError("STRUCTURAL FAIL: 200-arrival sufficiency not reached.")

    ordered_200 = [r["path"] for r in validated_prefix_200]
    boundary_idx_200 = ordered_200.index(boundary_file)

    ctx_tt, ctx_tid, ctx_tr = [], [], []

    def process_ctx_file(file_path, start_row):
        table = pq.read_table(file_path, columns=["instrument_id", "trade_time", "trade_id", "timestamp_received"])
        added = 0
        for row_ord in range(start_row, table.num_rows):
            if table.column("instrument_id")[row_ord].as_py() != instrument:
                continue
            tt = int(table.column("trade_time")[row_ord].as_py())
            if start_ms <= tt < end_ms:
                raise RuntimeError(f"STRUCTURAL FAIL: UNEXPECTED_TARGET_MATERIAL at {file_path} row {row_ord}")
            tid = int(table.column("trade_id")[row_ord].as_py())
            tr = int(table.column("timestamp_received")[row_ord].as_py())
            ctx_tt.append(tt); ctx_tid.append(tid); ctx_tr.append(tr)
            added += 1
        return added

    total_200 = process_ctx_file(boundary_file, boundary_row_ordinal + 1)
    if total_200 < MAX_K or not ctx_tr or (max(ctx_tr) - boundary_receipt) < MAX_X_MS:
        for i in range(boundary_idx_200 + 1, len(ordered_200)):
            total_200 += process_ctx_file(ordered_200[i], 0)
            if total_200 >= MAX_K and (max(ctx_tr) - boundary_receipt) >= MAX_X_MS:
                break

    return np.array(ctx_tt)[:200], np.array(ctx_tid)[:200], np.array(ctx_tr)[:200]


def build_extended_stream_to_horizon(instrument, boundary_file, boundary_row_ordinal, boundary_receipt,
                                       start_ms, end_ms, entry_horizon_receipt,
                                       already_validated_prefix=None):
    """
    Extends the validated physical-arrival stream (by receipt time)
    until entry_horizon_receipt is covered, or reports that the
    complete validated 14-day forward discovery universe was
    exhausted first (horizon_covered=False) -- the caller decides
    what that means (Stage A: unconditional hard-fail; Stage B when
    iterating: try again with a further target, or hard-fail once the
    universe itself -- not an iteration count -- is exhausted).
    """
    boundary_partition_dir = boundary_file.parent
    boundary_partition_date = datetime.strptime(boundary_partition_dir.name.replace("date=", ""), "%Y-%m-%d").date()

    if already_validated_prefix is not None:
        validated_prefix_ext = list(already_validated_prefix)
        running_max_last_ext = validated_prefix_ext[-1]["last_received"]
        already_paths = {r["path"] for r in validated_prefix_ext}
        records_ext = scan_partition_for_receipt_ranges(boundary_partition_dir, instrument, boundary_partition_dir, boundary_receipt, boundary_file)
        for offset in range(1, MAX_FORWARD_DAYS_SEARCH + 1):
            next_date = (boundary_partition_date + timedelta(days=offset)).isoformat()
            records_ext.extend(scan_partition_for_receipt_ranges(root / f"date={next_date}", instrument, boundary_partition_dir, boundary_receipt, boundary_file))
        by_first_ext = sorted(records_ext, key=lambda r: r["first_received"])
        remaining = [r for r in by_first_ext if r["path"] not in already_paths]
    else:
        records_ext = scan_partition_for_receipt_ranges(boundary_partition_dir, instrument, boundary_partition_dir, boundary_receipt, boundary_file)
        for offset in range(1, MAX_FORWARD_DAYS_SEARCH + 1):
            next_date = (boundary_partition_date + timedelta(days=offset)).isoformat()
            records_ext.extend(scan_partition_for_receipt_ranges(root / f"date={next_date}", instrument, boundary_partition_dir, boundary_receipt, boundary_file))
        by_first_ext = sorted(records_ext, key=lambda r: r["first_received"])
        final_idx_ext = next(i for i, r in enumerate(by_first_ext) if r["path"] == boundary_file)
        for i in range(final_idx_ext):
            if by_first_ext[i]["last_received"] >= boundary_receipt:
                raise RuntimeError("STRUCTURAL FAIL: pre-boundary crossing/ambiguity (extended context).")
        validated_prefix_ext = []
        running_max_last_ext = -1
        remaining = by_first_ext[final_idx_ext:]

    horizon_covered = False
    exhausted = len(remaining) == 0  # nothing left to scan at all in the discovery universe
    for idx, r in enumerate(remaining):
        if not r["internally_monotonic"]:
            raise RuntimeError(f"STRUCTURAL FAIL: {r['path']} not internally receipt-monotonic (extended).")
        if validated_prefix_ext and r["first_received"] <= running_max_last_ext:
            raise RuntimeError(f"STRUCTURAL FAIL: extended-context chronology ambiguity/overlap at position {len(validated_prefix_ext)}.")
        validated_prefix_ext.append(r)
        running_max_last_ext = max(running_max_last_ext, r["last_received"])

        if r["last_received"] >= entry_horizon_receipt:
            horizon_covered = True
            break

        if idx == len(remaining) - 1:
            # Consumed every record the 14-day discovery universe offers
            # without reaching the target -- universe demonstrably
            # exhausted, not merely "not yet extended enough".
            exhausted = True

    ordered_ext = [r["path"] for r in validated_prefix_ext]
    boundary_idx_ext = ordered_ext.index(boundary_file)

    ext_tt, ext_tid, ext_tr, ext_price = [], [], [], []

    def process_ext_file(file_path, start_row):
        table = pq.read_table(file_path, columns=["instrument_id", "trade_time", "trade_id", "timestamp_received", "price"])
        for row_ord in range(start_row, table.num_rows):
            if table.column("instrument_id")[row_ord].as_py() != instrument:
                continue
            tt = int(table.column("trade_time")[row_ord].as_py())
            if start_ms <= tt < end_ms:
                raise RuntimeError(f"STRUCTURAL FAIL: UNEXPECTED_TARGET_MATERIAL at {file_path} row {row_ord}")
            tid = int(table.column("trade_id")[row_ord].as_py())
            price = float(table.column("price")[row_ord].as_py())
            tr = int(table.column("timestamp_received")[row_ord].as_py())
            ext_tt.append(tt); ext_tid.append(tid); ext_tr.append(tr); ext_price.append(price)

    process_ext_file(boundary_file, boundary_row_ordinal + 1)
    for i in range(boundary_idx_ext + 1, len(ordered_ext)):
        process_ext_file(ordered_ext[i], 0)

    extended_tt = np.array(ext_tt); extended_tid = np.array(ext_tid)
    extended_tr = np.array(ext_tr); extended_price = np.array(ext_price)
    if len(extended_tr) > 1 and not np.all(np.diff(extended_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: extended stream not nondecreasing.")

    return extended_tt, extended_tid, extended_tr, extended_price, validated_prefix_ext, horizon_covered, exhausted


def classify(value, p10, p90):
    if value <= p10:
        return "SHORT"
    elif value > p90:
        return "LONG"
    return "NONE"


def pct(values, p):
    if len(values) == 0:
        return None
    return float(np.percentile(values, p))


def summarize_distribution(values):
    if len(values) == 0:
        return {"n": 0}
    v = np.asarray(values, dtype=np.float64)
    return {
        "n": int(len(v)), "median": float(np.median(v)), "mean": float(np.mean(v)),
        "p10": pct(v, 10), "p25": pct(v, 25), "p75": pct(v, 75), "p90": pct(v, 90),
        "worst": float(v.min()), "best": float(v.max()),
    }


def summarize_gross_return(values):
    if len(values) == 0:
        return {"n": 0}
    v = np.asarray(values, dtype=np.float64)
    d = summarize_distribution(v)
    d["pct_positive"] = float(100 * np.mean(v > 0))
    d["pct_negative"] = float(100 * np.mean(v < 0))
    d["pct_zero"] = float(100 * np.mean(v == 0))
    d["pct_gt_1bp"] = float(100 * np.mean(v > 1))
    d["pct_gt_2bp"] = float(100 * np.mean(v > 2))
    d["pct_gt_5bp"] = float(100 * np.mean(v > 5))
    d["pct_lt_neg1bp"] = float(100 * np.mean(v < -1))
    d["pct_lt_neg2bp"] = float(100 * np.mean(v < -2))
    d["pct_lt_neg5bp"] = float(100 * np.mean(v < -5))
    return d


def accounting_block(total_n, available_n):
    unavailable_n = total_n - available_n
    if available_n + unavailable_n != total_n:
        raise RuntimeError("STRUCTURAL FAIL: accounting block reconciliation failed.")
    return {"total_n": total_n, "available_n": available_n, "unavailable_n": unavailable_n,
            "availability_pct": 100 * available_n / total_n if total_n else 0.0}


def run_diagnostic(instrument, date_str):
    print(f"\n{'='*20} {instrument} {date_str} {'='*20}\n", flush=True)

    pop = reconstruct_population(instrument, date_str)
    print(f"[GATE 2] Target population: {pop['N_TARGET']} -- self-consistency PASS "
          f"(evidence={pop['evidence']})", flush=True)

    context_tt, context_tid, context_tr = build_200_context(
        instrument, pop["boundary_file"], pop["boundary_row_ordinal"], pop["boundary_receipt"],
        pop["start_ms"], pop["end_ms"]
    )

    combined_tt = np.concatenate([pop["raw_tt"], context_tt])
    combined_tid = np.concatenate([pop["raw_tid"], context_tid])
    combined_tr = np.concatenate([pop["raw_tr"], context_tr])
    combined_role = np.concatenate([pop["role"], np.full(200, 2, dtype=np.int8)])
    n_combined = len(combined_tid)

    if not np.all(np.diff(combined_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: combined (200-ctx) chronology not nondecreasing.")

    target_mask_only = combined_role == 0
    target_combined_idx = np.where(target_mask_only)[0]
    target_tt_only = combined_tt[target_mask_only]; target_tid_only = combined_tid[target_mask_only]
    canon_sort2 = np.lexsort((target_tid_only, target_tt_only))
    canonical_stream_tid = target_tid_only[canon_sort2]
    N_TARGET2 = len(canonical_stream_tid)
    if N_TARGET2 != pop["N_TARGET"]:
        raise RuntimeError("STRUCTURAL FAIL: N_TARGET mismatch.")

    canonical_rank_combined_idx = target_combined_idx[canon_sort2]
    combined_idx_to_canonical_rank = np.full(n_combined, -1, dtype=np.int64)
    combined_idx_to_canonical_rank[canonical_rank_combined_idx] = np.arange(N_TARGET2, dtype=np.int64)

    heap = []; emitted_count = 0
    emission_arrival_frontier = np.full(N_TARGET2, -1, dtype=np.int64)
    for i in range(n_combined):
        collector_index = i + 1
        if combined_role[i] == 0:
            heapq.heappush(heap, int(combined_idx_to_canonical_rank[i]))
        while heap:
            cand_rank = heap[0]
            cand_arrival_count = int(canonical_rank_combined_idx[cand_rank]) + 1
            if collector_index - cand_arrival_count >= K_POLICY:
                heapq.heappop(heap)
                emission_arrival_frontier[cand_rank] = i
                emitted_count += 1
            else:
                break

    if len(heap) != 0 or emitted_count != N_TARGET2:
        raise RuntimeError("STRUCTURAL FAIL: K5 simulation incomplete.")
    print("[GATE 3] K5 E_position reproduced from validated 200-arrival context: PASS", flush=True)

    sample_ranks = np.arange(SAMPLE_EVERY_NTH - 1, N_TARGET2, SAMPLE_EVERY_NTH)
    n_samples = len(sample_ranks)

    kernel_sample_tid = pop["kernel_result"]["sample_trade_id"]
    independent_sample_tid = canonical_stream_tid[sample_ranks]
    if len(kernel_sample_tid) != len(independent_sample_tid):
        raise RuntimeError(f"STRUCTURAL FAIL: sample count mismatch {len(kernel_sample_tid)} != {len(independent_sample_tid)}.")
    ki_mismatches = np.where(kernel_sample_tid != independent_sample_tid)[0]
    if len(ki_mismatches) > 0:
        raise RuntimeError(f"STRUCTURAL FAIL: frozen-kernel vs independent sample mismatch at index={ki_mismatches[0]}.")
    print(f"[GATE 4] Frozen-kernel sample alignment: {len(kernel_sample_tid)} samples, 0 mismatches -- PASS", flush=True)

    F_position = np.empty(n_samples, dtype=np.int64)
    R_arr = np.empty(n_samples, dtype=np.int64)
    lb_ptr = 0
    canon_tt = pop["canon_tt"]
    for i, rank in enumerate(sample_ranks):
        T = canon_tt[rank]
        while lb_ptr < rank and canon_tt[lb_ptr] <= T - LOOKBACK_MS:
            lb_ptr += 1
        contributor_positions = canonical_rank_combined_idx[lb_ptr:rank+1]
        F_position[i] = contributor_positions.max()
        R_arr[i] = combined_tr[contributor_positions].max()

    check_values = combined_tr[F_position]
    n_mismatch = int((check_values != R_arr).sum())
    if n_mismatch > 0:
        raise RuntimeError(f"STRUCTURAL FAIL: combined_tr[F_position]==R invariant violated ({n_mismatch} mismatches).")
    print(f"[GATE 5] Invariant combined_tr[F_position]==R: 0 mismatches / {n_samples} -- PASS", flush=True)

    E_position = emission_arrival_frontier[sample_ranks]
    if (E_position < 0).any():
        raise RuntimeError("STRUCTURAL FAIL: missing E_position.")
    A_position = np.maximum(F_position, E_position)
    A_receipt = combined_tr[A_position]
    assert (A_position >= F_position).all() and (A_position >= E_position).all()
    print("[GATE 6] A_position dominance assertions: PASS", flush=True)

    # ----- GATE 7 / STAGE A: extend to resolve Delta=0 entries -----
    max_a_receipt = int(A_receipt.max())
    stage_a_target_receipt = max_a_receipt + SAFETY_MARGIN_MS
    print(f"[GATE 7/A] Extending to resolve entries: target_receipt={stage_a_target_receipt}", flush=True)

    boundary_file = pop["boundary_file"]; boundary_row_ordinal = pop["boundary_row_ordinal"]
    boundary_receipt = pop["boundary_receipt"]

    (extended_tt, extended_tid, extended_tr, extended_price,
     validated_prefix, stage_a_covered, stage_a_exhausted) = build_extended_stream_to_horizon(
        instrument, boundary_file, boundary_row_ordinal, boundary_receipt,
        pop["start_ms"], pop["end_ms"], stage_a_target_receipt
    )
    if not stage_a_covered:
        raise RuntimeError(
            f"STRUCTURAL FAIL: Stage A entry-resolution horizon not covered "
            f"(discovery universe exhausted={stage_a_exhausted})."
        )
    print(f"[GATE 7/A] PASS -- extended stream: {len(extended_tid)} arrivals", flush=True)

    full_raw_tt = np.concatenate([pop["raw_tt"], extended_tt])
    full_raw_tid = np.concatenate([pop["raw_tid"], extended_tid])
    full_raw_tr = np.concatenate([pop["raw_tr"], extended_tr])
    full_raw_price = np.concatenate([pop["raw_price"], extended_price])
    if not np.all(np.diff(full_raw_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: full raw stream not nondecreasing after Stage A.")
    n_full_raw = len(full_raw_tid)

    entry_position = np.full(n_samples, -1, dtype=np.int64)
    entry_price = np.full(n_samples, np.nan)
    entry_time = np.full(n_samples, -1, dtype=np.int64)
    for i in range(n_samples):
        pos = A_position[i] + 1
        while pos < n_full_raw:
            if full_raw_tt[pos] > A_receipt[i]:
                entry_position[i] = pos
                entry_price[i] = full_raw_price[pos]
                entry_time[i] = full_raw_tt[pos]
                break
            pos += 1

    available_entry = entry_position >= 0
    n_available_entry = int(available_entry.sum())

    # PATCH #4: 100% Delta=0 entry availability is REQUIRED for this
    # replication experiment -- a hard structural gate, not a soft
    # PASS-with-partial-availability. Partial availability would make
    # the replication denominator chronology-dependent.
    if n_available_entry != n_samples:
        raise RuntimeError(
            f"STRUCTURAL FAIL: Delta=0 NEW entry availability {n_available_entry}/{n_samples} "
            f"< 100%. This replication experiment requires complete entry resolution."
        )
    pos_check = (entry_position > A_position).all()
    tt_check = (full_raw_tt[entry_position] > A_receipt).all()
    if not pos_check or not tt_check:
        raise RuntimeError("STRUCTURAL FAIL: entry causality assertion violated.")
    print(f"[ENTRY] Delta=0 NEW entry: {n_available_entry}/{n_samples} (100%) -- PASS", flush=True)

    # ----- GATE 7 / STAGE B: real per-entry exchange-time target, fully empirical -----
    # PATCH #2 + #3: no arbitrary iteration cap -- loop bound is the
    # validated discovery universe itself. Coverage failure is now a
    # hard structural fail, enforced BEFORE exit construction proceeds.
    max_entry_time = int(entry_time.max())
    max_exit_target_time = max_entry_time + HORIZON_MAX_MS
    current_max_tt = int(full_raw_tt.max()) if n_full_raw > 0 else -1
    print(f"[GATE 7/B] Real required exchange-time target: "
          f"max(entry_time)={max_entry_time} + H_max={HORIZON_MAX_MS} = {max_exit_target_time}", flush=True)

    stage_b_covered = current_max_tt >= max_exit_target_time
    if not stage_b_covered:
        stage_b_receipt_target = stage_a_target_receipt
        universe_exhausted = False
        while not stage_b_covered and not universe_exhausted:
            stage_b_receipt_target += SAFETY_MARGIN_MS
            (extended_tt2, extended_tid2, extended_tr2, extended_price2,
             validated_prefix, stage_b_step_covered, universe_exhausted) = build_extended_stream_to_horizon(
                instrument, boundary_file, boundary_row_ordinal, boundary_receipt,
                pop["start_ms"], pop["end_ms"], stage_b_receipt_target,
                already_validated_prefix=validated_prefix
            )
            full_raw_tt = np.concatenate([pop["raw_tt"], extended_tt2])
            full_raw_tid = np.concatenate([pop["raw_tid"], extended_tid2])
            full_raw_tr = np.concatenate([pop["raw_tr"], extended_tr2])
            full_raw_price = np.concatenate([pop["raw_price"], extended_price2])
            if not np.all(np.diff(full_raw_tr) >= 0):
                raise RuntimeError("STRUCTURAL FAIL: full raw stream not nondecreasing after Stage B extension.")
            n_full_raw = len(full_raw_tid)
            current_max_tt = int(full_raw_tt.max())
            stage_b_covered = current_max_tt >= max_exit_target_time
            # loop continues until either coverage is reached, or the
            # validated 14-day discovery universe itself is exhausted
            # (universe_exhausted=True) -- never an arbitrary retry count.

    # PATCH #3: enforce Stage B coverage as a hard structural gate
    # BEFORE proceeding to exit construction.
    if not stage_b_covered:
        raise RuntimeError(
            f"STRUCTURAL FAIL: Stage B exchange-time coverage not achieved "
            f"(target={max_exit_target_time}, observed_max={current_max_tt}, "
            f"validated 14-day discovery universe exhausted). Cannot proceed to "
            f"exit construction on an unproven coverage claim."
        )
    print(f"[GATE 7/B] PASS -- exchange-time target empirically covered "
          f"(observed_max={current_max_tt} >= target={max_exit_target_time})", flush=True)

    exit_position_by_h = {}
    exit_price_by_h = {}
    exit_time_by_h = {}

    for h_ms in HORIZONS_MS:
        exit_pos = np.full(n_samples, -1, dtype=np.int64)
        exit_price = np.full(n_samples, np.nan)
        exit_time = np.full(n_samples, -1, dtype=np.int64)
        for i in range(n_samples):
            target_h = entry_time[i] + h_ms
            pos = entry_position[i] + 1
            while pos < n_full_raw:
                if full_raw_tt[pos] > target_h:
                    exit_pos[i] = pos
                    exit_price[i] = full_raw_price[pos]
                    exit_time[i] = full_raw_tt[pos]
                    break
                pos += 1

        available_exit = exit_pos >= 0
        if available_exit.any():
            pos_check = (exit_pos[available_exit] > entry_position[available_exit]).all()
            tt_check = (full_raw_tt[exit_pos[available_exit]] > entry_time[available_exit] + h_ms).all()
            if not (pos_check and tt_check):
                raise RuntimeError(f"STRUCTURAL FAIL: H={h_ms}ms exit causality assertion violated.")

        exit_position_by_h[h_ms] = exit_pos
        exit_price_by_h[h_ms] = exit_price
        exit_time_by_h[h_ms] = exit_time
        n_avail = int(available_exit.sum())
        print(f"[EXIT H={h_ms}ms] {n_avail}/{n_samples} available "
              f"({n_samples - n_avail} unavailable, explicitly counted)", flush=True)

    threshold = CAUSAL_N10_THRESHOLDS[date_str]
    imbalance_at_samples = pop["kernel_result"]["imbalance"]
    directions = np.array([classify(v, threshold["p10"], threshold["p90"]) for v in imbalance_at_samples])
    n_short = int((directions == "SHORT").sum())
    n_long = int((directions == "LONG").sum())
    n_none = int((directions == "NONE").sum())
    print(f"N10 thresholds (frozen, pre-existing): P10={threshold['p10']}, P90={threshold['p90']}", flush=True)
    print(f"Direction counts: SHORT={n_short}, LONG={n_long}, NONE={n_none}", flush=True)

    result_record = {
        "instrument": instrument, "date": date_str, "n_samples": n_samples,
        "entry_availability": accounting_block(n_samples, n_available_entry),
        "horizon_stats": {},
    }

    npz_payload = {
        "sample_rank": sample_ranks, "entry_position": entry_position,
        "entry_time": entry_time, "entry_price": entry_price, "directions": directions,
    }

    overshoot_stats = {}

    for h_ms in HORIZONS_MS:
        exit_pos = exit_position_by_h[h_ms]
        exit_price = exit_price_by_h[h_ms]
        exit_time = exit_time_by_h[h_ms]
        available = exit_pos >= 0  # entry is always available (100% enforced above)
        n_avail = int(available.sum())

        hstat = {"availability": accounting_block(n_samples, n_avail)}

        npz_payload[f"exit_position_{h_ms}ms"] = exit_pos
        npz_payload[f"exit_price_{h_ms}ms"] = exit_price
        npz_payload[f"exit_time_{h_ms}ms"] = exit_time
        actual_horizon = np.where(available, exit_time - entry_time, -1)
        npz_payload[f"actual_horizon_ms_{h_ms}ms"] = actual_horizon

        # PATCH #7: overshoot diagnostics -- (actual_horizon - requested_horizon)
        overshoot = actual_horizon[available] - h_ms if available.any() else np.array([])
        overshoot_stats[str(h_ms)] = summarize_distribution(overshoot)

        long_mask = available & (directions == "LONG")
        short_mask = available & (directions == "SHORT")

        long_total_n = int((directions == "LONG").sum())
        short_total_n = int((directions == "SHORT").sum())
        long_avail_n = int(long_mask.sum())
        short_avail_n = int(short_mask.sum())

        hstat["signal_availability"] = {
            "long": accounting_block(long_total_n, long_avail_n),
            "short": accounting_block(short_total_n, short_avail_n),
        }

        long_gross = (exit_price[long_mask] / entry_price[long_mask] - 1) * 10_000 if long_mask.any() else np.array([])
        short_gross = (entry_price[short_mask] / exit_price[short_mask] - 1) * 10_000 if short_mask.any() else np.array([])
        pooled_gross = np.concatenate([long_gross, short_gross]) if (len(long_gross) or len(short_gross)) else np.array([])

        npz_payload[f"gross_bp_{h_ms}ms"] = np.where(
            (directions == "LONG") & available, (exit_price / entry_price - 1) * 10_000,
            np.where((directions == "SHORT") & available, (entry_price / exit_price - 1) * 10_000, np.nan)
        )

        hstat["gross_return_pooled"] = summarize_gross_return(pooled_gross)
        hstat["gross_return_long"] = summarize_gross_return(long_gross)
        hstat["gross_return_short"] = summarize_gross_return(short_gross)
        hstat["overshoot_ms"] = overshoot_stats[str(h_ms)]

        result_record["horizon_stats"][str(h_ms)] = hstat

        gp = hstat["gross_return_pooled"]
        gr_str = (f" | gross(pooled) median={gp['median']:.3f}bp mean={gp['mean']:.3f}bp "
                  f"pos%={gp['pct_positive']:.1f}% n={gp['n']}") if gp.get("n", 0) > 0 else ""
        print(f"[H={h_ms}ms] avail={n_avail}/{n_samples}{gr_str}", flush=True)

    with open(OUTPUT_DIR / f"{instrument}_{date_str}.json", "w") as f:
        json.dump(result_record, f, indent=2, default=str)
    np.savez_compressed(OUTPUT_DIR / f"{instrument}_{date_str}_signals.npz", **npz_payload)

    print(f"\n{instrument} {date_str}: ALL STRUCTURAL GATES PASS", flush=True)
    return result_record


all_results = []
run_status = []
failure_reasons = {}

for date_str in REPLICATION_DATES:
    try:
        rec = run_diagnostic(INSTRUMENT, date_str)
        env = "EARLY" if date_str in EARLY_THRESHOLD_ENVIRONMENT_DATES else "LATE"
        rec["threshold_environment"] = env
        all_results.append(rec)
        run_status.append((date_str, "PASS"))
    except RuntimeError as e:
        print(f"\n*** STRUCTURAL FAILURE at {INSTRUMENT} {date_str}: {e} ***", flush=True)
        run_status.append((date_str, f"FAIL: {e}"))
        failure_reasons[date_str] = str(e)
        # Each date is an independent replication unit -- one
        # structural failure must not abort the remaining dates.
    gc.collect()

structural_pass_dates = [d for d, s in run_status if s == "PASS"]
structural_fail_dates = [d for d, s in run_status if s != "PASS"]

# ----- PATCH #6: explicit structural denominator reconciliation -----
denominator_reconciliation = {
    "frozen_dates": len(REPLICATION_DATES),
    "structural_pass_dates": len(structural_pass_dates),
    "structural_fail_dates": len(structural_fail_dates),
    "early_frozen": len(EARLY_THRESHOLD_ENVIRONMENT_DATES),
    "late_frozen": len(LATE_THRESHOLD_ENVIRONMENT_DATES),
    "early_pass": sum(1 for d in structural_pass_dates if d in EARLY_THRESHOLD_ENVIRONMENT_DATES),
    "late_pass": sum(1 for d in structural_pass_dates if d in LATE_THRESHOLD_ENVIRONMENT_DATES),
    "pass_dates": structural_pass_dates,
    "fail_dates": structural_fail_dates,
    "failure_reasons": failure_reasons,
}
if denominator_reconciliation["structural_pass_dates"] + denominator_reconciliation["structural_fail_dates"] \
        != denominator_reconciliation["frozen_dates"]:
    raise RuntimeError("STRUCTURAL FAIL: top-level date denominator reconciliation failed.")

print(f"\n\n{'='*20} STRUCTURAL DENOMINATOR RECONCILIATION {'='*20}\n", flush=True)
print(json.dumps(denominator_reconciliation, indent=2), flush=True)

with open(OUTPUT_DIR / "structural_denominator_reconciliation.json", "w") as f:
    json.dump(denominator_reconciliation, f, indent=2)

# ----- PATCH #5: primary per-day / cross-day table, ALL / LONG / SHORT -----
print(f"\n\n{'='*20} PRIMARY EVIDENCE: PER-DAY REPLICATION TABLE (15s, 30s) {'='*20}\n", flush=True)
print("Each instrument-day is ONE replication unit -- primary evidence, not the "
      "pooled signal-level statistics below. Only structurally PASSing dates included.\n", flush=True)

per_day_table = {}
for h_key in ("15000", "30000"):
    per_day_table[h_key] = {"ALL": [], "LONG": [], "SHORT": []}
    print(f"--- Horizon {int(h_key)//1000}s ---")
    for direction_key, hstat_key in (("ALL", "gross_return_pooled"), ("LONG", "gross_return_long"), ("SHORT", "gross_return_short")):
        print(f"\n  [{direction_key}]")
        print(f"  {'Date':<12} {'Env':<6} {'N':>6} {'Mean(bp)':>10} {'Median(bp)':>11} {'Pos%':>7}")
        for rec in all_results:
            hs = rec["horizon_stats"][h_key][hstat_key]
            if hs.get("n", 0) > 0:
                row = {"date": rec["date"], "env": rec["threshold_environment"],
                       "n": hs["n"], "mean": hs["mean"], "median": hs["median"], "pct_positive": hs["pct_positive"]}
                per_day_table[h_key][direction_key].append(row)
                print(f"  {rec['date']:<12} {rec['threshold_environment']:<6} {hs['n']:>6} "
                      f"{hs['mean']:>10.4f} {hs['median']:>11.4f} {hs['pct_positive']:>6.1f}%")
        means = [r["mean"] for r in per_day_table[h_key][direction_key]]
        medians = [r["median"] for r in per_day_table[h_key][direction_key]]
        if means:
            n_positive_days = sum(1 for m in means if m > 0)
            print(f"\n    Cross-day (N={len(means)} days): mean-of-means={np.mean(means):.4f}bp "
                  f"median-of-means={np.median(means):.4f}bp mean-of-medians={np.mean(medians):.4f}bp "
                  f"positive_days={n_positive_days}/{len(means)}")

with open(OUTPUT_DIR / "per_day_replication_table.json", "w") as f:
    json.dump(per_day_table, f, indent=2, default=str)

# ----- PATCH #1: finished pooled signal-level aggregation, reloaded from .npz -----
print(f"\n\n{'='*20} SECONDARY: POOLED SIGNAL-LEVEL AGGREGATES (all structurally-passing days) {'='*20}\n", flush=True)
print("WARNING: pooled statistics are SECONDARY evidence -- signals within a day are "
      "correlated, not independent replications. One large day can dominate this.\n", flush=True)

for h_ms in HORIZONS_MS:
    pooled_all, pooled_long, pooled_short = [], [], []
    early_all, late_all = [], []

    for rec in all_results:
        npz_path = OUTPUT_DIR / f"{INSTRUMENT}_{rec['date']}_signals.npz"
        with np.load(npz_path, allow_pickle=True) as npz:
            gross = npz[f"gross_bp_{h_ms}ms"]
            directions = npz["directions"]

        valid = ~np.isnan(gross)
        long_vals = gross[valid & (directions == "LONG")]
        short_vals = gross[valid & (directions == "SHORT")]
        all_vals = gross[valid]

        pooled_all.extend(all_vals.tolist())
        pooled_long.extend(long_vals.tolist())
        pooled_short.extend(short_vals.tolist())

        if rec["threshold_environment"] == "EARLY":
            early_all.extend(all_vals.tolist())
        else:
            late_all.extend(all_vals.tolist())

    signal_denominator = {
        "pooled_n": len(pooled_all),
        "long_n": len(pooled_long),
        "short_n": len(pooled_short),
        "early_n": len(early_all),
        "late_n": len(late_all),
    }
    if signal_denominator["long_n"] + signal_denominator["short_n"] != signal_denominator["pooled_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: pooled LONG+SHORT != pooled ALL at H={h_ms}ms.")
    if signal_denominator["early_n"] + signal_denominator["late_n"] != signal_denominator["pooled_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: pooled EARLY+LATE != pooled ALL at H={h_ms}ms.")

    aggregate_record = {
        "horizon_ms": h_ms,
        "scope_note": (
            "SECONDARY evidence. Includes only structurally-passing replication "
            "dates (Aug27 discovery date excluded by design). Signal-level pooling "
            "across days; one large day can dominate -- see per_day_replication_table.json "
            "for the primary cross-day evidence."
        ),
        "signal_denominator": signal_denominator,
        "pooled_all": summarize_gross_return(np.array(pooled_all)),
        "pooled_long": summarize_gross_return(np.array(pooled_long)),
        "pooled_short": summarize_gross_return(np.array(pooled_short)),
        "early_threshold_environment": summarize_gross_return(np.array(early_all)),
        "late_threshold_environment": summarize_gross_return(np.array(late_all)),
    }

    with open(OUTPUT_DIR / f"aggregate_horizon_{h_ms}ms.json", "w") as f:
        json.dump(aggregate_record, f, indent=2, default=str)

    pa = aggregate_record["pooled_all"]
    print(f"[H={h_ms}ms] pooled_n={signal_denominator['pooled_n']} "
          f"mean={pa.get('mean','N/A')}bp median={pa.get('median','N/A')}bp "
          f"pos%={pa.get('pct_positive','N/A')} | "
          f"EARLY n={signal_denominator['early_n']} | LATE n={signal_denominator['late_n']}", flush=True)

print(f"\n{'='*20} SUMMARY {'='*20}", flush=True)
for date_str, status in run_status:
    env = "EARLY" if date_str in EARLY_THRESHOLD_ENVIRONMENT_DATES else "LATE"
    print(f"{INSTRUMENT} {date_str} [{env}]: {status}", flush=True)

with open(OUTPUT_DIR / "final_summary.json", "w") as f:
    json.dump(
        [{"instrument": INSTRUMENT, "date": d, "status": s,
          "threshold_environment": "EARLY" if d in EARLY_THRESHOLD_ENVIRONMENT_DATES else "LATE"}
         for d, s in run_status],
        f, indent=2
    )

print(f"\nOutput: {OUTPUT_DIR}", flush=True)
print(f"Discovery date {DISCOVERY_DATE_EXCLUDED} deliberately excluded from this replication set.", flush=True)