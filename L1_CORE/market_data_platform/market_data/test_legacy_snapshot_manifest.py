"""Synthetic security tests for Candidate C destination manifest."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import legacy_snapshot_export as exporter
import legacy_snapshot_manifest as manifest
import legacy_snapshot_authorization as authorization
import legacy_snapshot_scope as scope


def sha256(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def destination(tmp_path):
    root = tmp_path / "destination"
    root.mkdir()

    relative = (
        "trades/date=2026-08-21/"
        f"{uuid.UUID(int=1)}.parquet"
    )
    payload = root / relative
    payload.parent.mkdir(parents=True)
    timestamp = int(
        datetime(
            2026, 8, 21, 12, 0, tzinfo=timezone.utc
        ).timestamp() * 1000
    )

    rows = [
        {
            "timestamp_received": timestamp,
            "event_time": timestamp,
            "trade_time": timestamp,
            "trade_id": 1,
            "price": Decimal("50000.00000000"),
            "quantity": Decimal("0.10000000"),
            "is_buyer_maker": True,
            "instrument_id": "BTC-USD",
        },
        {
            "timestamp_received": timestamp + 1000,
            "event_time": timestamp + 1000,
            "trade_time": timestamp + 1000,
            "trade_id": 2,
            "price": Decimal("3000.00000000"),
            "quantity": Decimal("0.20000000"),
            "is_buyer_maker": False,
            "instrument_id": "ETH-USD",
        },
    ]

    table = pa.Table.from_pylist(
        rows,
        schema=exporter.DATASETS["trades"],
    )
    pq.write_table(table, payload)

    measured = exporter._validate_source_file_core(
        root, relative
    )

    request_id = "SYNTHETIC-REQUEST-001"

    source_root = tmp_path / "synthetic-source"
    source_root.mkdir()

    authorization_dir = root / "authorization"
    authorization_dir.mkdir()

    def identity(segment, identifier):
        record = {
            "authorization_schema_version": authorization.AUTH_VERSION,
            "authorization_id": identifier,
            "snapshot_request_id": request_id,
            "segment": segment,
            "purpose": authorization.PURPOSE,
            "permitted_operations": list(authorization.OPERATIONS),
            "source_root": str(source_root.resolve()),
            "destination_root": str(root.resolve()),
            "datasets": sorted(scope.DATASETS),
            "instruments": sorted(scope.INSTRUMENTS),
            "date_windows": authorization.WINDOWS[segment],
            "valid_from_utc": "2026-10-01T00:00:00+00:00",
            "valid_until_utc": "2026-10-05T00:00:00+00:00",
            "resource_budget_references": {
                "policy": "synthetic-development-only"
            },
        }

        name = (
            "non_h2.json" if segment == "NON_H2" else "h2.json"
        )

        raw = json.dumps(
            record, sort_keys=True, separators=(",", ":")
        ).encode()

        (authorization_dir / name).write_bytes(raw)

        return {
            "authorization_id": identifier,
            "snapshot_request_id": request_id,
            "segment": segment,
            "authorization_sha256": sha256(raw),
            "classification": "SEALED / TRANSPORT ONLY",
        }

    document = {
        "manifest_schema_version": 1,
        "snapshot_request_id": request_id,
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
        "production_transfer_authorized": False,
        "predictive_analysis_authorized": False,
        "scientific_readiness": "PENDING",
        "scope_accounting": scope.build_scope_accounting(
            observed_coverage={
                "trades/date=2026-08-21": measured["instruments"],
            },
            sanctioned_exclusions=[],
            trusted_evidence_digests={},
        ),
        "authorizations": {
            "authorization_schema_version": 1,
            "snapshot_request_id": request_id,
            "non_h2": identity("NON_H2", "SYNTHETIC-NON-H2"),
            "h2": identity("H2", "SYNTHETIC-H2"),
            "production_transfer_authorized": False,
            "predictive_analysis_authorized": False,
        },
        "files": [measured],
        "component_evidence": [],
        "inventory_started_utc": "2026-10-10T00:00:00+00:00",
        "inventory_ended_utc": "2026-10-10T00:01:00+00:00",
        "exceptions": [],
    }

    def seal():
        data = json.dumps(
            document, sort_keys=True, separators=(",", ":")
        ).encode()
        (root / "manifest.json").write_bytes(data)
        return sha256(data)

    return root, payload, document, seal


def test_external_digest_required(destination):
    root, _, _, seal = destination
    seal()
    with pytest.raises(ValueError, match="SHA-256"):
        manifest.verify_full_range_destination(root, None, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_valid_synthetic_parquet_integrity(destination):
    root, _, _, seal = destination
    result = manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))
    assert result["integrity_verified"] is True
    assert result["historical_timing_attestation"] == "UNATTESTED"
    assert result["classification"] == "INTEGRITY_ONLY_NOT_READY"
    assert result["verified_payload_files"] == 1


def test_manifest_tampering_rejected(destination):
    root, _, document, seal = destination
    trusted = seal()
    document["snapshot_request_id"] = "ALTERED"
    seal()
    with pytest.raises(ValueError, match="External manifest"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_payload_tampering_rejected(destination):
    root, payload, _, seal = destination
    trusted = seal()
    payload.write_bytes(b"TAMPERED")
    with pytest.raises(ValueError, match="size mismatch|SHA-256 mismatch"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_missing_payload_rejected(destination):
    root, payload, _, seal = destination
    trusted = seal()
    payload.unlink()
    with pytest.raises(ValueError, match="Missing destination"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_symlinked_payload_rejected(destination, tmp_path):
    root, payload, _, seal = destination
    trusted = seal()
    replacement = tmp_path / "outside.parquet"
    replacement.write_bytes(payload.read_bytes())
    payload.unlink()
    payload.symlink_to(replacement)
    with pytest.raises(ValueError, match="Symlinked"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_extra_manifest_field_rejected(destination):
    root, _, document, seal = destination
    document["unexpected"] = True
    with pytest.raises(ValueError, match="schema"):
        manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_production_authorization_flag_rejected(destination):
    root, _, document, seal = destination
    document["production_transfer_authorized"] = True
    with pytest.raises(ValueError, match="production_transfer_authorized"):
        manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_duplicate_payload_record_rejected(destination):
    root, _, document, seal = destination
    document["files"].append(dict(document["files"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_unexpected_file_must_be_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()
    (root / "unexpected.bin").write_bytes(b"UNLISTED")
    with pytest.raises(ValueError, match="Unexpected"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_unexpected_empty_directory_must_be_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()
    (root / "unlisted-directory").mkdir()
    with pytest.raises(ValueError, match="Unexpected"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_fake_parquet_must_be_rejected(destination):
    root, payload, document, seal = destination

    # Deliberately invalid Parquet with internally consistent manifest
    # size and SHA-256. Structural validation must independently reject it.
    invalid_bytes = b"SYNTHETIC-INVALID-PARQUET"
    payload.write_bytes(invalid_bytes)

    record = document["files"][0]
    record["size_bytes"] = len(invalid_bytes)
    record["sha256"] = sha256(invalid_bytes)

    trusted = seal()

    with pytest.raises(
        (ValueError, OSError, RuntimeError),
        match="Parquet|parquet|schema|content|magic bytes",
    ):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_fabricated_coverage_must_be_rejected(destination):
    root, _, document, seal = destination
    document["scope_accounting"]["classification"] = (
        "FULL_SCOPE_VERIFIED"
    )
    document["scope_accounting"]["observed_coverage"] = {
        partition: sorted(scope.INSTRUMENTS)
        for partition in scope.expected_partitions()
    }
    trusted = seal()
    with pytest.raises(ValueError, match="coverage|accounting|scope"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))



def test_missing_non_h2_authorization_evidence_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()
    (root / "authorization" / "non_h2.json").unlink()

    with pytest.raises(ValueError, match="Missing authorization"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_missing_h2_authorization_evidence_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()
    (root / "authorization" / "h2.json").unlink()

    with pytest.raises(ValueError, match="Missing authorization"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_modified_authorization_evidence_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()

    path = root / "authorization" / "non_h2.json"
    record = json.loads(path.read_text())
    record["authorization_id"] = "SUBSTITUTED"
    path.write_text(json.dumps(record, sort_keys=True))

    with pytest.raises(ValueError, match="Authorization evidence"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_duplicate_authorization_identity_rejected(destination):
    root, _, document, seal = destination

    document["authorizations"]["h2"]["authorization_id"] = (
        document["authorizations"]["non_h2"]["authorization_id"]
    )

    with pytest.raises(ValueError, match="Duplicate authorization"):
        manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_attested_manifest_injection_rejected(destination):
    root, _, document, seal = destination
    document["historical_timing_attestation"] = "ATTESTED"

    with pytest.raises(ValueError, match="Manifest schema"):
        manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_authorization_scope_substitution_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()

    path = root / "authorization" / "h2.json"
    record = json.loads(path.read_text())
    record["date_windows"] = authorization.WINDOWS["NON_H2"]
    path.write_text(json.dumps(record, sort_keys=True))

    with pytest.raises(PermissionError, match="Date-window scope"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_substituted_valid_authorization_rejected(destination):
    root, _, _, seal = destination
    trusted = seal()

    path = root / "authorization" / "non_h2.json"
    record = json.loads(path.read_text())

    # Preserve valid schema and scope while changing record identity.
    record["authorization_id"] = "VALID-BUT-SUBSTITUTED"

    path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":"))
    )

    with pytest.raises(ValueError, match="Authorization evidence"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_same_authorization_file_cannot_satisfy_both_roles(destination):
    root, _, _, seal = destination
    trusted = seal()

    non_h2 = root / "authorization" / "non_h2.json"
    h2 = root / "authorization" / "h2.json"

    h2.unlink()
    h2.symlink_to(non_h2)

    with pytest.raises(ValueError, match="Symlinked authorization"):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()))


def test_historical_verifier_rejects_timing_override(destination):
    root, _, _, seal = destination
    trusted = seal()

    with pytest.raises(TypeError):
        manifest.verify_full_range_destination(root, trusted, expected_source_root=str((root.parent / "synthetic-source").resolve()), historical_timing_attestation="ATTESTED")


def test_expired_authorizations_remain_integrity_verifiable(destination):
    root, _, _, seal = destination

    # Both fixture authorizations expired on October 5, 2026.
    # Historical integrity verification must not require renewal.
    result = manifest.verify_full_range_destination(root, seal(), expected_source_root=str((root.parent / "synthetic-source").resolve()))

    assert result["integrity_verified"] is True
    assert result["historical_timing_attestation"] == "UNATTESTED"
    assert result["classification"] == "INTEGRITY_ONLY_NOT_READY"



def test_missing_external_source_root_rejected(destination):
    root, _, _, seal = destination

    with pytest.raises(TypeError, match="expected_source_root"):
        manifest.verify_full_range_destination(root, seal())


def test_mutually_consistent_forged_source_roots_rejected(destination):
    root, _, document, seal = destination

    forged_source = str((root.parent / "forged-source").resolve())

    for filename, key in (
        ("non_h2.json", "non_h2"),
        ("h2.json", "h2"),
    ):
        path = root / "authorization" / filename
        record = json.loads(path.read_text(encoding="utf-8"))
        record["source_root"] = forged_source

        raw = json.dumps(
            record, sort_keys=True, separators=(",", ":")
        ).encode()

        path.write_bytes(raw)
        document["authorizations"][key]["authorization_sha256"] = sha256(raw)

    trusted = seal()
    actual_source = str((root.parent / "synthetic-source").resolve())

    with pytest.raises(PermissionError, match="Source root mismatch"):
        manifest.verify_full_range_destination(
            root,
            trusted,
            expected_source_root=actual_source,
        )


def _synthetic_sanctioned_exclusion_fixture(destination):
    """Add one manifest-bound synthetic exclusion without touching production."""
    root, _, document, seal = destination
    relative = "adjudications/synthetic-exclusion.txt"
    artifact = root / relative
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"Synthetic exclusion adjudication evidence")
    digest = sha256(artifact.read_bytes())

    document["component_evidence"].append({
        "relative_path": relative,
        "size_bytes": artifact.stat().st_size,
        "sha256": digest,
    })

    partition = "depth_levels/date=2026-08-21"
    claimed = {
        "partition": partition,
        "adjudication_id": "SYNTHETIC-ADJ-001",
        "reason": "Synthetic fixture exclusion",
        "evidence_path": str(artifact.absolute()),
    }

    accounting = scope.build_scope_accounting(
        observed_coverage={
            "trades/date=2026-08-21": sorted(scope.INSTRUMENTS),
        },
        sanctioned_exclusions=[claimed],
        trusted_evidence_digests={str(artifact.absolute()): digest},
    )

    accounting["sanctioned_exclusions"][0]["evidence_path"] = relative
    document["scope_accounting"] = accounting
    return root, document, seal, artifact, relative, partition


def _verify_synthetic_destination(root, seal):
    return manifest.verify_full_range_destination(
        root,
        seal(),
        expected_source_root=str(
            (root.parent / "synthetic-source").resolve()
        ),
    )


def test_sanctioned_exclusion_integrity_and_classification(destination):
    root, document, seal, _, relative, partition = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    result = _verify_synthetic_destination(root, seal)

    assert result["integrity_verified"] is True
    assert result["classification"] == "INTEGRITY_ONLY_NOT_READY"
    assert result["scientific_readiness"] == "PENDING"
    assert result["historical_timing_attestation"] == "UNATTESTED"
    # Only two of 94 partitions are accounted for in this fixture.
    # Unexplained gaps correctly keep scope classification INCOMPLETE.
    assert document["scope_accounting"]["classification"] == "INCOMPLETE"
    assert len(document["scope_accounting"]["unexplained_gaps"]) == 92
    assert len(document["scope_accounting"]["sanctioned_exclusions"]) == 1
    assert document["scope_accounting"]["sanctioned_exclusions"][0][
        "evidence_path"
    ] == relative
    assert document["scope_accounting"]["sanctioned_exclusions"][0][
        "partition"
    ] == partition


def test_sanctioned_exclusion_reconstructed_path_is_portable(
    destination, monkeypatch
):
    root, document, seal, _, relative, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    original_builder = scope.build_scope_accounting
    reconstructed = []

    def capture_accounting(*args, **kwargs):
        result = original_builder(*args, **kwargs)
        reconstructed.append(result)
        return result

    monkeypatch.setattr(scope, "build_scope_accounting", capture_accounting)
    _verify_synthetic_destination(root, seal)

    assert len(reconstructed) == 1
    actual = reconstructed[0]["sanctioned_exclusions"][0]["evidence_path"]
    expected = document["scope_accounting"]["sanctioned_exclusions"][0][
        "evidence_path"
    ]
    assert actual == expected == relative
    assert not Path(actual).is_absolute()


def test_forged_claimed_exclusion_digest_rejected_at_final_comparison(
    destination,
):
    root, document, seal, _, _, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    document["scope_accounting"]["sanctioned_exclusions"][0][
        "evidence_sha256"
    ] = "0" * 64

    with pytest.raises(
        ValueError,
        match="^Manifest scope accounting differs from validated Parquet coverage$",
    ):
        _verify_synthetic_destination(root, seal)


def test_tampered_sanctioned_exclusion_artifact_rejected(destination):
    root, _, seal, artifact, _, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    original = artifact.read_bytes()
    artifact.write_bytes(b"X" + original[1:])

    with pytest.raises(
        ValueError, match="^Destination file SHA-256 mismatch$"
    ):
        _verify_synthetic_destination(root, seal)


def test_exclusion_cannot_reference_authorization_evidence(
    destination,
):
    root, document, seal, _, _, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    # This file exists and is included in destination inventory, but it
    # was never declared or verified as component_evidence.
    document["scope_accounting"]["sanctioned_exclusions"][0][
        "evidence_path"
    ] = "authorization/non_h2.json"

    with pytest.raises(
        ValueError,
        match="^Exclusion evidence absent from verified component evidence$",
    ):
        _verify_synthetic_destination(root, seal)


@pytest.mark.parametrize(
    "injected_path",
    [
        "../outside-evidence.txt",
        "/tmp/outside-evidence.txt",
    ],
)
def test_exclusion_unsafe_path_rejected(destination, injected_path):
    root, document, seal, _, _, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    document["scope_accounting"]["sanctioned_exclusions"][0][
        "evidence_path"
    ] = injected_path

    with pytest.raises(ValueError, match="Unsafe relative path"):
        _verify_synthetic_destination(root, seal)


def test_symlinked_sanctioned_exclusion_artifact_rejected(destination):
    root, document, seal, artifact, relative, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    target = root.parent / "synthetic-evidence-target.txt"
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    artifact.symlink_to(target)

    assert document["component_evidence"][0]["relative_path"] == relative

    with pytest.raises(
        ValueError, match="^Symlinked destination component$"
    ):
        _verify_synthetic_destination(root, seal)


def test_exclusion_overlapping_observed_partition_rejected(destination):
    root, document, seal, _, _, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    document["scope_accounting"]["sanctioned_exclusions"][0][
        "partition"
    ] = "trades/date=2026-08-21"

    with pytest.raises(ValueError, match="contradicts validated coverage"):
        _verify_synthetic_destination(root, seal)


def test_complete_94_partition_sanctioned_scope(destination):
    """Full synthetic accounting never promotes scientific readiness."""
    from datetime import timedelta

    root, document, seal, artifact, relative, _ = (
        _synthetic_sanctioned_exclusion_fixture(destination)
    )

    observed_partition = "trades/date=2026-08-21"
    start = datetime(2026, 8, 21)
    end = datetime(2026, 10, 6)

    expected = {
        f"{dataset}/date={(start + timedelta(days=offset)).date()}"
        for dataset in scope.DATASETS
        for offset in range((end - start).days + 1)
    }

    assert len(expected) == 94
    assert observed_partition in expected

    digest = sha256(artifact.read_bytes())
    absolute = str(artifact.absolute())

    exclusions = [
        {
            "partition": partition,
            "adjudication_id": f"SYNTHETIC-ADJ-{index:03d}",
            "reason": "Synthetic full-scope exclusion",
            "evidence_path": absolute,
        }
        for index, partition in enumerate(
            sorted(expected - {observed_partition}), start=1
        )
    ]

    assert len(exclusions) == 93

    accounting = scope.build_scope_accounting(
        observed_coverage={
            observed_partition: sorted(scope.INSTRUMENTS),
        },
        sanctioned_exclusions=exclusions,
        trusted_evidence_digests={absolute: digest},
    )

    assert accounting["expected_partitions"] == sorted(expected)
    assert accounting["unexplained_gaps"] == []
    assert accounting["classification"] == (
        "VERIFIED_WITH_SANCTIONED_EXCLUSIONS"
    )
    assert len(accounting["sanctioned_exclusions"]) == 93

    for exclusion in accounting["sanctioned_exclusions"]:
        exclusion["evidence_path"] = relative

    document["scope_accounting"] = accounting

    result = _verify_synthetic_destination(root, seal)

    assert result["integrity_verified"] is True
    assert result["verified_payload_files"] == 1
    assert result["verified_component_evidence_files"] == 1
    assert result["classification"] == "INTEGRITY_ONLY_NOT_READY"
    assert result["scientific_readiness"] == "PENDING"
    assert result["historical_timing_attestation"] == "UNATTESTED"

    assert document["scope_accounting"]["unexplained_gaps"] == []
    assert len(document["scope_accounting"]["sanctioned_exclusions"]) == 93
    assert all(
        item["evidence_path"] == relative
        for item in document["scope_accounting"]["sanctioned_exclusions"]
    )
