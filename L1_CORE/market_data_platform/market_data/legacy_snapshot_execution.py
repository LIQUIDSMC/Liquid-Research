
"""Synthetic-only C-003 execution authorization and identity gate.

No production transfer, recovery, completion, or historical-time attestation.
"""

import hashlib
import json
from pathlib import Path

import legacy_snapshot_authorization as authorization
import legacy_snapshot_journal as journal
import legacy_snapshot_manifest as manifest
import legacy_snapshot_staging as staging
import legacy_snapshot_state as state


def verify_execution_gate(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
    expected_source_root,
    now=None,
):
    """Verify externally anchored identity before any payload acceptance.

    Caller expectations are independent inputs. Never derive them from
    identity.json or from the authorization files being verified.
    """
    root = staging._safe_directory(staging_root)

    # Caller-supplied expectations are checked before durable records.
    manifest._digest(expected_manifest_sha256)
    manifest._authorization_structure(
        expected_authorizations, expected_request_id
    )

    # A mismatched caller expectation is a rejection, not proof of corruption.
    staging.verify_staging_identity(
        root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )

    # A terminal state is never writable.
    state.require_bound_incomplete(
        root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )

    # Recompute authorization identities from the actual authorization bytes.
    # Share the destination verifier's canonical authorization paths.
    # The staging root is the authorization destination for this attempt;
    # this does not classify staging as a completed destination.
    paths = {}
    for segment, relative in manifest.AUTHORIZATION_EVIDENCE_PATHS.items():
        candidate = root
        for component in Path(relative).parts:
            candidate = candidate / component
            if candidate.is_symlink():
                raise ValueError("Symlinked authorization evidence")
        if not candidate.is_file():
            raise ValueError("Missing authorization evidence")
        paths[segment] = candidate

    pair = authorization.validate_pair(
        paths["NON_H2"],
        paths["H2"],
        expected_source_root,
        str(root.resolve()),
        now=now,
        historical=False,
    )

    if pair != expected_authorizations:
        raise PermissionError(
            "Execution authorization identities differ from external anchor"
        )

    if pair["snapshot_request_id"] != expected_request_id:
        raise PermissionError("Execution snapshot request mismatch")

    # The sealed manifest must independently bind the same authorization pair.
    raw = journal._read_regular(root, "manifest.json")
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise PermissionError("Sealed manifest differs from external anchor")

    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError("Invalid sealed manifest")

    if document.get("snapshot_request_id") != expected_request_id:
        raise PermissionError("Sealed manifest request mismatch")

    if document.get("authorizations") != pair:
        raise PermissionError("Sealed manifest authorization mismatch")

    # Validate the complete sealed inventory structure before returning.
    journal._sealed_manifest_inventory(root, expected_manifest_sha256)

    return {
        "execution_gate_verified": True,
        "staging_attempt_id": expected_attempt_id,
        "snapshot_request_id": expected_request_id,
        "authorization_binding": "RECOMPUTED_AND_MATCHED",
        "attempt_state": "INCOMPLETE",
        "production_transfer_authorized": False,
        "historical_timing_attestation": "UNATTESTED",
        "scientific_readiness": "PENDING",
    }



