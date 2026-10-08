"""
Candidate C — Legacy Reconciled Canonical Parquet Export.

Source-side export utility. Does not modify canonical source files.

Scientific status:
    Provenance: PASS/CLOSED
    Scientific readiness: PENDING
    H2 reserve: SEALED

A legacy-reconciled export is not a point-in-time-complete snapshot.
"""

import hashlib
import uuid
import json
import os
import time
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
import sqlite3

from L1_CORE.market_data_platform.market_data.storage import (
    TRADE_SCHEMA,
    DEPTH_LEVEL_SCHEMA,
)

CONTRACT_VERSION = "candidate-c-legacy-v1"
MANIFEST_SCHEMA_VERSION = 1

START_DATE = date(2026, 8, 21)
END_DATE = date(2026, 10, 6)

DATASETS = {
    "trades": TRADE_SCHEMA,
    "depth_levels": DEPTH_LEVEL_SCHEMA,
}

INSTRUMENTS = frozenset({"BTC-USD", "ETH-USD"})

H2_START = date(2026, 9, 4)
H2_END = date(2026, 10, 1)

HASH_CHUNK_BYTES = 1024 * 1024



def require_unsealed_h2_date(partition_date):
    """
    Fail closed for sealed H2 partitions.

    This guard has no production authorization bypass.
    """
    if not isinstance(partition_date, date):
        raise ValueError("Invalid H2 partition date")

    if H2_START <= partition_date <= H2_END:
        raise PermissionError(
            "H2 reserve SEALED: separate GM byte-level "
            "authorization required"
        )


