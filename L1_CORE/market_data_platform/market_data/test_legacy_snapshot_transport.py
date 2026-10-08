"""Synthetic authorization tests for Candidate C H2 transport."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from L1_CORE.market_data_platform.market_data import (
    legacy_snapshot_export as exp,
    legacy_snapshot_transport as transport,
)


@pytest.fixture
def authorization_fixture(tmp_path):
    source = tmp_path / "synthetic_source"
    destination = tmp_path / "synthetic_destination"
    record_path = tmp_path / "synthetic_authorization.json"

    now = datetime.now(timezone.utc)

    record = {
        "authorization_id": "SYNTHETIC-LRS3-H2-001",
        "purpose": "SYNTHETIC_DEVELOPMENT_TRANSPORT_ONLY",
        "permitted_operations": sorted(transport.TRANSPORT_OPERATIONS),
        "source_root": str(source),
        "destination_root": str(destination),
        "datasets": sorted(exp.DATASETS),
        "instruments": sorted(exp.INSTRUMENTS),
        "start_date": exp.H2_START.isoformat(),
        "end_date": exp.H2_END.isoformat(),
        "valid_from_utc": (now - timedelta(hours=1)).isoformat(),
        "valid_until_utc": (now + timedelta(hours=1)).isoformat(),
        "resource_budget_references": {
            "policy": "SYNTHETIC-TEST-BUDGET-ONLY"
        },
    }

    def write_record():
        record_path.write_text(
            json.dumps(record, sort_keys=True),
            encoding="utf-8",
        )
        return record_path

    return source, destination, record, write_record


def test_valid_synthetic_authorization(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    result = transport.validate_transport_authorization(
        write_record(), source, destination
    )

    assert result["authorization_id"] == record["authorization_id"]
    assert len(result["authorization_sha256"]) == 64
    assert result["classification"] == "SEALED / TRANSPORT ONLY"


def test_missing_authorization_rejected(authorization_fixture):
    source, destination, _, write_record = authorization_fixture

    with pytest.raises(ValueError):
        transport.validate_transport_authorization(
            write_record().with_name("missing.json"),
            source,
            destination,
        )


def test_expired_authorization_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["valid_until_utc"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_unapproved_operation_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["permitted_operations"].append("predictive_analysis")

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


@pytest.mark.parametrize("field", ["source_root", "destination_root"])
def test_root_mismatch_rejected(authorization_fixture, field):
    source, destination, record, write_record = authorization_fixture

    record[field] = str(source.parent / "unauthorized")

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_out_of_scope_dates_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["end_date"] = "2026-10-02"

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_unhashable_operation_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["permitted_operations"][0] = {"invalid": "operation"}

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_duplicate_operation_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["permitted_operations"][0] = record["permitted_operations"][1]

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_noncanonical_authorized_root_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["source_root"] = str(source.parent / "alias" / ".." / source.name)

    with pytest.raises(PermissionError):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_reversed_validity_interval_rejected(authorization_fixture):
    source, destination, record, write_record = authorization_fixture

    record["valid_from_utc"] = (
        datetime.now(timezone.utc) + timedelta(hours=2)
    ).isoformat()

    with pytest.raises(ValueError, match="interval ordering"):
        transport.validate_transport_authorization(
            write_record(), source, destination
        )


def test_malformed_authorization_rejected(authorization_fixture):
    source, destination, _, write_record = authorization_fixture

    path = write_record()
    path.write_text("{invalid-json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        transport.validate_transport_authorization(
            path, source, destination
        )


def test_synthetic_h2_transport_end_to_end(authorization_fixture):
    import hashlib
    from pathlib import Path
    from datetime import datetime, timedelta, timezone

    import pyarrow as pa
    import pyarrow.parquet as pq

    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_export as exp,
        legacy_snapshot_transport as transport,
    )

    source, destination, record, write_record = authorization_fixture

    current = exp.H2_START
    while current <= exp.H2_END:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={current.isoformat()}").mkdir(
                parents=True,
                exist_ok=True,
            )
        current += timedelta(days=1)

    timestamp = int(
        datetime(2026, 9, 4, 12, tzinfo=timezone.utc).timestamp() * 1000
    )

    from decimal import Decimal

    row = {
        "timestamp_received": timestamp,
        "event_time": timestamp,
        "trade_time": timestamp,
        "trade_id": 1,
        "price": Decimal("50000.00000000"),
        "quantity": Decimal("0.01000000"),
        "is_buyer_maker": True,
        "instrument_id": "BTC-USD",
    }

    relative = (
        Path("trades")
        / "date=2026-09-04"
        / "00000000-0000-4000-8000-000000000001.parquet"
    )

    source_file = source / relative
    pq.write_table(
        pa.Table.from_pylist([row], schema=exp.DATASETS["trades"]),
        source_file,
    )

    authorization_path = write_record()

    result = transport.run_synthetic_h2_transport(
        authorization_path=authorization_path,
        source_root=source,
        destination_root=destination,
        max_files=5,
        max_source_bytes=1_000_000,
        max_runtime_seconds=30,
    )

    destination_file = destination / relative

    assert destination_file.read_bytes() == source_file.read_bytes()
    assert result["file_count"] == 1
    assert result["source_bytes"] == source_file.stat().st_size
    assert result["classification"] == "SEALED / TRANSPORT ONLY"
    assert result["production_transfer_authorized"] is False
    assert result["predictive_analysis_authorized"] is False
    assert result["authorization_id"] == record["authorization_id"]
    assert result["files"][0]["sha256"] == hashlib.sha256(
        source_file.read_bytes()
    ).hexdigest()

    assert (destination / "transport_evidence.json").is_file()
    assert (destination / "TRANSPORT_COMPLETE").is_file()


def test_synthetic_transport_failure_cases(authorization_fixture):
    from datetime import timedelta
    from pathlib import Path

    import pytest

    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_export as exp,
        legacy_snapshot_transport as transport,
    )

    source, destination, record, write_record = authorization_fixture

    current = exp.H2_START
    while current <= exp.H2_END:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={current.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        current += timedelta(days=1)

    relative = (
        Path("trades")
        / "date=2026-09-04"
        / "00000000-0000-4000-8000-000000000001.parquet"
    )

    (source / relative).write_bytes(b"not a parquet file")
    authorization_path = write_record()

    cases = [
        ("file_budget", {"max_files": 0}, ValueError),
        ("byte_budget", {"max_source_bytes": 1}, RuntimeError),
        ("corrupt_parquet", {}, Exception),
    ]

    for label, overrides, expected_error in cases:
        target = destination.parent / f"destination_{label}"

        updated_record = dict(record)
        updated_record["destination_root"] = str(target)

        record_path = authorization_path.parent / f"auth_{label}.json"
        record_path.write_text(
            __import__("json").dumps(updated_record),
            encoding="utf-8",
        )

        parameters = {
            "authorization_path": record_path,
            "source_root": source,
            "destination_root": target,
            "max_files": 5,
            "max_source_bytes": 1_000_000,
            "max_runtime_seconds": 30,
        }
        parameters.update(overrides)

        with pytest.raises(expected_error):
            transport.run_synthetic_h2_transport(**parameters)

        assert not (target / "TRANSPORT_COMPLETE").exists(), label

    missing = source / "depth_levels" / "date=2026-09-04"
    missing.rmdir()

    missing_target = destination.parent / "destination_missing"
    updated_record = dict(record)
    updated_record["destination_root"] = str(missing_target)

    missing_auth = authorization_path.parent / "auth_missing.json"
    missing_auth.write_text(
        __import__("json").dumps(updated_record),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing or invalid"):
        transport.run_synthetic_h2_transport(
            authorization_path=missing_auth,
            source_root=source,
            destination_root=missing_target,
            max_files=5,
            max_source_bytes=1_000_000,
            max_runtime_seconds=30,
        )

    assert not (missing_target / "TRANSPORT_COMPLETE").exists()


def test_expired_authorization_blocks_h2_file_access(
    authorization_fixture,
    monkeypatch,
):
    from datetime import datetime, timedelta, timezone

    import pytest

    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_export as exp,
        legacy_snapshot_transport as transport,
    )

    source, destination, record, write_record = authorization_fixture

    record["valid_until_utc"] = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).isoformat()

    record["valid_from_utc"] = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()

    authorization_path = write_record()

    def forbidden_access(*args, **kwargs):
        raise AssertionError("H2 file access occurred before authorization")

    monkeypatch.setattr(exp, "_validate_source_file_core", forbidden_access)
    monkeypatch.setattr(exp, "inspect_parquet_metadata", forbidden_access)
    monkeypatch.setattr(exp, "sha256_file", forbidden_access)

    with pytest.raises(PermissionError):
        transport.run_synthetic_h2_transport(
            authorization_path=authorization_path,
            source_root=source,
            destination_root=destination,
            max_files=5,
            max_source_bytes=1_000_000,
            max_runtime_seconds=30,
        )

    assert not destination.exists()


def test_destination_verifier_adversarial(tmp_path):
    import hashlib
    import json

    import pytest

    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_transport as transport,
    )

    destination = tmp_path / "verified_destination"
    destination.mkdir()

    relative = (
        "trades/date=2026-09-04/"
        "00000000-0000-4000-8000-000000000001.parquet"
    )
    target = destination / relative
    target.parent.mkdir(parents=True)

    payload = b"synthetic destination bytes"
    target.write_bytes(payload)

    digest = "a" * 64
    evidence = {
        "prototype": True,
        "production_transfer_authorized": False,
        "predictive_analysis_authorized": False,
        "classification": transport.TRANSPORT_CLASSIFICATION,
        "authorization_sha256": digest,
        "destination_root": str(destination),
        "file_count": 1,
        "source_bytes": len(payload),
        "files": [{
            "relative_path": relative,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "classification": transport.TRANSPORT_CLASSIFICATION,
        }],
    }

    evidence_path = destination / "transport_evidence.json"
    marker = destination / "TRANSPORT_COMPLETE"

    def write_evidence():
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    write_evidence()
    marker.write_text(digest + "\n", encoding="utf-8")

    result = transport.verify_synthetic_h2_transport_destination(
        evidence_path, destination
    )
    assert result["verified"] is True
    assert result["file_count"] == 1

    target.write_bytes(b"modified destination bytes")
    with pytest.raises(ValueError):
        transport.verify_synthetic_h2_transport_destination(
            evidence_path, destination
        )

    target.write_bytes(payload)
    extra = destination / "unexpected.txt"
    extra.write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        transport.verify_synthetic_h2_transport_destination(
            evidence_path, destination
        )

    extra.unlink()
    marker.write_text("incorrect digest\n", encoding="utf-8")
    with pytest.raises(ValueError, match="marker"):
        transport.verify_synthetic_h2_transport_destination(
            evidence_path, destination
        )

    marker.write_text(digest + "\n", encoding="utf-8")
    evidence["files"][0]["relative_path"] = "../escape.parquet"
    write_evidence()
    with pytest.raises(ValueError):
        transport.verify_synthetic_h2_transport_destination(
            evidence_path, destination
        )


def test_transport_source_mutation_between_validations(
    authorization_fixture, monkeypatch
):
    from datetime import timedelta
    import pytest
    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_export as exp,
        legacy_snapshot_transport as transport,
    )

    source, destination, record, write_record = authorization_fixture
    current = exp.H2_START
    while current <= exp.H2_END:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={current.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        current += timedelta(days=1)

    relative = (
        "trades/date=2026-09-04/"
        "00000000-0000-4000-8000-000000000001.parquet"
    )
    target = source / relative
    target.write_bytes(b"synthetic fixture")

    original_validator = exp._validate_source_file_core
    calls = [0]

    def changing_validator(root, path):
        calls[0] += 1
        if calls[0] == 1:
            return {
                "sha256": "a" * 64,
                "size_bytes": target.stat().st_size,
                "instruments": ["BTC-USD"],
            }
        if calls[0] == 2:
            return {
                "sha256": "b" * 64,
                "size_bytes": target.stat().st_size,
                "instruments": ["BTC-USD"],
            }
        return original_validator(root, path)

    monkeypatch.setattr(exp, "_validate_source_file_core", changing_validator)

    with pytest.raises(ValueError, match="Source changed before copying"):
        transport.run_synthetic_h2_transport(
            authorization_path=write_record(),
            source_root=source,
            destination_root=destination,
            max_files=5,
            max_source_bytes=1_000_000,
            max_runtime_seconds=30,
        )

    assert calls[0] == 2
    assert not (destination / "TRANSPORT_COMPLETE").exists()


def test_transport_positive_file_budget_exceeded(
    authorization_fixture, monkeypatch
):
    from datetime import timedelta
    import pytest
    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_export as exp,
        legacy_snapshot_transport as transport,
    )

    source, destination, record, write_record = authorization_fixture
    current = exp.H2_START
    while current <= exp.H2_END:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={current.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        current += timedelta(days=1)

    folder = source / "trades" / "date=2026-09-04"
    for number in (1, 2):
        (folder / f"00000000-0000-4000-8000-{number:012d}.parquet").write_bytes(
            b"synthetic fixture"
        )

    monkeypatch.setattr(
        exp,
        "_validate_source_file_core",
        lambda root, path: {
            "sha256": exp.sha256_file(source / path),
            "size_bytes": (source / path).stat().st_size,
            "instruments": ["BTC-USD"],
        },
    )

    with pytest.raises(RuntimeError, match="file"):
        transport.run_synthetic_h2_transport(
            authorization_path=write_record(),
            source_root=source,
            destination_root=destination,
            max_files=1,
            max_source_bytes=1_000_000,
            max_runtime_seconds=30,
        )

    assert not (destination / "TRANSPORT_COMPLETE").exists()
