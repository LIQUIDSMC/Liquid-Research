"""Synthetic tests for Candidate C dual authorization."""
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

import legacy_snapshot_authorization as auth
import legacy_snapshot_scope as scope


@pytest.fixture
def authorization_fixture(tmp_path):
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()

    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()

    def record(segment, authorization_id):
        return {
            "authorization_schema_version": 1,
            "authorization_id": authorization_id,
            "snapshot_request_id": "SYNTHETIC-SNAPSHOT-001",
            "segment": segment,
            "purpose": auth.PURPOSE,
            "permitted_operations": list(auth.OPERATIONS),
            "source_root": str(source_root.resolve()),
            "destination_root": str(destination_root.resolve()),
            "datasets": sorted(scope.DATASETS),
            "instruments": sorted(scope.INSTRUMENTS),
            "date_windows": copy.deepcopy(auth.WINDOWS[segment]),
            "valid_from_utc": start,
            "valid_until_utc": end,
            "resource_budget_references": {
                "policy": "SYNTHETIC-RESOURCE-POLICY-001"
            },
        }

    non_h2 = record("NON_H2", "SYNTHETIC-AUTH-NONH2")
    h2 = record("H2", "SYNTHETIC-AUTH-H2")

    non_h2_path = tmp_path / "non_h2.json"
    h2_path = tmp_path / "h2.json"

    def write():
        non_h2_path.write_text(json.dumps(non_h2), encoding="utf-8")
        h2_path.write_text(json.dumps(h2), encoding="utf-8")

    write()

    return {
        "non_h2": non_h2,
        "h2": h2,
        "non_h2_path": non_h2_path,
        "h2_path": h2_path,
        "source_root": source_root,
        "destination_root": destination_root,
        "write": write,
    }


def validate_pair(fixture):
    fixture["write"]()
    return auth.validate_pair(
        fixture["non_h2_path"],
        fixture["h2_path"],
        str(fixture["source_root"]),
        str(fixture["destination_root"]),
    )


def test_valid_pair(authorization_fixture):
    result = validate_pair(authorization_fixture)
    assert result["snapshot_request_id"] == "SYNTHETIC-SNAPSHOT-001"
    assert result["non_h2"]["segment"] == "NON_H2"
    assert result["h2"]["segment"] == "H2"
    assert len(result["non_h2"]["authorization_sha256"]) == 64
    assert len(result["h2"]["authorization_sha256"]) == 64
    assert result["production_transfer_authorized"] is False
    assert result["predictive_analysis_authorized"] is False


def test_mismatched_snapshot_request_rejected(authorization_fixture):
    authorization_fixture["h2"]["snapshot_request_id"] = "OTHER-REQUEST"
    with pytest.raises(PermissionError, match="identity mismatch"):
        validate_pair(authorization_fixture)


def test_duplicate_authorization_id_rejected(authorization_fixture):
    authorization_fixture["h2"]["authorization_id"] = (
        authorization_fixture["non_h2"]["authorization_id"]
    )
    with pytest.raises(ValueError, match="distinct"):
        validate_pair(authorization_fixture)


def test_production_purpose_rejected(authorization_fixture):
    authorization_fixture["h2"]["purpose"] = "PRODUCTION_TRANSFER"
    with pytest.raises(PermissionError, match="Production"):
        validate_pair(authorization_fixture)


def test_h2_scope_expansion_rejected(authorization_fixture):
    authorization_fixture["h2"]["date_windows"] = [
        ["2026-09-04", "2026-10-06"]
    ]
    with pytest.raises(PermissionError, match="Date-window"):
        validate_pair(authorization_fixture)


def test_non_h2_scope_expansion_rejected(authorization_fixture):
    authorization_fixture["non_h2"]["date_windows"] = [
        ["2026-08-21", "2026-10-06"]
    ]
    with pytest.raises(PermissionError, match="Date-window"):
        validate_pair(authorization_fixture)


def test_extra_authorization_field_rejected(authorization_fixture):
    authorization_fixture["h2"]["production_approved"] = True
    with pytest.raises(ValueError, match="schema"):
        validate_pair(authorization_fixture)


def test_missing_operation_rejected(authorization_fixture):
    authorization_fixture["h2"]["permitted_operations"].remove("hash")
    with pytest.raises(PermissionError, match="operation"):
        validate_pair(authorization_fixture)


def test_wrong_source_root_rejected(authorization_fixture, tmp_path):
    authorization_fixture["h2"]["source_root"] = str(tmp_path)
    with pytest.raises(PermissionError, match="Source root"):
        validate_pair(authorization_fixture)


def test_expired_authorization_rejected(authorization_fixture):
    old = datetime.now(timezone.utc) - timedelta(days=2)
    authorization_fixture["h2"]["valid_from_utc"] = old.isoformat()
    authorization_fixture["h2"]["valid_until_utc"] = (
        old + timedelta(hours=1)
    ).isoformat()
    with pytest.raises(PermissionError, match="expired"):
        validate_pair(authorization_fixture)


def test_same_record_cannot_authorize_both_segments(authorization_fixture):
    f = authorization_fixture
    with pytest.raises(PermissionError, match="segment mismatch"):
        auth.validate_pair(
            f["h2_path"],
            f["h2_path"],
            str(f["source_root"]),
            str(f["destination_root"]),
        )


def test_symlinked_authorization_rejected(authorization_fixture, tmp_path):
    f = authorization_fixture
    link = tmp_path / "authorization_link.json"
    link.symlink_to(f["h2_path"])
    with pytest.raises(ValueError, match="symlinked"):
        auth.validate_pair(
            f["non_h2_path"],
            link,
            str(f["source_root"]),
            str(f["destination_root"]),
        )


def test_authorization_digest_changes_with_record(authorization_fixture):
    f = authorization_fixture
    first = validate_pair(f)["h2"]["authorization_sha256"]
    f["h2"]["resource_budget_references"]["policy"] = (
        "SYNTHETIC-RESOURCE-POLICY-002"
    )
    second = validate_pair(f)["h2"]["authorization_sha256"]
    assert first != second
