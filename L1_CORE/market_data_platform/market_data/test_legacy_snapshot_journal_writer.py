"""Synthetic-only tests for manifest-bound durable acceptance."""

import hashlib
import json

import pytest

import legacy_snapshot_journal as journal
import test_legacy_snapshot_staging as staging_fixtures


def prepare(tmp_path, *, payload=b"synthetic-payload"):
    record = staging_fixtures.identity()
    (tmp_path / "identity.json").write_text(json.dumps(record))

    (tmp_path / "payload").mkdir()
    relative = "synthetic/file.bin"
    destination = tmp_path / "payload" / relative
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)

    file_record = {
        "relative_path": relative,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "dataset": "trades",
        "partition_date": "2026-08-21",
        "instruments": ["NQ"],
        "row_count": 1,
        "row_groups": 1,
    }

    document = {
        "manifest_schema_version": 1,
        "snapshot_request_id": record["snapshot_request_id"],
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
        "production_transfer_authorized": False,
        "predictive_analysis_authorized": False,
        "scientific_readiness": "PENDING",
        "scope_accounting": {},
        "authorizations": record["authorizations"],
        "files": [file_record],
        "component_evidence": [],
        "inventory_started_utc": "2026-10-10T00:00:00+00:00",
        "inventory_ended_utc": "2026-10-10T00:01:00+00:00",
        "exceptions": [],
    }

    raw = journal._canonical(document)
    (tmp_path / "manifest.json").write_bytes(raw)

    (tmp_path / "journal.jsonl").write_bytes(b"")
    (tmp_path / "checkpoint.json").write_text(json.dumps({
        "journal_version": 1,
        "staging_attempt_id": record["staging_attempt_id"],
        "committed_sequence": 0,
        "committed_digest": journal.ZERO_DIGEST,
    }))

    return {
        "relative": relative,
        "destination": destination,
        "attempt": record["staging_attempt_id"],
        "digest": hashlib.sha256(raw).hexdigest(),
    }


def accept(root, setup, **kwargs):
    return journal._accept_manifest_file_unchecked(
        root,
        expected_attempt_id=setup["attempt"],
        expected_manifest_sha256=setup["digest"],
        relative_path=setup["relative"],
        **kwargs,
    )


def test_manifest_bound_acceptance(tmp_path):
    setup = prepare(tmp_path)
    result = accept(tmp_path, setup)
    assert result["committed_sequence"] == 1
    assert result["durability_attestation"] == (
        "FAULT_INJECTION_ONLY, NOT_HARDWARE_VERIFIED"
    )
    assert journal.verify_committed_journal(
        tmp_path, expected_attempt_id=setup["attempt"]
    )["committed_files_verified"] == 1


def test_absent_manifest_membership_rejected(tmp_path):
    setup = prepare(tmp_path)
    with pytest.raises(PermissionError, match="absent"):
        journal._accept_manifest_file_unchecked(
            tmp_path,
            expected_attempt_id=setup["attempt"],
            expected_manifest_sha256=setup["digest"],
            relative_path="unlisted/file.bin",
        )


def test_payload_differs_from_manifest_rejected(tmp_path):
    setup = prepare(tmp_path)
    setup["destination"].write_bytes(b"modified-payload")
    with pytest.raises(ValueError):
        accept(tmp_path, setup)


def test_wrong_external_manifest_digest_rejected(tmp_path):
    setup = prepare(tmp_path)
    setup["digest"] = "f" * 64
    with pytest.raises(ValueError, match="External manifest"):
        accept(tmp_path, setup)


def test_duplicate_acceptance_rejected(tmp_path):
    setup = prepare(tmp_path)
    accept(tmp_path, setup)
    with pytest.raises(ValueError, match="already accepted"):
        accept(tmp_path, setup)


def test_checkpoint_unchanged_after_journal_fsync_failure(tmp_path):
    setup = prepare(tmp_path)
    before = (tmp_path / "checkpoint.json").read_bytes()

    with pytest.raises(RuntimeError, match="Injected failure"):
        accept(tmp_path, setup, fault_after_journal_fsync=True)

    assert (tmp_path / "checkpoint.json").read_bytes() == before

    with pytest.raises(ValueError, match="Journal length"):
        journal.verify_committed_journal(
            tmp_path, expected_attempt_id=setup["attempt"]
        )


