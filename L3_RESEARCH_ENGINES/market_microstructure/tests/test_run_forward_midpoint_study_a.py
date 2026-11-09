import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_a import (
    StudyAError,
)
from L3_RESEARCH_ENGINES.market_microstructure.analysis import (
    run_forward_midpoint_study_a as runner,
)


def _write_csv(path: Path, rows: list[dict]) -> tuple[int, int, str]:
    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return len(frame), len(frame.columns), digest


def _synthetic_snapshot(tmp_path: Path) -> Path:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    obi_rows = [
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "publication_id": "p1",
            "slug": "a",
            "question": "A?",
            "midpoint": 0.40,
            "micro_price": 0.40,
            "obi": 0.10,
            "v_bid": 10,
            "v_ask": 9,
            "bid_count": 2,
            "ask_count": 2,
            "status": "ok",
        }
    ]
    near_rows = [
        {
            "timestamp": "2026-01-01T00:00:30Z",
            "publication_id": "p1",
            "slug": "a",
            "question": "A?",
            "midpoint": 0.40,
            "total_obi": 0.10,
            "near_obi": 0.20,
            "n_levels": 5,
            "v_bid_top_n": 10,
            "v_ask_top_n": 8,
            "bid_count": 2,
            "ask_count": 2,
            "status": "ok",
        }
    ]

    obi_count = _write_csv(snapshot / "obi_log.csv", obi_rows)
    near_count = _write_csv(snapshot / "near_book_depth_log.csv", near_rows)

    manifest = {
        "schema_version": runner.EXPECTED_SCHEMA_VERSION,
        "purpose": runner.EXPECTED_PURPOSE,
        "research_checkpoint": runner.EXPECTED_RESEARCH_CHECKPOINT,
        "snapshot_utc": runner.EXPECTED_SNAPSHOT_UTC,
        "source_commit": runner.EXPECTED_SOURCE_COMMIT,
        "source_host": runner.EXPECTED_SOURCE_HOST,
        "files": {
            "obi_log.csv": {
                "rows": obi_count[0],
                "columns": obi_count[1],
                "sha256": obi_count[2],
            },
            "near_book_depth_log.csv": {
                "rows": near_count[0],
                "columns": near_count[1],
                "sha256": near_count[2],
            },
        },
    }

    (snapshot / "MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    return snapshot


def _patch_expected_identity(monkeypatch, snapshot: Path) -> None:
    manifest_path = snapshot / "MANIFEST.json"
    monkeypatch.setattr(
        runner,
        "EXPECTED_MANIFEST_SHA256",
        hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        runner,
        "EXPECTED_FILES",
        {
            name: {
                "rows": metadata["rows"],
                "columns": metadata["columns"],
                "sha256": metadata["sha256"],
            }
            for name, metadata in manifest["files"].items()
        },
    )


def test_exact_cp17_constants_are_frozen():
    assert runner.EXPECTED_MANIFEST_SHA256 == (
        "7e45e2a844dae6cabacb86a2e52177a911c6090904879ecb2aecd8d4f76a0fb9"
    )
    assert runner.EXPECTED_SCHEMA_VERSION == 1
    assert runner.EXPECTED_PURPOSE == "LRS2 bounded analytical snapshot"
    assert runner.EXPECTED_RESEARCH_CHECKPOINT is False
    assert runner.EXPECTED_SNAPSHOT_UTC == "2026-10-07T00:20:08.645365+00:00"
    assert runner.EXPECTED_SOURCE_COMMIT == (
        "f691225fa7fc7aada1a1f9bc41d03fd2e1a06582"
    )
    assert runner.EXPECTED_SOURCE_HOST == "liquid-pi"
    assert runner.EXPECTED_FILES == {
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


def test_verified_loader_accepts_matching_synthetic_contract(
    tmp_path,
    monkeypatch,
):
    snapshot = _synthetic_snapshot(tmp_path)
    _patch_expected_identity(monkeypatch, snapshot)

    obi, near = runner.load_verified_cp17_frames(snapshot)

    assert len(obi) == 1
    assert len(near) == 1
    assert obi.iloc[0]["status"] == "ok"
    assert near.iloc[0]["status"] == "ok"


def test_manifest_hash_mismatch_fails_before_csv_load(tmp_path, monkeypatch):
    snapshot = _synthetic_snapshot(tmp_path)

    called = False

    def forbidden_read_csv(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("CSV must not load after manifest mismatch")

    monkeypatch.setattr(pd, "read_csv", forbidden_read_csv)

    with pytest.raises(StudyAError, match="MANIFEST.json sha256"):
        runner.load_verified_cp17_frames(snapshot)

    assert called is False


def test_source_hash_mismatch_fails_closed(tmp_path, monkeypatch):
    snapshot = _synthetic_snapshot(tmp_path)
    _patch_expected_identity(monkeypatch, snapshot)

    with (snapshot / "obi_log.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(StudyAError, match="obi_log.csv actual sha256"):
        runner.load_verified_cp17_frames(snapshot)


def test_manifest_identity_mismatch_fails_closed(tmp_path, monkeypatch):
    snapshot = _synthetic_snapshot(tmp_path)

    manifest_path = snapshot / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_host"] = "wrong-host"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )

    _patch_expected_identity(monkeypatch, snapshot)
    monkeypatch.setattr(runner, "EXPECTED_SOURCE_HOST", "liquid-pi")

    with pytest.raises(StudyAError, match="source_host"):
        runner.load_verified_cp17_frames(snapshot)


def test_row_count_mismatch_fails_after_verified_file_load(
    tmp_path,
    monkeypatch,
):
    snapshot = _synthetic_snapshot(tmp_path)
    _patch_expected_identity(monkeypatch, snapshot)

    expected = dict(runner.EXPECTED_FILES)
    expected["obi_log.csv"] = dict(expected["obi_log.csv"])
    expected["obi_log.csv"]["rows"] = 2
    monkeypatch.setattr(runner, "EXPECTED_FILES", expected)

    manifest_path = snapshot / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["obi_log.csv"]["rows"] = 2
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner,
        "EXPECTED_MANIFEST_SHA256",
        hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )

    with pytest.raises(StudyAError, match="obi_log.csv actual rows"):
        runner.load_verified_cp17_frames(snapshot)
