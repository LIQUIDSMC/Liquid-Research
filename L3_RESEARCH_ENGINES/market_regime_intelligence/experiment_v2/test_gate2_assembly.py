"""Synthetic integration regression tests for Experiment-v2 Gate 2."""

from dataclasses import replace

import numpy as np
import pytest

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_assembly import (
    assemble_gate2,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.test_gate2_numeric import (
    make_case as make_observations,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.test_gate2_episodes import (
    make_case as make_episodes,
)


def aligned_case(lengths, *, final_invalid=False):
    d4 = make_episodes(lengths, final_invalid=final_invalid)

    states = [
        d4.episodes[int(i)].state if i >= 0 else "INVALID"
        for i in d4.episode_id_by_endpoint
    ]

    d1, d3 = make_observations(states)

    assert np.array_equal(d3.endpoint_ms, d4.endpoint_ms)
    return d1, d3, d4


def test_completed_evidence_retains_all_reasons():
    d1, d3, d4 = aligned_case([1] * 10, final_invalid=True)

    result = assemble_gate2(d1, d3, d4)

    assert result.integrity is None
    assert result.completed is not None
    assert result.completed.evidence.reasons == frozenset({
        "EXCESSIVE_EPISODE_TURNOVER",
        "EXCESSIVE_REGIME_INELIGIBILITY",
    })


def test_structural_terminal_dominates_directional():
    d1, d3, d4 = aligned_case([1] * 10, final_invalid=True)

    result = assemble_gate2(d1, d3, d4)

    assert result.completed.evidence.action == "TERMINATE_INSTRUMENT_V1"
    assert result.completed.evidence.disposition == "STRUCTURALLY_INSUFFICIENT"


def test_zero_structural_episodes_are_legitimate():
    d1, d3, d4 = aligned_case([])

    result = assemble_gate2(d1, d3, d4)

    assert result.integrity is None
    assert result.completed is not None
    assert result.observations.n_eligible == 0
    assert result.episodes.k_total == 0
    assert result.episodes.turnover_status == (
        "NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES"
    )
    assert result.episodes.persistence_status == (
        "NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES"
    )
    assert "INSUFFICIENT_STATE_EPISODE_SUPPORT" in (
        result.completed.evidence.reasons
    )


def test_mismatched_endpoint_domains_fail_closed():
    d1, d3, d4 = aligned_case([2, 2], final_invalid=True)

    bad_d4 = replace(
        d4,
        endpoint_ms=d4.endpoint_ms + 300000,
    )

    result = assemble_gate2(d1, d3, bad_d4)

    assert result.completed is None
    assert result.integrity is not None
    assert result.integrity.tag == "INTEGRITY_FAILURE"


def test_corrupted_episode_assignment_fails_closed():
    d1, d3, d4 = aligned_case([2, 2], final_invalid=True)

    bad_ids = d4.episode_id_by_endpoint.copy()
    bad_ids[0] = -1

    result = assemble_gate2(
        d1,
        d3,
        replace(d4, episode_id_by_endpoint=bad_ids),
    )

    assert result.completed is None
    assert result.integrity is not None


def test_window_identity_mismatch_fails_closed():
    d1, d3, d4 = aligned_case([2, 2], final_invalid=True)

    result = assemble_gate2(
        d1,
        replace(d3, window="24h"),
        d4,
    )

    assert result.completed is None
    assert result.integrity is not None


def test_invalid_d1_day_exposure_fails_closed():
    d1, d3, d4 = aligned_case([2, 2], final_invalid=True)

    bad_status = replace(
        d1.day_statuses[0],
        candidate_count=999,
    )

    result = assemble_gate2(
        replace(d1, day_statuses=(bad_status,)),
        d3,
        d4,
    )

    assert result.completed is None
    assert result.integrity is not None


@pytest.mark.parametrize(
    "lengths,final_invalid",
    [
        ([1] * 10, True),
        ([2, 2], True),
        ([24, 96], True),
        ([1] * 5 + [120], False),
    ],
)
def test_completed_reason_union_matches_independent_diagnostics(
    lengths, final_invalid
):
    d1, d3, d4 = aligned_case(
        lengths,
        final_invalid=final_invalid,
    )

    result = assemble_gate2(d1, d3, d4)

    assert result.integrity is None
    assert result.completed is not None

    expected = result.observations.reasons | result.episodes.reasons

    if {
        "EXCESSIVE_EPISODE_TURNOVER",
        "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE",
    } <= expected:
        expected = expected | {"CONFLICTING_DIRECTIONAL_FAILURES"}

    assert result.completed.evidence.reasons == expected


@pytest.mark.parametrize(
    "label,lengths,final_invalid,action,disposition,reasons",
    [
        (
            "viable",
            [24] * 10,
            True,
            "PROCEED_TO_STAGE_2",
            "VIABLE",
            frozenset(),
        ),
        (
            "turnover",
            [1] * 10,
            True,
            "EVALUATE_24H_FALLBACK",
            "PATHOLOGICALLY_FRAGMENTED",
            frozenset({"EXCESSIVE_EPISODE_TURNOVER"}),
        ),
        (
            "persistence",
            [24] * 9 + [300],
            True,
            "EVALUATE_1H_FALLBACK",
            "STRUCTURALLY_INSUFFICIENT",
            frozenset({
                "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE",
            }),
        ),
        (
            "epistemic_precedence",
            [10] * 9 + [96],
            False,
            "TERMINATE_INSTRUMENT_V1",
            "EPISTEMICALLY_INDETERMINATE",
            frozenset({
                "EXCESSIVE_EPISODE_TURNOVER",
                "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING",
            }),
        ),
    ],
)
def test_gate2_routing_branch_regression(
    label, lengths, final_invalid, action, disposition, reasons
):
    d1, d3, d4 = aligned_case(lengths, final_invalid=final_invalid)

    selected = [
        i for i, valid in enumerate(d3.admissible) if valid
    ][::5]

    d1 = replace(
        d1,
        observation_time_ms=d1.observation_time_ms[selected],
        observation_trade_id=d1.observation_trade_id[selected],
        observation_day=tuple(d1.observation_day[i] for i in selected),
        day_statuses=(
            replace(
                d1.day_statuses[0],
                candidate_count=len(selected),
                candidate_endpoints=tuple(
                    int(d3.endpoint_ms[i]) for i in selected
                ),
            ),
        ),
    )

    result = assemble_gate2(d1, d3, d4)

    assert result.integrity is None, (label, result.integrity)
    assert result.completed is not None, label
    assert result.completed.evidence.action == action
    assert result.completed.evidence.disposition == disposition
    assert result.completed.evidence.reasons == reasons
