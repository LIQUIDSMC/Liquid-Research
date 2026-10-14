"""Synthetic-only C-003 committed acceptance journal verification.

Read-only foundation. No append, checkpoint update, recovery, or transfer API.
Local checkpoint consistency is NOT authenticated rollback protection.
"""

import hashlib
import json
from pathlib import Path

import legacy_snapshot_manifest as manifest
import legacy_snapshot_staging as staging


JOURNAL_VERSION = 1
ZERO_DIGEST = "0" * 64
ENTRY_FIELDS = {
    "sequence", "relative_path", "size_bytes", "sha256",
    "previous_digest", "entry_digest",
}
CHECKPOINT_FIELDS = {
    "journal_version", "staging_attempt_id",
    "committed_sequence", "committed_digest",
}


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _entry_digest(entry):
    unsigned = {key: value for key, value in entry.items()
                if key != "entry_digest"}
    return hashlib.sha256(_canonical(unsigned)).hexdigest()


def _read_regular(root, relative):
    candidate = root
    for part in Path(relative).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Symlinked staging journal component")
    if not candidate.is_file():
        raise ValueError(f"Missing staging journal component: {relative}")
    return candidate.read_bytes()


def _validate_entry(entry, sequence, previous_digest):
    if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
        raise ValueError("Invalid acceptance entry schema")
    if type(entry["sequence"]) is not int or entry["sequence"] != sequence:
        raise ValueError("Acceptance journal sequence mismatch")
    relative = manifest._relative(entry["relative_path"]).as_posix()
    if relative in {"identity.json", "checkpoint.json", "journal.jsonl"}:
        raise ValueError("Staging metadata cannot be accepted as payload")
    if type(entry["size_bytes"]) is not int or entry["size_bytes"] <= 0:
        raise ValueError("Invalid accepted file size")
    manifest._digest(entry["sha256"])
    manifest._digest(entry["previous_digest"])
    manifest._digest(entry["entry_digest"])
    if entry["previous_digest"] != previous_digest:
        raise ValueError("Acceptance journal chain mismatch")
    if entry["entry_digest"] != _entry_digest(entry):
        raise ValueError("Acceptance journal digest mismatch")
    return relative


def verify_committed_journal(staging_root, *, expected_attempt_id):
    """Verify committed prefix and accepted bytes; never infer completion.

    Uncommitted suffix recovery is intentionally NOT implemented here.
    Any suffix causes rejection until the separate recovery increment.
    """
    root = staging._safe_directory(staging_root)
    raw_checkpoint = _read_regular(root, "checkpoint.json")
    checkpoint = json.loads(raw_checkpoint)
    if not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_FIELDS:
        raise ValueError("Invalid checkpoint schema")
    if type(checkpoint["journal_version"]) is not int or (
        checkpoint["journal_version"] != JOURNAL_VERSION
    ):
        raise ValueError("Invalid checkpoint version")
    if checkpoint["staging_attempt_id"] != expected_attempt_id:
        raise PermissionError("Checkpoint staging attempt mismatch")
    sequence = checkpoint["committed_sequence"]
    if type(sequence) is not int or sequence < 0:
        raise ValueError("Invalid committed sequence")
    manifest._digest(checkpoint["committed_digest"])

    raw_journal = _read_regular(root, "journal.jsonl")
    lines = raw_journal.splitlines(keepends=True)
    if len(lines) != sequence:
        raise ValueError("Journal length differs from committed checkpoint")

    previous = ZERO_DIGEST
    accepted = set()
    for index, line in enumerate(lines, start=1):
        if not line.endswith(b"\n"):
            raise ValueError("Nonterminated committed journal entry")
        entry = json.loads(line)
        relative = _validate_entry(entry, index, previous)
        if relative in accepted:
            raise ValueError("Duplicate accepted destination path")
        accepted.add(relative)
        previous = entry["entry_digest"]
        manifest._verified_file(
            root / "payload",
            {
                "relative_path": relative,
                "size_bytes": entry["size_bytes"],
                "sha256": entry["sha256"],
            },
            manifest.EVIDENCE_FIELDS,
        )

    if checkpoint["committed_digest"] != previous:
        raise ValueError("Checkpoint digest differs from committed journal")

    return {
        "committed_files_verified": len(accepted),
        "committed_sequence": sequence,
        "rollback_attestation": "UNATTESTED",
        "historical_timing_attestation": "UNATTESTED",
        "scientific_readiness": "PENDING",
    }


