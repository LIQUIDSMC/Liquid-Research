
"""Synthetic-only C-003 durable attempt-state foundation.

This module does not authorize execution, transfer, recovery, or finalization.
State consistency is not authenticated rollback protection.
"""

import json
import os
import uuid

import legacy_snapshot_staging as staging
from legacy_snapshot_lock import exclusive_attempt_lock


STATE_VERSION = 1
STATE_FIELDS = frozenset({
    "state_schema_version",
    "staging_attempt_id",
    "state",
})
TERMINAL = frozenset({"FAILED", "COMPLETE"})


def _canonical(record):
    return json.dumps(
        record, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _directory_sync(root):
    fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _record(attempt_id, state):
    record = {
        "state_schema_version": STATE_VERSION,
        "staging_attempt_id": attempt_id,
        "state": state,
    }
    validate_state(record)
    return record


def validate_state(record):
    if not isinstance(record, dict) or set(record) != STATE_FIELDS:
        raise ValueError("Invalid attempt-state schema")

    if (
        type(record["state_schema_version"]) is not int
        or record["state_schema_version"] != STATE_VERSION
    ):
        raise ValueError("Invalid attempt-state version")

    try:
        parsed = uuid.UUID(record["staging_attempt_id"])
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Invalid state attempt ID") from exc

    if str(parsed) != record["staging_attempt_id"]:
        raise ValueError("Noncanonical state attempt ID")

    if record["state"] not in staging.STATES:
        raise ValueError("Invalid attempt state")

    return record


def read_state(staging_root, *, expected_attempt_id):
    root = staging._safe_directory(staging_root)
    path = root / "state.json"

    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or symlinked attempt-state record")

    record = validate_state(json.loads(path.read_bytes()))

    if record["staging_attempt_id"] != expected_attempt_id:
        raise PermissionError("Attempt-state identity mismatch")

    return record


def _initialize_state_unchecked(staging_root, *, expected_attempt_id):
    """Create INCOMPLETE state without overwriting an existing record."""
    root = staging._safe_directory(staging_root)
    record = _record(expected_attempt_id, "INCOMPLETE")
    path = root / "state.json"

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(fd, "wb") as handle:
        handle.write(_canonical(record) + bytes([10]))
        handle.flush()
        os.fsync(handle.fileno())

    _directory_sync(root)
    return record


def _publish_state_unchecked(
    staging_root,
    *,
    expected_attempt_id,
    new_state,
    fault_boundary=None,
):
    """Publish an allowed transition using atomic replacement.

    This is a single-process foundation. Concurrent writers and recovery
    reconciliation require separate implementation.
    """
    root = staging._safe_directory(staging_root)
    current = read_state(
        root,
        expected_attempt_id=expected_attempt_id,
    )

    if current["state"] in TERMINAL:
        raise PermissionError("Terminal attempt state is immutable")

    if current["state"] != "INCOMPLETE":
        raise ValueError("Unexpected attempt-state transition")

    if new_state not in TERMINAL:
        raise ValueError("Only terminal transitions are supported")

    updated = _record(expected_attempt_id, new_state)
    temporary = root / f".state-{uuid.uuid4().hex}.tmp"

    try:
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(fd, "wb") as handle:
            handle.write(_canonical(updated) + bytes([10]))
            handle.flush()
            os.fsync(handle.fileno())

        if fault_boundary == "AFTER_TEMP_FSYNC":
            raise RuntimeError("Injected failure after state temp fsync")

        # Recheck the visible state immediately before replacement.
        # This is NOT a concurrency-safe compare-and-swap.
        if read_state(
            root,
            expected_attempt_id=expected_attempt_id,
        ) != current:
            raise ValueError("Attempt state changed before publication")

        os.replace(temporary, root / "state.json")

        if fault_boundary == "AFTER_REPLACE":
            raise RuntimeError("Injected failure after state replace")

        _directory_sync(root)

    finally:
        if temporary.exists():
            temporary.unlink()

    return updated


def _require_incomplete_unchecked(staging_root, *, expected_attempt_id):
    record = read_state(
        staging_root,
        expected_attempt_id=expected_attempt_id,
    )
    if record["state"] != "INCOMPLETE":
        raise PermissionError("Attempt is terminal and not writable")
    return record



def _verify_external_identity(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
):
    """Verify all four independent identity anchors.

    Expected values must originate outside identity.json.
    """
    return staging.verify_staging_identity(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )


@exclusive_attempt_lock
def initialize_bound_state(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
):
    """Initialize state only for an externally verified staging identity."""
    _verify_external_identity(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )

    return _initialize_state_unchecked(
        staging_root,
        expected_attempt_id=expected_attempt_id,
    )


def require_bound_incomplete(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
):
    """Require matching durable identity and writable attempt state."""
    _verify_external_identity(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )

    return _require_incomplete_unchecked(
        staging_root,
        expected_attempt_id=expected_attempt_id,
    )


def _publish_bound_state_lock_held(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
    new_state,
    fault_boundary=None,
):
    """Publish terminal state only for an externally verified attempt.

    COMPLETE publication is a primitive, not finalization authorization.
    """
    _verify_external_identity(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )

    return _publish_state_unchecked(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        new_state=new_state,
        fault_boundary=fault_boundary,
    )



@exclusive_attempt_lock
def publish_bound_state(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
    new_state,
    fault_boundary=None,
):
    """Public terminal publication serialized with acceptance and recovery."""
    return _publish_bound_state_lock_held(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
        new_state=new_state,
        fault_boundary=fault_boundary,
    )