def test_checkpoint_ahead_of_journal_rejected(tmp_path):
    setup = prepare(tmp_path)
    checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
    checkpoint["committed_sequence"] = 1
    (tmp_path / "checkpoint.json").write_text(json.dumps(checkpoint))

    with pytest.raises(ValueError, match="Journal length"):
        journal.verify_committed_journal(
            tmp_path, expected_attempt_id=setup["attempt"]
        )


def test_committed_payload_tampering_rejected(tmp_path):
    setup = prepare(tmp_path)
    accept(tmp_path, setup)
    setup["destination"].write_bytes(b"tampered")

    with pytest.raises(ValueError):
        journal.verify_committed_journal(
            tmp_path, expected_attempt_id=setup["attempt"]
        )


def test_journal_payload_digest_disagreement_rejected(tmp_path):
    setup = prepare(tmp_path)
    accept(tmp_path, setup)

    path = tmp_path / "journal.jsonl"
    entry = json.loads(path.read_text())
    entry["sha256"] = "f" * 64
    entry["entry_digest"] = journal._entry_digest(entry)
    path.write_bytes(journal._canonical(entry) + b"\n")

    checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
    checkpoint["committed_digest"] = entry["entry_digest"]
    (tmp_path / "checkpoint.json").write_text(json.dumps(checkpoint))

    # The existing verifier checks journal ↔ payload.
    with pytest.raises(ValueError):
        journal.verify_committed_journal(
            tmp_path, expected_attempt_id=setup["attempt"]
        )



def _rewrite_sealed_manifest(root, setup, mutate):
    path = root / "manifest.json"
    document = json.loads(path.read_bytes())
    mutate(document)
    raw = journal._canonical(document)
    path.write_bytes(raw)
    setup["digest"] = hashlib.sha256(raw).hexdigest()


def test_evidence_only_path_cannot_be_accepted(tmp_path):
    setup = prepare(tmp_path)

    def mutate(document):
        record = document["files"].pop()
        document["component_evidence"].append({
            "relative_path": record["relative_path"],
            "size_bytes": record["size_bytes"],
            "sha256": record["sha256"],
        })

    _rewrite_sealed_manifest(tmp_path, setup, mutate)

    with pytest.raises(PermissionError, match="absent from sealed files"):
        accept(tmp_path, setup)


def test_duplicate_path_across_files_and_evidence_rejected(tmp_path):
    setup = prepare(tmp_path)

    def mutate(document):
        record = document["files"][0]
        document["component_evidence"].append({
            "relative_path": record["relative_path"],
            "size_bytes": record["size_bytes"],
            "sha256": record["sha256"],
        })

    _rewrite_sealed_manifest(tmp_path, setup, mutate)

    with pytest.raises(ValueError, match="ambiguous"):
        accept(tmp_path, setup)


def test_committed_journal_and_payload_agree_but_manifest_disagrees(tmp_path):
    setup = prepare(tmp_path)
    accept(tmp_path, setup)

    # The committed journal and actual payload remain unchanged and valid.
    assert journal.verify_committed_journal(
        tmp_path, expected_attempt_id=setup["attempt"]
    )["committed_files_verified"] == 1

    # Independently reseal a manifest claiming a different payload digest.
    # This simulates a separately anchored, conflicting manifest inventory.
    def mutate(document):
        document["files"][0]["sha256"] = "f" * 64

    _rewrite_sealed_manifest(tmp_path, setup, mutate)

    # Journal ↔ payload still passes; journal ↔ sealed manifest must fail.
    assert journal.verify_committed_journal(
        tmp_path, expected_attempt_id=setup["attempt"]
    )["committed_files_verified"] == 1

    with pytest.raises(ValueError, match="differs from sealed manifest"):
        journal._verify_committed_manifest_binding(
            tmp_path,
            expected_attempt_id=setup["attempt"],
            expected_manifest_sha256=setup["digest"],
        )


