"""Synthetic tests for Candidate C full-range scope accounting."""
import hashlib
from pathlib import Path

import pytest

import legacy_snapshot_scope as scope


@pytest.fixture
def expected():
    return scope.expected_partitions()


@pytest.fixture
def evidence(tmp_path):
    path = tmp_path / "adjudication.txt"
    path.write_text("Synthetic LRS3 exclusion adjudication evidence")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, {str(path): digest}


def exclusion(partition, path):
    return {
        "partition": partition,
        "adjudication_id": "SYNTHETIC-ADJ-001",
        "reason": "Synthetic exclusion fixture",
        "evidence_path": str(path),
    }


def test_expected_scope_counts(expected):
    assert len(expected) == 94
    assert sum(map(scope.is_h2_partition, expected)) == 56
    assert sum(not scope.is_h2_partition(p) for p in expected) == 38


def test_empty_coverage_is_incomplete(expected):
    result = scope.build_scope_accounting({}, [], {})
    assert result["classification"] == "INCOMPLETE"
    assert set(result["unexplained_gaps"]) == expected


def test_complete_coverage_is_full_scope_verified(expected):
    observed = {p: sorted(scope.INSTRUMENTS) for p in expected}
    result = scope.build_scope_accounting(observed, [], {})
    assert result["classification"] == "FULL_SCOPE_VERIFIED"
    assert not result["unexplained_gaps"]


def test_sanctioned_exclusion_is_separate_bucket(expected, evidence):
    path, trusted = evidence
    excluded = sorted(expected)[0]
    observed = {
        p: sorted(scope.INSTRUMENTS)
        for p in expected
        if p != excluded
    }
    result = scope.build_scope_accounting(
        observed, [exclusion(excluded, path)], trusted
    )
    assert result["classification"] == "VERIFIED_WITH_SANCTIONED_EXCLUSIONS"
    assert len(result["sanctioned_exclusions"]) == 1
    assert not result["unexplained_gaps"]
    assert excluded not in result["observed_coverage"]


def test_preemptive_exclusion_conflicts_with_observation(expected, evidence):
    path, trusted = evidence
    partition = sorted(expected)[0]
    with pytest.raises(ValueError, match="contradicts"):
        scope.build_scope_accounting(
            {partition: sorted(scope.INSTRUMENTS)},
            [exclusion(partition, path)],
            trusted,
        )


def test_duplicate_exclusions_rejected(expected, evidence):
    path, trusted = evidence
    item = exclusion(sorted(expected)[0], path)
    with pytest.raises(ValueError, match="Duplicate"):
        scope.build_scope_accounting({}, [item, item], trusted)


def test_missing_external_digest_rejected(expected, evidence):
    path, _ = evidence
    with pytest.raises(ValueError, match="Expected SHA-256"):
        scope.build_scope_accounting(
            {}, [exclusion(sorted(expected)[0], path)], {}
        )


def test_tampered_evidence_rejected(expected, evidence):
    path, trusted = evidence
    path.write_text("Tampered evidence")
    with pytest.raises(ValueError, match="mismatch"):
        scope.build_scope_accounting(
            {}, [exclusion(sorted(expected)[0], path)], trusted
        )


def test_partial_instrument_coverage_rejected(expected):
    with pytest.raises(ValueError, match="Partial instrument"):
        scope.build_scope_accounting(
            {sorted(expected)[0]: ["BTC-USD"]}, [], {}
        )


def test_out_of_scope_partition_rejected():
    with pytest.raises(ValueError, match="outside Candidate C scope"):
        scope.build_scope_accounting(
            {"trades/date=2026-10-07": sorted(scope.INSTRUMENTS)},
            [],
            {},
        )


def test_partition_buckets_are_disjoint_and_exhaustive(expected, evidence):
    path, trusted = evidence
    partitions = sorted(expected)
    observed = {partitions[0]: sorted(scope.INSTRUMENTS)}
    result = scope.build_scope_accounting(
        observed,
        [exclusion(partitions[1], path)],
        trusted,
    )

    o = set(result["observed_coverage"])
    s = {item["partition"] for item in result["sanctioned_exclusions"]}
    u = set(result["unexplained_gaps"])

    assert not (o & s)
    assert not (o & u)
    assert not (s & u)
    assert o | s | u == expected


def test_symlinked_evidence_rejected(expected, evidence, tmp_path):
    path, trusted = evidence
    link = tmp_path / "linked-evidence.txt"
    link.symlink_to(path)
    trusted[str(link)] = trusted[str(path)]
    with pytest.raises(ValueError, match="symlinked"):
        scope.build_scope_accounting(
            {}, [exclusion(sorted(expected)[0], link)], trusted
        )


def test_c003_arch_002_shared_scope_consistency():
    """Reject divergence between scope, export, and authorization."""
    from datetime import timedelta

    from L1_CORE.market_data_platform.market_data import (
        legacy_snapshot_scope as scope,
        legacy_snapshot_export as export,
    )

    import legacy_snapshot_authorization as authorization

    assert export.START_DATE == scope.START_DATE
    assert export.END_DATE == scope.END_DATE
    assert export.H2_START == scope.H2_START
    assert export.H2_END == scope.H2_END

    assert export.INSTRUMENTS == scope.INSTRUMENTS
    assert frozenset(export.DATASETS) == scope.DATASETS

    assert authorization.WINDOWS["H2"] == [
        [scope.H2_START.isoformat(), scope.H2_END.isoformat()]
    ]

    assert authorization.WINDOWS["NON_H2"] == [
        [
            scope.START_DATE.isoformat(),
            (scope.H2_START - timedelta(days=1)).isoformat(),
        ],
        [
            (scope.H2_END + timedelta(days=1)).isoformat(),
            scope.END_DATE.isoformat(),
        ],
    ]
