"""
Market Data Platform — Forked Canonical Tree Reconciliation
market_data_platform/market_data/reconcile_forked_canonical.py

INCIDENT: On 2026-08-24 between 23:41:22-23:41:33 PDT, the symlink at
L1_CORE/market_data_platform/data/canonical (intended to point at the
SSD-backed /mnt/lrs001/data/market_data_platform/canonical) was
replaced by a real directory. Exact triggering command not
established from available evidence. From that moment until the
collector was stopped on 2026-08-30, all live trade and depth writes
went to this repo-local directory instead of the intended SSD path.

This script reconciles that forked data back into the real SSD
canonical tree. This IS the promotion step for this data -- no
separate later promotion follows.

Memory-safe design: the Pi has ~905Mi RAM. An earlier version of this
script materialized the full ~1.1M-file copy plan into a Python list
before doing anything, and was OOM-killed. This version uses a
streaming generator (iter_copy_plan) that processes one date
partition at a time, keeping memory bounded regardless of corpus
size.

Preflight manifest (established 2026-08-30, re-verified fresh
2026-08-31, both trees frozen, collector stopped):

FORK TRADES (expected 47,918 total)
  Aug 25: 7,772   Aug 26: 3,483   Aug 27: 8,791   Aug 28: 9,169
  Aug 29: 8,433   Aug 30: 8,437   Aug 31: 1,833

FORK DEPTH (expected 1,088,320 total)
  Aug 25: 214,854   Aug 26: 87,989   Aug 27: 229,156   Aug 28: 233,368
  Aug 29: 110,155   Aug 30: 161,102   Aug 31: 51,696

ZERO-BYTE FILES (expected exactly 1):
  depth_levels/date=2026-08-31/921c0484-2830-476a-85ac-ce7e402fc49c.parquet

SSD Aug 25 existing (merge target, non-fork data already present):
  Trades: 3,092   Depth: 90,906

Expected Aug 25 post-merge totals:
  Trades: 10,864 (3,092 + 7,772)
  Depth: 305,760 (90,906 + 214,854)

Full-corpus filename collisions between fork and SSD: 0.

Usage:
    python3 -m L1_CORE.market_data_platform.market_data.reconcile_forked_canonical --verify-manifest
    python3 -m L1_CORE.market_data_platform.market_data.reconcile_forked_canonical --dry-run
    python3 -m L1_CORE.market_data_platform.market_data.reconcile_forked_canonical --execute
    python3 -m L1_CORE.market_data_platform.market_data.reconcile_forked_canonical --verify-post-merge

Never deletes or overwrites either source tree. Never deletes the
fork after copying -- fork cleanup is a deliberate, separate,
later decision made only after independent validation passes.
"""

import argparse
import shutil
import sys
from pathlib import Path

import pyarrow.parquet as pq

SSD_ROOT = Path("/mnt/lrs001/data/market_data_platform/canonical")
FORK_ROOT = Path("/mnt/lrs001/liquid-research-l0l4/L1_CORE/market_data_platform/data/canonical")
DATASETS = ["trades", "depth_levels"]

EXPECTED_FORK_COUNTS = {
    "trades": {
        "date=2026-08-25": 7772, "date=2026-08-26": 3483, "date=2026-08-27": 8791,
        "date=2026-08-28": 9169, "date=2026-08-29": 8433, "date=2026-08-30": 8437,
        "date=2026-08-31": 1833,
    },
    "depth_levels": {
        "date=2026-08-25": 214854, "date=2026-08-26": 87989, "date=2026-08-27": 229156,
        "date=2026-08-28": 233368, "date=2026-08-29": 110155, "date=2026-08-30": 161102,
        "date=2026-08-31": 51696,
    },
}
EXPECTED_ZERO_BYTE = {
    FORK_ROOT / "depth_levels" / "date=2026-08-31" / "921c0484-2830-476a-85ac-ce7e402fc49c.parquet"
}
EXPECTED_SSD_AUG25_EXISTING = {"trades": 3092, "depth_levels": 90906}
EXPECTED_AUG25_POST_MERGE = {"trades": 10864, "depth_levels": 305760}


