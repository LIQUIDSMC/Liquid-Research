"""Candidate C externally anchored manifest verification.

Synthetic-development integration foundation. No production authorization.
"""
import hashlib
import json
import re
from pathlib import Path

import legacy_snapshot_scope as scope
import legacy_snapshot_authorization as authorization
import legacy_snapshot_export as exporter

SCHEMA_VERSION = 1
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MANIFEST_FIELDS = {
    "manifest_schema_version", "snapshot_request_id",
    "export_classification", "point_in_time_complete",
    "production_transfer_authorized",
    "predictive_analysis_authorized",
    "scientific_readiness", "scope_accounting",
    "authorizations", "files", "component_evidence",
    "inventory_started_utc", "inventory_ended_utc",
    "exceptions",
}
FILE_FIELDS = {
    "relative_path", "size_bytes", "sha256",
    "dataset", "partition_date", "instruments",
    "row_count", "row_groups",
}
EVIDENCE_FIELDS = {"relative_path", "size_bytes", "sha256"}
AUTH_FIELDS = {
    "authorization_schema_version", "snapshot_request_id",
    "non_h2", "h2", "production_transfer_authorized",
    "predictive_analysis_authorized",
}
AUTH_ID_FIELDS = {
    "authorization_id", "snapshot_request_id", "segment",
    "authorization_sha256", "classification",
}


AUTHORIZATION_EVIDENCE_PATHS = {
    "NON_H2": "authorization/non_h2.json",
    "H2": "authorization/h2.json",
}


def _bind_authorization_evidence(root, manifest, expected_source_root):
    """Independently validate retained authorization evidence.

    Historical validation checks record bytes, identity, schema, and
    scope. It does not attest when any operation occurred.
    """
    claimed = manifest["authorizations"]
    request_id = manifest["snapshot_request_id"]

    paths = {}

    for segment, relative in AUTHORIZATION_EVIDENCE_PATHS.items():
        candidate = root

        for part in Path(relative).parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError(
                    f"Symlinked authorization evidence: {segment}"
                )

        if not candidate.is_file():
            raise ValueError(
                f"Missing authorization evidence: {segment}"
            )

        paths[segment] = candidate

    independently_validated = authorization.validate_pair(
        paths["NON_H2"],
        paths["H2"],
        expected_source_root,
        str(root.resolve()),
        historical=True,
    )

    if independently_validated != claimed:
        raise ValueError(
            "Authorization evidence differs from manifest binding"
        )

    if independently_validated["snapshot_request_id"] != request_id:
        raise ValueError(
            "Authorization evidence snapshot request mismatch"
        )

    return set(AUTHORIZATION_EVIDENCE_PATHS.values())


def _digest(value):
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise ValueError("Invalid SHA-256 digest")


