"""Versioned, synthetic-only Candidate C dual authorization validation."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from L1_CORE.market_data_platform.market_data import legacy_snapshot_scope as scope

AUTH_VERSION = 1
PURPOSE = "SYNTHETIC_DEVELOPMENT_TRANSPORT_ONLY"
OPERATIONS = [
    "copy", "destination_integrity_verification", "hash",
    "schema_validation", "store", "structural_validation",
]
from datetime import timedelta

WINDOWS = {
    "NON_H2": [
        [
            scope.START_DATE.isoformat(),
            (scope.H2_START - timedelta(days=1)).isoformat(),
        ],
        [
            (scope.H2_END + timedelta(days=1)).isoformat(),
            scope.END_DATE.isoformat(),
        ],
    ],
    "H2": [
        [scope.H2_START.isoformat(), scope.H2_END.isoformat()],
    ],
}
FIELDS = {
    "authorization_schema_version", "authorization_id",
    "snapshot_request_id", "segment", "purpose",
    "permitted_operations", "source_root", "destination_root",
    "datasets", "instruments", "date_windows",
    "valid_from_utc", "valid_until_utc",
    "resource_budget_references",
}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_root(value):
    if not isinstance(value, str):
        raise ValueError("Root must be a string")
    path = Path(value)
    if not path.is_absolute() or str(path) != str(path.resolve()):
        raise ValueError("Root must be an absolute canonical path")
    return str(path)


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("Invalid UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Authorization timestamp must be UTC")
    return parsed


def validate_record(path, segment, source_root, destination_root, now=None, *, historical=False):
    """Validate authorization scope and, unless historical, execution time.

    Historical mode validates retained record identity and scope only.
    It does not attest when any operation actually occurred.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Authorization missing or symlinked")

    raw = path.read_bytes()
    record = json.loads(raw)
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("Authorization schema mismatch")

    if type(record["authorization_schema_version"]) is not int or (
        record["authorization_schema_version"] != AUTH_VERSION
    ):
        raise ValueError("Authorization version mismatch")

    for field in ("authorization_id", "snapshot_request_id"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"Invalid {field}")

    if segment not in WINDOWS or record["segment"] != segment:
        raise PermissionError("Authorization segment mismatch")
    if record["purpose"] != PURPOSE:
        raise PermissionError("Production authorization is not issued")
    if record["permitted_operations"] != OPERATIONS:
        raise PermissionError("Unauthorized operation set")
    if record["datasets"] != sorted(scope.DATASETS):
        raise PermissionError("Dataset scope mismatch")
    if record["instruments"] != sorted(scope.INSTRUMENTS):
        raise PermissionError("Instrument scope mismatch")
    if record["date_windows"] != WINDOWS[segment]:
        raise PermissionError("Date-window scope mismatch")

    if _canonical_root(record["source_root"]) != _canonical_root(source_root):
        raise PermissionError("Source root mismatch")
    if _canonical_root(record["destination_root"]) != _canonical_root(destination_root):
        raise PermissionError("Destination root mismatch")

    start = _utc(record["valid_from_utc"])
    end = _utc(record["valid_until_utc"])
    if not start < end:
        raise PermissionError("Invalid authorization validity window")

    if historical:
        if now is not None:
            raise ValueError(
                "Historical validation does not accept a caller time override"
            )
    else:
        current = datetime.now(timezone.utc) if now is None else now
        if (
            not isinstance(current, datetime)
            or current.tzinfo is None
            or current.utcoffset().total_seconds() != 0
        ):
            raise ValueError("Current time must be UTC")
        if not start <= current < end:
            raise PermissionError("Authorization expired or not yet valid")

    references = record["resource_budget_references"]
    if not isinstance(references, dict) or not references or any(
        not isinstance(k, str) or not k.strip()
        or not isinstance(v, str) or not v.strip()
        for k, v in references.items()
    ):
        raise ValueError("Invalid resource budget references")

    return {
        "authorization_id": record["authorization_id"],
        "snapshot_request_id": record["snapshot_request_id"],
        "segment": segment,
        "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        "classification": "SEALED / TRANSPORT ONLY",
    }


def validate_pair(non_h2_path, h2_path, source_root, destination_root, now=None, *, historical=False):
    """Require two distinct records bound to one snapshot request."""
    non_h2 = validate_record(
        non_h2_path, "NON_H2", source_root, destination_root, now,
        historical=historical,
    )
    h2 = validate_record(
        h2_path, "H2", source_root, destination_root, now,
        historical=historical,
    )

    if Path(non_h2_path).resolve() == Path(h2_path).resolve():
        raise ValueError("Authorization records must be separate")
    if non_h2["authorization_id"] == h2["authorization_id"]:
        raise ValueError("Authorization IDs must be distinct")
    if non_h2["snapshot_request_id"] != h2["snapshot_request_id"]:
        raise PermissionError("Snapshot request identity mismatch")
    if non_h2["authorization_sha256"] == h2["authorization_sha256"]:
        raise ValueError("Authorization digests must be distinct")

    return {
        "authorization_schema_version": AUTH_VERSION,
        "snapshot_request_id": non_h2["snapshot_request_id"],
        "non_h2": non_h2,
        "h2": h2,
        "production_transfer_authorized": False,
        "predictive_analysis_authorized": False,
    }
