"""
LRS-2 — Market Microstructure Research
Forward Midpoint Study A canonical snapshot runner.

This module is a fail-closed provenance wrapper around the frozen Study-A
implementation. It does not define or modify Study-A scientific methodology.

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
    run_study_a_from_frames,
)


EXPECTED_MANIFEST_SHA256 = (
    "7e45e2a844dae6cabacb86a2e52177a911c6090904879ecb2aecd8d4f76a0fb9"
)
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_PURPOSE = "LRS2 bounded analytical snapshot"
EXPECTED_RESEARCH_CHECKPOINT = False
EXPECTED_SNAPSHOT_UTC = "2026-10-07T00:20:08.645365+00:00"
EXPECTED_SOURCE_COMMIT = "f691225fa7fc7aada1a1f9bc41d03fd2e1a06582"
EXPECTED_SOURCE_HOST = "liquid-pi"

EXPECTED_FILES = {
    "obi_log.csv": {
        "rows": 2595,
        "columns": 12,
        "sha256": (
            "d30ee244a59ddf86ad74184030414436118bb986345a11e98aaba24e6a78c4e8"
        ),
    },
    "near_book_depth_log.csv": {
        "rows": 2585,
        "columns": 13,
        "sha256": (
            "ecfaa0dfb6d2bddbf8e9cf7f757b72c37f0ceda57c986bf017844179b1404af0"
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
            f"CP17 provenance mismatch for {label}: "
            f"expected {expected!r}, got {actual!r}"
        )


def validate_cp17_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    """
    Validate the exact frozen CP17 analytical snapshot before outcome execution.

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
        raise StudyAError(f"missing CP17 manifest: {manifest_path}")

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
        raise StudyAError("unable to parse CP17 MANIFEST.json") from exc

    if not isinstance(manifest, dict):
        raise StudyAError("CP17 MANIFEST.json must contain a JSON object")

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
        raise StudyAError("CP17 manifest files field must be an object")

    for filename, expected in EXPECTED_FILES.items():
        metadata = manifest_files.get(filename)
        if not isinstance(metadata, dict):
            raise StudyAError(
                f"CP17 manifest is missing file metadata for {filename}"
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
            raise StudyAError(f"missing CP17 source file: {source_path}")

        _require_equal(
            f"{filename} actual sha256",
            _sha256(source_path),
            expected["sha256"],
        )

    return manifest


def load_verified_cp17_frames(
    snapshot_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validate provenance, then load and structurally verify the two CP17 frames.
    """
    snapshot_dir = Path(snapshot_dir)
    validate_cp17_snapshot(snapshot_dir)

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


def run_verified_cp17_study_a(
    snapshot_dir: Path,
) -> tuple[pd.DataFrame, ClusteredOLSResult]:
    """
    Execute frozen Study A only after exact CP17 provenance validation succeeds.
    """
    obi, near = load_verified_cp17_frames(snapshot_dir)
    return run_study_a_from_frames(obi, near)


def _print_result(
    eligible: pd.DataFrame,
    result: ClusteredOLSResult,
) -> None:
    same_direction_n = int(eligible["secondary_same_direction"].sum())
    secondary_rate = same_direction_n / len(eligible)

    print("STUDY_A_CP17_RESULT")
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
            "Run frozen LRS2 Forward Midpoint Study A against the exact "
            "verified CP17 analytical snapshot."
        )
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        required=True,
        help="Explicit directory containing MANIFEST.json and CP17 source CSVs.",
    )
    args = parser.parse_args()

    try:
        eligible, result = run_verified_cp17_study_a(args.snapshot_dir)
    except (StudyAError, OSError, ValueError) as exc:
        parser.exit(2, f"Study-A execution failed: {exc}\n")

    _print_result(eligible, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