def _relative(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Invalid relative path")
    path = Path(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or path.as_posix() != value
        or any(not part for part in path.parts)
    ):
        raise ValueError("Unsafe relative path")
    return path


def _verified_file(root, record, required_fields):
    if not isinstance(record, dict) or set(record) != required_fields:
        raise ValueError("Unexpected file-record schema")
    relative = _relative(record["relative_path"])
    size = record["size_bytes"]
    if type(size) is not int or size <= 0:
        raise ValueError("Invalid file size")
    _digest(record["sha256"])

    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Symlinked destination component")
    if not candidate.is_file():
        raise ValueError("Missing destination file")
    if candidate.stat().st_size != size:
        raise ValueError("Destination file size mismatch")

    hasher = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != record["sha256"]:
        raise ValueError("Destination file SHA-256 mismatch")
    return relative.as_posix()


def _verify_destination_inventory(root, expected_files):
    """Reject unlisted files, directories, and symlinked entries."""
    expected_directories = {""}
    for relative in expected_files:
        parts = Path(relative).parts
        for index in range(1, len(parts)):
            expected_directories.add(
                Path(*parts[:index]).as_posix()
            )

    pending = [(root, "")]
    while pending:
        directory, prefix = pending.pop()

        children = list(directory.iterdir())

        for child in children:
            relative = (
                f"{prefix}/{child.name}"
                if prefix else child.name
            )

            if child.is_symlink():
                raise ValueError(
                    f"Unexpected symlinked destination entry: {relative}"
                )

            if child.is_dir():
                if relative not in expected_directories:
                    raise ValueError(
                        f"Unexpected destination directory: {relative}"
                    )
                pending.append((child, relative))
            elif child.is_file():
                if relative not in expected_files:
                    raise ValueError(
                        f"Unexpected destination file: {relative}"
                    )
            else:
                raise ValueError(
                    f"Unexpected destination entry type: {relative}"
                )


def _authorization_structure(value, request_id):
    if not isinstance(value, dict) or set(value) != AUTH_FIELDS:
        raise ValueError("Invalid authorization binding schema")
    if value["authorization_schema_version"] != 1:
        raise ValueError("Authorization schema version mismatch")
    if value["snapshot_request_id"] != request_id:
        raise ValueError("Authorization request mismatch")
    if value["production_transfer_authorized"] is not False:
        raise PermissionError("Production transfer not authorized")
    if value["predictive_analysis_authorized"] is not False:
        raise PermissionError("Predictive analysis not authorized")

    identities = []
    for key, segment in (("non_h2", "NON_H2"), ("h2", "H2")):
        identity = value[key]
        if not isinstance(identity, dict) or set(identity) != AUTH_ID_FIELDS:
            raise ValueError("Invalid authorization identity")
        if (
            identity["segment"] != segment
            or identity["snapshot_request_id"] != request_id
            or identity["classification"] != "SEALED / TRANSPORT ONLY"
            or not isinstance(identity["authorization_id"], str)
            or not identity["authorization_id"].strip()
        ):
            raise ValueError("Authorization identity mismatch")
        _digest(identity["authorization_sha256"])
        identities.append(identity)

    if identities[0]["authorization_id"] == identities[1]["authorization_id"]:
        raise ValueError("Duplicate authorization IDs")
    if identities[0]["authorization_sha256"] == identities[1]["authorization_sha256"]:
        raise ValueError("Duplicate authorization digests")


def verify_full_range_destination(
    destination_root, expected_manifest_sha256, *, expected_source_root
):
    """Verify destination against a mandatory EXTERNALLY obtained digest.

    Never obtains the expected digest from destination files or markers.
    Does not require access to the source corpus.
    """
    _digest(expected_manifest_sha256)
    root = Path(destination_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Invalid destination root")

    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Missing or symlinked manifest")

    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError("External manifest SHA-256 mismatch")

    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ValueError("Manifest schema mismatch")
    if type(manifest["manifest_schema_version"]) is not int or (
        manifest["manifest_schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError("Manifest version mismatch")

    request_id = manifest["snapshot_request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("Invalid snapshot request ID")

    expected_flags = {
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
        "production_transfer_authorized": False,
        "predictive_analysis_authorized": False,
        "scientific_readiness": "PENDING",
    }
    for field, expected in expected_flags.items():
        if manifest[field] != expected or (
            isinstance(expected, bool)
            and manifest[field] is not expected
        ):
            raise ValueError(f"Invalid manifest field: {field}")

    _authorization_structure(manifest["authorizations"], request_id)

    authorization_evidence_paths = _bind_authorization_evidence(
        root, manifest, expected_source_root
    )

    for field in ("inventory_started_utc", "inventory_ended_utc"):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise ValueError(f"Invalid {field}")

    if not isinstance(manifest["exceptions"], list):
        raise ValueError("Invalid exceptions")

    records = manifest["files"]
    evidence = manifest["component_evidence"]
    if not isinstance(records, list) or not isinstance(evidence, list):
        raise ValueError("Invalid manifest file collections")

    seen = {"manifest.json"} | authorization_evidence_paths
    observed = {}

    for record in records:
        relative = _relative(record.get("relative_path", "") if isinstance(record, dict) else "")
        dataset, partition_date = _parse_payload(relative)
        if set(record) != FILE_FIELDS:
            raise ValueError("Unexpected payload fields")
        if (
            record["dataset"] != dataset
            or record["partition_date"] != partition_date
        ):
            raise ValueError("Payload scope mismatch")
        instruments = record["instruments"]
        if (
            not isinstance(instruments, list)
            or instruments != sorted(set(instruments))
            or not set(instruments).issubset(scope.INSTRUMENTS)
        ):
            raise ValueError("Invalid instrument evidence")
        name = _verified_file(root, record, FILE_FIELDS)
        if name in seen:
            raise ValueError("Duplicate destination path")

        # Reuse the canonical schema and row-level validator. This checks
        # actual Parquet content rather than trusting manifest assertions.
        measured = exporter._validate_source_file_core(root, name)
        for field in FILE_FIELDS:
            if measured[field] != record[field]:
                raise ValueError(
                    f"Parquet content evidence mismatch: {field}"
                )

        seen.add(name)
        partition = f"{dataset}/date={partition_date}"
        observed.setdefault(partition, set()).update(
            measured["instruments"]
        )

    verified_evidence_digests = {}

    for record in evidence:
        name = _verified_file(root, record, EVIDENCE_FIELDS)
        if name in seen:
            raise ValueError("Duplicate destination path")
        seen.add(name)
        verified_evidence_digests[name] = record["sha256"]

    _verify_destination_inventory(root, seen)

    # Reconstruct coverage exclusively from independently validated
    # destination Parquet rows, never from manifest coverage assertions.
    accounting = manifest["scope_accounting"]
    if not isinstance(accounting, dict):
        raise ValueError("Missing scope accounting")

    exclusions = accounting.get("sanctioned_exclusions")
    if not isinstance(exclusions, list):
        raise ValueError("Invalid sanctioned exclusions")

    validation_exclusions = []
    trusted_evidence_digests = {}
    original_evidence_paths = {}

    exclusion_fields = {
        "partition",
        "adjudication_id",
        "reason",
        "evidence_path",
    }

    for claimed in exclusions:
        if not isinstance(claimed, dict) or set(claimed) != (
            exclusion_fields | {"evidence_sha256"}
        ):
            raise ValueError("Invalid sanctioned exclusion schema")

        relative = _relative(claimed["evidence_path"]).as_posix()

        if relative not in verified_evidence_digests:
            raise ValueError(
                "Exclusion evidence absent from verified component evidence"
            )

        # _verified_file already checked every destination path component
        # for symlinks, verified file size, and verified SHA-256.
        absolute = str((root.resolve() / relative).absolute())

        validation_exclusions.append({
            field: absolute if field == "evidence_path" else claimed[field]
            for field in exclusion_fields
        })

        trusted_evidence_digests[absolute] = (
            verified_evidence_digests[relative]
        )
        original_evidence_paths[absolute] = relative

    measured_accounting = scope.build_scope_accounting(
        observed_coverage={
            partition: sorted(instruments)
            for partition, instruments in observed.items()
        },
        sanctioned_exclusions=validation_exclusions,
        trusted_evidence_digests=trusted_evidence_digests,
    )

    # Restore portable relative paths only in reconstructed accounting.
    # The original manifest accounting remains completely untouched.
    for verified in measured_accounting["sanctioned_exclusions"]:
        verified["evidence_path"] = original_evidence_paths[
            verified["evidence_path"]
        ]

    if accounting != measured_accounting:
        raise ValueError(
            "Manifest scope accounting differs from validated Parquet coverage"
        )

    # No READY classification is issued by this foundation verifier.
    return {
        "integrity_verified": True,
        "historical_timing_attestation": "UNATTESTED",
        "manifest_sha256": expected_manifest_sha256,
        "verified_payload_files": len(records),
        "verified_component_evidence_files": len(evidence),
        "classification": "INTEGRITY_ONLY_NOT_READY",
        "scientific_readiness": "PENDING",
    }


def _parse_payload(relative):
    import uuid
    parts = relative.parts
    if len(parts) != 3 or parts[0] not in scope.DATASETS:
        raise ValueError("Invalid canonical payload path")
    partition = f"{parts[0]}/{parts[1]}"
    scope.validate_partition(partition)
    filename = parts[2]
    if not filename.endswith(".parquet"):
        raise ValueError("Invalid payload extension")
    try:
        parsed = uuid.UUID(filename[:-8])
    except ValueError as exc:
        raise ValueError("Invalid payload UUID") from exc
    if f"{parsed}.parquet" != filename:
        raise ValueError("Noncanonical payload UUID")
    return parts[0], parts[1][5:]
