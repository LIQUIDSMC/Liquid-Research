"""Synthetic-only publication of externally anchored pair reports.

Neither evidence tree is modified. Report publication does not authorize
cleanup, establish storage independence, or certify preservation complete.
"""
import json
import os
import time
import uuid
from pathlib import Path

from L1_CORE.market_data_platform import evidence_pair as pair
from L1_CORE.market_data_platform import evidence_preservation as ep

MAX_RECORD_BYTES = 65536
WRITE_CHUNK_BYTES = 16384


class ReportError(ValueError):
    """Reporting failure with explicit publication and cleanup state."""

    def __init__(
        self, code, message, *, pair_report=None, published=False,
        cleanup_failed=False,
    ):
        super().__init__(message)
        self.code = code
        self.pair_report = pair_report
        self.published = published
        self.cleanup_failed = cleanup_failed


def _lexical_root(value):
    if not isinstance(value, (str, Path)):
        raise ReportError("INVALID_INPUT", "Invalid root type")
    raw = str(value)
    if (
        not raw
        or "\x00" in raw
        or not Path(raw).is_absolute()
        or any(component in {".", ".."} for component in raw.split("/"))
    ):
        raise ReportError("INVALID_INPUT", "Invalid absolute root syntax")
    return Path(raw)


def _validate_inputs(
    primary_root, secondary_root, report_directory, report_id,
    anchors, limits, clock,
):
    try:
        ep._uuid(report_id)
        validated_limits = pair._validate_inputs(anchors, limits, clock)
    except (ep.VerificationError, pair.PairInputError) as exc:
        raise ReportError("INVALID_INPUT", "Invalid report inputs") from exc
    roots = tuple(
        _lexical_root(value)
        for value in (primary_root, secondary_root, report_directory)
    )
    return roots, validated_limits


def _validated_roots(primary, secondary, directory):
    try:
        primary, secondary = pair._roots(primary, secondary)
        if (
            str(directory) != str(directory.resolve())
            or not directory.is_dir()
        ):
            raise ReportError(
                "INVALID_ROOTS", "Invalid report directory"
            )
        directory_info = directory.stat()
        directory_identity = (directory_info.st_dev, directory_info.st_ino)
        for evidence in (primary, secondary):
            info = evidence.stat()
            if (
                directory == evidence
                or directory in evidence.parents
                or evidence in directory.parents
                or directory_identity == (info.st_dev, info.st_ino)
            ):
                raise ReportError(
                    "INVALID_ROOTS", "Report and evidence locations overlap"
                )
    except ReportError:
        raise
    except (pair.PairInputError, OSError, ValueError, RuntimeError) as exc:
        raise ReportError(
            "INVALID_ROOTS", "Unable to validate report locations"
        ) from exc
    return primary, secondary, directory


def _remaining(deadline, clock, report=None):
    remaining = deadline - clock()
    if remaining <= 0:
        raise ReportError(
            "RESOURCE_LIMIT", "Reporting runtime exhausted",
            pair_report=report,
        )
    return remaining


