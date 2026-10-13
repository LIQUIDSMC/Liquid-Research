"""Focused synthetic tests for the C-003 staging identity foundation."""

import copy
import json
import uuid

import pytest

import legacy_snapshot_staging as staging


DIGEST = "a" * 64


def identity():
    request = "synthetic-request-001"
    return {
        "staging_schema_version": 1,
        "staging_attempt_id": str(uuid.uuid4()),
        "snapshot_request_id": request,
        "manifest_sha256": DIGEST,
        "authorizations": {
            "authorization_schema_version": 1,
            "snapshot_request_id": request,
            "non_h2": {
                "authorization_id": "synthetic-non-h2",
                "snapshot_request_id": request,
                "segment": "NON_H2",
                "authorization_sha256": "b" * 64,
                "classification": "SEALED / TRANSPORT ONLY",
            },
            "h2": {
                "authorization_id": "synthetic-h2",
                "snapshot_request_id": request,
                "segment": "H2",
                "authorization_sha256": "c" * 64,
                "classification": "SEALED / TRANSPORT ONLY",
            },
            "production_transfer_authorized": False,
            "predictive_analysis_authorized": False,
        },
    }


def verify(root, record):
    return staging.verify_staging_identity(
        root,
        expected_attempt_id=record["staging_attempt_id"],
        expected_request_id=record["snapshot_request_id"],
        expected_manifest_sha256=record["manifest_sha256"],
        expected_authorizations=record["authorizations"],
    )


def test_valid_identity_reports_unattested(tmp_path):
    record = identity()
    (tmp_path / "identity.json").write_text(json.dumps(record))
    result = verify(tmp_path, record)
    assert result["staging_identity_verified"] is True
    assert result["rollback_attestation"] == "UNATTESTED"
    assert result["historical_timing_attestation"] == "UNATTESTED"
    assert result["scientific_readiness"] == "PENDING"


@pytest.mark.parametrize("field,value", [
    ("staging_schema_version", True),
    ("staging_attempt_id", "not-a-uuid"),
    ("snapshot_request_id", ""),
    ("manifest_sha256", "not-a-digest"),
])
def test_invalid_identity_fields(field, value):
    record = identity()
    record[field] = value
    with pytest.raises(ValueError):
        staging.validate_identity(record)


def test_rejects_extra_identity_field():
    record = identity()
    record["rollback_attestation"] = "ATTESTED"
    with pytest.raises(ValueError):
        staging.validate_identity(record)


def test_rejects_wrong_expected_attempt_without_modifying_identity(tmp_path):
    record = identity()
    original = json.dumps(record)
    path = tmp_path / "identity.json"
    path.write_text(original)
    other = copy.deepcopy(record)
    other["staging_attempt_id"] = str(uuid.uuid4())
    with pytest.raises(PermissionError):
        verify(tmp_path, other)
    assert path.read_text() == original


def test_rejects_wrong_authorization_identity(tmp_path):
    record = identity()
    (tmp_path / "identity.json").write_text(json.dumps(record))
    other = copy.deepcopy(record)
    other["authorizations"]["non_h2"]["authorization_sha256"] = "d" * 64
    with pytest.raises(PermissionError):
        verify(tmp_path, other)


def test_rejects_symlinked_identity(tmp_path):
    record = identity()
    target = tmp_path / "actual.json"
    target.write_text(json.dumps(record))
    (tmp_path / "identity.json").symlink_to(target)
    with pytest.raises(ValueError, match="symlinked"):
        verify(tmp_path, record)


def test_rejects_symlinked_parent(tmp_path):
    record = identity()
    real = tmp_path / "real"
    real.mkdir()
    (real / "identity.json").write_text(json.dumps(record))
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="canonical"):
        verify(alias, record)


def test_rejects_relative_staging_root(tmp_path):
    with pytest.raises(ValueError, match="absolute"):
        staging._safe_directory("relative/staging")


@pytest.mark.parametrize("component", ["..", "."])
def test_rejects_noncanonical_staging_path(tmp_path, component):
    root = tmp_path / "attempt"
    root.mkdir()
    candidate = f"{root}/{component}"
    with pytest.raises(ValueError, match="canonical"):
        staging._safe_directory(candidate)


def test_rejects_symlinked_intermediate_component(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="canonical"):
        staging._safe_directory(alias / ".." / "real")
