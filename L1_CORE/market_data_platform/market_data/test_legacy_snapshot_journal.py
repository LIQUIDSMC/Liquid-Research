"""Focused synthetic committed-prefix acceptance journal regressions."""

import hashlib
import json

import pytest

import legacy_snapshot_journal as journal


def fixture(root, *, accepted=True):
    (root / "payload").mkdir()
    data = b"synthetic accepted payload"
    relative = "trades/date=2026-08-21/sample.parquet"
    target = root / "payload" / relative
    target.parent.mkdir(parents=True)
    if accepted:
        target.write_bytes(data)
    entry = {
        "sequence": 1,
        "relative_path": relative,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "previous_digest": journal.ZERO_DIGEST,
    }
    entry["entry_digest"] = journal._entry_digest(entry)
    (root / "journal.jsonl").write_bytes(
        journal._canonical(entry) + b"\n"
    )
    checkpoint = {
        "journal_version": 1,
        "staging_attempt_id": "synthetic-attempt",
        "committed_sequence": 1,
        "committed_digest": entry["entry_digest"],
    }
    (root / "checkpoint.json").write_text(json.dumps(checkpoint))
    return target, entry, checkpoint


def verify(root):
    return journal.verify_committed_journal(
        root, expected_attempt_id="synthetic-attempt"
    )


def test_valid_committed_payload(tmp_path):
    fixture(tmp_path)
    result = verify(tmp_path)
    assert result["committed_files_verified"] == 1
    assert result["rollback_attestation"] == "UNATTESTED"
    assert result["historical_timing_attestation"] == "UNATTESTED"
    assert result["scientific_readiness"] == "PENDING"


def test_missing_accepted_payload_rejected(tmp_path):
    fixture(tmp_path, accepted=False)
    with pytest.raises(ValueError, match="Missing destination file"):
        verify(tmp_path)


def test_modified_accepted_payload_rejected(tmp_path):
    target, _, _ = fixture(tmp_path)
    target.write_bytes(b"corrupted payload")
    with pytest.raises(ValueError):
        verify(tmp_path)


def test_journal_entry_tamper_rejected(tmp_path):
    fixture(tmp_path)
    path = tmp_path / "journal.jsonl"
    entry = json.loads(path.read_text())
    entry["size_bytes"] += 1
    path.write_bytes(journal._canonical(entry) + b"\n")
    with pytest.raises(ValueError, match="digest mismatch"):
        verify(tmp_path)


def test_checkpoint_digest_tamper_rejected(tmp_path):
    _, _, checkpoint = fixture(tmp_path)
    checkpoint["committed_digest"] = "f" * 64
    (tmp_path / "checkpoint.json").write_text(json.dumps(checkpoint))
    with pytest.raises(ValueError, match="Checkpoint digest"):
        verify(tmp_path)


def test_wrong_attempt_rejected(tmp_path):
    fixture(tmp_path)
    with pytest.raises(PermissionError, match="attempt mismatch"):
        journal.verify_committed_journal(
            tmp_path, expected_attempt_id="different-attempt"
        )


def test_uncommitted_suffix_rejected_until_recovery_increment(tmp_path):
    fixture(tmp_path)
    with (tmp_path / "journal.jsonl").open("ab") as handle:
        handle.write(b'{"uncommitted":true}\n')
    with pytest.raises(ValueError, match="Journal length"):
        verify(tmp_path)


def test_symlinked_checkpoint_rejected(tmp_path):
    fixture(tmp_path)
    original = tmp_path / "checkpoint.json"
    replacement = tmp_path / "actual-checkpoint.json"
    original.rename(replacement)
    original.symlink_to(replacement)
    with pytest.raises(ValueError, match="Symlinked"):
        verify(tmp_path)


def test_symlinked_payload_parent_rejected(tmp_path):
    fixture(tmp_path)
    directory = tmp_path / "payload" / "trades"
    directory.rename(tmp_path / "moved-trades")
    directory.symlink_to(tmp_path / "moved-trades", target_is_directory=True)
    with pytest.raises(ValueError, match="Symlinked"):
        verify(tmp_path)


def test_empty_committed_prefix(tmp_path):
    (tmp_path / "payload").mkdir()
    (tmp_path / "journal.jsonl").write_bytes(b"")
    (tmp_path / "checkpoint.json").write_text(json.dumps({
        "journal_version": 1,
        "staging_attempt_id": "synthetic-attempt",
        "committed_sequence": 0,
        "committed_digest": journal.ZERO_DIGEST,
    }))
    assert verify(tmp_path)["committed_files_verified"] == 0