def _sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _record_bytes(report_id, anchors, report):
    record = {
        "record_schema_version": 1,
        "report_id": report_id,
        "expected_predeclaration_sha256":
            anchors["expected_predeclaration_sha256"],
        "expected_artifact_list_sha256":
            anchors["expected_artifact_list_sha256"],
        "pair_report": report,
    }
    raw = (
        json.dumps(
            record, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
    if len(raw) > MAX_RECORD_BYTES:
        raise ReportError(
            "RESOURCE_LIMIT", "Report record size exceeded",
            pair_report=report,
        )
    return raw


def _check_pair_result(report):
    classification = report["classification"]
    exhausted = report["budget_exhausted"]
    if (
        type(exhausted) is not bool
        or classification not in {"PAIR_VERIFIED", "PAIR_NOT_VERIFIED"}
        or (classification == "PAIR_VERIFIED" and exhausted)
    ):
        raise RuntimeError("Invalid internal pair-report outcome")
    if exhausted:
        raise ReportError(
            "RESOURCE_LIMIT", "Pair verification exhausted its budget",
            pair_report=report,
        )


def verify_and_record_synthetic_pair(
    primary_root,
    secondary_root,
    report_directory,
    report_id,
    *,
    expected_run_id,
    expected_attempt_id,
    expected_manifest_sha256,
    expected_predeclaration_sha256,
    expected_artifact_list_sha256,
    limits,
    clock=time.monotonic,
):
    """Verify and exclusively publish a bounded synthetic pair report.

    Requires quiescent evidence and a trusted local report directory.
    Cooperating publishers cannot overwrite an existing final record.
    No safety against noncooperating directory mutation is claimed.
    """
    anchors = {
        "expected_run_id": expected_run_id,
        "expected_attempt_id": expected_attempt_id,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_predeclaration_sha256": expected_predeclaration_sha256,
        "expected_artifact_list_sha256": expected_artifact_list_sha256,
    }
    roots, validated_limits = _validate_inputs(
        primary_root, secondary_root, report_directory, report_id,
        anchors, limits, clock,
    )
    deadline = clock() + validated_limits["max_runtime_seconds"]
    primary, secondary, directory = _validated_roots(*roots)

    final = directory / f"{report_id}.json"
    report = None
    temporary = None
    temporary_owned = False
    descriptor = None
    published = False
    failure = None
    failure_cause = None

    try:
        _remaining(deadline, clock)
        # lstat also detects dangling symlinks and existing directories.
        try:
            final.lstat()
        except FileNotFoundError:
            pass
        else:
            raise ReportError("REPORT_EXISTS", "Report destination occupied")

        phase_limits = dict(validated_limits)
        phase_limits["max_runtime_seconds"] = _remaining(deadline, clock)
        report = pair.verify_synthetic_pair(
            primary, secondary, **anchors, limits=phase_limits, clock=clock,
        )
        _check_pair_result(report)
        _remaining(deadline, clock, report)
        raw = _record_bytes(report_id, anchors, report)
        _remaining(deadline, clock, report)

        temporary = directory / f".report-{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(temporary, flags, 0o600)
        temporary_owned = True

        offset = 0
        while offset < len(raw):
            _remaining(deadline, clock, report)
            written = os.write(
                descriptor, raw[offset:offset + WRITE_CHUNK_BYTES]
            )
            if written <= 0:
                raise OSError("Report write made no progress")
            offset += written

        _remaining(deadline, clock, report)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        _remaining(deadline, clock, report)

        try:
            os.link(temporary, final)
        except FileExistsError as exc:
            raise ReportError(
                "REPORT_EXISTS", "Report destination occupied",
                pair_report=report,
            ) from exc
        published = True

        # Final-link creation is the commit point. No subsequent deadline
        # check may undo publication or alter established pair results.
        try:
            _sync_directory(directory)
        except OSError as exc:
            raise ReportError(
                "PUBLICATION_DURABILITY_UNCERTAIN",
                "Report linked but directory synchronization failed",
                pair_report=report, published=True,
            ) from exc

    except BaseException as exc:
        if isinstance(exc, ReportError):
            failure = exc
        elif isinstance(exc, OSError):
            failure = ReportError(
                "REPORT_IO_ERROR", "Report filesystem operation failed",
                pair_report=report, published=published,
            )
            failure_cause = exc
        else:
            # Preserve PairInputError and unexpected programming exceptions.
            failure = exc

    cleanup_failed = False
    if descriptor is not None:
        try:
            os.close(descriptor)
        except OSError:
            cleanup_failed = True
    if temporary_owned:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            cleanup_failed = True

    if failure is not None:
        if isinstance(failure, ReportError):
            failure.cleanup_failed = cleanup_failed
        elif cleanup_failed:
            failure.add_note("Report temporary-file cleanup also failed")
        if failure_cause is not None:
            raise failure from failure_cause
        raise failure

    if cleanup_failed:
        raise ReportError(
            "REPORT_IO_ERROR", "Report temporary-file cleanup failed",
            pair_report=report, published=published, cleanup_failed=True,
        )

    return {
        "publication": "REPORT_RECORDED",
        "report_location": str(final),
        "pair_report": report,
    }
