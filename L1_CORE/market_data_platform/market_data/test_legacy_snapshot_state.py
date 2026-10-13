
"""Synthetic attempt-state publication tests."""

import json
import uuid

import pytest

import legacy_snapshot_state as state


@pytest.fixture
def attempt(tmp_path):
    identifier = str(uuid.uuid4())
    state._initialize_state_unchecked(
        tmp_path, expected_attempt_id=identifier
    )
    return tmp_path, identifier


def test_initialize_incomplete(attempt):
    root, identifier = attempt
    record = state.read_state(
        root, expected_attempt_id=identifier
    )
    assert record["state"] == "INCOMPLETE"
    assert record["state_schema_version"] == 1


def test_existing_state_cannot_be_reinitialized(attempt):
    root, identifier = attempt
    with pytest.raises(FileExistsError):
        state._initialize_state_unchecked(
            root, expected_attempt_id=identifier
        )


def test_wrong_expected_identity_does_not_mutate_state(attempt):
    root, identifier = attempt
    before = (root / "state.json").read_bytes()

    with pytest.raises(PermissionError, match="identity mismatch"):
        state.read_state(
            root, expected_attempt_id=str(uuid.uuid4())
        )

    assert (root / "state.json").read_bytes() == before


def test_failed_is_terminal(attempt):
    root, identifier = attempt
    result = state._publish_state_unchecked(
        root,
        expected_attempt_id=identifier,
        new_state="FAILED",
    )
    assert result["state"] == "FAILED"

    with pytest.raises(PermissionError, match="Terminal"):
        state._publish_state_unchecked(
            root,
            expected_attempt_id=identifier,
            new_state="COMPLETE",
        )

    with pytest.raises(PermissionError, match="terminal"):
        state._require_incomplete_unchecked(
            root, expected_attempt_id=identifier
        )


def test_complete_is_terminal(attempt):
    root, identifier = attempt
    state._publish_state_unchecked(
        root,
        expected_attempt_id=identifier,
        new_state="COMPLETE",
    )

    with pytest.raises(PermissionError, match="Terminal"):
        state._publish_state_unchecked(
            root,
            expected_attempt_id=identifier,
            new_state="FAILED",
        )


def test_malformed_state_fails_closed(attempt):
    root, identifier = attempt
    path = root / "state.json"
    record = json.loads(path.read_bytes())
    record["unexpected"] = True
    path.write_text(json.dumps(record))

    with pytest.raises(ValueError, match="schema"):
        state.read_state(
            root, expected_attempt_id=identifier
        )


def test_state_symlink_rejected(attempt, tmp_path):
    root, identifier = attempt
    path = root / "state.json"
    other = tmp_path / "other.json"
    path.rename(other)
    path.symlink_to(other)

    with pytest.raises(ValueError, match="symlinked"):
        state.read_state(
            root, expected_attempt_id=identifier
        )


def test_temp_fsync_failure_preserves_incomplete(attempt):
    root, identifier = attempt
    before = (root / "state.json").read_bytes()

    with pytest.raises(RuntimeError, match="temp fsync"):
        state._publish_state_unchecked(
            root,
            expected_attempt_id=identifier,
            new_state="FAILED",
            fault_boundary="AFTER_TEMP_FSYNC",
        )

    assert (root / "state.json").read_bytes() == before
    assert state._require_incomplete_unchecked(
        root, expected_attempt_id=identifier
    )["state"] == "INCOMPLETE"


def test_post_replace_failure_exposes_terminal_state(attempt):
    root, identifier = attempt

    with pytest.raises(RuntimeError, match="state replace"):
        state._publish_state_unchecked(
            root,
            expected_attempt_id=identifier,
            new_state="FAILED",
            fault_boundary="AFTER_REPLACE",
        )

    # Process-level visibility only; not a power-loss durability claim.
    assert state.read_state(
        root, expected_attempt_id=identifier
    )["state"] == "FAILED"


def test_incomplete_to_incomplete_republication_rejected(attempt):
    root, identifier = attempt

    with pytest.raises(ValueError, match="terminal transitions"):
        state._publish_state_unchecked(
            root,
            expected_attempt_id=identifier,
            new_state="INCOMPLETE",
        )
