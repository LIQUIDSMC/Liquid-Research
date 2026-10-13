"""
Candidate C full-range scope accounting.

Synthetic-development foundation only.
No source-corpus enumeration, production access, or H2 authorization.
"""
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import re

DATASETS = frozenset({"trades", "depth_levels"})
INSTRUMENTS = frozenset({"BTC-USD", "ETH-USD"})
START_DATE = date(2026, 8, 21)
END_DATE = date(2026, 10, 6)
H2_START = date(2026, 9, 4)
H2_END = date(2026, 10, 1)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def expected_partitions():
    """Return all 94 canonical dataset/date partition identifiers."""
    result = set()
    current = START_DATE
    while current <= END_DATE:
        for dataset in DATASETS:
            result.add(f"{dataset}/date={current.isoformat()}")
        current += timedelta(days=1)
    assert len(result) == 94
    return frozenset(result)


def is_h2_partition(partition):
    """Identify the sealed H2 interval from a canonical partition."""
    validate_partition(partition)
    partition_date = date.fromisoformat(partition.split("date=", 1)[1])
    return H2_START <= partition_date <= H2_END


def validate_partition(partition):
    if not isinstance(partition, str) or partition not in expected_partitions():
        raise ValueError(f"Partition outside Candidate C scope: {partition!r}")


def _validate_digest(value):
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError("Expected SHA-256 must be 64 lowercase hex characters")


def verify_exclusion_evidence(exclusion, trusted_evidence_digests):
    """
    Verify an exclusion's supporting artifact against a caller-supplied digest.

    The expected digest must NOT come from the exclusion record itself.
    This verifies evidence bytes, not scientific adjudication.
    """
    if not isinstance(exclusion, dict) or set(exclusion) != {
        "partition",
        "adjudication_id",
        "reason",
        "evidence_path",
    }:
        raise ValueError("Invalid exclusion schema")

    for field in ("adjudication_id", "reason"):
        value = exclusion[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Invalid exclusion {field}")

    partition = exclusion["partition"]
    validate_partition(partition)

    evidence_name = exclusion["evidence_path"]
    if not isinstance(evidence_name, str) or not evidence_name:
        raise ValueError("Invalid exclusion evidence path")

    if not isinstance(trusted_evidence_digests, dict):
        raise ValueError("Missing independently supplied evidence digests")

    expected_digest = trusted_evidence_digests.get(evidence_name)
    _validate_digest(expected_digest)

    evidence_path = Path(evidence_name)
    if not evidence_path.is_absolute():
        raise ValueError("Evidence path must be absolute")
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise ValueError("Evidence artifact missing or symlinked")

    actual_digest = sha256(evidence_path.read_bytes()).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError("Exclusion evidence SHA-256 mismatch")

    return {
        **exclusion,
        "evidence_sha256": actual_digest,
    }


def build_scope_accounting(
    observed_coverage,
    sanctioned_exclusions,
    trusted_evidence_digests,
):
    """
    Enforce E = O disjoint-union S disjoint-union U.

    observed_coverage maps canonical partition to observed instruments.
    A partition counts as observed only when BOTH instruments are present.
    Caller must supply coverage derived from validated source-file records.
    This function does not independently validate source-file bytes.
    """
    expected = expected_partitions()

    if not isinstance(observed_coverage, dict):
        raise ValueError("Observed coverage must be a mapping")
    if not isinstance(sanctioned_exclusions, list):
        raise ValueError("Sanctioned exclusions must be a list")

    observed = set()
    normalized_coverage = {}

    for partition, instruments in observed_coverage.items():
        validate_partition(partition)

        if (
            not isinstance(instruments, (list, tuple, set, frozenset))
            or any(not isinstance(item, str) for item in instruments)
            or len(instruments) != len(set(instruments))
        ):
            raise ValueError("Invalid instrument coverage")

        instrument_set = set(instruments)
        if not instrument_set.issubset(INSTRUMENTS):
            raise ValueError("Unexpected instrument in observed coverage")

        if instrument_set != INSTRUMENTS:
            raise ValueError(
                f"Partial instrument coverage is not a complete partition: "
                f"{partition}"
            )

        observed.add(partition)
        normalized_coverage[partition] = sorted(instrument_set)

    sanctioned = {}
    for exclusion in sanctioned_exclusions:
        verified = verify_exclusion_evidence(
            exclusion, trusted_evidence_digests
        )
        partition = verified["partition"]

        if partition in observed:
            raise ValueError(
                f"Exclusion contradicts validated coverage: {partition}"
            )
        if partition in sanctioned:
            raise ValueError(f"Duplicate exclusion: {partition}")

        sanctioned[partition] = verified

    sanctioned_set = set(sanctioned)
    unexplained = expected - observed - sanctioned_set

    if (
        observed & sanctioned_set
        or observed & unexplained
        or sanctioned_set & unexplained
        or observed | sanctioned_set | unexplained != expected
    ):
        raise AssertionError("Partition accounting invariant violated")

    if unexplained:
        classification = "INCOMPLETE"
    elif sanctioned:
        classification = "VERIFIED_WITH_SANCTIONED_EXCLUSIONS"
    else:
        classification = "FULL_SCOPE_VERIFIED"

    return {
        "scope_schema_version": 1,
        "expected_partitions": sorted(expected),
        "observed_coverage": normalized_coverage,
        "sanctioned_exclusions": [
            sanctioned[key] for key in sorted(sanctioned)
        ],
        "unexplained_gaps": sorted(unexplained),
        "classification": classification,
        "point_in_time_complete": False,
        "scientific_readiness": "PENDING",
    }
