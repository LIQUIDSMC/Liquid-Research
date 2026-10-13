"""Synthetic-only C-003 staging identity foundation.

This module does not authorize transfers, accept payloads, resume copies,
or publish completion. Those operations require later audited increments.
"""

import json
import os
import uuid
from pathlib import Path

import legacy_snapshot_manifest as manifest
import legacy_snapshot_authorization as authorization


IDENTITY_VERSION = 1
IDENTITY_FIELDS = {
    "staging_schema_version",
    "staging_attempt_id",
    "snapshot_request_id",
    "manifest_sha256",
    "authorizations",
}
STATES = frozenset({"INCOMPLETE", "FAILED", "COMPLETE"})


def _safe_directory(path):
    """Require a canonical absolute directory without symlink traversal."""
    raw = str(path)
    if os.path.normpath(raw) != raw:
        raise ValueError("Staging directory must be a canonical path")
    path = Path(raw)
    authorization._canonical_root(str(path))
    if not path.is_dir():
        raise ValueError("Missing staging directory")
    return path


def validate_identity(identity):
    """Validate exact schema without granting execution authority."""
    if not isinstance(identity, dict) or set(identity) != IDENTITY_FIELDS:
        raise ValueError("Invalid staging identity schema")
    if type(identity["staging_schema_version"]) is not int or (
        identity["staging_schema_version"] != IDENTITY_VERSION
    ):
        raise ValueError("Invalid staging identity version")
    try:
        parsed = uuid.UUID(identity["staging_attempt_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid staging attempt ID") from exc
    if str(parsed) != identity["staging_attempt_id"]:
        raise ValueError("Noncanonical staging attempt ID")
    request_id = identity["snapshot_request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("Invalid staging snapshot request ID")
    manifest._digest(identity["manifest_sha256"])
    manifest._authorization_structure(identity["authorizations"], request_id)
    return identity


def verify_staging_identity(
    staging_root, *, expected_attempt_id, expected_request_id,
    expected_manifest_sha256, expected_authorizations
):
    """Read and compare a durable identity; no resume authorization implied."""
    root = _safe_directory(staging_root)
    identity_path = root / "identity.json"
    if identity_path.is_symlink() or not identity_path.is_file():
        raise ValueError("Missing or symlinked staging identity")
    identity = validate_identity(json.loads(identity_path.read_bytes()))
    expected = {
        "staging_schema_version": IDENTITY_VERSION,
        "staging_attempt_id": expected_attempt_id,
        "snapshot_request_id": expected_request_id,
        "manifest_sha256": expected_manifest_sha256,
        "authorizations": expected_authorizations,
    }
    validate_identity(expected)
    if identity != expected:
        raise PermissionError("Staging identity does not match expected attempt")
    return {
        "staging_identity_verified": True,
        "staging_attempt_id": identity["staging_attempt_id"],
        "snapshot_request_id": identity["snapshot_request_id"],
        "rollback_attestation": "UNATTESTED",
        "historical_timing_attestation": "UNATTESTED",
        "scientific_readiness": "PENDING",
    }
