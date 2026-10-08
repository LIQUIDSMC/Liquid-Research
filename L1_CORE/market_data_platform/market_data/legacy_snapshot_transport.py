"""
Candidate C H2 transport-only development interface.

H2 predictive research remains SEALED.
Production transfer is not authorized.
"""

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from L1_CORE.market_data_platform.market_data import legacy_snapshot_export as exp


TRANSPORT_OPERATIONS = frozenset({
    "structural_validation",
    "schema_validation",
    "hash",
    "copy",
    "store",
    "destination_integrity_verification",
})

TRANSPORT_CLASSIFICATION = "SEALED / TRANSPORT ONLY"


def validate_transport_authorization(record_path, source_root, destination_root):
    """Validate an explicit local record before any H2 file access."""
    record_path = Path(record_path)

    if record_path.is_symlink() or not record_path.is_file():
        raise ValueError("Authorization record missing or symlinked")

    raw = record_path.read_bytes()
    record = json.loads(raw)

    if not isinstance(record, dict):
        raise ValueError("Authorization must be a JSON object")

    required = {
        "authorization_id",
        "purpose",
        "permitted_operations",
        "source_root",
        "destination_root",
        "datasets",
        "instruments",
        "start_date",
        "end_date",
        "valid_from_utc",
        "valid_until_utc",
        "resource_budget_references",
    }

    if set(record) != required:
        raise ValueError("Authorization fields do not match schema")

    if not isinstance(record["authorization_id"], str) or not record["authorization_id"].strip():
        raise ValueError("Invalid authorization ID")

    if record["purpose"] != "SYNTHETIC_DEVELOPMENT_TRANSPORT_ONLY":
        raise PermissionError("Production authorization has not been issued")

    operations = record["permitted_operations"]

    if (
        not isinstance(operations, list)
        or any(not isinstance(operation, str) for operation in operations)
        or len(operations) != len(TRANSPORT_OPERATIONS)
        or set(operations) != TRANSPORT_OPERATIONS
    ):
        raise PermissionError("Transport operations are not explicitly authorized")

    if record["datasets"] != sorted(exp.DATASETS):
        raise PermissionError("Dataset scope mismatch")

    if record["instruments"] != sorted(exp.INSTRUMENTS):
        raise PermissionError("Instrument scope mismatch")

    if record["start_date"] != exp.H2_START.isoformat():
        raise PermissionError("H2 start date mismatch")

    if record["end_date"] != exp.H2_END.isoformat():
        raise PermissionError("H2 end date mismatch")

    for field, expected in (
        ("source_root", source_root),
        ("destination_root", destination_root),
    ):
        actual = record[field]
        if not isinstance(actual, str) or not Path(actual).is_absolute():
            raise ValueError(f"Invalid {field}")

        actual_path = Path(actual)
        expected_path = Path(expected)

        if (
            actual_path != actual_path.resolve()
            or expected_path != expected_path.resolve()
            or actual_path != expected_path
        ):
            raise PermissionError(f"{field} authorization mismatch")

    try:
        valid_from = datetime.fromisoformat(record["valid_from_utc"])
        valid_until = datetime.fromisoformat(record["valid_until_utc"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid authorization validity interval") from exc

    if (
        valid_from.tzinfo is None
        or valid_until.tzinfo is None
        or valid_from.utcoffset().total_seconds() != 0
        or valid_until.utcoffset().total_seconds() != 0
    ):
        raise ValueError("Authorization timestamps must be UTC")

    now = datetime.now(timezone.utc)

    if valid_from >= valid_until:
        raise ValueError("Invalid authorization interval ordering")

    if not valid_from <= now < valid_until:
        raise PermissionError("Authorization is not currently valid")

    references = record["resource_budget_references"]

    if (
        not isinstance(references, dict)
        or not references
        or any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or not value.strip()
            for key, value in references.items()
        )
    ):
        raise ValueError("Invalid resource-budget references")

    return {
        "authorization_id": record["authorization_id"],
        "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        "classification": TRANSPORT_CLASSIFICATION,
        "record": record,
    }


def run_synthetic_h2_transport(
    authorization_path,
    source_root,
    destination_root,
    max_files,
    max_source_bytes,
    max_runtime_seconds,
):
    """
    Synthetic-development H2 transport only.

    No production authorization or predictive research permission.
    Resource limits are cooperative, not hard enforcement.
    """
    import os
    import shutil
    import time
    from datetime import timedelta

    if (
        not isinstance(max_files, int)
        or isinstance(max_files, bool)
        or max_files <= 0
    ):
        raise ValueError("max_files must be a positive integer")

    exp.validate_resource_budgets(
        max_source_bytes=max_source_bytes,
        max_runtime_seconds=max_runtime_seconds,
    )

    if max_source_bytes is None or max_runtime_seconds is None:
        raise ValueError("Explicit byte and runtime budgets are required")

    authorization = validate_transport_authorization(
        authorization_path,
        source_root,
        destination_root,
    )

    source = Path(source_root).resolve()
    destination = Path(destination_root).resolve()

    if (
        source == destination
        or source.is_relative_to(destination)
        or destination.is_relative_to(source)
    ):
        raise ValueError("Source and destination must not overlap")

    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination must not already exist")

    started = time.monotonic()
    copied_files = 0
    copied_bytes = 0
    evidence = []

    def check_runtime():
        if time.monotonic() - started >= max_runtime_seconds:
            raise RuntimeError("Transport runtime budget exceeded")

    def authorized_paths():
        current = exp.H2_START

        while current <= exp.H2_END:
            for dataset in sorted(exp.DATASETS):
                partition = source / dataset / f"date={current.isoformat()}"

                if partition.is_symlink() or not partition.is_dir():
                    raise ValueError("Missing or invalid synthetic H2 partition")

                with os.scandir(partition) as entries:
                    for entry in entries:
                        if entry.is_symlink() or not entry.is_file():
                            raise ValueError("Invalid synthetic H2 source entry")

                        relative = Path(dataset) / partition.name / entry.name
                        parsed_dataset, parsed_date = exp.parse_canonical_path(
                            relative
                        )

                        if parsed_dataset != dataset or parsed_date != current:
                            raise ValueError("Source outside authorized H2 scope")

                        yield relative

            current += timedelta(days=1)

    destination.mkdir(parents=True, exist_ok=False)

    try:
        for relative in authorized_paths():
            check_runtime()

            copied_files += 1

            if copied_files > max_files:
                raise RuntimeError("Transport file-count budget exceeded")

            source_file = source / relative
            size = source_file.stat().st_size

            if copied_bytes + size > max_source_bytes:
                raise RuntimeError("Transport source-byte budget exceeded")

            dataset, partition_date = exp.parse_canonical_path(relative)

            if not exp.H2_START <= partition_date <= exp.H2_END:
                raise PermissionError("Partition outside authorized H2 interval")

            validated = exp._validate_source_file_core(
                source,
                relative,
            )

            if not set(validated["instruments"]).issubset(
                authorization["record"]["instruments"]
            ):
                raise PermissionError("Instrument outside authorized scope")

            source_hash = validated["sha256"]
            source_identity = exp.file_identity(source_file)

            if source_identity["size_bytes"] != validated["size_bytes"]:
                raise ValueError("Source changed after validation")

            revalidated = exp._validate_source_file_core(source, relative)
            source_identity_after = exp.file_identity(source_file)

            if (
                revalidated["sha256"] != source_hash
                or revalidated["size_bytes"] != validated["size_bytes"]
                or not exp.stable_identity(
                    source_identity, source_identity_after
                )
            ):
                raise ValueError("Source changed before copying")

            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)

            with source_file.open("rb") as reader, target.open("xb") as writer:
                shutil.copyfileobj(reader, writer, exp.HASH_CHUNK_BYTES)
                writer.flush()
                os.fsync(writer.fileno())

            if target.stat().st_size != size:
                raise ValueError("Destination size mismatch")

            if exp.sha256_file(target) != source_hash:
                raise ValueError("Destination SHA-256 mismatch")

            source_after_copy = exp.file_identity(source_file)

            if not exp.stable_identity(
                source_identity,
                source_after_copy,
            ):
                raise ValueError("Source changed during transport")

            if exp.sha256_file(source_file) != source_hash:
                raise ValueError("Source SHA-256 changed during transport")

            copied_bytes += size
            check_runtime()

            evidence.append({
                "relative_path": relative.as_posix(),
                "size_bytes": size,
                "sha256": source_hash,
                "classification": TRANSPORT_CLASSIFICATION,
            })

        check_runtime()

        result = {
            "prototype": True,
            "production_transfer_authorized": False,
            "predictive_analysis_authorized": False,
            "classification": TRANSPORT_CLASSIFICATION,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": authorization["authorization_sha256"],
            "source_root": str(source),
            "destination_root": str(destination),
            "file_count": copied_files,
            "source_bytes": copied_bytes,
            "max_files": max_files,
            "max_source_bytes": max_source_bytes,
            "max_runtime_seconds": max_runtime_seconds,
            "resource_budget_references": authorization["record"][
                "resource_budget_references"
            ],
            "files": evidence,
        }

        evidence_path = destination / "transport_evidence.json"

        evidence_path.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        completion_marker = destination / "TRANSPORT_COMPLETE"
        completion_marker.write_text(
            authorization["authorization_sha256"] + "\n",
            encoding="utf-8",
        )

        return result

    except BaseException:
        raise


