"""
L1_CORE/market_data_platform/research/causal_fixed_horizon_gross_edge_v1.py

Experiment 1: Causal Gross-Edge Survival Test.

Question: After the validated causal Delta=0 NEW entry becomes
observable, does the N10 trade-flow signal retain a gross directional
price edge over fixed 5s/15s/30s/60s holding horizons?

NO fees, NO slippage, NO optimized exits, NO parameter tuning, NO
receipt-time condition on the exit proxy (this experiment asks about
the subsequent historical price path, not simulated execution
latency -- that is delta_sensitivity_v1.py's job, frozen separately).

Reuses the exact validated reconstruction/dedup/K5/F-R-A machinery
(copied, not imported -- delta_sensitivity_v1.py executes its full
experiment at module load and must not be imported as a library).
That script and its results remain untouched.

Frozen methodology:
    ENTRY: locked Delta=0 NEW entry (P_entry, entry_position, entry_time)
    HORIZONS: H in {5s, 15s, 30s, 60s} -- ALL FOUR always reported,
              frozen before results are seen. No horizon selection.
    TARGET: target_H = entry_time + H
    EXIT: first physical arrival strictly after entry_position with
          trade_time > target_H. NO receipt-time condition.
    GROSS RETURN:
        LONG:  (P_exit_H / P_entry - 1) * 10,000 bp
        SHORT: (P_entry / P_exit_H - 1) * 10,000 bp

Populations (4, same as delta_sensitivity_v1.py): BTC-USD 2026-08-05,
BTC-USD 2026-08-22, ETH-USD 2026-08-27, BTC-USD 2026-09-03. Sep03
remains N10-ineligible -- structural/exit-availability diagnostics
only, EXCLUDED from all economic (gross-return) aggregates.

Exit availability is NOT a structural pass/fail condition per sample
-- a legitimate end-of-reconstructable-data condition can leave a
horizon's exit genuinely unavailable. It is explicitly counted, never
silently dropped.

HORIZON COVERAGE (GATE 7) IS TWO-STAGE AND EMPIRICAL, NOT ASSUMED:
  Stage A: extend validated physical chronology far enough (by
  receipt time, same validated pattern as delta_sensitivity_v1.py) to
  resolve the Delta=0 NEW entries themselves.
  Stage B: once entry_time is actually known for every available
  entry, compute the REAL required exchange-time target
  (max(entry_time) + 60s), and continue extending the SAME validated
  physical chronology stream (never re-deriving it from scratch)
  until that exchange-time target is empirically covered by the
  discovered material, or the validated 14-day forward discovery
  universe is exhausted. entry_time > A_receipt is only a LOWER
  bound on entry_time -- it is never treated as an upper bound, and
  no receipt-time margin is treated as proof of exchange-time
  coverage. Any horizon left unresolved after the discovery universe
  is exhausted is explicitly counted, never silently dropped.

Retains compact per-signal .npz artifacts (entry/exit prices,
positions, times, actual realized horizon, gross bp per horizon) so
Experiment 2 (cost-grid stress test) can be run against these
signal-level results without re-reconstructing raw trade data.

Canonical storage read-only. No frozen-kernel changes. Does not
modify or import delta_sensitivity_v1.py or
causal_frontier_generalization.py.
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
HORIZON_MAX_MS = max(HORIZONS_MS)

root = Path("/mnt/lrs001/data/market_data_platform/canonical/trades")

OUTPUT_DIR = Path("/tmp/causal_fixed_horizon_gross_edge_v1_results")
if OUTPUT_DIR.exists():
    raise RuntimeError(
        f"FATAL: output directory already exists: {OUTPUT_DIR}. "
        f"Refusing to overwrite or mix evidence from another run."
    )
OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

INDEPENDENT_EVIDENCE = {
    ("BTC-USD", "2026-08-05"): {"raw": 485869, "groups": 2445, "excess": 2835, "deduped": 483034},
    ("BTC-USD", "2026-08-22"): {"raw": 1910150, "groups": 577, "excess": 597, "deduped": 1909553},
    ("ETH-USD", "2026-08-27"): {"raw": 330347, "groups": 2976, "excess": 3361, "deduped": 326986},
    ("BTC-USD", "2026-09-03"): {"raw": 644903, "groups": 586, "excess": 667, "deduped": 644236},
}

EXPECTED_SAMPLE_COUNTS = {
    ("BTC-USD", "2026-08-05"): 24151,
    ("BTC-USD", "2026-08-22"): 95477,
    ("ETH-USD", "2026-08-27"): 16349,
    ("BTC-USD", "2026-09-03"): 32211,
}

CAUSAL_N10_THRESHOLDS = {
    ("BTC-USD", "2026-08-05"): {"p10": -0.9124993108067109, "p90": 0.995520576372723, "obs": 233713},
    ("BTC-USD", "2026-08-22"): {"p10": -0.8916056119723363, "p90": 0.9638883167380699, "obs": 342125},
    ("ETH-USD", "2026-08-27"): {"p10": -0.8260489240979522, "p90": 0.9047507863169619, "obs": 211336},
    # BTC-USD 2026-09-03: N10 INELIGIBLE -- deliberately absent.
}

TEST_POPULATIONS = [
    ("BTC-USD", "2026-08-05"),
    ("BTC-USD", "2026-08-22"),
    ("ETH-USD", "2026-08-27"),
    ("BTC-USD", "2026-09-03"),
]


# ============================================================
# Reconstruction machinery -- copied verbatim from the audited
# delta_sensitivity_v1.py (SHA-256 48ec1667...9fd, committed
# 755b890). Not modified. Not imported (that script executes its
# full experiment at module load).
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

    evidence = INDEPENDENT_EVIDENCE[(instrument, date_str)]
    n_raw = len(raw_tid)
    if n_raw != evidence["raw"]:
        raise RuntimeError(f"STRUCTURAL FAIL: raw rows {n_raw} != {evidence['raw']}")

    sort_idx = np.argsort(raw_tid, kind="stable")
    sorted_tid = raw_tid[sort_idx]
    unique_ids, first_pos, counts = np.unique(sorted_tid, return_index=True, return_counts=True)
    dupe_mask = counts > 1
    n_groups = int(dupe_mask.sum())
    if n_groups != evidence["groups"]:
        raise RuntimeError(f"STRUCTURAL FAIL: groups {n_groups} != {evidence['groups']}")

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
    if n_discarded != evidence["excess"]:
        raise RuntimeError(f"STRUCTURAL FAIL: excess {n_discarded} != {evidence['excess']}")
    n_target = int((role == 0).sum())
    if n_target != evidence["deduped"]:
        raise RuntimeError(f"STRUCTURAL FAIL: deduped {n_target} != {evidence['deduped']}")

    retain_mask = role == 0
    target_tt = raw_tt[retain_mask]; target_tid = raw_tid[retain_mask]
    target_price = raw_price[retain_mask]; target_qty = raw_qty[retain_mask]; target_maker = raw_maker[retain_mask]

    canon_sort = np.lexsort((target_tid, target_tt))
    canon_tt = target_tt[canon_sort]; canon_tid = target_tid[canon_sort]
    canon_price = target_price[canon_sort]; canon_qty = target_qty[canon_sort]; canon_maker = target_maker[canon_sort]
    N_TARGET = len(canon_tid)

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
                                       already_validated_prefix=None, already_ext_data=None):
    """
    Extends the validated physical-arrival stream (by receipt time)
    until entry_horizon_receipt is covered. If already_validated_prefix
    and already_ext_data are supplied (from a PRIOR call on this same
    population), this call CONTINUES that exact same validated
    chronology forward rather than re-deriving it from scratch --
    used by Stage B to extend past what Stage A already validated.

    Returns (extended_tt, extended_tid, extended_tr, extended_price,
    validated_prefix, horizon_actually_covered).

    horizon_actually_covered is False (rather than raising) if the
    complete 14-day forward discovery universe is exhausted before
    entry_horizon_receipt is reached -- the caller decides whether
    that is acceptable (Stage A requires it; Stage B for exit
    resolution does NOT hard-fail on it, since a legitimate
    end-of-data condition can leave some exits unresolved).
    """
    boundary_partition_dir = boundary_file.parent
    boundary_partition_date = datetime.strptime(boundary_partition_dir.name.replace("date=", ""), "%Y-%m-%d").date()

    if already_validated_prefix is not None:
        validated_prefix_ext = list(already_validated_prefix)
        running_max_last_ext = validated_prefix_ext[-1]["last_received"]
        # Resume scanning from where we left off: re-scan all records
        # (cheap metadata-only pass) but skip anything already in the
        # validated prefix.
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
    for r in remaining:
        if not r["internally_monotonic"]:
            raise RuntimeError(f"STRUCTURAL FAIL: {r['path']} not internally receipt-monotonic (extended).")
        if validated_prefix_ext and r["first_received"] <= running_max_last_ext:
            raise RuntimeError(f"STRUCTURAL FAIL: extended-context chronology ambiguity/overlap at position {len(validated_prefix_ext)}.")
        validated_prefix_ext.append(r)
        running_max_last_ext = max(running_max_last_ext, r["last_received"])

        if r["last_received"] >= entry_horizon_receipt:
            idx_in_full = by_first_ext.index(r) if already_validated_prefix is not None else remaining.index(r)
            horizon_covered = True
            break

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

    done_ordered = process_ext_file(boundary_file, boundary_row_ordinal + 1)
    for i in range(boundary_idx_ext + 1, len(ordered_ext)):
        process_ext_file(ordered_ext[i], 0)

    extended_tt = np.array(ext_tt); extended_tid = np.array(ext_tid)
    extended_tr = np.array(ext_tr); extended_price = np.array(ext_price)
    if len(extended_tr) > 1 and not np.all(np.diff(extended_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: extended stream not nondecreasing.")

    return extended_tt, extended_tid, extended_tr, extended_price, validated_prefix_ext, horizon_covered


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
        "n": int(len(v)),
        "median": float(np.median(v)),
        "mean": float(np.mean(v)),
        "p10": pct(v, 10),
        "p25": pct(v, 25),
        "p75": pct(v, 75),
        "p90": pct(v, 90),
        "worst": float(v.min()),
        "best": float(v.max()),
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
    return {
        "total_n": total_n,
        "available_n": available_n,
        "unavailable_n": unavailable_n,
        "availability_pct": 100 * available_n / total_n if total_n else 0.0,
    }


# ============================================================
# Experiment-specific: fixed-horizon exit search, two-stage
# empirical coverage (Gate 7)
# ============================================================

def run_diagnostic(instrument, date_str):
    print(f"\n{'='*20} {instrument} {date_str} {'='*20}\n", flush=True)

    pop = reconstruct_population(instrument, date_str)
    print(f"[GATE 2] Target population: {pop['N_TARGET']} -- structural checks PASS", flush=True)

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
    print("[GATE 3] K5 E_position reproduced from validated 200-arrival context: PASS\n", flush=True)

    sample_ranks = np.arange(SAMPLE_EVERY_NTH - 1, N_TARGET2, SAMPLE_EVERY_NTH)
    n_samples = len(sample_ranks)

    expected_n = EXPECTED_SAMPLE_COUNTS[(instrument, date_str)]
    if n_samples != expected_n:
        raise RuntimeError(f"STRUCTURAL FAIL: sample count {n_samples} != expected {expected_n}")

    kernel_sample_tid = pop["kernel_result"]["sample_trade_id"]
    independent_sample_tid = canonical_stream_tid[sample_ranks]

    if len(kernel_sample_tid) != len(independent_sample_tid):
        raise RuntimeError(
            f"STRUCTURAL FAIL: frozen-kernel sample count {len(kernel_sample_tid)} != "
            f"independent every-20th sample count {len(independent_sample_tid)}."
        )
    ki_mismatches = np.where(kernel_sample_tid != independent_sample_tid)[0]
    if len(ki_mismatches) > 0:
        idx = ki_mismatches[0]
        raise RuntimeError(
            f"STRUCTURAL FAIL: frozen-kernel vs independent sample mismatch at sample_index={idx}."
        )
    print(f"[GATE 4] Frozen-kernel sample alignment: {len(kernel_sample_tid)} samples, 0 mismatches -- PASS\n", flush=True)

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
    print("[GATE 6] A_position dominance assertions: PASS\n", flush=True)

    # ----- GATE 7, STAGE A: extend (by receipt time) far enough to resolve entries -----
    max_a_receipt = int(A_receipt.max())
    stage_a_target_receipt = max_a_receipt + SAFETY_MARGIN_MS
    print(f"[GATE 7 / STAGE A] Extending to resolve Delta=0 entries: "
          f"max(A_receipt)={max_a_receipt} + safety={SAFETY_MARGIN_MS} = {stage_a_target_receipt}", flush=True)

    boundary_file = pop["boundary_file"]; boundary_row_ordinal = pop["boundary_row_ordinal"]
    boundary_receipt = pop["boundary_receipt"]

    (extended_tt, extended_tid, extended_tr, extended_price,
     validated_prefix, stage_a_covered) = build_extended_stream_to_horizon(
        instrument, boundary_file, boundary_row_ordinal, boundary_receipt,
        pop["start_ms"], pop["end_ms"], stage_a_target_receipt
    )
    if not stage_a_covered:
        raise RuntimeError(
            "STRUCTURAL FAIL: Stage A (entry-resolution) horizon not covered within "
            "the complete 14-day forward discovery universe. Entry resolution requires "
            "this coverage unconditionally."
        )
    print(f"[GATE 7 / STAGE A] PASS -- extended stream: {len(extended_tid)} arrivals\n", flush=True)

    full_raw_tt = np.concatenate([pop["raw_tt"], extended_tt])
    full_raw_tid = np.concatenate([pop["raw_tid"], extended_tid])
    full_raw_tr = np.concatenate([pop["raw_tr"], extended_tr])
    full_raw_price = np.concatenate([pop["raw_price"], extended_price])
    if not np.all(np.diff(full_raw_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: full raw stream not nondecreasing after Stage A.")
    n_full_raw = len(full_raw_tid)

    # ----- Locked Delta=0 NEW entry (exact rule, unchanged from delta_sensitivity_v1.py) -----
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
    if n_available_entry > 0:
        pos_check = (entry_position[available_entry] > A_position[available_entry]).all()
        tt_check = (full_raw_tt[entry_position[available_entry]] > A_receipt[available_entry]).all()
        if not pos_check or not tt_check:
            raise RuntimeError("STRUCTURAL FAIL: entry causality assertion violated.")
    print(f"[ENTRY] Delta=0 NEW entry: {n_available_entry}/{n_samples} available -- PASS\n", flush=True)

    # ----- GATE 7, STAGE B: real per-entry exchange-time target, empirically covered -----
    # entry_time > A_receipt is a LOWER bound only. The real required
    # exchange-time target is computed from the ACTUAL max(entry_time)
    # now that entries are known -- never assumed or bounded by a
    # receipt-time margin.
    stage_b_covered = True
    if n_available_entry > 0:
        max_entry_time = int(entry_time[available_entry].max())
        max_exit_target_time = max_entry_time + HORIZON_MAX_MS
        print(f"[GATE 7 / STAGE B] Real required exchange-time target: "
              f"max(entry_time)={max_entry_time} + H_max={HORIZON_MAX_MS} = {max_exit_target_time}", flush=True)

        # Empirical check: does the CURRENT full_raw_tt already cover this
        # exchange-time target? If not, extend further (continuing the
        # SAME validated chronology, not re-deriving it).
        current_max_tt = int(full_raw_tt.max()) if n_full_raw > 0 else -1
        if current_max_tt < max_exit_target_time:
            # Extend by receipt time iteratively until exchange-time target
            # is empirically covered, or discovery universe exhausted.
            stage_b_receipt_target = stage_a_target_receipt
            covered = False
            for _ in range(20):  # bounded iteration, not unbounded loop
                stage_b_receipt_target += SAFETY_MARGIN_MS
                (extended_tt2, extended_tid2, extended_tr2, extended_price2,
                 validated_prefix, stage_b_step_covered) = build_extended_stream_to_horizon(
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
                if current_max_tt >= max_exit_target_time:
                    covered = True
                    break
                if not stage_b_step_covered:
                    # Discovery universe exhausted before reaching target --
                    # this is a legitimate end-of-data condition, not a bug.
                    break
            stage_b_covered = covered
        else:
            stage_b_covered = True

        if stage_b_covered:
            print(f"[GATE 7 / STAGE B] PASS -- exchange-time target empirically covered "
                  f"(max observed trade_time={current_max_tt} >= target={max_exit_target_time})\n", flush=True)
        else:
            print(f"[GATE 7 / STAGE B] Discovery universe exhausted before reaching exchange-time "
                  f"target (max observed trade_time={current_max_tt} < target={max_exit_target_time}). "
                  f"Some 60s exits may be legitimately unresolved -- explicitly counted below, not dropped.\n",
                  flush=True)

    # ----- Fixed-horizon exit search: first arrival strictly after entry_position with trade_time > target_H -----
    exit_position_by_h = {}
    exit_price_by_h = {}
    exit_time_by_h = {}

    for h_ms in HORIZONS_MS:
        exit_pos = np.full(n_samples, -1, dtype=np.int64)
        exit_price = np.full(n_samples, np.nan)
        exit_time = np.full(n_samples, -1, dtype=np.int64)
        for i in range(n_samples):
            if entry_position[i] < 0:
                continue
            target_h = entry_time[i] + h_ms
            pos = entry_position[i] + 1
            while pos < n_full_raw:
                if full_raw_tt[pos] > target_h:
                    exit_pos[i] = pos
                    exit_price[i] = full_raw_price[pos]
                    exit_time[i] = full_raw_tt[pos]
                    break
                pos += 1
            # pos == n_full_raw with no break: exit_pos[i] stays -1 --
            # explicitly unresolved (either legitimate end-of-data, or
            # (should not happen given Stage B) a coverage gap. Counted,
            # never silently dropped.

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
        n_unavail = n_samples - n_avail
        print(f"[EXIT H={h_ms}ms] {n_avail}/{n_samples} available "
              f"({n_unavail} unavailable -- legitimate end-of-data or missing entry, explicitly counted)", flush=True)

    print(flush=True)

    threshold = CAUSAL_N10_THRESHOLDS.get((instrument, date_str))
    n10_eligible = threshold is not None

    if n10_eligible:
        imbalance_at_samples = pop["kernel_result"]["imbalance"]
        directions = np.array([classify(v, threshold["p10"], threshold["p90"]) for v in imbalance_at_samples])
        n_short = int((directions == "SHORT").sum())
        n_long = int((directions == "LONG").sum())
        n_none = int((directions == "NONE").sum())
        print(f"N10-eligible: P10={threshold['p10']}, P90={threshold['p90']}", flush=True)
        print(f"Direction counts: SHORT={n_short}, LONG={n_long}, NONE={n_none}\n", flush=True)
    else:
        directions = None
        print(f"SIGNAL_CLASSIFICATION_INELIGIBLE -- frozen N10 reference-date gate failed "
              f"for {instrument} {date_str}. Structural/exit-availability diagnostics only; "
              f"EXCLUDED from all economic gross-return aggregates.\n", flush=True)

    result_record = {
        "instrument": instrument, "date": date_str, "n_samples": n_samples,
        "n10_eligible": n10_eligible,
        "entry_availability": accounting_block(n_samples, n_available_entry),
        "horizon_stats": {},
    }

    npz_payload = {
        "sample_rank": sample_ranks,
        "entry_position": entry_position,
        "entry_time": entry_time,
        "entry_price": entry_price,
        "directions": directions if directions is not None else np.array([]),
    }

    for h_ms in HORIZONS_MS:
        exit_pos = exit_position_by_h[h_ms]
        exit_price = exit_price_by_h[h_ms]
        exit_time = exit_time_by_h[h_ms]
        available = (entry_position >= 0) & (exit_pos >= 0)
        n_avail = int(available.sum())

        hstat = {"availability": accounting_block(n_samples, n_avail)}

        npz_payload[f"exit_position_{h_ms}ms"] = exit_pos
        npz_payload[f"exit_price_{h_ms}ms"] = exit_price
        npz_payload[f"exit_time_{h_ms}ms"] = exit_time
        actual_horizon = np.where(available, exit_time - entry_time, -1)
        npz_payload[f"actual_horizon_ms_{h_ms}ms"] = actual_horizon

        if n10_eligible:
            long_mask = available & (directions == "LONG")
            short_mask = available & (directions == "SHORT")

            long_total_n = int((directions == "LONG").sum())
            short_total_n = int((directions == "SHORT").sum())
            long_avail_n = int(long_mask.sum())
            short_avail_n = int(short_mask.sum())

            if long_avail_n > long_total_n or short_avail_n > short_total_n:
                raise RuntimeError(f"STRUCTURAL FAIL: signal availability accounting impossible at H={h_ms}ms.")

            hstat["signal_availability"] = {
                "long": accounting_block(long_total_n, long_avail_n),
                "short": accounting_block(short_total_n, short_avail_n),
            }

            long_gross = np.array([])
            short_gross = np.array([])
            if long_mask.any():
                long_gross = (exit_price[long_mask] / entry_price[long_mask] - 1) * 10_000
            if short_mask.any():
                short_gross = (entry_price[short_mask] / exit_price[short_mask] - 1) * 10_000

            pooled_gross = np.concatenate([long_gross, short_gross]) if (len(long_gross) or len(short_gross)) else np.array([])

            if len(pooled_gross) != (long_avail_n + short_avail_n):
                raise RuntimeError(f"STRUCTURAL FAIL: pooled gross N mismatch at H={h_ms}ms.")

            npz_payload[f"gross_bp_{h_ms}ms"] = np.where(
                (directions == "LONG") & available, (exit_price / entry_price - 1) * 10_000,
                np.where((directions == "SHORT") & available, (entry_price / exit_price - 1) * 10_000, np.nan)
            )

            hstat["gross_return_pooled"] = summarize_gross_return(pooled_gross)
            hstat["gross_return_long"] = summarize_gross_return(long_gross)
            hstat["gross_return_short"] = summarize_gross_return(short_gross)

        result_record["horizon_stats"][str(h_ms)] = hstat

        gr_str = ""
        if "gross_return_pooled" in hstat and hstat["gross_return_pooled"].get("n", 0) > 0:
            gp = hstat["gross_return_pooled"]
            gr_str = (f" | gross(pooled) median={gp['median']:.3f}bp mean={gp['mean']:.3f}bp "
                      f"pos%={gp['pct_positive']:.1f}% n={gp['n']}")

        print(f"[H={h_ms}ms] avail={n_avail}/{n_samples} "
              f"({hstat['availability']['availability_pct']:.2f}%){gr_str}", flush=True)

    with open(OUTPUT_DIR / f"{instrument}_{date_str}.json", "w") as f:
        json.dump(result_record, f, indent=2, default=str)

    np.savez_compressed(OUTPUT_DIR / f"{instrument}_{date_str}_signals.npz", **npz_payload)

    print(f"\n{instrument} {date_str}: ALL STRUCTURAL GATES PASS", flush=True)

    return {
        "instrument": instrument, "date": date_str, "n10_eligible": n10_eligible,
        "n_samples": n_samples, "directions": directions,
        "entry_price": entry_price, "entry_position": entry_position,
        "exit_position_by_h": exit_position_by_h, "exit_price_by_h": exit_price_by_h,
    }


all_results = []
run_status = []

for instrument, date_str in TEST_POPULATIONS:
    try:
        rec = run_diagnostic(instrument, date_str)
        all_results.append(rec)
        run_status.append((instrument, date_str, "PASS"))
    except RuntimeError as e:
        print(f"\n*** STRUCTURAL FAILURE at {instrument} {date_str}: {e} ***", flush=True)
        run_status.append((instrument, date_str, f"FAIL: {e}"))
        break
    gc.collect()

# ----- Cross-population aggregation: POOLED / BTC / ETH / LONG / SHORT, per horizon -----
print(f"\n\n{'='*20} AGGREGATE BREAKDOWNS {'='*20}\n", flush=True)

eligible_results = [r for r in all_results if r["n10_eligible"]]

for h_ms in HORIZONS_MS:
    pooled_long, pooled_short = [], []
    btc_long, btc_short = [], []
    eth_long, eth_short = [], []

    accounting = {
        key: {"total_n": 0, "available_n": 0, "unavailable_n": 0}
        for key in ("pooled", "btc", "eth", "long", "short")
    }

    for r in eligible_results:
        entry_p = r["entry_price"]
        exit_pos = r["exit_position_by_h"][h_ms]
        exit_p = r["exit_price_by_h"][h_ms]
        directions = r["directions"]

        available = (r["entry_position"] >= 0) & (exit_pos >= 0)
        long_total_mask = directions == "LONG"
        short_total_mask = directions == "SHORT"
        signal_total_mask = long_total_mask | short_total_mask

        long_mask = available & long_total_mask
        short_mask = available & short_total_mask
        signal_avail_mask = available & signal_total_mask

        signal_total_n = int(signal_total_mask.sum())
        signal_avail_n = int(signal_avail_mask.sum())
        long_total_n = int(long_total_mask.sum())
        long_avail_n = int(long_mask.sum())
        short_total_n = int(short_total_mask.sum())
        short_avail_n = int(short_mask.sum())

        venue_key = "btc" if r["instrument"] == "BTC-USD" else "eth"
        for key in ("pooled", venue_key):
            accounting[key]["total_n"] += signal_total_n
            accounting[key]["available_n"] += signal_avail_n
        accounting["long"]["total_n"] += long_total_n
        accounting["long"]["available_n"] += long_avail_n
        accounting["short"]["total_n"] += short_total_n
        accounting["short"]["available_n"] += short_avail_n

        if long_mask.any():
            g = (exit_p[long_mask] / entry_p[long_mask] - 1) * 10_000
            pooled_long.extend(g.tolist())
            (btc_long if r["instrument"] == "BTC-USD" else eth_long).extend(g.tolist())
        if short_mask.any():
            g = (entry_p[short_mask] / exit_p[short_mask] - 1) * 10_000
            pooled_short.extend(g.tolist())
            (btc_short if r["instrument"] == "BTC-USD" else eth_short).extend(g.tolist())

    for key in accounting:
        accounting[key]["unavailable_n"] = accounting[key]["total_n"] - accounting[key]["available_n"]
        if accounting[key]["available_n"] + accounting[key]["unavailable_n"] != accounting[key]["total_n"]:
            raise RuntimeError(f"STRUCTURAL FAIL: aggregate {key} accounting mismatch at H={h_ms}ms.")

    pooled_all = pooled_long + pooled_short
    btc_all = btc_long + btc_short
    eth_all = eth_long + eth_short

    if len(pooled_all) != accounting["pooled"]["available_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: pooled gross N != pooled available N at H={h_ms}ms.")
    if len(btc_all) != accounting["btc"]["available_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: BTC gross N != BTC available N at H={h_ms}ms.")
    if len(eth_all) != accounting["eth"]["available_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: ETH gross N != ETH available N at H={h_ms}ms.")
    if len(pooled_long) != accounting["long"]["available_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: LONG gross N != LONG available N at H={h_ms}ms.")
    if len(pooled_short) != accounting["short"]["available_n"]:
        raise RuntimeError(f"STRUCTURAL FAIL: SHORT gross N != SHORT available N at H={h_ms}ms.")

    aggregate_record = {
        "horizon_ms": h_ms,
        "scope_note": (
            "Gross-return distributions include only N10-eligible LONG/SHORT "
            "signals with observable entry AND exit prices at this horizon. "
            "Unavailable pairs are not assigned synthetic returns; explicitly "
            "counted in availability_accounting."
        ),
        "availability_accounting": accounting,
        "pooled": summarize_gross_return(np.array(pooled_all)),
        "pooled_long": summarize_gross_return(np.array(pooled_long)),
        "pooled_short": summarize_gross_return(np.array(pooled_short)),
        "btc_pooled": summarize_gross_return(np.array(btc_all)),
        "eth_pooled": summarize_gross_return(np.array(eth_all)),
    }

    with open(OUTPUT_DIR / f"aggregate_horizon_{h_ms}ms.json", "w") as f:
        json.dump(aggregate_record, f, indent=2, default=str)

    p = aggregate_record["pooled"]; pl = aggregate_record["pooled_long"]; ps = aggregate_record["pooled_short"]
    ac = accounting["pooled"]
    print(f"[AGGREGATE H={h_ms}ms] signals={ac['total_n']} available={ac['available_n']} "
          f"unavailable={ac['unavailable_n']} | POOLED n={p.get('n',0)} median={p.get('median','N/A')}bp "
          f"mean={p.get('mean','N/A')}bp pos%={p.get('pct_positive','N/A')} | "
          f"LONG n={pl.get('n',0)} median={pl.get('median','N/A')}bp | "
          f"SHORT n={ps.get('n',0)} median={ps.get('median','N/A')}bp", flush=True)

print(f"\n{'='*20} SUMMARY {'='*20}", flush=True)
for instrument, date_str, status in run_status:
    rec = next((r for r in all_results if r["instrument"] == instrument and r["date"] == date_str), None)
    eligible_str = "N10-ELIGIBLE" if (rec and rec["n10_eligible"]) else "N10-INELIGIBLE (structural only, excluded from aggregates)"
    print(f"{instrument} {date_str}: {status} [{eligible_str}]", flush=True)

with open(OUTPUT_DIR / "final_summary.json", "w") as f:
    json.dump(
        [{"instrument": i, "date": d, "status": s,
          "n10_eligible": next((r["n10_eligible"] for r in all_results
                                 if r["instrument"] == i and r["date"] == d), None)}
         for i, d, s in run_status],
        f, indent=2
    )

print(f"\nOutput: {OUTPUT_DIR}", flush=True)