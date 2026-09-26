#!/usr/bin/env python3
"""
Create a bounded, validated LRS2 analytical snapshot.

Infrastructure only:
- does not modify LRS2 methodology or research state
- does not run checkpoint analysis
- does not transfer data between hosts
- does not modify source CSVs

A snapshot becomes visible at its final path only after both source files
have been copied, parsed, hashed, and described by a manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OBI = (
    REPO_ROOT
    / "L3_RESEARCH_ENGINES"
    / "market_microstructure"
    / "data"
    / "obi_log.csv"
)

DEFAULT_NEAR = (
    REPO_ROOT
    / "L3_RESEARCH_ENGINES"
    / "market_microstructure"
    / "data"
    / "near_book_depth_log.csv"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_csv(path: Path) -> dict[str, int]:
    frame = pd.read_csv(path)
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
    }


def provenance_path(path: Path) -> str:
    """Use repo-relative provenance when possible, otherwise absolute."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def source_boundary(path: Path) -> dict[str, int | str]:
    stat = path.stat()

    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        end = handle.tell()

        if end == 0:
            last_row = ""
        else:
            read_size = min(end, 64 * 1024)
            handle.seek(end - read_size)
            tail = handle.read(read_size)

            lines = tail.splitlines()
            last_row = lines[-1].decode("utf-8") if lines else ""

    return {
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "last_row": last_row,
    }


def copy_stable_source(source: Path, destination: Path) -> dict:
    before = source_boundary(source)

    with source.open("rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())

    after = source_boundary(source)

    if before != after:
        raise RuntimeError(
            f"Source changed during snapshot copy; refusing publication: {source}"
        )

    destination_size = destination.stat().st_size
    if destination_size != before["size_bytes"]:
        raise RuntimeError(
            f"Snapshot size mismatch for {source}: "
            f"source={before['size_bytes']} destination={destination_size}"
        )

    return {
        "before_copy": before,
        "after_copy": after,
    }


def write_json_fsync(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def create_snapshot(
    output_root: Path,
    obi_source: Path,
    near_source: Path,
) -> Path:
    for source in (obi_source, near_source):
        if not source.is_file():
            raise RuntimeError(f"Required source missing: {source}")

    output_root.mkdir(parents=True, exist_ok=True)

    snapshot_utc = datetime.now(timezone.utc)
    snapshot_id = snapshot_utc.strftime("%Y%m%dT%H%M%S.%fZ")
    final_dir = output_root / snapshot_id

    if final_dir.exists():
        raise RuntimeError(f"Refusing to overwrite snapshot: {final_dir}")

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{snapshot_id}.tmp-",
            dir=output_root,
        )
    )

    try:
        obi_dest = temp_dir / "obi_log.csv"
        near_dest = temp_dir / "near_book_depth_log.csv"

        obi_boundary = copy_stable_source(obi_source, obi_dest)
        near_boundary = copy_stable_source(near_source, near_dest)

        obi_validation = validate_csv(obi_dest)
        near_validation = validate_csv(near_dest)

        obi_hash = sha256_file(obi_dest)
        near_hash = sha256_file(near_dest)

        manifest = {
            "schema_version": 1,
            "purpose": "LRS2 bounded analytical snapshot",
            "research_checkpoint": False,
            "cp15": False,
            "source_host": socket.gethostname(),
            "source_commit": git_head(REPO_ROOT),
            "snapshot_utc": snapshot_utc.isoformat(),
            "sources": {
                "obi": provenance_path(obi_source),
                "near_book_depth": provenance_path(near_source),
            },
            "files": {
                "obi_log.csv": {
                    "sha256": obi_hash,
                    **obi_validation,
                    "source_boundary": obi_boundary,
                },
                "near_book_depth_log.csv": {
                    "sha256": near_hash,
                    **near_validation,
                    "source_boundary": near_boundary,
                },
            },
        }

        write_json_fsync(temp_dir / "MANIFEST.json", manifest)

        # Re-verify bytes after all snapshot artifacts have been produced.
        if sha256_file(obi_dest) != obi_hash:
            raise RuntimeError("OBI snapshot changed during validation")
        if sha256_file(near_dest) != near_hash:
            raise RuntimeError("Near-book snapshot changed during validation")

        # Same-filesystem rename: incomplete snapshots never appear at
        # their final immutable path.
        os.rename(temp_dir, final_dir)

        print(f"SNAPSHOT_READY={final_dir}")
        print(f"OBI_ROWS={obi_validation['rows']}")
        print(f"NEAR_ROWS={near_validation['rows']}")
        print(f"OBI_SHA256={obi_hash}")
        print(f"NEAR_SHA256={near_hash}")
        print("RESEARCH_CHECKPOINT=NO")
        print("CP15=NO")

        return final_dir

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a bounded LRS2 analytical snapshot."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory under which the immutable snapshot directory is created.",
    )
    parser.add_argument("--obi-source", type=Path, default=DEFAULT_OBI)
    parser.add_argument("--near-source", type=Path, default=DEFAULT_NEAR)
    args = parser.parse_args()

    try:
        create_snapshot(
            output_root=args.output_root.resolve(),
            obi_source=args.obi_source.resolve(),
            near_source=args.near_source.resolve(),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
