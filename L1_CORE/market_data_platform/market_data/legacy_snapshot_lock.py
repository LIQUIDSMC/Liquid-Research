
"""Cooperative, local-filesystem lock for synthetic C-003 operations.

No distributed, adversarial, or noncooperating-process guarantees.
"""
import errno
import fcntl
import functools
import os

import legacy_snapshot_staging as staging

LOCK_NAME = ".legacy-snapshot-operation.lock"



def _verify_lock_identity(descriptor, lock_path):
    """Require the held descriptor to match the current lock pathname."""
    import stat

    opened = os.fstat(descriptor)

    if not stat.S_ISREG(opened.st_mode):
        raise PermissionError("Operation lock is not a regular file")

    try:
        named = os.lstat(lock_path)
    except FileNotFoundError as exc:
        raise PermissionError("Operation lock pathname disappeared") from exc

    if not stat.S_ISREG(named.st_mode):
        raise PermissionError("Operation lock pathname is not regular")

    if (
        opened.st_dev != named.st_dev
        or opened.st_ino != named.st_ino
    ):
        raise PermissionError("Operation lock pathname changed")

    if opened.st_nlink != 1:
        raise PermissionError("Operation lock has unexpected hard links")

def exclusive_attempt_lock(function):
    """Serialize cooperating public operations on one staging root."""

    @functools.wraps(function)
    def wrapped(staging_root, *args, **kwargs):
        root = staging._safe_directory(staging_root)
        lock_path = root / LOCK_NAME

        if lock_path.is_symlink():
            raise PermissionError("Symlinked staging operation lock")

        flags = os.O_RDWR | os.O_CREAT | os.O_NONBLOCK

        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW

        descriptor = os.open(lock_path, flags, 0o600)

        try:
            try:
                fcntl.flock(
                    descriptor,
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError as exc:
                raise PermissionError(
                    "Staging operation already in progress"
                ) from exc

            try:
                _verify_lock_identity(descriptor, lock_path)
                return function(root, *args, **kwargs)
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    return wrapped
