
"""Execution gate rejection tests; no production transfer."""

import json
import uuid

import pytest

import legacy_snapshot_execution as execution
import legacy_snapshot_state as state


def test_gate_requires_identity(tmp_path):
    attempt = str(uuid.uuid4())
    state._initialize_state_unchecked(
        tmp_path, expected_attempt_id=attempt
    )

    with pytest.raises((ValueError, PermissionError)):
        execution.verify_execution_gate(
            tmp_path,
            expected_attempt_id=attempt,
            expected_request_id="synthetic-request",
            expected_manifest_sha256="0" * 64,
            expected_authorizations={},
            expected_source_root=str(tmp_path),
        )


def test_gate_rejects_invalid_manifest_anchor(tmp_path):
    with pytest.raises(ValueError):
        execution.verify_execution_gate(
            tmp_path,
            expected_attempt_id=str(uuid.uuid4()),
            expected_request_id="synthetic-request",
            expected_manifest_sha256="invalid",
            expected_authorizations={},
            expected_source_root=str(tmp_path),
        )


def test_state_remains_unchanged_when_gate_rejects(tmp_path):
    attempt = str(uuid.uuid4())
    state._initialize_state_unchecked(
        tmp_path, expected_attempt_id=attempt
    )
    before = (tmp_path / "state.json").read_bytes()

    with pytest.raises((ValueError, PermissionError)):
        execution.verify_execution_gate(
            tmp_path,
            expected_attempt_id=attempt,
            expected_request_id="synthetic-request",
            expected_manifest_sha256="0" * 64,
            expected_authorizations={},
            expected_source_root=str(tmp_path),
        )

    assert (tmp_path / "state.json").read_bytes() == before


# Real authorization-record integration fixtures. No mocks.
from datetime import datetime, timedelta, timezone
import hashlib

import legacy_snapshot_authorization as authorization
import legacy_snapshot_journal as journal
import legacy_snapshot_scope as scope
import legacy_snapshot_staging as staging


def _authorized_attempt(tmp_path, *, request_id="synthetic-request",
                        valid=True):
    root = tmp_path / "destination"
    root.mkdir(parents=True)
    source_root = tmp_path / "synthetic-source"
    source_root.mkdir()
    attempt_id = str(uuid.uuid4())

    current = datetime.now(timezone.utc)
    if valid:
        start, end = current - timedelta(hours=1), current + timedelta(hours=1)
    else:
        start, end = current - timedelta(days=2), current - timedelta(days=1)

    auth_dir = root / "authorization"
    auth_dir.mkdir()
    for segment, filename in (("NON_H2", "non_h2.json"), ("H2", "h2.json")):
        record = {
            "authorization_schema_version": 1,
            "authorization_id": str(uuid.uuid4()),
            "snapshot_request_id": request_id,
            "segment": segment,
            "purpose": authorization.PURPOSE,
            "permitted_operations": authorization.OPERATIONS,
            "source_root": str(source_root),
            "destination_root": str(root),
            "datasets": sorted(scope.DATASETS),
            "instruments": sorted(scope.INSTRUMENTS),
            "date_windows": authorization.WINDOWS[segment],
            "valid_from_utc": start.isoformat(),
            "valid_until_utc": end.isoformat(),
            "resource_budget_references": {"synthetic": "test-only"},
        }
        (auth_dir / filename).write_bytes(journal._canonical(record))

    pair = authorization.validate_pair(
        auth_dir / "non_h2.json",
        auth_dir / "h2.json",
        str(source_root),
        str(root),
        historical=not valid,
    )

    document = {
        "manifest_schema_version": 1,
        "snapshot_request_id": request_id,
        "export_classification": "legacy_reconciled",
        "point_in_time_complete": False,
        "production_transfer_authorized": False,
        "predictive_analysis_authorized": False,
        "scientific_readiness": "PENDING",
        "scope_accounting": {},
        "authorizations": pair,
        "files": [],
        "component_evidence": [],
        "inventory_started_utc": current.isoformat(),
        "inventory_ended_utc": current.isoformat(),
        "exceptions": [],
    }
    raw = journal._canonical(document)
    (root / "manifest.json").write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()

    identity = {
        "staging_schema_version": 1,
        "staging_attempt_id": attempt_id,
        "snapshot_request_id": request_id,
        "manifest_sha256": digest,
        "authorizations": pair,
    }
    (root / "identity.json").write_bytes(journal._canonical(identity))
    state.initialize_bound_state(
        root,
        expected_attempt_id=attempt_id,
        expected_request_id=request_id,
        expected_manifest_sha256=digest,
        expected_authorizations=pair,
    )

    kwargs = {
        "expected_attempt_id": attempt_id,
        "expected_request_id": request_id,
        "expected_manifest_sha256": digest,
        "expected_authorizations": pair,
        "expected_source_root": str(source_root),
    }
    return root, kwargs