def _sync_directory(directory):
    """Synchronize directory metadata after atomic replacement."""
    import os

    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_checkpoint(root, checkpoint, *, fault_boundary=None):
    """Publish a synchronized checkpoint using atomic replacement."""
    import os
    import uuid

    temporary = root / f".checkpoint-{uuid.uuid4().hex}.tmp"

    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical(checkpoint) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())

        if fault_boundary == "AFTER_TEMP_FSYNC":
            raise RuntimeError("Injected failure after checkpoint temp fsync")

        os.replace(temporary, root / "checkpoint.json")

        if fault_boundary == "AFTER_REPLACE":
            raise RuntimeError("Injected failure after checkpoint replace")

        _sync_directory(root)
    finally:
        if temporary.exists():
            temporary.unlink()


def _sealed_manifest_inventory(root, expected_manifest_sha256):
    """Load payload inventory from an externally anchored sealed manifest.

    Evidence records are never eligible for snapshot payload acceptance.
    """
    manifest._digest(expected_manifest_sha256)
    raw = _read_regular(root, "manifest.json")

    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError("External manifest SHA-256 mismatch")

    document = json.loads(raw)

    if not isinstance(document, dict) or set(document) != manifest.MANIFEST_FIELDS:
        raise ValueError("Sealed manifest schema mismatch")

    if type(document["manifest_schema_version"]) is not int or (
        document["manifest_schema_version"] != manifest.SCHEMA_VERSION
    ):
        raise ValueError("Sealed manifest version mismatch")

    manifest._authorization_structure(
        document["authorizations"],
        document["snapshot_request_id"],
    )

    if not isinstance(document["files"], list):
        raise ValueError("Invalid sealed payload inventory")

    if not isinstance(document["component_evidence"], list):
        raise ValueError("Invalid sealed evidence inventory")

    payload = {}
    evidence = set()

    for record in document["files"]:
        if not isinstance(record, dict) or set(record) != manifest.FILE_FIELDS:
            raise ValueError("Invalid sealed payload record")

        name = manifest._relative(record["relative_path"]).as_posix()

        if name in payload:
            raise ValueError("Duplicate sealed payload path")

        if type(record["size_bytes"]) is not int or record["size_bytes"] <= 0:
            raise ValueError("Invalid sealed payload size")

        manifest._digest(record["sha256"])
        payload[name] = record

    for record in document["component_evidence"]:
        if not isinstance(record, dict) or set(record) != manifest.EVIDENCE_FIELDS:
            raise ValueError("Invalid sealed evidence record")

        name = manifest._relative(record["relative_path"]).as_posix()

        if name in evidence or name in payload:
            raise ValueError("Duplicate or ambiguous sealed inventory path")

        evidence.add(name)

    return payload


def _verify_committed_manifest_binding(
    root,
    *,
    expected_attempt_id,
    expected_manifest_sha256,
):
    """Verify committed journal ↔ payload ↔ externally sealed manifest."""
    inventory = _sealed_manifest_inventory(root, expected_manifest_sha256)

    verified = verify_committed_journal(
        root,
        expected_attempt_id=expected_attempt_id,
    )

    for line in _read_regular(root, "journal.jsonl").splitlines():
        entry = json.loads(line)
        relative = entry["relative_path"]

        if relative not in inventory:
            raise ValueError("Committed journal path absent from sealed files")

        expected = inventory[relative]

        if (
            entry["size_bytes"] != expected["size_bytes"]
            or entry["sha256"] != expected["sha256"]
        ):
            raise ValueError("Committed journal differs from sealed manifest")

    return verified, inventory


