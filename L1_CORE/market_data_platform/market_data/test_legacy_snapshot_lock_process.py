
"""Cross-process tests for the synthetic C-003 cooperative lock."""

import os
import select
import subprocess
import sys

import pytest

from legacy_snapshot_lock import exclusive_attempt_lock


@exclusive_attempt_lock
def _protected_operation(staging_root):
    return "ENTERED"


CHILD = """
import sys
import time

from legacy_snapshot_lock import exclusive_attempt_lock

@exclusive_attempt_lock
def hold(root):
    print("LOCK_ACQUIRED", flush=True)
    time.sleep(60)

hold(sys.argv[1])
"""


def _start_lock_holder(root):
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(root)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        readable, _, _ = select.select([child.stdout], [], [], 5)

        if not readable:
            raise AssertionError("Child did not acquire lock within 5 seconds")

        message = child.stdout.readline().strip()

        if message != "LOCK_ACQUIRED":
            raise AssertionError(
                f"Unexpected child response: {message!r}"
            )

        if child.poll() is not None:
            raise AssertionError("Child exited before contention test")

        return child

    except BaseException:
        child.kill()
        child.communicate(timeout=5)
        raise


def _stop_child(child):
    if child.poll() is None:
        child.kill()

    child.communicate(timeout=5)


def test_separate_process_blocks_protected_operation(tmp_path):
    child = _start_lock_holder(tmp_path)

    try:
        with pytest.raises(
            PermissionError,
            match="already in progress",
        ):
            _protected_operation(tmp_path)
    finally:
        _stop_child(child)

    assert _protected_operation(tmp_path) == "ENTERED"


def test_process_termination_releases_lock(tmp_path):
    child = _start_lock_holder(tmp_path)

    try:
        with pytest.raises(PermissionError):
            _protected_operation(tmp_path)
    finally:
        _stop_child(child)

    # SIGKILL terminates the lock holder without running its cleanup.
    # The operating system must release the advisory lock.
    assert child.returncode is not None
    assert _protected_operation(tmp_path) == "ENTERED"


def test_lock_file_persists_after_release(tmp_path):
    from legacy_snapshot_lock import LOCK_NAME

    assert _protected_operation(tmp_path) == "ENTERED"

    lock_path = tmp_path / LOCK_NAME
    assert lock_path.is_file()

    original_inode = os.stat(lock_path).st_ino

    assert _protected_operation(tmp_path) == "ENTERED"

    assert lock_path.is_file()
    assert os.stat(lock_path).st_ino == original_inode


def test_symlinked_lock_file_rejected(tmp_path):
    from legacy_snapshot_lock import LOCK_NAME

    target = tmp_path / "unrelated.txt"
    target.write_text("unchanged")

    (tmp_path / LOCK_NAME).symlink_to(target)

    with pytest.raises(PermissionError, match="Symlinked"):
        _protected_operation(tmp_path)

    assert target.read_text() == "unchanged"



def test_lock_path_replacement_rejected(tmp_path, monkeypatch):
    import legacy_snapshot_lock as lock_module

    lock_path = tmp_path / lock_module.LOCK_NAME
    original_open = lock_module.os.open

    def replacing_open(path, flags, mode=0o777):
        descriptor = original_open(path, flags, mode)

        if os.fspath(path) == os.fspath(lock_path):
            replacement = tmp_path / "replacement-lock"
            replacement.write_bytes(b"replacement")
            os.replace(replacement, lock_path)

        return descriptor

    with monkeypatch.context() as patch:
        patch.setattr(lock_module.os, "open", replacing_open)

        with pytest.raises(
            PermissionError,
            match="pathname changed",
        ):
            _protected_operation(tmp_path)

    # Once the injected replacement stops, a fresh operation can
    # acquire the lock currently named by the pathname.
    assert _protected_operation(tmp_path) == "ENTERED"


def test_hard_linked_lock_file_rejected(tmp_path):
    from legacy_snapshot_lock import LOCK_NAME

    lock_path = tmp_path / LOCK_NAME
    lock_path.write_bytes(b"")

    second_name = tmp_path / "second-link"
    os.link(lock_path, second_name)

    with pytest.raises(
        PermissionError,
        match="unexpected hard links",
    ):
        _protected_operation(tmp_path)

    assert second_name.exists()