def verify_manifest():
    print("===== MANIFEST VERIFICATION =====")
    ok = True

    for dataset, expected_dates in EXPECTED_FORK_COUNTS.items():
        for date_dir, expected_count in expected_dates.items():
            actual = len(list((FORK_ROOT / dataset / date_dir).glob("*.parquet")))
            status = "OK" if actual == expected_count else "MISMATCH"
            if actual != expected_count:
                ok = False
            print(f"  [{status}] fork/{dataset}/{date_dir}: expected={expected_count} actual={actual}")

    zero_byte_found = set()
    for dataset in DATASETS:
        for date_dir in EXPECTED_FORK_COUNTS[dataset]:
            for f in (FORK_ROOT / dataset / date_dir).glob("*.parquet"):
                if f.stat().st_size == 0:
                    zero_byte_found.add(f)

    if zero_byte_found != EXPECTED_ZERO_BYTE:
        ok = False
        print(f"  [MISMATCH] zero-byte files: expected={EXPECTED_ZERO_BYTE} actual={zero_byte_found}")
    else:
        print("  [OK] zero-byte files match manifest exactly (1 file)")

    for dataset, expected_count in EXPECTED_SSD_AUG25_EXISTING.items():
        actual = len(list((SSD_ROOT / dataset / "date=2026-08-25").glob("*.parquet")))
        status = "OK" if actual == expected_count else "MISMATCH"
        if actual != expected_count:
            ok = False
        print(f"  [{status}] SSD/{dataset}/date=2026-08-25 (pre-merge): expected={expected_count} actual={actual}")

    print()
    if ok:
        print("MANIFEST VERIFICATION: PASS")
    else:
        print("MANIFEST VERIFICATION: FAIL -- state has drifted since preflight. Do not proceed.")
        sys.exit(1)
    return ok


def iter_copy_plan():
    """
    Memory-safe generator: yields (dataset, date_dir, src, dest, action)
    one file at a time. Iterates date-partition by date-partition (per
    the known manifest) rather than an unbounded rglob, so memory stays
    bounded to one partition's listing at a time regardless of total
    corpus size (~1.1M files across both datasets).
    """
    for dataset in DATASETS:
        fork_dir = FORK_ROOT / dataset
        ssd_dir = SSD_ROOT / dataset

        for date_dir in sorted(EXPECTED_FORK_COUNTS[dataset]):
            partition = fork_dir / date_dir
            for f in partition.glob("*.parquet"):
                if f.stat().st_size == 0:
                    yield (dataset, date_dir, f, None, "zero_byte")
                    continue

                rel = f.relative_to(fork_dir)
                dest = ssd_dir / rel

                if dest.exists():
                    yield (dataset, date_dir, f, dest, "collision")
                    continue

                yield (dataset, date_dir, f, dest, "copy")


def dry_run():
    print("===== DRY RUN =====")
    counts = {"trades": {"copy": 0, "zero_byte": 0, "collision": 0},
              "depth_levels": {"copy": 0, "zero_byte": 0, "collision": 0}}
    collision_examples = []
    zero_byte_examples = []

    for dataset, date_dir, src, dest, action in iter_copy_plan():
        counts[dataset][action] += 1
        if action == "collision" and len(collision_examples) < 20:
            collision_examples.append((src, dest))
        if action == "zero_byte" and len(zero_byte_examples) < 20:
            zero_byte_examples.append(src)

    for dataset in DATASETS:
        c = counts[dataset]
        print(f"  {dataset}: would copy={c['copy']} zero_byte_skip={c['zero_byte']} collision={c['collision']}")

    print("\nZero-byte examples:")
    for f in zero_byte_examples:
        print(f"  SKIP: {f}")

    print("\nCollision examples (would abort --execute):")
    for src, dest in collision_examples:
        print(f"  COLLISION: {src} -> {dest}")

    total_copy = sum(counts[d]["copy"] for d in DATASETS)
    total_collision = sum(counts[d]["collision"] for d in DATASETS)
    print(f"\nTotal files that would be copied: {total_copy}")
    print(f"Total collisions: {total_collision}")
    print("Dry run complete. No files copied.")