def _accept_manifest_file_unchecked(
    staging_root,
    *,
    expected_attempt_id,
    expected_manifest_sha256,
    relative_path,
    fault_after_journal_fsync=False,
    fault_boundary=None,
):
    """Accept an existing synthetic payload into the committed journal.

    Preconditions:
      - Caller provides the externally anchored manifest digest.
      - Staging identity and authorization are NOT established here.
      - Caller must separately enforce current execution authorization.
      - Recovery of an uncommitted suffix is NOT supported here.

    No production transfer or completion is authorized.
    """
    import os

    root = staging._safe_directory(staging_root)
    relative = manifest._relative(relative_path).as_posix()

    if relative in {
        "identity.json",
        "journal.jsonl",
        "checkpoint.json",
        "manifest.json",
    }:
        raise PermissionError("Staging metadata cannot be accepted as payload")

    verified, inventory = _verify_committed_manifest_binding(
        root,
        expected_attempt_id=expected_attempt_id,
        expected_manifest_sha256=expected_manifest_sha256,
    )

    if relative not in inventory:
        raise PermissionError("File absent from sealed files inventory")

    expected = inventory[relative]

    # Confirm the expected record itself has a valid size/digest.
    if type(expected["size_bytes"]) is not int or expected["size_bytes"] <= 0:
        raise ValueError("Invalid sealed manifest file size")
    manifest._digest(expected["sha256"])

    # Never trust a caller-provided digest as acceptance authority.
    manifest._verified_file(
        root / "payload",
        {
            "relative_path": relative,
            "size_bytes": expected["size_bytes"],
            "sha256": expected["sha256"],
        },
        manifest.EVIDENCE_FIELDS,
    )

    # Existing committed entries were independently bound to the manifest.
    checkpoint = json.loads(_read_regular(root, "checkpoint.json"))
    sequence = verified["committed_sequence"] + 1

    # Reject duplicate acceptance before mutating the journal.
    for line in _read_regular(root, "journal.jsonl").splitlines():
        entry = json.loads(line)
        if entry["relative_path"] == relative:
            raise ValueError("Payload already accepted")

    entry = {
        "sequence": sequence,
        "relative_path": relative,
        "size_bytes": expected["size_bytes"],
        "sha256": expected["sha256"],
        "previous_digest": checkpoint["committed_digest"],
    }
    entry["entry_digest"] = _entry_digest(entry)

    journal_path = root / "journal.jsonl"

    # The read-only verifier has already rejected symlinked journal paths.
    with journal_path.open("ab") as handle:
        handle.write(_canonical(entry) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())

    # Test-only failure boundary: checkpoint must still point to old prefix.
    if fault_after_journal_fsync:
        raise RuntimeError("Injected failure after journal fsync")

    new_checkpoint = {
        "journal_version": JOURNAL_VERSION,
        "staging_attempt_id": expected_attempt_id,
        "committed_sequence": sequence,
        "committed_digest": entry["entry_digest"],
    }

    _atomic_checkpoint(
        root,
        new_checkpoint,
        fault_boundary=fault_boundary,
    )

    return {
        "accepted_relative_path": relative,
        "committed_sequence": sequence,
        "rollback_attestation": "UNATTESTED",
        "historical_timing_attestation": "UNATTESTED",
        "durability_attestation": "FAULT_INJECTION_ONLY, NOT_HARDWARE_VERIFIED",
        "scientific_readiness": "PENDING",
    }


from legacy_snapshot_lock import exclusive_attempt_lock

@exclusive_attempt_lock
def accept_manifest_file(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
    expected_source_root,
    relative_path,
    now=None,
):
    """Public synthetic acceptance entry point.

    Mandatory externally anchored identity, current authorization, and
    attempt-state checks precede all journal mutation.

    No production transfer, recovery, or finalization is authorized.
    """
    import legacy_snapshot_execution as execution

    execution.verify_execution_gate(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
        expected_source_root=expected_source_root,
        now=now,
    )

    # Reject invalid caller paths before integrity-failure classification.
    relative = manifest._relative(relative_path).as_posix()
    if relative in {
        "identity.json", "manifest.json",
        "checkpoint.json", "journal.jsonl", "state.json",
    }:
        raise PermissionError("Staging metadata cannot be accepted")

    execution._verify_committed_payloads_or_fail_lock_held(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )

    return _accept_manifest_file_unchecked(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_manifest_sha256=expected_manifest_sha256,
        relative_path=relative,
    )



