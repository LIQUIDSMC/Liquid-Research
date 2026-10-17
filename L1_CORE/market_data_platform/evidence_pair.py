"""Read-only, synthetic-only verification of two anchored evidence bundles.

Distinct directory locations do not establish independent storage failure
domains. Results are returned in memory; this module publishes no status,
repairs no evidence, and authorizes no deletion or experiment adoption.
"""
import math
import time
from pathlib import Path

from L1_CORE.market_data_platform import evidence_preservation as ep


class PairInputError(ValueError):
    """Invalid caller inputs or roots, detected before content verification.

    This intentionally remains a plain ValueError: caller-input exceptions
    are separate from content failures, which are returned in the report.
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _validate_inputs(anchors, limits, clock):
    try:
        ep._uuid(anchors["expected_run_id"])
        ep._uuid(anchors["expected_attempt_id"])
        for field in (
            "expected_manifest_sha256",
            "expected_predeclaration_sha256",
            "expected_artifact_list_sha256",
        ):
            ep._digest(anchors[field])
        ep._schema(limits, ep.LIMIT_FIELDS, "limits")
        for field in ep.LIMIT_FIELDS - {"max_runtime_seconds"}:
            ep._require(
                type(limits[field]) is int and limits[field] > 0,
                f"Invalid limit: {field}",
            )
        seconds = limits["max_runtime_seconds"]
        ep._require(
            type(seconds) in {int, float}
            and math.isfinite(seconds)
            and seconds > 0,
            "Invalid limit: max_runtime_seconds",
        )
        ep._require(callable(clock), "Clock must be callable")
    except ep.VerificationError as exc:
        raise PairInputError("INVALID_INPUT", str(exc)) from exc
    return dict(limits)


def _roots(primary_root, secondary_root):
    try:
        roots = []
        identities = []
        for value in (primary_root, secondary_root):
            root = Path(value)
            if not root.is_absolute() or str(root) != str(root.resolve()):
                raise PairInputError(
                    "INVALID_ROOTS", "Roots must be absolute and canonical"
                )
            if not root.is_dir():
                raise PairInputError(
                    "INVALID_ROOTS", "Roots must be existing directories"
                )
            info = root.stat()
            roots.append(root)
            identities.append((info.st_dev, info.st_ino))

        primary, secondary = roots
        if (
            primary == secondary
            or primary in secondary.parents
            or secondary in primary.parents
            or identities[0] == identities[1]
        ):
            raise PairInputError(
                "INVALID_ROOTS", "Roots must be distinct and nonoverlapping"
            )
        return primary, secondary
    except PairInputError:
        raise
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        raise PairInputError(
            "INVALID_ROOTS", "Unable to validate bundle roots"
        ) from exc


def _not_attempted():
    return {
        "status": "NOT_ATTEMPTED",
        "error_code": "NOT_ATTEMPTED",
        "verification": None,
    }


def _failed(code):
    return {
        "status": "FAILED",
        "error_code": code,
        "verification": None,
    }


def verify_synthetic_pair(
    primary_root,
    secondary_root,
    *,
    expected_run_id,
    expected_attempt_id,
    expected_manifest_sha256,
    expected_predeclaration_sha256,
    expected_artifact_list_sha256,
    limits,
    clock=time.monotonic,
):
    """Verify both copies against external anchors with one shared deadline.

    A copy's result reflects only its own verifier call. Subsequent deadline
    checks can stop further work and invalidate operation-level success,
    but cannot erase established verification results or relabel failures.
    Unexpected programming exceptions propagate to the caller.
    """
    anchors = {
        "expected_run_id": expected_run_id,
        "expected_attempt_id": expected_attempt_id,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_predeclaration_sha256": expected_predeclaration_sha256,
        "expected_artifact_list_sha256": expected_artifact_list_sha256,
    }
    validated_limits = _validate_inputs(anchors, limits, clock)

    # Established before any filesystem inspection.
    deadline = clock() + validated_limits["max_runtime_seconds"]
    primary, secondary = _roots(primary_root, secondary_root)

    results = [_not_attempted(), _not_attempted()]
    budget_exhausted = False

    for index, root in enumerate((primary, secondary)):
        remaining = deadline - clock()
        if remaining <= 0:
            budget_exhausted = True
            break

        phase_limits = dict(validated_limits)
        phase_limits["max_runtime_seconds"] = remaining
        verifier_exhausted = False
        try:
            verification = ep.verify_bundle(
                root,
                **anchors,
                limits=phase_limits,
                clock=clock,
            )
        except ep.RuntimeLimitExceeded:
            results[index] = _failed("RESOURCE_LIMIT")
            verifier_exhausted = True
            budget_exhausted = True
        except ep.VerificationError:
            results[index] = _failed("VERIFICATION_FAILED")
        except OSError:
            results[index] = _failed("IO_ERROR")
        else:
            results[index] = {
                "status": "VERIFIED",
                "error_code": None,
                "verification": verification,
            }

        # Preserve the established per-copy result, including unrelated
        # verification or I/O failures coinciding with deadline exhaustion.
        post_call_exhausted = deadline - clock() <= 0
        if post_call_exhausted:
            budget_exhausted = True
        if verifier_exhausted or post_call_exhausted:
            break

    # This check changes only operation-level budget/classification.
    if deadline - clock() <= 0:
        budget_exhausted = True

    pair_verified = (
        not budget_exhausted
        and all(result["status"] == "VERIFIED" for result in results)
    )
    return {
        "report_schema_version": 1,
        "classification": (
            "PAIR_VERIFIED" if pair_verified else "PAIR_NOT_VERIFIED"
        ),
        "run_id": expected_run_id,
        "attempt_id": expected_attempt_id,
        "manifest_sha256": expected_manifest_sha256,
        "budget_exhausted": budget_exhausted,
        "primary": results[0],
        "secondary": results[1],
        "storage_independence": "NOT_ATTESTED",
    }
