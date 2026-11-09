"""
LRS-2 — Market Microstructure Research
Forward Midpoint Study B canonical snapshot runner.

This module is a fail-closed provenance wrapper around the frozen Study-B
implementation. It does not define or modify Study-B scientific methodology.

The caller must explicitly supply the immutable snapshot directory. No live-data
discovery or fallback source path is permitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_a import (
    ClusteredOLSResult,
    StudyAError,
)
from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_b import (
    run_study_b_from_frames,
)


EXPECTED_MANIFEST_SHA256 = (
    "b2a80ba423448401ee8435f6d9c67c0485af537c9b456a03289eb103b79ba5f7"
)
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_PURPOSE = "LRS2 bounded analytical snapshot"
EXPECTED_RESEARCH_CHECKPOINT = False
EXPECTED_SNAPSHOT_UTC = "2026-11-07T13:03:39.259331+00:00"
EXPECTED_SOURCE_COMMIT = "f691225fa7fc7aada1a1f9bc41d03fd2e1a06582"
EXPECTED_SOURCE_HOST = "liquid-pi"

EXPECTED_FILES = {
    "obi_log.csv": {
        "rows": 3655,
        "columns": 12,
        "sha256": (
            "74063d05e85ea3a26e07815020928ca301e592e10c120edbc0271852721d8001"
        ),
    },
    "near_book_depth_log.csv": {
        "rows": 3646,
        "columns": 13,
        "sha256": (
            "c0454875be0ce76ec55eaffa9c2286e3c0d9de2b564b4d042bba4b8d40da9f04"
        ),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise StudyAError(
            f"Study-B provenance mismatch for {label}: "
            f"expected {expected!r}, got {actual!r}"
        )


def validate_study_b_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    """
    Validate the exact frozen Study-B analytical snapshot before execution.

    Validation is fail-closed. No alternate snapshot identity, source file,
    manifest, or scientific parameter is accepted.
    """
    snapshot_dir = Path(snapshot_dir)

    if not snapshot_dir.is_dir():
        raise StudyAError(
            f"explicit snapshot directory does not exist: {snapshot_dir}"
        )

    manifest_path = snapshot_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        raise StudyAError(f"missing Study-B manifest: {manifest_path}")

    manifest_sha = _sha256(manifest_path)
    _require_equal(
        "MANIFEST.json sha256",
        manifest_sha,
        EXPECTED_MANIFEST_SHA256,
    )

    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise StudyAError("unable to parse Study-B MANIFEST.json") from exc

    if not isinstance(manifest, dict):
        raise StudyAError("Study-B MANIFEST.json must contain a JSON object")

    _require_equal(
        "schema_version",
        manifest.get("schema_version"),
        EXPECTED_SCHEMA_VERSION,
    )
    _require_equal("purpose", manifest.get("purpose"), EXPECTED_PURPOSE)
    _require_equal(
        "research_checkpoint",
        manifest.get("research_checkpoint"),
        EXPECTED_RESEARCH_CHECKPOINT,
    )
    _require_equal(
        "snapshot_utc",
        manifest.get("snapshot_utc"),
        EXPECTED_SNAPSHOT_UTC,
    )
    _require_equal(
        "source_commit",
        manifest.get("source_commit"),
        EXPECTED_SOURCE_COMMIT,
    )
    _require_equal(
        "source_host",
        manifest.get("source_host"),
        EXPECTED_SOURCE_HOST,
    )

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, dict):
        raise StudyAError("Study-B manifest files field must be an object")

    for filename, expected in EXPECTED_FILES.items():
        metadata = manifest_files.get(filename)
        if not isinstance(metadata, dict):
            raise StudyAError(
                f"Study-B manifest is missing file metadata for {filename}"
            )

        _require_equal(
            f"{filename} manifest rows",
            metadata.get("rows"),
            expected["rows"],
        )
        _require_equal(
            f"{filename} manifest columns",
            metadata.get("columns"),
            expected["columns"],
        )
        _require_equal(
            f"{filename} manifest sha256",
            metadata.get("sha256"),
            expected["sha256"],
        )

        source_path = snapshot_dir / filename
        if not source_path.is_file():
            raise StudyAError(f"missing Study-B source file: {source_path}")

        _require_equal(
            f"{filename} actual sha256",
            _sha256(source_path),
            expected["sha256"],
        )

    return manifest


def load_verified_study_b_frames(
    snapshot_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validate provenance, then load and structurally verify Study-B frames.
    """
    snapshot_dir = Path(snapshot_dir)
    validate_study_b_snapshot(snapshot_dir)

    obi = pd.read_csv(snapshot_dir / "obi_log.csv")
    near = pd.read_csv(snapshot_dir / "near_book_depth_log.csv")

    _require_equal(
        "obi_log.csv actual rows",
        len(obi),
        EXPECTED_FILES["obi_log.csv"]["rows"],
    )
    _require_equal(
        "obi_log.csv actual columns",
        len(obi.columns),
        EXPECTED_FILES["obi_log.csv"]["columns"],
    )
    _require_equal(
        "near_book_depth_log.csv actual rows",
        len(near),
        EXPECTED_FILES["near_book_depth_log.csv"]["rows"],
    )
    _require_equal(
        "near_book_depth_log.csv actual columns",
        len(near.columns),
        EXPECTED_FILES["near_book_depth_log.csv"]["columns"],
    )

    return obi, near


def run_verified_study_b(
    snapshot_dir: Path,
) -> tuple[pd.DataFrame, ClusteredOLSResult]:
    """
    Execute frozen Study B only after exact provenance validation succeeds.
    """
    obi, near = load_verified_study_b_frames(snapshot_dir)
    return run_study_b_from_frames(obi, near)


def _print_result(
    eligible: pd.DataFrame,
    result: ClusteredOLSResult,
) -> None:
    same_direction_n = int(eligible["secondary_same_direction"].sum())
    secondary_rate = same_direction_n / len(eligible)

    print("STUDY_B_RESULT")
    print(f"eligible_n={result.eligible_n}")
    print(f"slug_clusters={result.slug_clusters}")
    print(f"intercept={result.intercept:.17g}")
    print(f"beta={result.beta:.17g}")
    print(f"clustered_se_beta={result.clustered_se_beta:.17g}")
    print(f"beta_ci_95_low={result.beta_ci_95_low:.17g}")
    print(f"beta_ci_95_high={result.beta_ci_95_high:.17g}")
    print(
        "beta_p_value_two_sided="
        f"{result.beta_p_value_two_sided:.17g}"
    )
    print(f"secondary_same_direction_n={same_direction_n}")
    print(f"secondary_same_direction_rate={secondary_rate:.17g}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run frozen LRS2 Forward Midpoint Study B against the exact "
            "verified retained analytical snapshot."
        )
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        required=True,
        help=(
            "Explicit directory containing MANIFEST.json and frozen "
            "Study-B source CSVs."
        ),
    )
    args = parser.parse_args()

    try:
        eligible, result = run_verified_study_b(args.snapshot_dir)
    except (StudyAError, OSError, ValueError) as exc:
        parser.exit(2, f"Study-B execution failed: {exc}\n")

    _print_result(eligible, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