def verify_synthetic_h2_transport_destination(evidence_path, destination_root):
    """Independently verify synthetic transport output against recorded hashes."""
    import re

    destination = Path(destination_root)
    evidence_path = Path(evidence_path)

    if not destination.is_absolute() or destination != destination.resolve():
        raise ValueError("Destination root must be canonical and absolute")
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("Destination root missing or symlinked")
    if evidence_path != destination / "transport_evidence.json":
        raise ValueError("Evidence must be at the canonical destination path")
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise ValueError("Evidence missing or symlinked")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise ValueError("Invalid evidence object")
    if evidence.get("prototype") is not True:
        raise ValueError("Not synthetic prototype evidence")
    if evidence.get("production_transfer_authorized") is not False:
        raise PermissionError("Unexpected production authorization")
    if evidence.get("predictive_analysis_authorized") is not False:
        raise PermissionError("Unexpected predictive authorization")
    if evidence.get("classification") != TRANSPORT_CLASSIFICATION:
        raise ValueError("Incorrect evidence classification")
    if evidence.get("destination_root") != str(destination):
        raise ValueError("Destination root mismatch")

    digest = evidence.get("authorization_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid authorization digest")

    marker = destination / "TRANSPORT_COMPLETE"
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("Completion marker missing or symlinked")
    if marker.read_text(encoding="utf-8") != digest + "\n":
        raise ValueError("Completion marker mismatch")

    entries = evidence.get("files")
    if not isinstance(entries, list):
        raise ValueError("Invalid evidence file list")
    if type(evidence.get("file_count")) is not int:
        raise ValueError("Invalid file count")
    if evidence["file_count"] != len(entries):
        raise ValueError("Evidence file count mismatch")

    expected = set()
    total = 0

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid file entry")
        relative_text = entry.get("relative_path")
        if not isinstance(relative_text, str):
            raise ValueError("Invalid relative path")
        relative = Path(relative_text)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != relative_text
            or relative_text in expected
        ):
            raise ValueError("Unsafe or duplicate relative path")

        dataset, partition_date = exp.parse_canonical_path(relative)
        if dataset not in exp.DATASETS:
            raise ValueError("Unexpected dataset")
        if not exp.H2_START <= partition_date <= exp.H2_END:
            raise ValueError("Partition outside H2 scope")
        if entry.get("classification") != TRANSPORT_CLASSIFICATION:
            raise ValueError("Incorrect file classification")

        size = entry.get("size_bytes")
        sha = entry.get("sha256")
        if type(size) is not int or size <= 0:
            raise ValueError("Invalid file size")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("Invalid file hash")

        target = destination / relative
        if target.is_symlink() or not target.is_file():
            raise ValueError("Destination file missing or symlinked")
        if target.stat().st_size != size:
            raise ValueError("Destination file size mismatch")
        if exp.sha256_file(target) != sha:
            raise ValueError("Destination file SHA-256 mismatch")

        expected.add(relative_text)
        total += size

    if type(evidence.get("source_bytes")) is not int:
        raise ValueError("Invalid source byte count")
    if evidence["source_bytes"] != total:
        raise ValueError("Evidence byte count mismatch")

    actual = set()
    for item in destination.rglob("*"):
        if item.is_symlink():
            raise ValueError("Symlink found in destination")
        if item.is_file():
            actual.add(item.relative_to(destination).as_posix())
        elif not item.is_dir():
            raise ValueError("Unexpected destination object")

    allowed = expected | {"transport_evidence.json", "TRANSPORT_COMPLETE"}
    if actual != allowed:
        raise ValueError("Missing or unexpected destination files")

    return {
        "verified": True,
        "classification": TRANSPORT_CLASSIFICATION,
        "authorization_sha256": digest,
        "file_count": len(entries),
        "verified_bytes": total,
    }