def test_real_unexpired_pair_passes_canonical_path(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    result = execution.verify_execution_gate(root, **kwargs)
    assert result["execution_gate_verified"] is True
    assert result["authorization_binding"] == "RECOMPUTED_AND_MATCHED"


def test_expired_pair_preserves_incomplete_state(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path, valid=False)
    before = (root / "state.json").read_bytes()
    with pytest.raises(PermissionError, match="expired or not yet valid"):
        execution.verify_execution_gate(root, **kwargs)
    assert (root / "state.json").read_bytes() == before


def test_caller_request_mismatch_preserves_incomplete_state(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    before = (root / "state.json").read_bytes()
    kwargs["expected_request_id"] = "different-external-request"
    with pytest.raises((PermissionError, ValueError)):
        execution.verify_execution_gate(root, **kwargs)
    assert (root / "state.json").read_bytes() == before


def test_valid_unexpired_substituted_pair_rejected(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    other_root, other_kwargs = _authorized_attempt(
        tmp_path / "other", request_id="different-request"
    )
    # Produce a genuinely valid unexpired pair for this same destination
    # and source, but with a different request identity.
    auth_dir = root / "authorization"
    for filename in ("non_h2.json", "h2.json"):
        record = json.loads(
            (other_root / "authorization" / filename).read_bytes()
        )
        record["source_root"] = kwargs["expected_source_root"]
        record["destination_root"] = str(root)
        (auth_dir / filename).write_bytes(journal._canonical(record))

    substituted = authorization.validate_pair(
        auth_dir / "non_h2.json",
        auth_dir / "h2.json",
        kwargs["expected_source_root"],
        str(root),
    )
    assert substituted["snapshot_request_id"] == "different-request"
    assert substituted != kwargs["expected_authorizations"]

    before = (root / "state.json").read_bytes()
    with pytest.raises(PermissionError, match="identities differ"):
        execution.verify_execution_gate(root, **kwargs)
    assert (root / "state.json").read_bytes() == before


def _prepare_authorized_payload(root, kwargs):
    """Add one synthetic payload and an empty committed journal."""
    payload = b"synthetic-authorized-payload"
    relative = "synthetic/authorized.bin"
    destination = root / "payload" / relative
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)

    document = json.loads((root / "manifest.json").read_bytes())
    document["files"] = [{
        "relative_path": relative,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "dataset": "trades",
        "partition_date": "2026-08-21",
        "instruments": ["NQ"],
        "row_count": 1,
        "row_groups": 1,
    }]

    raw = journal._canonical(document)
    (root / "manifest.json").write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()

    identity = json.loads((root / "identity.json").read_bytes())
    identity["manifest_sha256"] = digest
    (root / "identity.json").write_bytes(journal._canonical(identity))
    kwargs["expected_manifest_sha256"] = digest

    (root / "journal.jsonl").write_bytes(b"")
    (root / "checkpoint.json").write_bytes(journal._canonical({
        "journal_version": 1,
        "staging_attempt_id": kwargs["expected_attempt_id"],
        "committed_sequence": 0,
        "committed_digest": journal.ZERO_DIGEST,
    }))

    return relative


def test_public_writer_requires_external_identity(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    with pytest.raises(TypeError):
        journal.accept_manifest_file(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            relative_path=relative,
        )

    assert (root / "journal.jsonl").read_bytes() == b""


def test_public_writer_accepts_valid_authorized_payload(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    result = journal.accept_manifest_file(
        root,
        **kwargs,
        relative_path=relative,
    )

    assert result["committed_sequence"] == 1
    assert journal.verify_committed_journal(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["committed_files_verified"] == 1
    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "INCOMPLETE"


def test_expired_public_writer_mutates_nothing(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path, valid=False)
    relative = _prepare_authorized_payload(root, kwargs)

    before = {
        name: (root / name).read_bytes()
        for name in ("state.json", "journal.jsonl", "checkpoint.json")
    }

    with pytest.raises(PermissionError, match="expired or not yet valid"):
        journal.accept_manifest_file(
            root,
            **kwargs,
            relative_path=relative,
        )

    assert all(
        (root / name).read_bytes() == contents
        for name, contents in before.items()
    )


def test_terminal_state_blocks_public_writer(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    state.publish_bound_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_request_id=kwargs["expected_request_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
        expected_authorizations=kwargs["expected_authorizations"],
        new_state="FAILED",
    )

    before = (root / "journal.jsonl").read_bytes()

    with pytest.raises(PermissionError, match="terminal"):
        journal.accept_manifest_file(
            root,
            **kwargs,
            relative_path=relative,
        )

    assert (root / "journal.jsonl").read_bytes() == before



def test_bound_initialization_rejects_missing_identity(tmp_path):
    attempt_id = str(uuid.uuid4())

    with pytest.raises((ValueError, PermissionError)):
        state.initialize_bound_state(
            tmp_path,
            expected_attempt_id=attempt_id,
            expected_request_id="synthetic-request",
            expected_manifest_sha256="0" * 64,
            expected_authorizations={},
        )

    assert not (tmp_path / "state.json").exists()


def test_bound_initialization_rejects_wrong_external_anchor(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    (root / "state.json").unlink()

    wrong = dict(kwargs)
    wrong["expected_request_id"] = "incorrect-request"

    with pytest.raises((ValueError, PermissionError)):
        state.initialize_bound_state(
            root,
            expected_attempt_id=wrong["expected_attempt_id"],
            expected_request_id=wrong["expected_request_id"],
            expected_manifest_sha256=wrong["expected_manifest_sha256"],
            expected_authorizations=wrong["expected_authorizations"],
        )

    assert not (root / "state.json").exists()


def test_bound_publication_rejects_wrong_external_anchor(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)

    before = (root / "state.json").read_bytes()

    with pytest.raises((ValueError, PermissionError)):
        state.publish_bound_state(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_request_id="wrong-external-request",
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            expected_authorizations=kwargs["expected_authorizations"],
            new_state="FAILED",
        )

    assert (root / "state.json").read_bytes() == before


def test_bound_publication_rejects_tampered_identity(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)

    identity_path = root / "identity.json"
    identity = json.loads(identity_path.read_bytes())
    identity["snapshot_request_id"] = "tampered-request"
    identity_path.write_bytes(journal._canonical(identity))

    before = (root / "state.json").read_bytes()

    with pytest.raises((ValueError, PermissionError)):
        state.publish_bound_state(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_request_id=kwargs["expected_request_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            expected_authorizations=kwargs["expected_authorizations"],
            new_state="FAILED",
        )

    assert (root / "state.json").read_bytes() == before


def test_bound_publication_reaches_terminal_failed(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)

    result = state.publish_bound_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_request_id=kwargs["expected_request_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
        expected_authorizations=kwargs["expected_authorizations"],
        new_state="FAILED",
    )

    assert result["state"] == "FAILED"

    with pytest.raises(PermissionError, match="terminal"):
        state.require_bound_incomplete(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_request_id=kwargs["expected_request_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            expected_authorizations=kwargs["expected_authorizations"],
        )



def test_committed_payload_corruption_publishes_failed(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    committed = root / "payload" / relative
    original = committed.read_bytes()
    committed.write_bytes(b"X" * len(original))

    with pytest.raises(ValueError, match="corruption; attempt FAILED"):
        journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "FAILED"


def test_uncommitted_suffix_does_not_publish_failed(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    # A complete line beyond checkpoint sequence zero is an uncommitted
    # suffix, not independently established committed-data corruption.
    with (root / "journal.jsonl").open("ab") as handle:
        handle.write(b'{"uncommitted":"synthetic"}\\n')

    before = (root / "state.json").read_bytes()

    with pytest.raises(ValueError, match="recovery/audit required"):
        journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    assert (root / "state.json").read_bytes() == before



def test_committed_manifest_contradiction_publishes_failed(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    journal_path = root / "journal.jsonl"
    checkpoint_path = root / "checkpoint.json"

    entries = journal_path.read_bytes().splitlines()
    assert len(entries) == 1

    entry = json.loads(entries[0])
    assert entry["relative_path"] == relative

    # Construct an internally valid committed journal entry whose
    # content claim contradicts the externally anchored manifest.
    entry["sha256"] = hashlib.sha256(
        b"different-synthetic-content"
    ).hexdigest()

    entry["entry_digest"] = journal._entry_digest(entry)

    journal_path.write_bytes(
        journal._canonical(entry) + bytes([10])
    )

    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint["committed_digest"] = entry["entry_digest"]
    checkpoint_path.write_bytes(journal._canonical(checkpoint))

    # The contradiction is not a broken journal chain:
    # the rewritten entry and checkpoint agree.
    assert checkpoint["committed_sequence"] == 1
    assert checkpoint["committed_digest"] == entry["entry_digest"]

    with pytest.raises(
        ValueError,
        match="manifest contradiction; attempt FAILED",
    ):
        journal.accept_manifest_file(
            root,
            **kwargs,
            relative_path=relative,
        )

    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "FAILED"


def test_wrong_external_anchor_does_not_publish_failed(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    before = (root / "state.json").read_bytes()

    wrong = dict(kwargs)
    wrong["expected_request_id"] = "wrong-caller-request"

    with pytest.raises((ValueError, PermissionError)):
        journal.accept_manifest_file(
            root,
            **wrong,
            relative_path=relative,
        )

    assert (root / "state.json").read_bytes() == before



def _create_recoverable_authorized_suffix(tmp_path):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    with pytest.raises(
        RuntimeError,
        match="Injected failure after journal fsync",
    ):
        journal._accept_manifest_file_unchecked(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            relative_path=relative,
            fault_after_journal_fsync=True,
        )

    assessment = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
    )

    assert assessment["recovery_status"] == "RECOVERABLE_SINGLE_SUFFIX"

    return root, kwargs, relative


def test_authorized_single_suffix_recovery(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, relative = _create_recoverable_authorized_suffix(tmp_path)

    before_journal = (root / "journal.jsonl").read_bytes()
    before_payload = (root / "payload" / relative).read_bytes()

    result = recover_authorized_single_suffix(root, **kwargs)

    assert result["recovery_status"] == "RECOVERED_SINGLE_SUFFIX"
    assert result["committed_sequence"] == 1

    assert (root / "journal.jsonl").read_bytes() == before_journal
    assert (root / "payload" / relative).read_bytes() == before_payload

    assert journal.verify_committed_journal(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["committed_sequence"] == 1

    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "INCOMPLETE"


def test_recovery_wrong_external_anchor_preserves_checkpoint(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    before = {
        name: (root / name).read_bytes()
        for name in ("checkpoint.json", "journal.jsonl", "state.json")
    }

    wrong = dict(kwargs)
    wrong["expected_request_id"] = "incorrect-caller-request"

    with pytest.raises((ValueError, PermissionError)):
        recover_authorized_single_suffix(root, **wrong)

    for name, contents in before.items():
        assert (root / name).read_bytes() == contents


def test_recovery_rejects_corrupt_suffix_without_mutation(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, relative = _create_recoverable_authorized_suffix(tmp_path)

    payload = root / "payload" / relative
    payload.write_bytes(b"X" * len(payload.read_bytes()))

    before = {
        name: (root / name).read_bytes()
        for name in ("checkpoint.json", "journal.jsonl", "state.json")
    }

    with pytest.raises(ValueError):
        recover_authorized_single_suffix(root, **kwargs)

    for name, contents in before.items():
        assert (root / name).read_bytes() == contents


def test_recovery_rejects_no_suffix(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs = _authorized_attempt(tmp_path)
    _prepare_authorized_payload(root, kwargs)

    before = (root / "checkpoint.json").read_bytes()

    with pytest.raises(ValueError, match="No recoverable single suffix"):
        recover_authorized_single_suffix(root, **kwargs)

    assert (root / "checkpoint.json").read_bytes() == before



def test_recovery_fault_after_temp_fsync(tmp_path, monkeypatch):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, relative = _create_recoverable_authorized_suffix(tmp_path)

    before_checkpoint = (root / "checkpoint.json").read_bytes()
    before_journal = (root / "journal.jsonl").read_bytes()
    before_payload = (root / "payload" / relative).read_bytes()

    original_atomic = journal._atomic_checkpoint

    def injected_atomic(root_arg, checkpoint, *, fault_boundary=None):
        return original_atomic(
            root_arg,
            checkpoint,
            fault_boundary="AFTER_TEMP_FSYNC",
        )

    with monkeypatch.context() as patch:
        patch.setattr(journal, "_atomic_checkpoint", injected_atomic)

        with pytest.raises(
            RuntimeError,
            match="Injected failure after checkpoint temp fsync",
        ):
            recover_authorized_single_suffix(root, **kwargs)

    assert (root / "checkpoint.json").read_bytes() == before_checkpoint
    assert (root / "journal.jsonl").read_bytes() == before_journal
    assert (root / "payload" / relative).read_bytes() == before_payload

    assessment = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
    )

    assert assessment["recovery_status"] == "RECOVERABLE_SINGLE_SUFFIX"

    # Retry after the injected fault has been removed.
    recovered = recover_authorized_single_suffix(root, **kwargs)

    assert recovered["recovery_status"] == "RECOVERED_SINGLE_SUFFIX"
    assert recovered["committed_sequence"] == 1

    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "INCOMPLETE"


def test_recovery_fault_after_checkpoint_replace(tmp_path, monkeypatch):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, relative = _create_recoverable_authorized_suffix(tmp_path)

    before_journal = (root / "journal.jsonl").read_bytes()
    before_payload = (root / "payload" / relative).read_bytes()

    original_atomic = journal._atomic_checkpoint

    def injected_atomic(root_arg, checkpoint, *, fault_boundary=None):
        return original_atomic(
            root_arg,
            checkpoint,
            fault_boundary="AFTER_REPLACE",
        )

    with monkeypatch.context() as patch:
        patch.setattr(journal, "_atomic_checkpoint", injected_atomic)

        with pytest.raises(
            RuntimeError,
            match="Injected failure after checkpoint replace",
        ):
            recover_authorized_single_suffix(root, **kwargs)

    # The checkpoint replacement occurred before the injected failure.
    verified = journal.verify_committed_journal(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )

    assert verified["committed_sequence"] == 1

    assert (root / "journal.jsonl").read_bytes() == before_journal
    assert (root / "payload" / relative).read_bytes() == before_payload

    assessment = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
    )

    assert assessment["recovery_status"] == "NO_SUFFIX"

    # Retrying must not advance the checkpoint a second time.
    before_retry = (root / "checkpoint.json").read_bytes()

    with pytest.raises(ValueError, match="No recoverable single suffix"):
        recover_authorized_single_suffix(root, **kwargs)

    assert (root / "checkpoint.json").read_bytes() == before_retry

    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "INCOMPLETE"



def test_public_writer_rejects_busy_staging_lock(tmp_path):
    import fcntl
    import os

    from legacy_snapshot_lock import LOCK_NAME

    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    descriptor = os.open(
        root / LOCK_NAME,
        os.O_RDWR | os.O_CREAT,
        0o600,
    )

    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

        before = {
            name: (root / name).read_bytes()
            for name in ("state.json", "journal.jsonl", "checkpoint.json")
        }

        with pytest.raises(
            PermissionError,
            match="already in progress",
        ):
            journal.accept_manifest_file(
                root,
                **kwargs,
                relative_path=relative,
            )

        assert all(
            (root / name).read_bytes() == contents
            for name, contents in before.items()
        )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    result = journal.accept_manifest_file(
        root,
        **kwargs,
        relative_path=relative,
    )

    assert result["committed_sequence"] == 1


def test_recovery_rejects_busy_staging_lock(tmp_path):
    import fcntl
    import os

    from legacy_snapshot_execution import recover_authorized_single_suffix
    from legacy_snapshot_lock import LOCK_NAME

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    descriptor = os.open(
        root / LOCK_NAME,
        os.O_RDWR | os.O_CREAT,
        0o600,
    )

    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

        before = {
            name: (root / name).read_bytes()
            for name in ("state.json", "journal.jsonl", "checkpoint.json")
        }

        with pytest.raises(
            PermissionError,
            match="already in progress",
        ):
            recover_authorized_single_suffix(root, **kwargs)

        assert all(
            (root / name).read_bytes() == contents
            for name, contents in before.items()
        )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    result = recover_authorized_single_suffix(root, **kwargs)

    assert result["recovery_status"] == "RECOVERED_SINGLE_SUFFIX"



def test_recovered_payload_cannot_be_accepted_twice(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, relative = _create_recoverable_authorized_suffix(tmp_path)

    recover_authorized_single_suffix(root, **kwargs)

    before = {
        name: (root / name).read_bytes()
        for name in ("journal.jsonl", "checkpoint.json", "state.json")
    }

    with pytest.raises(ValueError, match="already accepted"):
        journal.accept_manifest_file(
            root,
            **kwargs,
            relative_path=relative,
        )

    for name, contents in before.items():
        assert (root / name).read_bytes() == contents


def test_recovered_attempt_remains_incomplete(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    result = recover_authorized_single_suffix(root, **kwargs)

    assert result["attempt_state"] == "INCOMPLETE"
    assert result["production_transfer_authorized"] is False
    assert result["scientific_readiness"] == "PENDING"

    durable = state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )

    assert durable["state"] == "INCOMPLETE"


def test_recovery_cannot_repeat_after_terminal_failure(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    state.publish_bound_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_request_id=kwargs["expected_request_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
        expected_authorizations=kwargs["expected_authorizations"],
        new_state="FAILED",
    )

    before = {
        name: (root / name).read_bytes()
        for name in ("journal.jsonl", "checkpoint.json", "state.json")
    }

    with pytest.raises((ValueError, PermissionError)):
        recover_authorized_single_suffix(root, **kwargs)

    for name, contents in before.items():
        assert (root / name).read_bytes() == contents



def _prepare_two_authorized_payloads(root, kwargs):
    """Seal two synthetic payloads before either is accepted."""
    payloads = (
        ("synthetic/authorized-a.bin", b"synthetic-payload-A"),
        ("synthetic/authorized-b.bin", b"synthetic-payload-B"),
    )

    document = json.loads((root / "manifest.json").read_bytes())
    records = []

    for relative, payload in payloads:
        destination = root / "payload" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

        records.append({
            "relative_path": relative,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "dataset": "trades",
            "partition_date": "2026-08-21",
            "instruments": ["NQ"],
            "row_count": 1,
            "row_groups": 1,
        })

    document["files"] = records

    raw = journal._canonical(document)
    (root / "manifest.json").write_bytes(raw)

    digest = hashlib.sha256(raw).hexdigest()

    identity = json.loads((root / "identity.json").read_bytes())
    identity["manifest_sha256"] = digest
    (root / "identity.json").write_bytes(journal._canonical(identity))

    kwargs["expected_manifest_sha256"] = digest

    (root / "journal.jsonl").write_bytes(b"")

    (root / "checkpoint.json").write_bytes(
        journal._canonical({
            "journal_version": journal.JOURNAL_VERSION,
            "staging_attempt_id": kwargs["expected_attempt_id"],
            "committed_sequence": 0,
            "committed_digest": journal.ZERO_DIGEST,
        })
    )

    return payloads


def test_recovery_then_accept_second_sealed_payload(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs = _authorized_attempt(tmp_path)
    payloads = _prepare_two_authorized_payloads(root, kwargs)

    relative_a, bytes_a = payloads[0]
    relative_b, bytes_b = payloads[1]

    sealed_manifest_before = (root / "manifest.json").read_bytes()
    sealed_identity_before = (root / "identity.json").read_bytes()

    # File A reaches the durable journal, but its checkpoint does not.
    with pytest.raises(
        RuntimeError,
        match="Injected failure after journal fsync",
    ):
        journal._accept_manifest_file_unchecked(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            relative_path=relative_a,
            fault_after_journal_fsync=True,
        )

    assessment = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
    )

    assert assessment["recovery_status"] == "RECOVERABLE_SINGLE_SUFFIX"
    assert assessment["relative_path"] == relative_a

    # Authorized recovery promotes A's verified journal entry.
    recovered = recover_authorized_single_suffix(root, **kwargs)

    assert recovered["recovery_status"] == "RECOVERED_SINGLE_SUFFIX"
    assert recovered["committed_sequence"] == 1

    # The ordinary public writer must now accept distinct file B.
    accepted = journal.accept_manifest_file(
        root,
        **kwargs,
        relative_path=relative_b,
    )

    assert accepted["accepted_relative_path"] == relative_b
    assert accepted["committed_sequence"] == 2

    verified = journal.verify_committed_journal(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )

    assert verified["committed_sequence"] == 2
    assert verified["committed_files_verified"] == 2

    entries = [
        json.loads(line)
        for line in (root / "journal.jsonl").read_bytes().splitlines()
    ]

    assert [entry["relative_path"] for entry in entries] == [
        relative_a,
        relative_b,
    ]

    assert entries[0]["sequence"] == 1
    assert entries[1]["sequence"] == 2

    assert entries[0]["previous_digest"] == journal.ZERO_DIGEST
    assert entries[1]["previous_digest"] == entries[0]["entry_digest"]

    checkpoint = json.loads((root / "checkpoint.json").read_bytes())

    assert checkpoint["committed_sequence"] == 2
    assert checkpoint["committed_digest"] == entries[1]["entry_digest"]

    assert (root / "payload" / relative_a).read_bytes() == bytes_a
    assert (root / "payload" / relative_b).read_bytes() == bytes_b

    assert (root / "manifest.json").read_bytes() == sealed_manifest_before
    assert (root / "identity.json").read_bytes() == sealed_identity_before

    durable_state = state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )

    assert durable_state["state"] == "INCOMPLETE"



def _assert_recovery_records_unchanged(root, before):
    for relative, expected_bytes in before.items():
        assert (root / relative).read_bytes() == expected_bytes


def _capture_recovery_records(root):
    return {
        relative: (root / relative).read_bytes()
        for relative in (
            "identity.json",
            "manifest.json",
            "state.json",
            "checkpoint.json",
            "journal.jsonl",
            "authorization/non_h2.json",
            "authorization/h2.json",
        )
    }


def test_recovery_expired_authorization_preserves_durable_records(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs = _authorized_attempt(tmp_path, valid=False)
    relative = _prepare_authorized_payload(root, kwargs)

    with pytest.raises(
        RuntimeError,
        match="Injected failure after journal fsync",
    ):
        journal._accept_manifest_file_unchecked(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            relative_path=relative,
            fault_after_journal_fsync=True,
        )

    assessment = journal.assess_uncommitted_suffix(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
        expected_manifest_sha256=kwargs["expected_manifest_sha256"],
    )

    assert assessment["recovery_status"] == "RECOVERABLE_SINGLE_SUFFIX"

    before = _capture_recovery_records(root)

    with pytest.raises(PermissionError):
        recover_authorized_single_suffix(root, **kwargs)

    _assert_recovery_records_unchanged(root, before)


def test_recovery_future_time_rejects_expired_authority(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)
    before = _capture_recovery_records(root)

    # The authorization is valid now, but not at this future instant.
    future = datetime.now(timezone.utc) + timedelta(days=2)

    with pytest.raises(PermissionError):
        recover_authorized_single_suffix(
            root,
            **kwargs,
            now=future,
        )

    _assert_recovery_records_unchanged(root, before)


def test_recovery_wrong_source_root_preserves_durable_records(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)
    before = _capture_recovery_records(root)

    wrong = dict(kwargs)
    wrong["expected_source_root"] = str(tmp_path / "incorrect-source")

    with pytest.raises((ValueError, PermissionError)):
        recover_authorized_single_suffix(root, **wrong)

    _assert_recovery_records_unchanged(root, before)



def test_recovery_rejects_partial_suffix(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    journal_path = root / "journal.jsonl"
    raw = journal_path.read_bytes()

    # Simulate interruption while writing the final journal line.
    journal_path.write_bytes(raw[:-1])

    before = _capture_recovery_records(root)

    with pytest.raises(ValueError, match="Incomplete uncommitted suffix"):
        recover_authorized_single_suffix(root, **kwargs)

    _assert_recovery_records_unchanged(root, before)


def test_recovery_rejects_multiple_suffix_entries(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    journal_path = root / "journal.jsonl"
    raw = journal_path.read_bytes()

    # Duplicate line creates two entries beyond the committed checkpoint.
    journal_path.write_bytes(raw + raw)

    before = _capture_recovery_records(root)

    with pytest.raises(ValueError, match="exactly one suffix entry"):
        recover_authorized_single_suffix(root, **kwargs)

    _assert_recovery_records_unchanged(root, before)


def test_recovery_rejects_invalid_suffix_chain(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    journal_path = root / "journal.jsonl"
    entry = json.loads(journal_path.read_bytes().splitlines()[0])

    entry["previous_digest"] = "f" * 64
    entry["entry_digest"] = journal._entry_digest(entry)

    journal_path.write_bytes(journal._canonical(entry) + bytes([10]))

    before = _capture_recovery_records(root)

    with pytest.raises(ValueError, match="chain mismatch"):
        recover_authorized_single_suffix(root, **kwargs)

    _assert_recovery_records_unchanged(root, before)


def test_recovery_rejects_suffix_manifest_disagreement(tmp_path):
    from legacy_snapshot_execution import recover_authorized_single_suffix

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)

    journal_path = root / "journal.jsonl"
    entry = json.loads(journal_path.read_bytes().splitlines()[0])

    entry["sha256"] = "a" * 64
    entry["entry_digest"] = journal._entry_digest(entry)

    journal_path.write_bytes(journal._canonical(entry) + bytes([10]))

    before = _capture_recovery_records(root)

    with pytest.raises(ValueError, match="contradicts sealed manifest"):
        recover_authorized_single_suffix(root, **kwargs)

    _assert_recovery_records_unchanged(root, before)



def test_cross_process_state_publication_rejected_during_lock(tmp_path):
    from test_legacy_snapshot_lock_process import (
        _start_lock_holder,
        _stop_child,
    )

    root, kwargs = _authorized_attempt(tmp_path)
    _prepare_authorized_payload(root, kwargs)
    before = _capture_recovery_records(root)

    child = _start_lock_holder(root)
    try:
        with pytest.raises(PermissionError, match="already in progress"):
            state.publish_bound_state(
                root,
                expected_attempt_id=kwargs["expected_attempt_id"],
                expected_request_id=kwargs["expected_request_id"],
                expected_manifest_sha256=kwargs["expected_manifest_sha256"],
                expected_authorizations=kwargs["expected_authorizations"],
                new_state="FAILED",
            )

        _assert_recovery_records_unchanged(root, before)
    finally:
        _stop_child(child)

    assert state.read_state(
        root, expected_attempt_id=kwargs["expected_attempt_id"]
    )["state"] == "INCOMPLETE"


def test_cross_process_terminal_publication_blocks_acceptance(tmp_path):
    import os
    import select
    import subprocess
    import sys

    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)

    child_script = """
import json
import sys
import time

import legacy_snapshot_state as state
from legacy_snapshot_lock import exclusive_attempt_lock

root = sys.argv[1]
arguments = json.loads(sys.argv[2])

@exclusive_attempt_lock
def publish_and_hold(staging_root):
    state._publish_bound_state_lock_held(
        staging_root,
        expected_attempt_id=arguments["expected_attempt_id"],
        expected_request_id=arguments["expected_request_id"],
        expected_manifest_sha256=arguments["expected_manifest_sha256"],
        expected_authorizations=arguments["expected_authorizations"],
        new_state="FAILED",
    )
    print("TERMINAL_LOCK_HELD", flush=True)
    time.sleep(60)

publish_and_hold(root)
"""

    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            child_script,
            str(root),
            json.dumps(kwargs),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )

    try:
        ready, _, _ = select.select([child.stdout], [], [], 5)
        assert ready, "Child did not publish terminal state in time"
        assert child.stdout.readline().strip() == "TERMINAL_LOCK_HELD"
        assert child.poll() is None

        before = _capture_recovery_records(root)

        with pytest.raises(PermissionError, match="already in progress"):
            journal.accept_manifest_file(
                root, **kwargs, relative_path=relative
            )

        _assert_recovery_records_unchanged(root, before)
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)

    with pytest.raises(PermissionError):
        journal.accept_manifest_file(
            root, **kwargs, relative_path=relative
        )

    _assert_recovery_records_unchanged(root, before)

    assert state.read_state(
        root, expected_attempt_id=kwargs["expected_attempt_id"]
    )["state"] == "FAILED"



def test_cross_process_recovery_rejected_during_lock(tmp_path):
    from test_legacy_snapshot_lock_process import (
        _start_lock_holder,
        _stop_child,
    )

    root, kwargs, _ = _create_recoverable_authorized_suffix(tmp_path)
    before = _capture_recovery_records(root)

    child = _start_lock_holder(root)
    try:
        with pytest.raises(PermissionError, match="already in progress"):
            execution.recover_authorized_single_suffix(root, **kwargs)

        _assert_recovery_records_unchanged(root, before)
    finally:
        _stop_child(child)

    result = execution.recover_authorized_single_suffix(root, **kwargs)

    assert result["recovery_status"] == "RECOVERED_SINGLE_SUFFIX"
    assert result["committed_sequence"] == 1

    assert (root / "journal.jsonl").read_bytes() == before["journal.jsonl"]
    assert (root / "state.json").read_bytes() == before["state.json"]

    assert journal.verify_committed_journal(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["committed_sequence"] == 1

    assert state.read_state(
        root,
        expected_attempt_id=kwargs["expected_attempt_id"],
    )["state"] == "INCOMPLETE"


@pytest.mark.parametrize("operation", [
    "accept_new",
    "accept_after_commit",
    "verify_committed",
    "verify_execution_committed",
    "recover",
])
def test_symlinked_payload_root_rejected_without_record_mutation(
    tmp_path, operation
):
    if operation == "recover":
        root, kwargs, relative = _create_recoverable_authorized_suffix(
            tmp_path
        )
    else:
        root, kwargs = _authorized_attempt(tmp_path)
        relative = _prepare_authorized_payload(root, kwargs)
        if operation in {
            "accept_after_commit", "verify_committed",
            "verify_execution_committed",
        }:
            journal.accept_manifest_file(
                root, **kwargs, relative_path=relative
            )

    external = tmp_path / "external-payload"
    (root / "payload").rename(external)
    (root / "payload").symlink_to(external, target_is_directory=True)

    before = _capture_recovery_records(root)
    payload_before = (external / relative).read_bytes()

    expected_error = (
        "^Symlinked committed payload root$"
        if operation == "verify_execution_committed"
        else "Symlinked"
    )
    with pytest.raises(ValueError, match=expected_error):
        if operation == "verify_execution_committed":
            execution.verify_execution_gate(root, **kwargs)
            execution.verify_committed_payloads_or_fail(
                root,
                expected_attempt_id=kwargs["expected_attempt_id"],
                expected_request_id=kwargs["expected_request_id"],
                expected_manifest_sha256=kwargs["expected_manifest_sha256"],
                expected_authorizations=kwargs["expected_authorizations"],
            )
        elif operation == "recover":
            execution.recover_authorized_single_suffix(root, **kwargs)
        elif operation == "verify_committed":
            journal.verify_committed_journal(
                root,
                expected_attempt_id=kwargs["expected_attempt_id"],
            )
        else:
            journal.accept_manifest_file(
                root, **kwargs, relative_path=relative
            )

    _assert_recovery_records_unchanged(root, before)
    assert (external / relative).read_bytes() == payload_before
    assert (root / "payload").is_symlink()


def test_direct_corruption_verifier_respects_cross_process_lock(tmp_path):
    from test_legacy_snapshot_lock_process import (
        _start_lock_holder,
        _stop_child,
    )

    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)
    journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    payload = root / "payload" / relative
    payload.write_bytes(b"X" * len(payload.read_bytes()))
    execution.verify_execution_gate(root, **kwargs)

    arguments = {
        key: kwargs[key]
        for key in (
            "expected_attempt_id",
            "expected_request_id",
            "expected_manifest_sha256",
            "expected_authorizations",
        )
    }
    before = _capture_recovery_records(root)
    payload_before = payload.read_bytes()

    child = _start_lock_holder(root)
    try:
        with pytest.raises(
            PermissionError,
            match="^Staging operation already in progress$",
        ):
            execution.verify_committed_payloads_or_fail(
                root, **arguments
            )

        _assert_recovery_records_unchanged(root, before)
        assert payload.read_bytes() == payload_before
    finally:
        _stop_child(child)

    with pytest.raises(
        ValueError,
        match="^Confirmed committed payload corruption; attempt FAILED$",
    ):
        execution.verify_committed_payloads_or_fail(root, **arguments)

    assert state.read_state(
        root, expected_attempt_id=kwargs["expected_attempt_id"]
    )["state"] == "FAILED"
    for name, contents in before.items():
        if name != "state.json":
            assert (root / name).read_bytes() == contents
    assert payload.read_bytes() == payload_before


@pytest.mark.parametrize("version", [True, 999])
def test_invalid_checkpoint_version_preserves_records_despite_corruption(
    tmp_path, version
):
    root, kwargs = _authorized_attempt(tmp_path)
    relative = _prepare_authorized_payload(root, kwargs)
    journal.accept_manifest_file(root, **kwargs, relative_path=relative)

    checkpoint_path = root / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint["journal_version"] = version
    checkpoint_path.write_bytes(journal._canonical(checkpoint))

    payload = root / "payload" / relative
    payload.write_bytes(b"X" * len(payload.read_bytes()))
    execution.verify_execution_gate(root, **kwargs)

    before = _capture_recovery_records(root)
    payload_before = payload.read_bytes()

    with pytest.raises(ValueError, match="^Invalid checkpoint version$"):
        execution.verify_committed_payloads_or_fail(
            root,
            expected_attempt_id=kwargs["expected_attempt_id"],
            expected_request_id=kwargs["expected_request_id"],
            expected_manifest_sha256=kwargs["expected_manifest_sha256"],
            expected_authorizations=kwargs["expected_authorizations"],
        )

    _assert_recovery_records_unchanged(root, before)
    assert payload.read_bytes() == payload_before
    assert state.read_state(
        root, expected_attempt_id=kwargs["expected_attempt_id"]
    )["state"] == "INCOMPLETE"
