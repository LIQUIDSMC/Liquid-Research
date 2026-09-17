"""
/tmp/delta_sensitivity_v1.py -- TEMPORARY, NOT committed.

Delta-latency sensitivity study, extending the validated causal
actionability-frontier methodology (F_position -> E_position ->
A_position -> NEW entry rule) with hypothetical post-actionability
execution delays Delta in {0, 150, 250, 500, 1000, 2000} ms.

Reuses the EXACT audited reconstruction/K5/F-R-A machinery pattern
from /tmp/causal_frontier_generalization.py (that script itself is
NOT modified -- read-only reference only).

Populations (4): BTC-USD 2026-08-05, BTC-USD 2026-08-22,
ETH-USD 2026-08-27, BTC-USD 2026-09-03.

Delta=0: EXACT locked validated NEW entry rule -- NO receipt-time
condition. Gate 8 validates this rule's causal predicates and
availability; it does NOT claim an independent comparison against a
separately retained Delta=0 baseline artifact, because no such
artifact survives to compare against. This is implementation of the
locked rule, not independent verification against prior output.

Delta>0: D_delta = A_receipt + Delta. First physical arrival after
A_position satisfying BOTH:
    timestamp_received >= D_delta
    trade_time > D_delta

Extended chronology coverage requirement (per population, computed
AFTER F/E/A are known): max(A_receipt) + Delta_max(2000ms) + 60000ms
safety margin.

Locked causal N10 thresholds (independently reconstructed/verified
against L1_CORE/market_data_platform/research/results/
threshold_stability_v1/threshold_stability_results.json):
    BTC Aug05: P10=-0.9124993108067109  P90=0.995520576372723   obs=233713
    BTC Aug22: P10=-0.8916056119723363  P90=0.9638883167380699  obs=342125
    ETH Aug27: P10=-0.8260489240979522  P90=0.9047507863169619  obs=211336
    BTC Sep03: N10 INELIGIBLE -- structural diagnostics only, EXCLUDED
               from all direction-adjusted adverse-move statistics
               and from pooled/BTC/LONG/SHORT aggregates.

Phase 1 output ONLY: entry availability, entry price by Delta, entry
physical displacement, entry receipt delay, entry exchange-time
displacement, and direction-adjusted adverse entry move (bp) for
LONG/SHORT samples only. NO exits, NO P&L, NO fees/sizing, NO fill
claims, NO profitability conclusion.

STOP ON FIRST STRUCTURAL FAILURE per population. Numerical/diagnostic
variation (availability, adverse-move magnitude) reported, never
gated on.

Canonical storage read-only. No frozen-kernel changes. Does not
modify /tmp/causal_frontier_generalization.py.

Memory-conscious: compact NumPy arrays, intermediates released per
population via gc.collect(). Fail-closed fresh output directory
(refuses to overwrite an existing run).
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

DELTAS_MS = [0, 150, 250, 500, 1000, 2000]
DELTA_MAX_MS = max(DELTAS_MS)

root = Path("/mnt/lrs001/data/market_data_platform/canonical/trades")

OUTPUT_DIR = Path("/tmp/delta_sensitivity_v1_results")
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
    # Frozen N10 reference-date gate failed (2026-09-01/02, 2026-08-31).
    # No skipping/backfill. Any lookup for this key must fail closed.
}

TEST_POPULATIONS = [
    ("BTC-USD", "2026-08-05"),
    ("BTC-USD", "2026-08-22"),
    ("ETH-USD", "2026-08-27"),
    ("BTC-USD", "2026-09-03"),
]


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
                                       start_ms, end_ms, entry_horizon_receipt):
    boundary_partition_dir = boundary_file.parent
    boundary_partition_date = datetime.strptime(boundary_partition_dir.name.replace("date=", ""), "%Y-%m-%d").date()

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
    horizon_covered = False

    for i in range(final_idx_ext, len(by_first_ext)):
        r = by_first_ext[i]
        if not r["internally_monotonic"]:
            raise RuntimeError(f"STRUCTURAL FAIL: {r['path']} not internally receipt-monotonic (extended).")
        if validated_prefix_ext and r["first_received"] <= running_max_last_ext:
            raise RuntimeError(f"STRUCTURAL FAIL: extended-context chronology ambiguity/overlap at position {len(validated_prefix_ext)}.")
        validated_prefix_ext.append(r)
        running_max_last_ext = max(running_max_last_ext, r["last_received"])

        if r["last_received"] >= entry_horizon_receipt:
            if i + 1 < len(by_first_ext):
                next_first = by_first_ext[i+1]["first_received"]
                if next_first <= entry_horizon_receipt:
                    raise RuntimeError(f"STRUCTURAL FAIL: horizon-closure check failed (next_first={next_first}).")
            horizon_covered = True
            break

    if not horizon_covered:
        raise RuntimeError(
            f"STRUCTURAL FAIL: required extended horizon ({entry_horizon_receipt}) not covered "
            f"within complete 14-day discovery universe."
        )

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
            tr = int(table.column("timestamp_received")[row_ord].as_py())
            if tr > entry_horizon_receipt:
                return True
            tid = int(table.column("trade_id")[row_ord].as_py())
            price = float(table.column("price")[row_ord].as_py())
            ext_tt.append(tt); ext_tid.append(tid); ext_tr.append(tr); ext_price.append(price)
        return False

    done = process_ext_file(boundary_file, boundary_row_ordinal + 1)
    if not done:
        for i in range(boundary_idx_ext + 1, len(ordered_ext)):
            if process_ext_file(ordered_ext[i], 0):
                done = True
                break

    extended_tt = np.array(ext_tt); extended_tid = np.array(ext_tid)
    extended_tr = np.array(ext_tr); extended_price = np.array(ext_price)
    if not np.all(np.diff(extended_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: extended stream not nondecreasing.")
    if len(extended_tr) > 0 and extended_tr.max() > entry_horizon_receipt:
        raise RuntimeError("STRUCTURAL FAIL: extended_tr.max() exceeds required horizon.")

    return extended_tt, extended_tid, extended_tr, extended_price


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
        "p75": pct(v, 75),
        "p90": pct(v, 90),
        "p95": pct(v, 95),
        "p99": pct(v, 99),
        "worst": float(v.max()),
    }


def summarize_adverse_bp(adverse_bp):
    if len(adverse_bp) == 0:
        return {"n": 0}
    v = np.asarray(adverse_bp, dtype=np.float64)
    d = summarize_distribution(v)
    d["pct_worse_than_0bp"] = float(100 * np.mean(v > 0))
    d["pct_worse_than_1bp"] = float(100 * np.mean(v > 1))
    d["pct_worse_than_2bp"] = float(100 * np.mean(v > 2))
    d["pct_worse_than_5bp"] = float(100 * np.mean(v > 5))
    return d


def run_diagnostic(instrument, date_str):
    print(f"\n{'='*20} {instrument} {date_str} {'='*20}\n", flush=True)

    pop = reconstruct_population(instrument, date_str)
    print(f"[GATE 2] Target population: {pop['N_TARGET']} -- structural checks PASS", flush=True)
    print(f"Boundary (derived): {pop['boundary_file'].name}, row_ordinal={pop['boundary_row_ordinal']}, "
          f"receipt={pop['boundary_receipt']}\n", flush=True)

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
            f"STRUCTURAL FAIL: frozen-kernel vs independent sample mismatch at "
            f"sample_index={idx}, canonical_rank={sample_ranks[idx]}."
        )
    print(f"[GATE 4] Frozen-kernel sample alignment: {len(kernel_sample_tid)} samples, "
          f"0 mismatches vs independent every-20th population -- PASS\n", flush=True)

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
    E_receipt = combined_tr[E_position]
    A_position = np.maximum(F_position, E_position)
    A_receipt = combined_tr[A_position]
    assert (A_position >= F_position).all() and (A_position >= E_position).all()
    print("[GATE 6] A_position dominance assertions: PASS\n", flush=True)

    max_a_receipt = int(A_receipt.max())
    required_horizon_receipt = max_a_receipt + DELTA_MAX_MS + SAFETY_MARGIN_MS
    print(f"[GATE 7] Required extended horizon: max(A_receipt)={max_a_receipt} + "
          f"Delta_max={DELTA_MAX_MS} + safety={SAFETY_MARGIN_MS} = {required_horizon_receipt}", flush=True)

    boundary_file = pop["boundary_file"]; boundary_row_ordinal = pop["boundary_row_ordinal"]
    boundary_receipt = pop["boundary_receipt"]

    extended_tt, extended_tid, extended_tr, extended_price = build_extended_stream_to_horizon(
        instrument, boundary_file, boundary_row_ordinal, boundary_receipt,
        pop["start_ms"], pop["end_ms"], required_horizon_receipt
    )
    print(f"[GATE 7] PASS -- extended stream: {len(extended_tid)} arrivals through required horizon\n", flush=True)

    full_raw_tt = np.concatenate([pop["raw_tt"], extended_tt])
    full_raw_tid = np.concatenate([pop["raw_tid"], extended_tid])
    full_raw_tr = np.concatenate([pop["raw_tr"], extended_tr])
    full_raw_price = np.concatenate([pop["raw_price"], extended_price])
    if not np.all(np.diff(full_raw_tr) >= 0):
        raise RuntimeError("STRUCTURAL FAIL: full raw entry-search stream not nondecreasing.")
    n_full_raw = len(full_raw_tid)

    entry_position_by_delta = {}
    entry_price_by_delta = {}

    # ----- GATE 8: Delta=0. EXACT locked NEW rule. NO receipt condition. -----
    entry_position_0 = np.full(n_samples, -1, dtype=np.int64)
    entry_price_0 = np.full(n_samples, np.nan)
    for i in range(n_samples):
        pos = A_position[i] + 1
        while pos < n_full_raw:
            if full_raw_tt[pos] > A_receipt[i]:
                entry_position_0[i] = pos
                entry_price_0[i] = full_raw_price[pos]
                break
            pos += 1

    entry_position_by_delta[0] = entry_position_0
    entry_price_by_delta[0] = entry_price_0

    available_0 = entry_position_0 >= 0
    n_available_0 = int(available_0.sum())
    if n_available_0 > 0:
        pos_check = (entry_position_0[available_0] > A_position[available_0]).all()
        tt_check = (full_raw_tt[entry_position_0[available_0]] > A_receipt[available_0]).all()
        if not pos_check or not tt_check:
            raise RuntimeError("STRUCTURAL FAIL: Delta=0 entry causality assertion violated.")
    print(f"[GATE 8] Delta=0: implements locked validated NEW rule (no receipt condition). "
          f"{n_available_0}/{n_samples} available, causal predicates verified -- PASS. "
          f"(Implementation of the locked rule; not an independent comparison against a "
          f"separately retained baseline artifact.)\n", flush=True)

    # ----- GATE 9: Delta>0. BOTH timestamp_received >= D_delta AND trade_time > D_delta. -----
    for delta_ms in DELTAS_MS[1:]:
        D_delta = A_receipt + delta_ms
        entry_position_d = np.full(n_samples, -1, dtype=np.int64)
        entry_price_d = np.full(n_samples, np.nan)
        for i in range(n_samples):
            pos = A_position[i] + 1
            target_d = D_delta[i]
            while pos < n_full_raw:
                if full_raw_tr[pos] >= target_d and full_raw_tt[pos] > target_d:
                    entry_position_d[i] = pos
                    entry_price_d[i] = full_raw_price[pos]
                    break
                pos += 1

        available_d = entry_position_d >= 0
        if available_d.any():
            pos_check = (entry_position_d[available_d] > A_position[available_d]).all()
            recv_check = (full_raw_tr[entry_position_d[available_d]] >= D_delta[available_d]).all()
            tt_check = (full_raw_tt[entry_position_d[available_d]] > D_delta[available_d]).all()
            if not (pos_check and recv_check and tt_check):
                raise RuntimeError(f"STRUCTURAL FAIL: Delta={delta_ms}ms entry causality assertion violated.")

        entry_position_by_delta[delta_ms] = entry_position_d
        entry_price_by_delta[delta_ms] = entry_price_d
        n_avail_d = int(available_d.sum())
        n_unavail_d = n_samples - n_avail_d
        print(f"[GATE 9] Delta={delta_ms}ms: {n_avail_d}/{n_samples} available "
              f"({n_unavail_d} unavailable, explicitly counted), causality PASS", flush=True)

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
              f"for {instrument} {date_str}. Structural diagnostics only; EXCLUDED from all "
              f"direction-adjusted adverse-move statistics and pooled/BTC/LONG/SHORT "
              f"aggregates.\n", flush=True)

    result_record = {
        "instrument": instrument, "date": date_str, "n_samples": n_samples,
        "n10_eligible": n10_eligible,
        "delta_stats": {},
    }

    for delta_ms in DELTAS_MS:
        entry_pos = entry_position_by_delta[delta_ms]
        entry_price = entry_price_by_delta[delta_ms]
        available = entry_pos >= 0
        n_avail = int(available.sum())

        stat = {
            "total_n": n_samples,
            "available_n": n_avail,
            "unavailable_n": n_samples - n_avail,
            "availability_pct": 100 * n_avail / n_samples if n_samples else 0.0,
        }

        if n_avail > 0:
            disp = entry_pos[available] - A_position[available]
            recv_delay = full_raw_tr[entry_pos[available]] - A_receipt[available]
            tt_disp = full_raw_tt[entry_pos[available]] - A_receipt[available]
            stat["displacement"] = summarize_distribution(disp)
            stat["receipt_delay"] = summarize_distribution(recv_delay)
            stat["exchange_time_displacement"] = summarize_distribution(tt_disp)
            stat["entry_price"] = summarize_distribution(entry_price[available])

        if n10_eligible and delta_ms > 0:
            entry_0 = entry_price_by_delta[0]
            available_0_pair = entry_position_by_delta[0] >= 0
            both_avail = available & available_0_pair

            signal_mask = (directions == "LONG") | (directions == "SHORT")
            long_total_mask = directions == "LONG"
            short_total_mask = directions == "SHORT"

            long_mask = both_avail & long_total_mask
            short_mask = both_avail & short_total_mask

            signal_total_n = int(signal_mask.sum())
            signal_both_available_n = int((both_avail & signal_mask).sum())
            signal_unavailable_pair_n = signal_total_n - signal_both_available_n

            long_total_n = int(long_total_mask.sum())
            long_both_available_n = int(long_mask.sum())
            long_unavailable_pair_n = long_total_n - long_both_available_n

            short_total_n = int(short_total_mask.sum())
            short_both_available_n = int(short_mask.sum())
            short_unavailable_pair_n = short_total_n - short_both_available_n

            if signal_both_available_n + signal_unavailable_pair_n != signal_total_n:
                raise RuntimeError("STRUCTURAL FAIL: signal availability accounting mismatch.")
            if long_both_available_n + long_unavailable_pair_n != long_total_n:
                raise RuntimeError("STRUCTURAL FAIL: LONG availability accounting mismatch.")
            if short_both_available_n + short_unavailable_pair_n != short_total_n:
                raise RuntimeError("STRUCTURAL FAIL: SHORT availability accounting mismatch.")

            stat["signal_availability"] = {
                "signal_total_n": signal_total_n,
                "signal_both_available_n": signal_both_available_n,
                "signal_unavailable_pair_n": signal_unavailable_pair_n,
                "long_total_n": long_total_n,
                "long_both_available_n": long_both_available_n,
                "long_unavailable_pair_n": long_unavailable_pair_n,
                "short_total_n": short_total_n,
                "short_both_available_n": short_both_available_n,
                "short_unavailable_pair_n": short_unavailable_pair_n,
            }

            long_adverse = np.array([])
            short_adverse = np.array([])
            if long_mask.any():
                p_delta = entry_price[long_mask]; p_0 = entry_0[long_mask]
                long_adverse = (p_delta / p_0 - 1) * 10_000
            if short_mask.any():
                p_delta = entry_price[short_mask]; p_0 = entry_0[short_mask]
                short_adverse = (p_0 / p_delta - 1) * 10_000

            pooled_adverse = np.concatenate([long_adverse, short_adverse]) if (len(long_adverse) or len(short_adverse)) else np.array([])

            stat["adverse_move_pooled"] = summarize_adverse_bp(pooled_adverse)
            stat["adverse_move_long"] = summarize_adverse_bp(long_adverse)
            stat["adverse_move_short"] = summarize_adverse_bp(short_adverse)

        result_record["delta_stats"][str(delta_ms)] = stat

        adv_str = ""
        if "adverse_move_pooled" in stat and stat["adverse_move_pooled"].get("n", 0) > 0:
            am = stat["adverse_move_pooled"]
            adv_str = f" | adverse(pooled) median={am['median']:.3f}bp p90={am['p90']:.3f}bp n={am['n']}"

        print(f"[Delta={delta_ms}ms] avail={n_avail}/{n_samples} "
              f"({stat['availability_pct']:.2f}%){adv_str}", flush=True)

    with open(OUTPUT_DIR / f"{instrument}_{date_str}.json", "w") as f:
        json.dump(result_record, f, indent=2, default=str)

    print(f"\n{instrument} {date_str}: ALL STRUCTURAL GATES PASS", flush=True)

    # Return only what's needed for aggregation -- not full arrays -- to stay memory-conscious.
    return {
        "instrument": instrument, "date": date_str, "n10_eligible": n10_eligible,
        "n_samples": n_samples, "directions": directions,
        "entry_price_by_delta": entry_price_by_delta,
        "entry_position_by_delta": entry_position_by_delta,
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

# ----- Cross-population aggregation: POOLED / BTC / ETH / LONG / SHORT -----
print(f"\n\n{'='*20} AGGREGATE BREAKDOWNS {'='*20}\n", flush=True)

eligible_results = [r for r in all_results if r["n10_eligible"]]

for delta_ms in DELTAS_MS[1:]:
    pooled_long, pooled_short = [], []
    btc_long, btc_short = [], []
    eth_long, eth_short = [], []

    accounting = {
        "pooled": {
            "signal_total_n": 0,
            "signal_both_available_n": 0,
            "signal_unavailable_pair_n": 0,
        },
        "btc": {
            "signal_total_n": 0,
            "signal_both_available_n": 0,
            "signal_unavailable_pair_n": 0,
        },
        "eth": {
            "signal_total_n": 0,
            "signal_both_available_n": 0,
            "signal_unavailable_pair_n": 0,
        },
        "long": {
            "signal_total_n": 0,
            "signal_both_available_n": 0,
            "signal_unavailable_pair_n": 0,
        },
        "short": {
            "signal_total_n": 0,
            "signal_both_available_n": 0,
            "signal_unavailable_pair_n": 0,
        },
    }

    for r in eligible_results:
        entry_0 = r["entry_price_by_delta"][0]
        entry_d_price = r["entry_price_by_delta"][delta_ms]
        entry_d_pos = r["entry_position_by_delta"][delta_ms]
        entry_0_pos = r["entry_position_by_delta"][0]
        directions = r["directions"]

        available_0 = entry_0_pos >= 0
        available_d = entry_d_pos >= 0
        both_avail = available_0 & available_d

        long_total_mask = directions == "LONG"
        short_total_mask = directions == "SHORT"
        signal_mask = long_total_mask | short_total_mask

        long_mask = both_avail & long_total_mask
        short_mask = both_avail & short_total_mask
        signal_both_mask = both_avail & signal_mask

        signal_total_n = int(signal_mask.sum())
        signal_both_n = int(signal_both_mask.sum())
        signal_unavailable_n = signal_total_n - signal_both_n

        long_total_n = int(long_total_mask.sum())
        long_both_n = int(long_mask.sum())
        long_unavailable_n = long_total_n - long_both_n

        short_total_n = int(short_total_mask.sum())
        short_both_n = int(short_mask.sum())
        short_unavailable_n = short_total_n - short_both_n

        if signal_both_n + signal_unavailable_n != signal_total_n:
            raise RuntimeError(
                f"STRUCTURAL FAIL: aggregate signal accounting mismatch "
                f"for {r['instrument']} {r['date']} Delta={delta_ms}ms."
            )
        if long_both_n + long_unavailable_n != long_total_n:
            raise RuntimeError(
                f"STRUCTURAL FAIL: aggregate LONG accounting mismatch "
                f"for {r['instrument']} {r['date']} Delta={delta_ms}ms."
            )
        if short_both_n + short_unavailable_n != short_total_n:
            raise RuntimeError(
                f"STRUCTURAL FAIL: aggregate SHORT accounting mismatch "
                f"for {r['instrument']} {r['date']} Delta={delta_ms}ms."
            )

        venue_key = "btc" if r["instrument"] == "BTC-USD" else "eth"

        for key in ("pooled", venue_key):
            accounting[key]["signal_total_n"] += signal_total_n
            accounting[key]["signal_both_available_n"] += signal_both_n
            accounting[key]["signal_unavailable_pair_n"] += signal_unavailable_n

        accounting["long"]["signal_total_n"] += long_total_n
        accounting["long"]["signal_both_available_n"] += long_both_n
        accounting["long"]["signal_unavailable_pair_n"] += long_unavailable_n

        accounting["short"]["signal_total_n"] += short_total_n
        accounting["short"]["signal_both_available_n"] += short_both_n
        accounting["short"]["signal_unavailable_pair_n"] += short_unavailable_n

        if long_mask.any():
            adv = (entry_d_price[long_mask] / entry_0[long_mask] - 1) * 10_000
            pooled_long.extend(adv.tolist())
            if r["instrument"] == "BTC-USD":
                btc_long.extend(adv.tolist())
            else:
                eth_long.extend(adv.tolist())

        if short_mask.any():
            adv = (entry_0[short_mask] / entry_d_price[short_mask] - 1) * 10_000
            pooled_short.extend(adv.tolist())
            if r["instrument"] == "BTC-USD":
                btc_short.extend(adv.tolist())
            else:
                eth_short.extend(adv.tolist())

    # Cross-check aggregate accounting itself.
    for key, counts in accounting.items():
        if (
            counts["signal_both_available_n"]
            + counts["signal_unavailable_pair_n"]
            != counts["signal_total_n"]
        ):
            raise RuntimeError(
                f"STRUCTURAL FAIL: aggregate {key} denominator accounting "
                f"mismatch at Delta={delta_ms}ms."
            )

    pooled_all = pooled_long + pooled_short
    btc_all = btc_long + btc_short
    eth_all = eth_long + eth_short

    # Adverse arrays must exactly match their disclosed observable denominators.
    if len(pooled_all) != accounting["pooled"]["signal_both_available_n"]:
        raise RuntimeError(
            f"STRUCTURAL FAIL: pooled adverse N != pooled both-available N "
            f"at Delta={delta_ms}ms."
        )
    if len(btc_all) != accounting["btc"]["signal_both_available_n"]:
        raise RuntimeError(
            f"STRUCTURAL FAIL: BTC adverse N != BTC both-available N "
            f"at Delta={delta_ms}ms."
        )
    if len(eth_all) != accounting["eth"]["signal_both_available_n"]:
        raise RuntimeError(
            f"STRUCTURAL FAIL: ETH adverse N != ETH both-available N "
            f"at Delta={delta_ms}ms."
        )
    if len(pooled_long) != accounting["long"]["signal_both_available_n"]:
        raise RuntimeError(
            f"STRUCTURAL FAIL: LONG adverse N != LONG both-available N "
            f"at Delta={delta_ms}ms."
        )
    if len(pooled_short) != accounting["short"]["signal_both_available_n"]:
        raise RuntimeError(
            f"STRUCTURAL FAIL: SHORT adverse N != SHORT both-available N "
            f"at Delta={delta_ms}ms."
        )

    aggregate_record = {
        "delta_ms": delta_ms,
        "scope_note": (
            "Adverse-move distributions include only N10-eligible LONG/SHORT "
            "signals with observable entry prices at BOTH Delta=0 and this "
            "Delta. Unavailable pairs are not assigned synthetic adverse moves; "
            "they are explicitly counted in availability_accounting."
        ),
        "availability_accounting": accounting,
        "pooled": summarize_adverse_bp(np.array(pooled_all)),
        "pooled_long": summarize_adverse_bp(np.array(pooled_long)),
        "pooled_short": summarize_adverse_bp(np.array(pooled_short)),
        "btc_pooled": summarize_adverse_bp(np.array(btc_all)),
        "eth_pooled": summarize_adverse_bp(np.array(eth_all)),
    }

    with open(OUTPUT_DIR / f"aggregate_delta_{delta_ms}ms.json", "w") as f:
        json.dump(aggregate_record, f, indent=2, default=str)

    ac = aggregate_record["availability_accounting"]["pooled"]

    print(
        f"[AGGREGATE Delta={delta_ms}ms] "
        f"signals={ac['signal_total_n']} "
        f"both_available={ac['signal_both_available_n']} "
        f"unavailable_pairs={ac['signal_unavailable_pair_n']} | "
        f"POOLED adverse_n={aggregate_record['pooled'].get('n', 0)} "
        f"median={aggregate_record['pooled'].get('median', 'N/A')}bp | "
        f"LONG n={aggregate_record['pooled_long'].get('n', 0)} "
        f"median={aggregate_record['pooled_long'].get('median', 'N/A')}bp | "
        f"SHORT n={aggregate_record['pooled_short'].get('n', 0)} "
        f"median={aggregate_record['pooled_short'].get('median', 'N/A')}bp",
        flush=True,
    )

print(f"\n{'='*20} SUMMARY {'='*20}", flush=True)
for instrument, date_str, status in run_status:
    rec = next((r for r in all_results if r["instrument"] == instrument and r["date"] == date_str), None)
    eligible_str = "N10-ELIGIBLE" if (rec and rec["n10_eligible"]) else "N10-INELIGIBLE (structural only, excluded from aggregates)"
    print(f"{instrument} {date_str}: {status} [{eligible_str}]", flush=True)

with open(OUTPUT_DIR / "final_summary.json", "w") as f:
    json.dump(
        [{"instrument": i, "date": d, "status": s} for i, d, s in run_status],
        f, indent=2
    )

print(f"\nOutput: {OUTPUT_DIR}", flush=True)