def utc_now():
    """Return an explicit UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    """Compute SHA-256 without loading the entire file into memory."""
    digest = hashlib.sha256()

    with open(path, "rb") as source:
        while True:
            chunk = source.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def parse_canonical_path(relative_path):
    """
    Validate canonical dataset/date/filename structure.

    Returns (dataset, partition_date).
    """
    path = Path(relative_path)

    if len(path.parts) != 3:
        raise ValueError("Unexpected canonical path structure")

    dataset, partition, filename = path.parts

    if dataset not in DATASETS:
        raise ValueError("Dataset outside Candidate C contract")

    if not partition.startswith("date="):
        raise ValueError("Missing UTC date partition")

    try:
        partition_date = date.fromisoformat(partition[5:])
    except ValueError as exc:
        raise ValueError("Invalid UTC partition date") from exc

    if not START_DATE <= partition_date <= END_DATE:
        raise ValueError("Date outside Candidate C contract")

    if not filename.endswith(".parquet"):
        raise ValueError("Not a canonical Parquet filename")

    try:
        parsed_uuid = uuid.UUID(filename[:-8])
    except ValueError as exc:
        raise ValueError("Invalid canonical UUID filename") from exc

    if str(parsed_uuid) + ".parquet" != filename:
        raise ValueError("Noncanonical UUID filename")

    return dataset, partition_date


def inspect_parquet_metadata(path, dataset):
    """
    Read Parquet metadata without loading the complete dataset.

    Metadata readability is necessary but not sufficient for
    accepting a source file.
    """
    parquet = pq.ParquetFile(path)

    expected_schema = DATASETS[dataset]
    actual_schema = parquet.schema_arrow

    if not actual_schema.equals(expected_schema):
        raise ValueError("Canonical Arrow schema mismatch")

    rows = parquet.metadata.num_rows

    if rows <= 0:
        raise ValueError("Empty canonical Parquet file")

    return {
        "row_count": rows,
        "row_groups": parquet.metadata.num_row_groups,
    }


def file_identity(path):
    """Capture ordinary filesystem identity/change indicators."""
    stat = os.stat(path, follow_symlinks=False)

    return {
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
    }


def stable_identity(before, after):
    """Detect ordinary filesystem changes during inspection."""
    return before == after


def manifest_header(source_root):
    """Create the initial versioned export metadata."""
    return {
        "contract_version": CONTRACT_VERSION,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
        "source_root": str(Path(source_root).resolve()),
        "inventory_started_utc": utc_now(),
        "datasets": sorted(DATASETS),
        "instruments": sorted(INSTRUMENTS),
        "start_date": START_DATE.isoformat(),
        "end_date": END_DATE.isoformat(),
        "h2_reserve": {
            "start_date": H2_START.isoformat(),
            "end_date": H2_END.isoformat(),
            "status": "SEALED",
            "predictive_analysis_authorized": False,
        },
        "scientific_readiness": "PENDING",
    }


def validate_source_file(source_root, relative_path):
    """Validate an unsealed canonical file; H2 remains denied."""
    _, partition_date = parse_canonical_path(Path(relative_path))
    require_unsealed_h2_date(partition_date)
    return _validate_source_file_core(source_root, relative_path)


def _validate_source_file_core(source_root, relative_path):
    """
    Validate one canonical Parquet file without loading all rows.

    This is legacy reconciliation evidence, not proof of
    point-in-time completeness or immutable publication.

    Raises ValueError/OSError on failed validation.
    """
    relative_path = Path(relative_path)
    dataset, partition_date = parse_canonical_path(relative_path)

    root = Path(source_root).resolve()
    path = root / relative_path

    for index in range(1, len(relative_path.parts) + 1):
        component = root / Path(*relative_path.parts[:index])
        if component.is_symlink():
            raise ValueError("Symlink in canonical source path")

    if not path.resolve().is_relative_to(root):
        raise ValueError("Source escapes canonical root")

    if not path.is_file():
        raise ValueError("Source must be a regular non-symlink file")

    before = file_identity(path)

    if before["size_bytes"] <= 0:
        raise ValueError("Zero-byte canonical file")

    metadata = inspect_parquet_metadata(path, dataset)

    parquet = pq.ParquetFile(path)

    inspected_rows = 0
    observed_instruments = set()

    for batch in parquet.iter_batches(batch_size=8192):
        timestamps = batch.column(
            batch.schema.get_field_index("timestamp_received")
        ).to_pylist()
        instruments = batch.column(
            batch.schema.get_field_index("instrument_id")
        ).to_pylist()

        for timestamp, instrument in zip(timestamps, instruments):
            if instrument not in INSTRUMENTS:
                raise ValueError(
                    f"Unexpected or missing instrument_id: {instrument!r}"
                )

            if not isinstance(timestamp, int):
                raise ValueError("Invalid timestamp_received")

            row_date = datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc,
            ).date()

            if row_date != partition_date:
                raise ValueError(
                    "timestamp_received does not match UTC partition"
                )

            observed_instruments.add(instrument)
            inspected_rows += 1

    if inspected_rows != metadata["row_count"]:
        raise ValueError("Parquet row count mismatch")

    after_read = file_identity(path)

    if not stable_identity(before, after_read):
        raise ValueError("Source changed during Parquet validation")

    digest = sha256_file(path)

    after_hash = file_identity(path)

    if not stable_identity(before, after_hash):
        raise ValueError("Source changed during SHA-256 hashing")

    return {
        "relative_path": relative_path.as_posix(),
        "dataset": dataset,
        "partition_date": partition_date.isoformat(),
        "instruments": sorted(observed_instruments),
        "size_bytes": after_hash["size_bytes"],
        "sha256": digest,
        "row_count": inspected_rows,
        "row_groups": metadata["row_groups"],
    }


def iter_candidate_paths(source_root, max_files):
    """
    Enumerate Candidate C canonical entries with a hard count limit.

    The limit is a safety boundary, not permission to accept a
    partial inventory. Hitting it raises an exception.

    Yields relative paths. No Parquet files are opened here.
    """
    if not isinstance(max_files, int) or isinstance(max_files, bool):
        raise ValueError("max_files must be a positive integer")

    if max_files <= 0:
        raise ValueError("max_files must be a positive integer")

    root = Path(source_root).resolve()
    seen = 0

    current = START_DATE

    from datetime import timedelta

    while current <= END_DATE:
        require_unsealed_h2_date(current)
        for dataset in sorted(DATASETS):
            partition = root / dataset / f"date={current.isoformat()}"

            if partition.is_symlink():
                raise ValueError(
                    f"Symlinked canonical partition: {partition}"
                )

            if not partition.exists():
                raise ValueError(
                    f"Missing canonical partition: {partition}"
                )

            if not partition.is_dir():
                raise ValueError(
                    f"Not a canonical directory: {partition}"
                )

            with os.scandir(partition) as entries:
                for entry in entries:
                    seen += 1

                    if seen > max_files:
                        raise RuntimeError(
                            f"Inventory limit exceeded: max_files={max_files}"
                        )

                    yield (
                        Path(dataset)
                        / f"date={current.isoformat()}"
                        / entry.name
                    )

        current += timedelta(days=1)


def compare_inventories(source_root, max_files, index_path):
    """
    Compare two bounded source inventories using a disk-backed index.

    Returns added/missing paths. This is not a point-in-time snapshot.

    The caller must provide an isolated temporary SQLite index path.
    """
    import sqlite3

    index = Path(index_path)

    if index.exists():
        raise FileExistsError(
            f"Refusing to overwrite inventory index: {index}"
        )

    connection = sqlite3.connect(str(index))

    try:
        connection.execute(
            "CREATE TABLE inventory ("
            "path TEXT PRIMARY KEY, "
            "seen_end INTEGER NOT NULL DEFAULT 0)"
        )

        start_count = 0

        for relative in iter_candidate_paths(source_root, max_files):
            connection.execute(
                "INSERT INTO inventory(path) VALUES (?)",
                (relative.as_posix(),),
            )
            start_count += 1

        connection.commit()

        added = []
        end_count = 0

        for relative in iter_candidate_paths(source_root, max_files):
            path = relative.as_posix()
            end_count += 1

            cursor = connection.execute(
                "UPDATE inventory SET seen_end = 1 WHERE path = ?",
                (path,),
            )

            if cursor.rowcount == 0:
                added.append(path)

        missing = [
            row[0]
            for row in connection.execute(
                "SELECT path FROM inventory "
                "WHERE seen_end = 0 ORDER BY path"
            )
        ]

        return {
            "start_count": start_count,
            "end_count": end_count,
            "added": sorted(added),
            "missing": missing,
            "reconciled": not added and not missing,
        }

    finally:
        connection.close()


def write_jsonl_record(handle, record):
    """
    Write one deterministic JSON Lines record.

    The caller owns the output file and its lifecycle.
    """
    if not isinstance(record, dict):
        raise TypeError("JSONL record must be a dictionary")

    encoded = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    handle.write(encoded + "\n")


def stream_jsonl_records(path):
    """
    Read JSON Lines records incrementally.

    Reject malformed records and non-dictionary entries.
    """
    with open(path, "r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                raise ValueError(
                    f"Empty JSONL record at line {line_number}"
                )

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Malformed JSONL at line {line_number}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Non-object JSONL record at line {line_number}"
                )

            yield record


def write_export_exception(handle, category, message, relative_path=None):
    """
    Append one blocking Candidate C export exception.

    No exception is silently downgraded to a warning.
    """
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Exception category must be nonempty")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Exception message must be nonempty")

    if relative_path is not None:
        relative_path = str(relative_path)

    record = {
        "category": category,
        "message": message,
        "relative_path": relative_path,
        "blocks_acceptance": True,
    }

    write_jsonl_record(handle, record)
    return record


def initialize_export_inventory(connection, source_root, max_files):
    """
    Record the starting Candidate C inventory in SQLite.

    Returns the starting file count. The caller owns the database
    connection and transaction lifecycle.
    """
    connection.execute(
        "CREATE TABLE export_inventory ("
        "path TEXT PRIMARY KEY, "
        "validated INTEGER NOT NULL DEFAULT 0, "
        "seen_end INTEGER NOT NULL DEFAULT 0)"
    )

    count = 0

    for relative in iter_candidate_paths(source_root, max_files):
        connection.execute(
            "INSERT INTO export_inventory(path) VALUES (?)",
            (relative.as_posix(),),
        )
        count += 1

    connection.commit()
    return count


def iter_unvalidated_export_paths(connection):
    """
    Stream starting-inventory paths not yet marked validated.

    Paths are ordered for deterministic processing.
    """
    cursor = connection.execute(
        "SELECT path FROM export_inventory "
        "WHERE validated = 0 ORDER BY path"
    )

    for row in cursor:
        yield row[0]


def mark_export_path_validated(connection, relative_path):
    """Mark one starting-inventory entry as validated."""
    cursor = connection.execute(
        "UPDATE export_inventory SET validated = 1 WHERE path = ?",
        (str(relative_path),),
    )

    if cursor.rowcount != 1:
        raise ValueError(
            f"Path absent from starting inventory: {relative_path}"
        )


def reconcile_export_inventory(
    connection,
    source_root,
    max_files,
    exception_handle,
):
    """
    Compare the ending inventory against the starting SQLite inventory.

    Stream blocking discrepancies to the exception ledger instead of
    retaining potentially millions of paths in Python memory.
    """
    connection.execute(
        "UPDATE export_inventory SET seen_end = 0"
    )

    end_count = 0
    added_count = 0

    for relative in iter_candidate_paths(source_root, max_files):
        relative_path = relative.as_posix()
        end_count += 1

        cursor = connection.execute(
            "UPDATE export_inventory "
            "SET seen_end = 1 WHERE path = ?",
            (relative_path,),
        )

        if cursor.rowcount == 0:
            added_count += 1
            write_export_exception(
                exception_handle,
                category="inventory_added",
                message="File appeared after starting inventory",
                relative_path=relative_path,
            )

    missing_count = 0

    cursor = connection.execute(
        "SELECT path FROM export_inventory "
        "WHERE seen_end = 0 ORDER BY path"
    )

    for (relative_path,) in cursor:
        missing_count += 1
        write_export_exception(
            exception_handle,
            category="inventory_missing",
            message="File disappeared after starting inventory",
            relative_path=relative_path,
        )

    connection.commit()

    return {
        "end_count": end_count,
        "added_count": added_count,
        "missing_count": missing_count,
        "reconciled": added_count == 0 and missing_count == 0,
    }


def validate_resource_budgets(
    max_source_bytes=None,
    max_runtime_seconds=None,
):
    """Reject invalid resource limits before starting an export."""
    for name, value in (
        ("max_source_bytes", max_source_bytes),
        ("max_runtime_seconds", max_runtime_seconds),
    ):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 < value < float("inf")
        ):
            raise ValueError(f"{name} must be a positive finite number")


def validate_export_inventory(
    connection,
    source_root,
    files_handle,
    exception_handle,
    max_source_bytes=None,
    max_runtime_seconds=None,
):
    """
    Validate starting-inventory files and stream their results.

    Every validation failure creates a blocking exception.
    The caller owns output handles and transaction lifecycle.
    """
    validate_resource_budgets(
        max_source_bytes=max_source_bytes,
        max_runtime_seconds=max_runtime_seconds,
    )

    validated_count = 0
    failed_count = 0
    inspected_bytes = 0
    started = time.monotonic()

    for relative_path in iter_unvalidated_export_paths(connection):
        try:
            if (
                max_runtime_seconds is not None
                and time.monotonic() - started >= max_runtime_seconds
            ):
                raise RuntimeError("Validation runtime budget exceeded")

            candidate = Path(source_root) / relative_path
            candidate_bytes = candidate.lstat().st_size

            if (
                max_source_bytes is not None
                and inspected_bytes + candidate_bytes > max_source_bytes
            ):
                raise RuntimeError("Validation source-byte budget exceeded")

            inspected_bytes += candidate_bytes

            record = validate_source_file(
                source_root,
                relative_path,
            )

            write_jsonl_record(files_handle, record)

            mark_export_path_validated(
                connection,
                relative_path,
            )

            validated_count += 1

        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            failed_count += 1

            write_export_exception(
                exception_handle,
                category="file_validation_failed",
                message=f"{type(exc).__name__}: {exc}",
                relative_path=relative_path,
            )

    connection.commit()

    return {
        "validated_count": validated_count,
        "failed_count": failed_count,
        "all_validated": failed_count == 0,
    }


def evaluate_export_acceptance(
    connection,
    files_path,
    exceptions_path,
    start_count,
    reconciliation,
):
    """
    Independently evaluate Candidate C export acceptance.

    Fail closed on incomplete inventory, duplicate file records,
    unvalidated entries, or blocking exceptions.
    """
    reasons = []

    if not reconciliation.get("reconciled", False):
        reasons.append("Ending inventory does not match starting inventory")

    if reconciliation.get("end_count") != start_count:
        reasons.append("Starting and ending file counts differ")

    inventory_count = connection.execute(
        "SELECT COUNT(*) FROM export_inventory"
    ).fetchone()[0]

    if inventory_count != start_count:
        reasons.append(
            "SQLite inventory count differs from starting inventory"
        )

    unseen_end = connection.execute(
        "SELECT COUNT(*) FROM export_inventory WHERE seen_end != 1"
    ).fetchone()[0]

    if unseen_end:
        reasons.append(
            f"{unseen_end} starting inventory files absent from ending scan"
        )

    if reconciliation.get("added_count") != 0:
        reasons.append("Ending inventory contains added files")

    if reconciliation.get("missing_count") != 0:
        reasons.append("Ending inventory contains missing files")

    unvalidated = connection.execute(
        "SELECT COUNT(*) FROM export_inventory WHERE validated = 0"
    ).fetchone()[0]

    if unvalidated:
        reasons.append(f"{unvalidated} inventory files remain unvalidated")

    connection.execute(
        "CREATE TEMP TABLE IF NOT EXISTS acceptance_records "
        "(path TEXT PRIMARY KEY)"
    )
    connection.execute("DELETE FROM acceptance_records")

    record_count = 0

    for record in stream_jsonl_records(files_path):
        try:
            validate_manifest_file_record(record)
        except ValueError as exc:
            reasons.append(f"Invalid manifest record: {exc}")

        relative_path = record.get("relative_path")

        if not isinstance(relative_path, str):
            reasons.append("File record missing relative_path")
            continue

        try:
            connection.execute(
                "INSERT INTO acceptance_records(path) VALUES (?)",
                (relative_path,),
            )
        except sqlite3.IntegrityError:
            reasons.append(f"Duplicate file record: {relative_path}")

        record_count += 1

    if record_count != start_count:
        reasons.append(
            f"File record count {record_count} differs from "
            f"starting inventory {start_count}"
        )

    unmatched = connection.execute(
        "SELECT COUNT(*) FROM acceptance_records AS a "
        "LEFT JOIN export_inventory AS i ON a.path = i.path "
        "WHERE i.path IS NULL"
    ).fetchone()[0]

    if unmatched:
        reasons.append(
            f"{unmatched} file records absent from starting inventory"
        )

    missing_records = connection.execute(
        "SELECT COUNT(*) FROM export_inventory AS i "
        "LEFT JOIN acceptance_records AS a ON i.path = a.path "
        "WHERE a.path IS NULL"
    ).fetchone()[0]

    if missing_records:
        reasons.append(
            f"{missing_records} starting files lack manifest records"
        )

    exception_count = 0

    for record in stream_jsonl_records(exceptions_path):
        exception_count += 1
        if record.get("blocks_acceptance") is not True:
            reasons.append("Exception record lacks blocking flag")

    if exception_count:
        reasons.append(f"{exception_count} export exceptions recorded")

    return {
        "accepted": len(reasons) == 0,
        "reasons": reasons,
        "record_count": record_count,
        "exception_count": exception_count,
        "unvalidated_count": unvalidated,
    }


def validate_manifest_file_record(record):
    """
    Validate the structure and internal consistency of one
    Candidate C file-manifest record.

    This does not rehash source or destination bytes.
    """
    required = {
        "relative_path",
        "dataset",
        "partition_date",
        "instruments",
        "size_bytes",
        "sha256",
        "row_count",
        "row_groups",
    }

    if not isinstance(record, dict):
        raise ValueError("Manifest file record must be an object")

    if set(record) != required:
        missing = sorted(required - set(record))
        unexpected = sorted(set(record) - required)
        raise ValueError(
            f"Manifest fields mismatch: missing={missing}, "
            f"unexpected={unexpected}"
        )

    relative_path = record["relative_path"]

    if not isinstance(relative_path, str):
        raise ValueError("relative_path must be a string")

    dataset, partition_date = parse_canonical_path(relative_path)

    if record["dataset"] != dataset:
        raise ValueError("Manifest dataset/path mismatch")

    if record["partition_date"] != partition_date.isoformat():
        raise ValueError("Manifest date/path mismatch")

    instruments = record["instruments"]

    if (
        not isinstance(instruments, list)
        or not instruments
        or any(not isinstance(item, str) for item in instruments)
        or instruments != sorted(set(instruments))
        or not set(instruments).issubset(INSTRUMENTS)
    ):
        raise ValueError("Invalid manifest instruments")

    for field in ("size_bytes", "row_count", "row_groups"):
        value = record[field]

        if type(value) is not int or value <= 0:
            raise ValueError(
                f"{field} must be a positive integer"
            )

    digest = record["sha256"]

    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef"
               for character in digest)
    ):
        raise ValueError("Invalid SHA-256 digest format")

    return True


EXPORT_STATES = frozenset({
    "IN_PROGRESS",
    "VALIDATED",
    "ACCEPTED",
})

EXPORT_TRANSITIONS = {
    "IN_PROGRESS": frozenset({"VALIDATED"}),
    "VALIDATED": frozenset({"ACCEPTED"}),
    "ACCEPTED": frozenset(),
}


def initialize_export_state(connection):
    """Initialize an export as incomplete and not transferable."""
    connection.execute(
        "CREATE TABLE export_state ("
        "id INTEGER PRIMARY KEY CHECK (id = 1), "
        "state TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO export_state(id, state) VALUES (1, ?)",
        ("IN_PROGRESS",),
    )
    connection.commit()


def get_export_state(connection):
    """Return the current export lifecycle state."""
    row = connection.execute(
        "SELECT state FROM export_state WHERE id = 1"
    ).fetchone()

    if row is None or row[0] not in EXPORT_STATES:
        raise ValueError("Missing or invalid export lifecycle state")

    return row[0]


def transition_export_state(connection, expected, target):
    """Perform a guarded, one-way lifecycle transition."""
    if target not in EXPORT_TRANSITIONS.get(expected, frozenset()):
        raise ValueError(
            f"Forbidden export transition: {expected} -> {target}"
        )

    cursor = connection.execute(
        "UPDATE export_state SET state = ? "
        "WHERE id = 1 AND state = ?",
        (target, expected),
    )

    if cursor.rowcount != 1:
        connection.rollback()
        raise ValueError(
            "Export lifecycle state changed or is inconsistent"
        )

    connection.commit()
    return target


def build_export_seal(
    connection,
    files_path,
    exceptions_path,
    acceptance,
):
    """
    Build a versioned completion-seal payload.

    Caller must durably finalize JSONL files before invoking this.
    This function does not publish or authorize a transfer.
    """
    if get_export_state(connection) != "VALIDATED":
        raise ValueError("Export must be VALIDATED before sealing")

    if not isinstance(acceptance, dict):
        raise ValueError("Missing export acceptance result")

    if acceptance.get("accepted") is not True:
        raise ValueError("Cannot seal a rejected export")

    if type(acceptance.get("exception_count")) is not int:
        raise ValueError("Invalid exception count")

    if acceptance["exception_count"] != 0:
        raise ValueError("Cannot seal export with exceptions")

    record_count = acceptance.get("record_count")

    if type(record_count) is not int or record_count <= 0:
        raise ValueError("Invalid accepted record count")

    files_path = Path(files_path)
    exceptions_path = Path(exceptions_path)

    if not files_path.is_file() or files_path.is_symlink():
        raise ValueError("Missing or symlinked files ledger")

    if not exceptions_path.is_file() or exceptions_path.is_symlink():
        raise ValueError("Missing or symlinked exception ledger")

    if exceptions_path.stat().st_size != 0:
        raise ValueError("Exception ledger must be empty")

    return {
        "contract_version": CONTRACT_VERSION,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "seal_version": 1,
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
        "accepted": True,
        "record_count": record_count,
        "files_jsonl_sha256": sha256_file(files_path),
        "exceptions_jsonl_sha256": sha256_file(exceptions_path),
    }


def build_verified_export_seal(
    connection,
    files_path,
    exceptions_path,
    reconciliation,
):
    """
    Re-evaluate inventory acceptance before constructing a seal.

    This is not a complete durable publication protocol.
    """
    if get_export_state(connection) != "VALIDATED":
        raise ValueError("Export must be VALIDATED before sealing")

    if not isinstance(reconciliation, dict):
        raise ValueError("Missing inventory reconciliation")

    inventory_count = connection.execute(
        "SELECT COUNT(*) FROM export_inventory"
    ).fetchone()[0]

    if inventory_count <= 0:
        raise ValueError("Cannot seal an empty inventory")

    acceptance = evaluate_export_acceptance(
        connection,
        files_path,
        exceptions_path,
        start_count=inventory_count,
        reconciliation=reconciliation,
    )

    if acceptance["accepted"] is not True:
        raise ValueError(
            "Independent acceptance check failed: "
            + "; ".join(acceptance["reasons"][:10])
        )

    return build_export_seal(
        connection,
        files_path,
        exceptions_path,
        acceptance,
    )


def verify_manifest_file_bytes(root, record):
    """
    Independently verify one manifest file against actual bytes.

    This function verifies integrity, not scientific completeness.
    """
    validate_manifest_file_record(record)

    _, partition_date = parse_canonical_path(record["relative_path"])
    require_unsealed_h2_date(partition_date)

    root_input = Path(root)
    if root_input.is_symlink():
        raise ValueError("Verification root is symlinked")

    root = root_input.resolve()
    relative = Path(record["relative_path"])
    path = root / relative

    for index in range(1, len(relative.parts) + 1):
        component = root / Path(*relative.parts[:index])

        if component.is_symlink():
            raise ValueError("Symlink in verification path")

    if not path.resolve().is_relative_to(root):
        raise ValueError("Verification path escapes root")

    if not path.is_file():
        raise ValueError("Manifest file missing or not regular")

    before = file_identity(path)

    if before["size_bytes"] != record["size_bytes"]:
        raise ValueError("Manifest file size mismatch")

    digest = sha256_file(path)

    after = file_identity(path)

    if not stable_identity(before, after):
        raise ValueError("File changed during verification")

    if digest != record["sha256"]:
        raise ValueError("Manifest SHA-256 mismatch")

    return {
        "relative_path": record["relative_path"],
        "verified": True,
        "size_bytes": after["size_bytes"],
        "sha256": digest,
    }


def run_candidate_c_export_prototype(
    source_root,
    output_dir,
    max_files,
    max_source_bytes=None,
    max_runtime_seconds=None,
):
    """
    Development-only Candidate C export orchestration.

    No automatic resume, transfer, or production authorization.
    The output is not a published or transferable snapshot.
    """
    source_root = Path(source_root).resolve()
    output_dir = Path(output_dir).absolute()

    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("Export output directory already exists")

    if output_dir == source_root:
        raise ValueError("Export output cannot equal source root")

    if output_dir.is_relative_to(source_root):
        raise ValueError("Export output cannot be inside source root")

    if not isinstance(max_files, int) or isinstance(max_files, bool):
        raise ValueError("max_files must be a positive integer")

    if max_files <= 0:
        raise ValueError("max_files must be a positive integer")

    validate_resource_budgets(
        max_source_bytes=max_source_bytes,
        max_runtime_seconds=max_runtime_seconds,
    )

    output_dir.mkdir(parents=True, exist_ok=False)

    database_path = output_dir / "inventory.sqlite3"
    files_path = output_dir / "files.jsonl"
    exceptions_path = output_dir / "exceptions.jsonl"

    connection = sqlite3.connect(database_path)

    try:
        initialize_export_state(connection)

        start_count = initialize_export_inventory(
            connection,
            source_root,
            max_files,
        )

        with (
            files_path.open("x", encoding="utf-8") as files_handle,
            exceptions_path.open("x", encoding="utf-8")
            as exceptions_handle,
        ):
            validation = validate_export_inventory(
                connection,
                source_root,
                files_handle,
                exceptions_handle,
                max_source_bytes=max_source_bytes,
                max_runtime_seconds=max_runtime_seconds,
            )

            reconciliation = reconcile_export_inventory(
                connection,
                source_root,
                max_files,
                exceptions_handle,
            )

            files_handle.flush()
            os.fsync(files_handle.fileno())
            exceptions_handle.flush()
            os.fsync(exceptions_handle.fileno())

        acceptance = evaluate_export_acceptance(
            connection,
            files_path,
            exceptions_path,
            start_count,
            reconciliation,
        )

        result = {
            "prototype": True,
            "transfer_authorized": False,
            "source_root": str(source_root),
            "output_dir": str(output_dir),
            "start_count": start_count,
            "validation": validation,
            "reconciliation": reconciliation,
            "acceptance": acceptance,
            "seal": None,
        }

        if not acceptance["accepted"]:
            return result

        transition_export_state(
            connection,
            "IN_PROGRESS",
            "VALIDATED",
        )

        result["seal"] = build_verified_export_seal(
            connection,
            files_path,
            exceptions_path,
            reconciliation,
        )

        return result

    finally:
        connection.close()


def publish_candidate_c_prototype(
    connection,
    output_dir,
    seal,
    source_root,
):
    """
    Publish a validated synthetic-development export.

    This does not authorize production transfer or scientific use.
    """
    output_dir = Path(output_dir)

    if not output_dir.is_dir() or output_dir.is_symlink():
        raise ValueError("Invalid export directory")

    if get_export_state(connection) != "VALIDATED":
        raise ValueError("Export must be VALIDATED before publication")

    if not isinstance(seal, dict):
        raise ValueError("Missing export seal")

    if seal.get("accepted") is not True:
        raise ValueError("Cannot publish an unaccepted seal")

    files_path = output_dir / "files.jsonl"
    exceptions_path = output_dir / "exceptions.jsonl"
    manifest_path = output_dir / "manifest.json"
    temporary_path = output_dir / "manifest.json.tmp"
    completion_path = output_dir / "COMPLETE"

    for path in (manifest_path, temporary_path, completion_path):
        if path.exists() or path.is_symlink():
            raise ValueError(f"Publication artifact already exists: {path.name}")

    if sha256_file(files_path) != seal["files_jsonl_sha256"]:
        raise ValueError("Files ledger changed before publication")

    if sha256_file(exceptions_path) != seal["exceptions_jsonl_sha256"]:
        raise ValueError("Exception ledger changed before publication")

    payload = {
        **manifest_header(source_root),
        "publication": seal,
        "prototype": True,
        "transfer_authorized": False,
    }

    encoded = (
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    with temporary_path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary_path, manifest_path)

    with manifest_path.open("rb") as handle:
        if handle.read() != encoded:
            raise ValueError("Published manifest verification failed")

    marker = {
        "manifest_sha256": sha256_file(manifest_path),
        "prototype": True,
        "transfer_authorized": False,
    }

    completion_tmp = output_dir / "COMPLETE.tmp"
    if completion_tmp.exists() or completion_tmp.is_symlink():
        raise ValueError("Temporary completion marker already exists")

    with completion_tmp.open("x", encoding="utf-8") as handle:
        json.dump(marker, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    directory_fd = os.open(output_dir, os.O_RDONLY)
    try:
        os.fsync(directory_fd)

        transition_export_state(
            connection,
            "VALIDATED",
            "ACCEPTED",
        )

        os.replace(completion_tmp, completion_path)
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)

    return {
        "manifest_path": str(manifest_path),
        "completion_path": str(completion_path),
        "state": get_export_state(connection),
        "transfer_authorized": False,
    }


def verify_published_candidate_c_prototype(
    output_dir,
    expected_source_root,
):
    """
    Independently verify a completed Candidate C prototype publication.

    Reads the manifest, completion marker, ledgers, SQLite inventory,
    and source bytes. Does not authorize transfer or scientific use.
    """
    output_dir = Path(output_dir)
    source_input = Path(expected_source_root)

    if output_dir.is_symlink() or not output_dir.is_dir():
        raise ValueError("Invalid publication directory")

    if source_input.is_symlink() or not source_input.is_dir():
        raise ValueError("Invalid expected source root")

    source_root = source_input.resolve()

    names = (
        "manifest.json",
        "COMPLETE",
        "files.jsonl",
        "exceptions.jsonl",
        "inventory.sqlite3",
    )

    for name in names:
        path = output_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or symlinked publication artifact: {name}")

    for name in ("manifest.json.tmp", "COMPLETE.tmp"):
        path = output_dir / name
        if path.exists() or path.is_symlink():
            raise ValueError(f"Unfinished publication artifact: {name}")

    manifest_path = output_dir / "manifest.json"
    marker_path = output_dir / "COMPLETE"
    files_path = output_dir / "files.jsonl"
    exceptions_path = output_dir / "exceptions.jsonl"
    database_path = output_dir / "inventory.sqlite3"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))

    if not isinstance(manifest, dict) or not isinstance(marker, dict):
        raise ValueError("Invalid publication metadata")

    if set(marker) != {
        "manifest_sha256", "prototype", "transfer_authorized"
    }:
        raise ValueError("Unexpected completion-marker fields")

    if marker["prototype"] is not True:
        raise ValueError("Publication is not a prototype")

    if marker["transfer_authorized"] is not False:
        raise ValueError("Transfer authorization must remain false")

    if marker["manifest_sha256"] != sha256_file(manifest_path):
        raise ValueError("Completion-marker manifest hash mismatch")

    expected_header = manifest_header(source_root)
    expected_header.pop("inventory_started_utc")

    for key, expected in expected_header.items():
        if manifest.get(key) != expected:
            raise ValueError(f"Manifest header mismatch: {key}")

    if not isinstance(manifest.get("inventory_started_utc"), str):
        raise ValueError("Missing inventory timestamp")

    if manifest.get("prototype") is not True:
        raise ValueError("Manifest is not marked prototype")

    if manifest.get("transfer_authorized") is not False:
        raise ValueError("Manifest transfer authorization is invalid")

    seal = manifest.get("publication")

    if not isinstance(seal, dict):
        raise ValueError("Missing publication seal")

    expected_seal_fields = {
        "contract_version",
        "manifest_schema_version",
        "seal_version",
        "export_classification",
        "point_in_time_complete",
        "accepted",
        "record_count",
        "files_jsonl_sha256",
        "exceptions_jsonl_sha256",
    }

    if set(seal) != expected_seal_fields:
        raise ValueError("Unexpected publication seal fields")

    if (
        seal["contract_version"] != CONTRACT_VERSION
        or seal["manifest_schema_version"] != MANIFEST_SCHEMA_VERSION
        or seal["seal_version"] != 1
        or seal["export_classification"] != "legacy_reconciled"
        or seal["point_in_time_complete"] is not False
        or seal["accepted"] is not True
        or type(seal["record_count"]) is not int
        or seal["record_count"] <= 0
    ):
        raise ValueError("Invalid publication seal")

    if sha256_file(files_path) != seal["files_jsonl_sha256"]:
        raise ValueError("Files ledger hash mismatch")

    if sha256_file(exceptions_path) != seal["exceptions_jsonl_sha256"]:
        raise ValueError("Exception ledger hash mismatch")

    if exceptions_path.stat().st_size != 0:
        raise ValueError("Blocking export exceptions exist")

    connection = sqlite3.connect(
        f"file:{database_path.resolve()}?mode=ro",
        uri=True,
    )

    try:
        if get_export_state(connection) != "ACCEPTED":
            raise ValueError("Export lifecycle is not ACCEPTED")

        inventory_count = connection.execute(
            "SELECT COUNT(*) FROM export_inventory"
        ).fetchone()[0]

        incomplete_count = connection.execute(
            "SELECT COUNT(*) FROM export_inventory "
            "WHERE validated != 1 OR seen_end != 1"
        ).fetchone()[0]

        if incomplete_count:
            raise ValueError("Inventory contains incomplete entries")

        if inventory_count != seal["record_count"]:
            raise ValueError("Inventory count differs from seal")

        connection.execute(
            "CREATE TEMP TABLE verification_paths "
            "(path TEXT PRIMARY KEY)"
        )

        verified = 0

        for record in stream_jsonl_records(files_path):
            validate_manifest_file_record(record)

            relative_path = record["relative_path"]

            try:
                connection.execute(
                    "INSERT INTO verification_paths(path) VALUES (?)",
                    (relative_path,),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    "Duplicate manifest file record"
                ) from exc

            row = connection.execute(
                "SELECT validated, seen_end FROM export_inventory "
                "WHERE path = ?",
                (relative_path,),
            ).fetchone()

            if row != (1, 1):
                raise ValueError("Manifest file absent from accepted inventory")

            verify_manifest_file_bytes(source_root, record)
            verified += 1

        if verified != inventory_count:
            raise ValueError("Manifest records do not cover inventory")

    finally:
        connection.close()

    return {
        "verified": True,
        "prototype": True,
        "transfer_authorized": False,
        "record_count": verified,
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
    }


def inspect_candidate_c_publication(output_dir, expected_source_root):
    """
    Classify a Candidate C prototype publication without modifying it.

    COMPLETE requires independent verification of all evidence.
    Other classifications are never authorization to recover, transfer,
    or promote the export.
    """
    output_dir = Path(output_dir)

    if output_dir.is_symlink() or not output_dir.is_dir():
        return {
            "classification": "INVALID",
            "verified": False,
            "reason": "Invalid publication directory",
        }

    manifest = output_dir / "manifest.json"
    complete = output_dir / "COMPLETE"
    manifest_tmp = output_dir / "manifest.json.tmp"
    complete_tmp = output_dir / "COMPLETE.tmp"

    if any(
        path.exists() or path.is_symlink()
        for path in (manifest_tmp, complete_tmp)
    ):
        return {
            "classification": "INTERRUPTED",
            "verified": False,
            "reason": "Unfinished publication artifacts exist",
        }

    if not complete.exists() and manifest.exists():
        return {
            "classification": "INTERRUPTED",
            "verified": False,
            "reason": "Manifest exists without completion marker",
        }

    if not complete.exists():
        return {
            "classification": "INCOMPLETE",
            "verified": False,
            "reason": "Completion marker absent",
        }

    try:
        result = verify_published_candidate_c_prototype(
            output_dir,
            expected_source_root,
        )
    except (ValueError, OSError, sqlite3.DatabaseError, KeyError, TypeError) as exc:
        return {
            "classification": "INVALID",
            "verified": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }

    return {
        "classification": "COMPLETE",
        "verified": True,
        "reason": "Independent verification passed",
        "record_count": result["record_count"],
        "transfer_authorized": False,
    }


def verify_candidate_c_destination(
    output_dir,
    expected_source_root,
    destination_root,
):
    """
    Verify an independently supplied destination against a completed
    Candidate C prototype export.

    Read-only. Never copies files or authorizes transfer.
    """
    source_result = verify_published_candidate_c_prototype(
        output_dir,
        expected_source_root,
    )

    destination_input = Path(destination_root)

    if destination_input.is_symlink() or not destination_input.is_dir():
        raise ValueError("Invalid destination root")

    destination = destination_input.resolve()
    source = Path(expected_source_root).resolve()
    export = Path(output_dir).resolve()

    if destination == source or destination == export:
        raise ValueError("Destination must be separate from source and export")

    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Destination overlaps canonical source")

    if destination.is_relative_to(export) or export.is_relative_to(destination):
        raise ValueError("Destination overlaps export directory")

    files_path = Path(output_dir) / "files.jsonl"

    with tempfile.TemporaryDirectory(
        prefix="lrs3-destination-verify-"
    ) as temporary_directory:
        connection = sqlite3.connect(
            Path(temporary_directory) / "expected_files.sqlite3"
        )

        try:
            connection.execute(
                "CREATE TABLE expected_files (path TEXT PRIMARY KEY)"
            )

            verified = 0

            for record in stream_jsonl_records(files_path):
                validate_manifest_file_record(record)
                relative_path = record["relative_path"]

                try:
                    connection.execute(
                        "INSERT INTO expected_files(path) VALUES (?)",
                        (relative_path,),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError("Duplicate destination record") from exc

                verify_manifest_file_bytes(destination, record)
                verified += 1

            observed = 0

            for dataset in sorted(DATASETS):
                dataset_dir = destination / dataset

                if not dataset_dir.is_dir() or dataset_dir.is_symlink():
                    raise ValueError(f"Missing destination dataset: {dataset}")

                for partition in dataset_dir.iterdir():
                    if partition.is_symlink() or not partition.is_dir():
                        raise ValueError("Invalid destination partition")

                    if not partition.name.startswith("date="):
                        raise ValueError("Unexpected destination partition name")

                    try:
                        partition_date = date.fromisoformat(
                            partition.name.removeprefix("date=")
                        )
                    except ValueError as exc:
                        raise ValueError(
                            "Invalid destination partition date"
                        ) from exc

                    if (
                        partition.name != f"date={partition_date.isoformat()}"
                        or not START_DATE <= partition_date <= END_DATE
                    ):
                        raise ValueError(
                            "Destination partition outside contract"
                        )

                    for entry in partition.iterdir():
                        if entry.is_symlink() or not entry.is_file():
                            raise ValueError("Unexpected destination entry")

                        relative = entry.relative_to(destination).as_posix()

                        match = connection.execute(
                            "SELECT 1 FROM expected_files WHERE path = ?",
                            (relative,),
                        ).fetchone()

                        if match is None:
                            raise ValueError(
                                f"Unexpected destination file: {relative}"
                            )

                        observed += 1

            for entry in destination.iterdir():
                if entry.name not in DATASETS:
                    raise ValueError(
                        f"Unexpected destination top-level entry: {entry.name}"
                    )

            if observed != verified:
                raise ValueError("Destination inventory count mismatch")

        finally:
            connection.close()

    return {
        "verified": True,
        "record_count": verified,
        "source_verified": source_result["verified"],
        "destination_verified": True,
        "prototype": True,
        "transfer_authorized": False,
    }
