"""Synthetic regression tests for C-003 authorization time semantics."""

import json
from datetime import datetime, timezone

import pytest

import legacy_snapshot_authorization as auth
import legacy_snapshot_scope as scope


REFERENCE_TIME = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def make_record(
    tmp_path,
    segment,
    *,
    valid_from="2026-10-01T00:00:00+00:00",
    valid_until="2026-10-05T00:00:00+00:00",
):
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir(exist_ok=True)
    destination_root.mkdir(exist_ok=True)

    record = {
        "authorization_schema_version": auth.AUTH_VERSION,
        "authorization_id": f"synthetic-{segment}",
        "snapshot_request_id": "synthetic-c003-request",
        "segment": segment,
        "purpose": auth.PURPOSE,
        "permitted_operations": list(auth.OPERATIONS),
        "source_root": str(source_root.resolve()),
        "destination_root": str(destination_root.resolve()),
        "datasets": sorted(scope.DATASETS),
        "instruments": sorted(scope.INSTRUMENTS),
        "date_windows": auth.WINDOWS[segment],
        "valid_from_utc": valid_from,
        "valid_until_utc": valid_until,
        "resource_budget_references": {
            "policy": "synthetic-development-only"
        },
    }

    path = tmp_path / f"{segment.lower()}_authorization.json"
    path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    return path, str(source_root.resolve()), str(destination_root.resolve())


def test_expired_authorization_passes_historical_validation(tmp_path):
    path, source, destination = make_record(tmp_path, "NON_H2")

    result = auth.validate_record(
        path, "NON_H2", source, destination, historical=True
    )

    assert result["authorization_id"] == "synthetic-NON_H2"
    assert result["segment"] == "NON_H2"


def test_expired_authorization_cannot_authorize_execution(tmp_path):
    path, source, destination = make_record(tmp_path, "NON_H2")

    with pytest.raises(PermissionError, match="expired|not yet valid"):
        auth.validate_record(
            path, "NON_H2", source, destination, now=REFERENCE_TIME
        )


def test_future_authorization_cannot_authorize_execution(tmp_path):
    path, source, destination = make_record(
        tmp_path,
        "NON_H2",
        valid_from="2026-10-11T00:00:00+00:00",
        valid_until="2026-10-20T00:00:00+00:00",
    )

    with pytest.raises(PermissionError, match="expired|not yet valid"):
        auth.validate_record(
            path, "NON_H2", source, destination, now=REFERENCE_TIME
        )


def test_historical_mode_rejects_invalid_validity_window(tmp_path):
    path, source, destination = make_record(
        tmp_path,
        "NON_H2",
        valid_from="2026-10-05T00:00:00+00:00",
        valid_until="2026-10-01T00:00:00+00:00",
    )

    with pytest.raises(PermissionError, match="validity window"):
        auth.validate_record(
            path, "NON_H2", source, destination, historical=True
        )


def test_historical_mode_rejects_caller_time_override(tmp_path):
    path, source, destination = make_record(tmp_path, "NON_H2")

    with pytest.raises(ValueError, match="time override"):
        auth.validate_record(
            path,
            "NON_H2",
            source,
            destination,
            now=REFERENCE_TIME,
            historical=True,
        )


def test_historical_pair_validates_expired_distinct_records(tmp_path):
    non_h2, source, destination = make_record(tmp_path, "NON_H2")
    h2, _, _ = make_record(tmp_path, "H2")

    result = auth.validate_pair(
        non_h2, h2, source, destination, historical=True
    )

    assert result["snapshot_request_id"] == "synthetic-c003-request"
    assert result["non_h2"]["authorization_id"] != result["h2"]["authorization_id"]
    assert result["non_h2"]["authorization_sha256"] != result["h2"]["authorization_sha256"]
    assert result["production_transfer_authorized"] is False
    assert result["predictive_analysis_authorized"] is False


def test_historical_pair_rejects_time_override(tmp_path):
    non_h2, source, destination = make_record(tmp_path, "NON_H2")
    h2, _, _ = make_record(tmp_path, "H2")

    with pytest.raises(ValueError, match="time override"):
        auth.validate_pair(
            non_h2,
            h2,
            source,
            destination,
            now=REFERENCE_TIME,
            historical=True,
        )


def test_historical_validation_still_enforces_scope(tmp_path):
    path, source, destination = make_record(tmp_path, "NON_H2")

    with pytest.raises(PermissionError, match="Destination root mismatch"):
        auth.validate_record(
            path,
            "NON_H2",
            source,
            str((tmp_path / "wrong-destination").resolve()),
            historical=True,
        )
