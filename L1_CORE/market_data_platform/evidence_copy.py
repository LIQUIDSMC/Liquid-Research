"""Increment 2: copy prepared synthetic bundles under a cooperative lock.

No research execution, cleanup, second-copy verification, or production use.
COPY_VERIFIED is not preservation-complete or cleanup authorization.
"""
import fcntl
import hashlib
import json
import math
import os
import shutil
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from L1_CORE.market_data_platform import evidence_preservation as ep

LOCK_NAME = ".preservation.lock"
LIMIT_FIELDS = ep.LIMIT_FIELDS | {"min_free_bytes_after_copy"}


class CopyError(ep.VerificationError):
    """Machine-readable failure, optionally including a reporting failure."""

    def __init__(self, code, message, *, reporting_error=None):
        super().__init__(message)
        self.code = code
        self.reporting_error = reporting_error


def _require(condition, code, message):
    if not condition:
        raise CopyError(code, message)


def _validate_limits(limits):
    ep._schema(limits, LIMIT_FIELDS, "copy limits")
    for name in ep.LIMIT_FIELDS - {"max_runtime_seconds"}:
        ep._require(type(limits[name]) is int and limits[name] > 0,
                    f"Invalid limit: {name}")
    seconds = limits["max_runtime_seconds"]
    ep._require(type(seconds) in {int, float} and
                math.isfinite(seconds) and seconds > 0,
                "Invalid limit: max_runtime_seconds")
    reserve = limits["min_free_bytes_after_copy"]
    ep._require(type(reserve) is int and reserve >= 0,
                "Invalid limit: min_free_bytes_after_copy")


def _root(value):
    root = Path(value)
    ep._require(root.is_absolute() and str(root) == str(root.resolve()),
                "Root must be absolute and canonical")
    ep._require(root.is_dir(), "Missing directory root")
    return root


class _Budget:
    def __init__(self, seconds, clock):
        self.clock = clock
        self.deadline = clock() + seconds

    def remaining(self):
        remaining = self.deadline - self.clock()
        _require(remaining > 0, "RESOURCE_LIMIT", "Operation runtime exhausted")
        return remaining

    def verifier_limits(self, limits):
        derived = {name: limits[name] for name in ep.LIMIT_FIELDS}
        derived["max_runtime_seconds"] = self.remaining()
        return derived


def _lock_identity(descriptor, pathname):
    opened = os.fstat(descriptor)
    try:
        named = pathname.lstat()
    except FileNotFoundError as exc:
        raise CopyError("LOCK_INVALID", "Operation lock pathname disappeared") from exc
    _require(
        stat.S_ISREG(opened.st_mode) and stat.S_ISREG(named.st_mode)
        and opened.st_nlink == 1
        and (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino),
        "LOCK_INVALID", "Invalid or replaced operation lock",
    )