def test_failure_after_temp_fsync_preserves_previous_checkpoint(tmp_path):
    setup = prepare(tmp_path)
    before = (tmp_path / "checkpoint.json").read_bytes()

    with pytest.raises(RuntimeError, match="temp fsync"):
        accept(tmp_path, setup, fault_boundary="AFTER_TEMP_FSYNC")

    # Journal append was synchronized, but replacement never occurred.
    assert (tmp_path / "checkpoint.json").read_bytes() == before

    checkpoint = json.loads((tmp_path / "checkpoint.json").read_bytes())
    assert checkpoint["committed_sequence"] == 0

    with pytest.raises(ValueError, match="Journal length"):
        journal.verify_committed_journal(
            tmp_path, expected_attempt_id=setup["attempt"]
        )


def test_failure_after_replace_has_new_checkpoint_but_no_dir_fsync(tmp_path):
    setup = prepare(tmp_path)
    before = (tmp_path / "checkpoint.json").read_bytes()

    with pytest.raises(RuntimeError, match="checkpoint replace"):
        accept(tmp_path, setup, fault_boundary="AFTER_REPLACE")

    # Logical process-level visibility differs from the pre-replace case.
    # This does NOT prove persistence across a hardware power loss.
    after = (tmp_path / "checkpoint.json").read_bytes()
    assert after != before

    checkpoint = json.loads(after)
    assert checkpoint["committed_sequence"] == 1

    assert journal.verify_committed_journal(
        tmp_path, expected_attempt_id=setup["attempt"]
    )["committed_files_verified"] == 1



def test_recovery_assessment_empty_journal(tmp_path):
    setup = prepare(tmp_path)

    result = journal.assess_uncommitted_suffix(
        tmp_path,
        expected_attempt_id=setup["attempt"],
        expected_manifest_sha256=setup["digest"],
    )

    assert result["recovery_status"] == "NO_SUFFIX"
    assert result["mutation_performed"] is False


def test_recovery_assessment_after_journal_fsync_fault(tmp_path):
    setup = prepare(tmp_path)

    with pytest.raises(
        RuntimeError,
        match="Injected failure after journal fsync",
    ):
        accept(
            tmp_path,
            setup,
            fault_after_journal_fsync=True,
        )

    before_journal = (tmp_path / "journal.jsonl").read_bytes()
    before_checkpoint = (tmp_path / "checkpoint.json").read_bytes()

    result = journal.assess_uncommitted_suffix(
        tmp_path,
        expected_attempt_id=setup["attempt"],
        expected_manifest_sha256=setup["digest"],
    )

    assert result["recovery_status"] == "RECOVERABLE_SINGLE_SUFFIX"
    assert result["recovered_sequence_candidate"] == 1
    assert result["relative_path"] == setup["relative"]

    assert (tmp_path / "journal.jsonl").read_bytes() == before_journal
    assert (tmp_path / "checkpoint.json").read_bytes() == before_checkpoint


def test_recovery_assessment_rejects_tampered_suffix(tmp_path):
    setup = prepare(tmp_path)

    with pytest.raises(RuntimeError):
        accept(
            tmp_path,
            setup,
            fault_after_journal_fsync=True,
        )

    payload = setup["destination"]
    payload.write_bytes(b"X" * len(payload.read_bytes()))

    with pytest.raises(ValueError):
        journal.assess_uncommitted_suffix(
            tmp_path,
            expected_attempt_id=setup["attempt"],
            expected_manifest_sha256=setup["digest"],
        )


def test_recovery_assessment_rejects_checkpoint_ahead(tmp_path):
    setup = prepare(tmp_path)

    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint["committed_sequence"] = 1
    checkpoint_path.write_bytes(journal._canonical(checkpoint))

    with pytest.raises(ValueError, match="Checkpoint ahead"):
        journal.assess_uncommitted_suffix(
            tmp_path,
            expected_attempt_id=setup["attempt"],
            expected_manifest_sha256=setup["digest"],
        )