def _verify_committed_payloads_or_fail_lock_held(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
):
    """Verify committed payload bytes; publish FAILED on proven corruption.

    This does not implement recovery or general corruption classification.
    The caller must hold the attempt lock and first pass
    verify_execution_gate().
    """
    root = staging._safe_directory(staging_root)
    checkpoint = json.loads(journal._read_regular(root, "checkpoint.json"))

    if not isinstance(checkpoint, dict) or set(checkpoint) != journal.CHECKPOINT_FIELDS:
        raise ValueError("Malformed checkpoint; recovery/audit required")
    if checkpoint["staging_attempt_id"] != expected_attempt_id:
        raise PermissionError("Checkpoint attempt mismatch")

    count = checkpoint["committed_sequence"]
    if type(count) is not int or count < 0:
        raise ValueError("Invalid committed checkpoint sequence")

    lines = journal._read_regular(root, "journal.jsonl").splitlines(keepends=True)
    if len(lines) != count:
        raise ValueError("Journal/checkpoint mismatch; recovery/audit required")

    previous = journal.ZERO_DIGEST
    entries = []
    seen = set()

    # Establish the committed chain before attributing any payload mismatch
    # to durable corruption. Ambiguous journal failures do not mutate state.
    for sequence, line in enumerate(lines, start=1):
        if not line.endswith(bytes([10])):
            raise ValueError("Unterminated committed journal")
        entry = json.loads(line)
        relative = journal._validate_entry(entry, sequence, previous)
        if relative in seen:
            raise ValueError("Duplicate committed journal path")
        seen.add(relative)
        entries.append((relative, entry))
        previous = entry["entry_digest"]

    if checkpoint["committed_digest"] != previous:
        raise ValueError("Checkpoint chain mismatch")

    inventory = journal._sealed_manifest_inventory(
        root, expected_manifest_sha256
    )

    for relative, entry in entries:
        record = inventory.get(relative)
        if record is None or (
            record["size_bytes"] != entry["size_bytes"]
            or record["sha256"] != entry["sha256"]
        ):
            state._publish_bound_state_lock_held(
                root,
                expected_attempt_id=expected_attempt_id,
                expected_request_id=expected_request_id,
                expected_manifest_sha256=expected_manifest_sha256,
                expected_authorizations=expected_authorizations,
                new_state="FAILED",
            )
            raise ValueError(
                "Confirmed committed manifest contradiction; attempt FAILED"
            )

        # A missing, symlinked, or unreadable file remains an ambiguous
        # operational failure here; do not automatically poison the attempt.
        candidate = root / "payload"
        if candidate.is_symlink():
            raise ValueError("Symlinked committed payload root")
        for component in Path(relative).parts:
            candidate = candidate / component
            if candidate.is_symlink():
                raise ValueError("Symlinked committed payload")
        if not candidate.is_file():
            raise ValueError("Missing committed payload")

        raw = candidate.read_bytes()
        if (
            len(raw) != entry["size_bytes"]
            or hashlib.sha256(raw).hexdigest() != entry["sha256"]
        ):
            state._publish_bound_state_lock_held(
                root,
                expected_attempt_id=expected_attempt_id,
                expected_request_id=expected_request_id,
                expected_manifest_sha256=expected_manifest_sha256,
                expected_authorizations=expected_authorizations,
                new_state="FAILED",
            )
            raise ValueError(
                "Confirmed committed payload corruption; attempt FAILED"
            )

    return {
        "committed_payloads_verified": len(entries),
        "attempt_state": "INCOMPLETE",
        "scientific_readiness": "PENDING",
    }



from legacy_snapshot_lock import exclusive_attempt_lock


@exclusive_attempt_lock
def verify_committed_payloads_or_fail(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
):
    """Serialize verification and any FAILED transition.

    The caller must first pass verify_execution_gate().
    """
    return _verify_committed_payloads_or_fail_lock_held(
        staging_root,
        expected_attempt_id=expected_attempt_id,
        expected_request_id=expected_request_id,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_authorizations=expected_authorizations,
    )


@exclusive_attempt_lock
def recover_authorized_single_suffix(
    staging_root,
    *,
    expected_attempt_id,
    expected_request_id,
    expected_manifest_sha256,
    expected_authorizations,
    expected_source_root,
    now=None,
):
    """Recover one verified synthetic journal suffix.

    Advances checkpoint only. No journal append, payload copy, or COMPLETE.
    Single-process synthetic development; concurrent mutation unsupported.
    """
    gate = {
        "expected_attempt_id": expected_attempt_id,
        "expected_request_id": expected_request_id,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_authorizations": expected_authorizations,
        "expected_source_root": expected_source_root,
        "now": now,
    }

    root = staging._safe_directory(staging_root)

    verify_execution_gate(root, **gate)

    assessment = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=expected_attempt_id,
        expected_manifest_sha256=expected_manifest_sha256,
    )

    if assessment["recovery_status"] != "RECOVERABLE_SINGLE_SUFFIX":
        raise ValueError("No recoverable single suffix")

    verify_execution_gate(root, **gate)

    repeated = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=expected_attempt_id,
        expected_manifest_sha256=expected_manifest_sha256,
    )

    if repeated != assessment:
        raise ValueError("Recovery assessment changed before publication")

    checkpoint = {
        "journal_version": journal.JOURNAL_VERSION,
        "staging_attempt_id": expected_attempt_id,
        "committed_sequence": assessment["recovered_sequence_candidate"],
        "committed_digest": assessment["recovered_digest_candidate"],
    }

    journal._atomic_checkpoint(root, checkpoint)

    verified, _ = journal._verify_committed_manifest_binding(
        root,
        expected_attempt_id=expected_attempt_id,
        expected_manifest_sha256=expected_manifest_sha256,
    )

    if verified["committed_sequence"] != checkpoint["committed_sequence"]:
        raise ValueError("Recovered checkpoint verification failed")

    return {
        "recovery_status": "RECOVERED_SINGLE_SUFFIX",
        "committed_sequence": checkpoint["committed_sequence"],
        "journal_modified": False,
        "payload_modified": False,
        "checkpoint_modified": True,
        "attempt_state": "INCOMPLETE",
        "production_transfer_authorized": False,
        "historical_timing_attestation": "UNATTESTED",
        "scientific_readiness": "PENDING",
        "durability_attestation": "FAULT_INJECTION_ONLY, NOT_HARDWARE_VERIFIED",
    }