@contextmanager
def _destination_lock(root):
    pathname = root / LOCK_NAME
    _require(not pathname.is_symlink(), "LOCK_INVALID", "Symlinked operation lock")
    flags = os.O_RDWR | os.O_CREAT | os.O_NONBLOCK
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(pathname, flags, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CopyError("LOCK_BUSY", "Preservation operation already in progress") from exc
        try:
            _lock_identity(descriptor, pathname)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _verify(root, anchors, limits, budget, phase):
    phase_limits = budget.verifier_limits(limits)
    try:
        verified = ep.verify_bundle(
            root, **anchors, limits=phase_limits, clock=budget.clock
        )
    except ep.RuntimeLimitExceeded as exc:
        raise CopyError("RESOURCE_LIMIT", "Verifier runtime exhausted") from exc
    except ep.VerificationError as exc:
        code = (
            "DESTINATION_VERIFICATION_FAILED"
            if phase == "destination" else "SOURCE_INVALID"
        )
        raise CopyError(code, f"{phase.capitalize()} verification failed") from exc
    budget.remaining()
    return verified


def _capacity(root, required, reserve):
    _require(shutil.disk_usage(root).free >= required + reserve,
             "RESOURCE_LIMIT", "Insufficient destination capacity")


def _record(anchors, state, error_code=None):
    return {
        "schema_version": 1,
        "run_id": anchors["expected_run_id"],
        "attempt_id": anchors["expected_attempt_id"],
        "expected_manifest_sha256": anchors["expected_manifest_sha256"],
        "state": state,
        "error_code": error_code,
    }


def _publish_control(attempt, record, budget=None):
    """Exclusive temporary write, fsync, replace, and directory fsync.

    Failure reporting can call this without an operational deadline.
    Interrupted temporary records are retained, never interpreted as success.
    """
    if budget is not None:
        budget.remaining()
    temporary = attempt / f".attempt-{uuid.uuid4().hex}.tmp"
    raw = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    if budget is not None:
        budget.remaining()
    os.replace(temporary, attempt / "attempt.json")
    descriptor = os.open(attempt, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _capture_source(source, anchors, limits, budget):
    """Capture externally anchored control bytes before source verification."""
    reader = ep._Reader(source, budget.verifier_limits(limits), budget.clock)
    metadata_names = ep.CONTROLS | {ep.SINGLETONS["PROVENANCE"]}
    ep._require(
        all(name in reader.initial and stat.S_ISREG(reader.initial[name][2])
            for name in metadata_names), "Missing source metadata",
    )
    ep._require(
        sum(reader.initial[name][3] for name in metadata_names)
        <= limits["max_metadata_bytes"], "Metadata byte limit exceeded",
    )
    manifest_digest, raw_manifest = reader.read("manifest.json", collect=True)
    ep._require(manifest_digest == anchors["expected_manifest_sha256"],
                "External manifest digest mismatch")
    list_digest, raw_list = reader.read("artifact_list.json", collect=True)
    ep._require(list_digest == anchors["expected_artifact_list_sha256"],
                "External artifact-list digest mismatch")
    budget.remaining()
    return reader, raw_manifest, raw_list


def _copy_file(reader, name, payload, expected, budget, capacity_root,
               bytes_remaining, reserve):
    budget.remaining()
    source_file = reader.root / name
    initial = reader.initial[name]
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source_file, flags)
    copied = 0
    hasher = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as source_handle:
        _require(ep._signature(os.fstat(source_handle.fileno())) == initial,
                 "SOURCE_CHANGED", "Source changed before copy")
        destination = payload / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as destination_handle:
            while True:
                budget.remaining()
                _capacity(capacity_root, bytes_remaining - copied, reserve)
                chunk = source_handle.read(65536)
                if not chunk:
                    break
                copied += len(chunk)
                _require(copied <= expected[0], "SOURCE_CHANGED",
                         "Source grew during copy")
                destination_handle.write(chunk)
                hasher.update(chunk)
            destination_handle.flush()
        _require(ep._signature(os.fstat(source_handle.fileno())) == initial,
                 "SOURCE_CHANGED", "Source changed during copy")
    _require(ep._signature(source_file.lstat()) == initial,
             "SOURCE_CHANGED", "Source pathname changed")
    _require(copied == expected[0] and hasher.hexdigest() == expected[1],
             "SOURCE_CHANGED", "Copied bytes disagree with anchored inventory")


def _copy_synthetic_bundle(
    source_root, destination_root, expected_run_id, expected_attempt_id,
    expected_manifest_sha256, expected_predeclaration_sha256,
    expected_artifact_list_sha256, limits, *, clock=time.monotonic,
):
    """Copy only prepared synthetic evidence; retain partial failed attempts."""
    _validate_limits(limits)
    limits = dict(limits)
    for value in (expected_run_id, expected_attempt_id):
        ep._uuid(value)
    for value in (expected_manifest_sha256, expected_predeclaration_sha256,
                  expected_artifact_list_sha256):
        ep._digest(value)
    budget = _Budget(limits["max_runtime_seconds"], clock)
    source, destination = _root(source_root), _root(destination_root)
    _require(
        source != destination
        and not source.is_relative_to(destination)
        and not destination.is_relative_to(source),
        "INVALID_ROOTS", "Source and destination must not overlap",
    )
    anchors = {
        "expected_run_id": expected_run_id,
        "expected_attempt_id": expected_attempt_id,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_predeclaration_sha256": expected_predeclaration_sha256,
        "expected_artifact_list_sha256": expected_artifact_list_sha256,
    }
    with _destination_lock(destination):
        budget.remaining()
        attempts = destination / "attempts"
        _require(not attempts.is_symlink(), "INVALID_ROOTS",
                 "Symlinked attempts directory")
        if attempts.exists():
            _require(attempts.is_dir(), "INVALID_ROOTS",
                     "Attempts path is not a directory")
        attempt = attempts / expected_attempt_id
        _require(not attempt.exists() and not attempt.is_symlink(),
                 "ATTEMPT_EXISTS", "Attempt already exists")

        # Capture anchored bytes first, then verify the same stable tree.
        try:
            reader, raw_manifest, raw_list = _capture_source(
                source, anchors, limits, budget
            )
        except ep.RuntimeLimitExceeded as exc:
            raise CopyError("RESOURCE_LIMIT", "Source capture runtime exhausted") from exc
        except ep.VerificationError as exc:
            raise CopyError("SOURCE_INVALID", "Source capture failed") from exc
        _verify(source, anchors, limits, budget, "source")
        try:
            _require(reader.scan() == reader.initial,
                     "SOURCE_CHANGED", "Source changed during verification")
        except ep.RuntimeLimitExceeded as exc:
            raise CopyError("RESOURCE_LIMIT", "Source scan runtime exhausted") from exc
        except ep.VerificationError as exc:
            raise CopyError("SOURCE_CHANGED", "Source changed during verification") from exc
        manifest = ep._json(raw_manifest)
        expected = {
            "manifest.json": (len(raw_manifest), expected_manifest_sha256),
            "artifact_list.json": (len(raw_list), expected_artifact_list_sha256),
        }
        for entry in manifest["artifacts"]:
            budget.remaining()
            expected[entry["relative_path"]] = (entry["size_bytes"], entry["sha256"])
        total = sum(size for size, _ in expected.values())
        _require(total <= limits["max_logical_bytes"], "RESOURCE_LIMIT",
                 "Logical byte limit exceeded")
        reserve = limits["min_free_bytes_after_copy"]
        _capacity(destination, total, reserve)
        budget.remaining()
        attempts.mkdir(exist_ok=True)
        attempt.mkdir(exist_ok=False)
        payload = attempt / "payload"
        try:
            _publish_control(attempt, _record(anchors, "INCOMPLETE"), budget)
            payload.mkdir()
            remaining_bytes = total
            for name, expected_file in sorted(expected.items()):
                _copy_file(
                    reader, name, payload, expected_file, budget,
                    destination, remaining_bytes, reserve,
                )
                remaining_bytes -= expected_file[0]
            budget.remaining()
            _require(reader.scan() == reader.initial,
                     "SOURCE_CHANGED", "Source inventory changed during copy")
            verified = _verify(payload, anchors, limits, budget, "destination")
            budget.remaining()
            _require(reader.scan() == reader.initial,
                     "SOURCE_CHANGED", "Source changed before publication")
            budget.remaining()
            # Successful publication is the commit point. Do not downgrade
            # this verified state merely because time elapses afterward.
            _publish_control(attempt, _record(anchors, "COPY_VERIFIED"), budget)
            return {
                "classification": "COPY_VERIFIED",
                "attempt_root": str(attempt),
                "verification": verified,
            }
        except Exception as exc:
            if isinstance(exc, CopyError):
                failure = exc
            elif isinstance(exc, ep.RuntimeLimitExceeded):
                failure = CopyError("RESOURCE_LIMIT", "Source scan runtime exhausted")
            elif isinstance(exc, ep.VerificationError):
                failure = CopyError("SOURCE_CHANGED", "Source changed during copy")
            else:
                failure = CopyError("COPY_IO_ERROR", "Copy operation failed")
            try:
                _publish_control(
                    attempt, _record(anchors, "INCOMPLETE", failure.code)
                )
            except Exception as reporting:
                raise CopyError(
                    failure.code, str(failure), reporting_error=reporting
                ) from exc
            if failure is exc:
                raise
            raise failure from exc


def copy_synthetic_bundle(
    source_root, destination_root, expected_run_id, expected_attempt_id,
    expected_manifest_sha256, expected_predeclaration_sha256,
    expected_artifact_list_sha256, limits, *, clock=time.monotonic,
):
    """Public synthetic copy API; classified operational failures are CopyError.

    INVALID_INPUT is a pre-attempt failure, never an attempt error_code.
    Successful COPY_VERIFIED publication commits the successful outcome.
    """
    try:
        return _copy_synthetic_bundle(
            source_root, destination_root, expected_run_id, expected_attempt_id,
            expected_manifest_sha256, expected_predeclaration_sha256,
            expected_artifact_list_sha256, limits, clock=clock,
        )
    except CopyError:
        raise
    except ep.RuntimeLimitExceeded as exc:
        raise CopyError("RESOURCE_LIMIT", "Operation runtime exhausted") from exc
    except ep.VerificationError as exc:
        raise CopyError("INVALID_INPUT", str(exc)) from exc
    except OSError as exc:
        raise CopyError("COPY_IO_ERROR", "Copy filesystem operation failed") from exc