def assess_uncommitted_suffix(
    staging_root,
    *,
    expected_attempt_id,
    expected_manifest_sha256,
):
    """Read-only assessment; does not authorize or perform recovery.

    This function is an internal diagnostic primitive. Its result is
    not sufficient authority to mutate a checkpoint.
    """
    root = staging._safe_directory(staging_root)

    inventory = _sealed_manifest_inventory(
        root, expected_manifest_sha256
    )

    checkpoint = json.loads(_read_regular(root, "checkpoint.json"))

    if not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_FIELDS:
        raise ValueError("Invalid checkpoint schema")

    if (
        type(checkpoint["journal_version"]) is not int
        or checkpoint["journal_version"] != JOURNAL_VERSION
    ):
        raise ValueError("Invalid checkpoint version")

    if checkpoint["staging_attempt_id"] != expected_attempt_id:
        raise PermissionError("Checkpoint attempt mismatch")

    committed = checkpoint["committed_sequence"]

    if type(committed) is not int or committed < 0:
        raise ValueError("Invalid committed sequence")

    manifest._digest(checkpoint["committed_digest"])

    raw = _read_regular(root, "journal.jsonl")
    lines = raw.splitlines(keepends=True)

    if len(lines) < committed:
        raise ValueError("Checkpoint ahead of journal")

    previous = ZERO_DIGEST
    accepted = set()

    for index, line in enumerate(lines[:committed], start=1):
        if not line.endswith(bytes([10])):
            raise ValueError("Unterminated committed journal entry")

        entry = json.loads(line)
        relative = _validate_entry(entry, index, previous)

        if relative in accepted:
            raise ValueError("Duplicate committed destination")

        accepted.add(relative)
        previous = entry["entry_digest"]

        record = inventory.get(relative)

        if record is None or (
            record["size_bytes"] != entry["size_bytes"]
            or record["sha256"] != entry["sha256"]
        ):
            raise ValueError("Committed entry contradicts sealed manifest")

        manifest._verified_file(
            root / "payload",
            {
                "relative_path": relative,
                "size_bytes": entry["size_bytes"],
                "sha256": entry["sha256"],
            },
            manifest.EVIDENCE_FIELDS,
        )

    if previous != checkpoint["committed_digest"]:
        raise ValueError("Committed checkpoint digest mismatch")

    suffix = lines[committed:]

    if not suffix:
        return {
            "recovery_status": "NO_SUFFIX",
            "committed_sequence": committed,
            "suffix_entries": 0,
            "mutation_performed": False,
        }

    if len(suffix) != 1:
        raise ValueError("Recovery requires exactly one suffix entry")

    line = suffix[0]

    if not line.endswith(bytes([10])):
        raise ValueError("Incomplete uncommitted suffix")

    entry = json.loads(line)
    relative = _validate_entry(
        entry,
        committed + 1,
        previous,
    )

    if relative in accepted:
        raise ValueError("Duplicate suffix destination")

    record = inventory.get(relative)

    if record is None or (
        record["size_bytes"] != entry["size_bytes"]
        or record["sha256"] != entry["sha256"]
    ):
        raise ValueError("Suffix contradicts sealed manifest")

    manifest._verified_file(
        root / "payload",
        {
            "relative_path": relative,
            "size_bytes": entry["size_bytes"],
            "sha256": entry["sha256"],
        },
        manifest.EVIDENCE_FIELDS,
    )

    return {
        "recovery_status": "RECOVERABLE_SINGLE_SUFFIX",
        "committed_sequence": committed,
        "recovered_sequence_candidate": committed + 1,
        "recovered_digest_candidate": entry["entry_digest"],
        "relative_path": relative,
        "suffix_entries": 1,
        "mutation_performed": False,
        "scientific_readiness": "PENDING",
    }