def execute():
    verify_manifest()

    # First pass (streaming, memory-safe): check for any collision
    # before writing anything.
    collision_count = 0
    collision_examples = []
    for dataset, date_dir, src, dest, action in iter_copy_plan():
        if action == "collision":
            collision_count += 1
            if len(collision_examples) < 20:
                collision_examples.append((src, dest))

    if collision_count:
        print(f"ABORTING: {collision_count} filename collision(s) at destination. Refusing to execute.")
        for src, dest in collision_examples:
            print(f"  COLLISION: {src} -> {dest}")
        sys.exit(1)

    print("===== EXECUTING COPY =====")
    copied_by_dataset = {"trades": 0, "depth_levels": 0}
    skipped_zero_byte = 0
    failed = []

    # Second pass (streaming, memory-safe): perform the actual copies.
    for dataset, date_dir, src, dest, action in iter_copy_plan():
        if action == "zero_byte":
            skipped_zero_byte += 1
            continue
        if action == "collision":
            continue  # already aborted above if any existed

        try:
            pq.read_metadata(src)

            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_dest = dest.with_suffix(".parquet.tmp")
            shutil.copy2(src, tmp_dest)

            if tmp_dest.stat().st_size != src.stat().st_size:
                raise RuntimeError(f"size mismatch after copy: {tmp_dest}")
            pq.read_metadata(tmp_dest)

            tmp_dest.rename(dest)
            copied_by_dataset[dataset] += 1

            total_copied = copied_by_dataset["trades"] + copied_by_dataset["depth_levels"]
            if total_copied % 25000 == 0:
                print(f"  Progress: {total_copied} files copied so far "
                      f"(trades={copied_by_dataset['trades']} depth={copied_by_dataset['depth_levels']})")
        except Exception as e:
            failed.append((src, dest, str(e)))
            print(f"  FAILED: {src} -> {dest}: {e}")

    print(f"\nTrades copied: {copied_by_dataset['trades']}")
    print(f"Depth copied: {copied_by_dataset['depth_levels']}")
    print(f"Failed: {len(failed)}")
    print(f"Zero-byte excluded (expected): {skipped_zero_byte}")

    if failed:
        print("\nEXECUTION COMPLETED WITH FAILURES. Review before trusting the merge.")
        sys.exit(1)
    else:
        print("\nEXECUTION COMPLETE. Run --verify-post-merge next.")


def verify_post_merge():
    print("===== POST-MERGE VERIFICATION =====")
    ok = True

    for dataset, expected in EXPECTED_AUG25_POST_MERGE.items():
        actual = len(list((SSD_ROOT / dataset / "date=2026-08-25").glob("*.parquet")))
        status = "OK" if actual == expected else "MISMATCH"
        if actual != expected:
            ok = False
        print(f"  [{status}] SSD/{dataset}/date=2026-08-25 post-merge: expected={expected} actual={actual}")

    for dataset in DATASETS:
        for date_dir in EXPECTED_FORK_COUNTS[dataset]:
            if date_dir == "date=2026-08-25":
                continue
            expected = EXPECTED_FORK_COUNTS[dataset][date_dir]
            actual = len(list((SSD_ROOT / dataset / date_dir).glob("*.parquet")))
            status = "OK" if actual == expected else "MISMATCH"
            if actual != expected:
                ok = False
            print(f"  [{status}] SSD/{dataset}/{date_dir} (new partition): expected={expected} actual={actual}")

    print()
    print("POST-MERGE VERIFICATION:", "PASS" if ok else "FAIL")
    if not ok:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify-manifest", action="store_true")
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--verify-post-merge", action="store_true")
    args = parser.parse_args()

    if args.verify_manifest:
        verify_manifest()
    elif args.dry_run:
        dry_run()
    elif args.execute:
        execute()
    elif args.verify_post_merge:
        verify_post_merge()


if __name__ == "__main__":
    main()
