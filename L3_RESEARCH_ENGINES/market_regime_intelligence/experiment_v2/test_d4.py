"""Regression tests for Experiment-v2 D4 structural episode topology."""

from dataclasses import replace

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WindowD0Terminal,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d2 import (
    D2Constructed,
    D2Result,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d3 import (
    D3Constructed,
    D3Result,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d4 import (
    AuditedPrehistory,
    D2_BOUNDARY,
    D3_INADMISSIBILITY,
    STATE_CHANGE,
    construct_d4,
)


STEP = 300_000


def inputs(states):
    endpoints = np.arange(len(states), dtype=np.int64) * STEP
    admissible = np.array(
        [state != "INVALID" for state in states], dtype=np.bool_
    )
    reasons = tuple(
        () if valid else ("REGIME_STATE_INVALID",)
        for valid in admissible
    )
    d2 = D2Result(
        window="4h",
        d2=D2Constructed(
            "4h", int(endpoints[0]), int(endpoints[-1]), endpoints.copy()
        ),
        terminal=None,
    )
    d3 = D3Result(
        window="4h",
        d3=D3Constructed(
            "4h", endpoints.copy(), admissible, tuple(states), reasons
        ),
        terminal=None,
    )
    return d2, d3


def history(states, provenance="test-only synthetic fixture"):
    endpoints = np.arange(
        -len(states), 0, dtype=np.int64
    ) * STEP
    return AuditedPrehistory(
        window="4h",
        endpoint_ms=endpoints,
        state=tuple(states),
        earliest_auditable_endpoint_ms=int(endpoints[0]),
        provenance=provenance,
    )


def test_state_change_and_internal_invalidity_do_not_censor():
    d2, d3 = inputs(
        ["INVALID", "HIGH", "HIGH", "LOW", "INVALID", "HIGH", "INVALID"]
    )
    result = construct_d4(d2, d3)
    assert result.terminal is None
    episodes = result.d4.episodes
    assert len(episodes) == 3
    assert [e.state for e in episodes] == ["HIGH", "LOW", "HIGH"]
    assert episodes[0].left_boundary_cause == D3_INADMISSIBILITY
    assert episodes[0].right_boundary_cause == STATE_CHANGE
    assert episodes[1].left_boundary_cause == STATE_CHANGE
    assert episodes[1].right_boundary_cause == D3_INADMISSIBILITY
    assert episodes[2].left_boundary_cause == D3_INADMISSIBILITY
    assert episodes[2].right_boundary_cause == D3_INADMISSIBILITY
    assert not any(e.left_censored or e.right_censored for e in episodes)
    assert result.d4.episode_id_by_endpoint.tolist() == [
        -1, 0, 0, 1, -1, 2, -1
    ]
    assert result.d4.k_high == 2
    assert result.d4.k_low == 1
    assert result.d4.k_total == 3
    assert result.d4.t_classified_ms == 4 * STEP


def test_left_edge_resolved_by_historical_transition():
    d2, d3 = inputs(["HIGH", "HIGH", "LOW"])
    result = construct_d4(d2, d3, history(["LOW", "HIGH", "HIGH"]))
    assert result.terminal is None
    first = result.d4.episodes[0]
    assert first.left_boundary_cause == D2_BOUNDARY
    assert first.left_censored is False
    assert first.right_boundary_cause == STATE_CHANGE
    assert first.right_censored is False


def test_left_edge_resolved_by_historical_invalidity():
    d2, d3 = inputs(["HIGH", "INVALID"])
    result = construct_d4(d2, d3, history(["LOW", "INVALID", "HIGH"]))
    assert result.terminal is None
    assert result.d4.episodes[0].left_censored is False
    assert result.d4.episodes[0].right_censored is False


def test_continuous_prehistory_produces_left_censoring():
    d2, d3 = inputs(["HIGH", "LOW"])
    result = construct_d4(d2, d3, history(["HIGH", "HIGH"]))
    assert result.terminal is None
    assert result.d4.episodes[0].left_censored is True
    assert result.d4.episodes[0].right_censored is False


def test_one_cell_can_be_censored_on_both_sides():
    d2, d3 = inputs(["HIGH"])
    result = construct_d4(d2, d3, history(["HIGH"]))
    assert result.terminal is None
    episode = result.d4.episodes[0]
    assert episode.left_censored is True
    assert episode.right_censored is True
    assert episode.observed_duration_ms == STEP
    assert episode.endpoint_count == 1
    assert result.d4.t_classified_ms == STEP


def test_right_edge_always_censored():
    d2, d3 = inputs(["INVALID", "LOW"])
    result = construct_d4(d2, d3)
    assert result.terminal is None
    episode = result.d4.episodes[0]
    assert episode.left_censored is False
    assert episode.right_censored is True
    assert episode.right_boundary_cause == D2_BOUNDARY


def test_zero_episode_population():
    d2, d3 = inputs(["INVALID", "INVALID"])
    result = construct_d4(d2, d3)
    assert result.terminal is None
    assert result.d4.episodes == ()
    assert result.d4.k_total == 0
    assert result.d4.t_classified_ms == 0
    assert result.d4.episode_id_by_endpoint.tolist() == [-1, -1]


def test_missing_prehistory_fails_closed():
    d2, d3 = inputs(["HIGH"])
    result = construct_d4(d2, d3)
    assert result.d4 is None
    assert result.terminal.invariant == "I22"


def test_discontinuous_prehistory_fails_closed():
    d2, d3 = inputs(["HIGH"])
    bad = history(["LOW", "HIGH"])
    bad = replace(
        bad, endpoint_ms=np.array([-3 * STEP, -STEP], dtype=np.int64),
        earliest_auditable_endpoint_ms=-3 * STEP,
    )
    result = construct_d4(d2, d3, bad)
    assert result.d4 is None
    assert result.terminal.invariant == "I22"


def test_malformed_d3_state_fails_closed():
    d2, d3 = inputs(["INVALID", "LOW"])
    bad = replace(d3.d3, state=("HIGH", "LOW"))
    result = construct_d4(d2, replace(d3, d3=bad))
    assert result.d4 is None
    assert result.terminal.invariant == "I21"


def test_mismatched_d2_d3_domain_fails_closed():
    d2, d3 = inputs(["INVALID", "LOW"])
    bad = replace(
        d3.d3,
        endpoint_ms=np.array([0, 2 * STEP], dtype=np.int64),
    )
    result = construct_d4(d2, replace(d3, d3=bad))
    assert result.d4 is None
    assert result.terminal.invariant == "I19"


def test_upstream_d0_terminal_propagates():
    terminal = WindowD0Terminal(
        tag="D0_TERMINAL",
        window="4h",
        reason="NO_TARGET_OBSERVATION_POPULATION",
        provenance="C1",
    )
    d2 = D2Result("4h", None, terminal)
    d3 = D3Result("4h", None, terminal)
    result = construct_d4(d2, d3)
    assert result.d4 is None
    assert result.terminal == terminal


def test_constructed_arrays_are_immutable():
    d2, d3 = inputs(["INVALID", "LOW"])
    result = construct_d4(d2, d3)
    assert result.terminal is None
    assert not result.d4.endpoint_ms.flags.writeable
    assert not result.d4.episode_id_by_endpoint.flags.writeable


def test_d3_integrity_failure_propagates():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
        WindowIntegrityFailure,
    )

    d2, d3 = inputs(["INVALID", "LOW"])
    failure = WindowIntegrityFailure(
        tag="INTEGRITY_FAILURE",
        window="4h",
        invariant="I15",
        provenance="Synthetic upstream D3 failure",
    )
    result = construct_d4(d2, replace(d3, d3=None, terminal=failure))

    assert result.d4 is None
    assert result.terminal == failure


def test_prehistory_with_inadmissible_first_d2_cell_is_not_required():
    d2, d3 = inputs(["INVALID", "HIGH", "HIGH"])
    supplied = history(["LOW", "HIGH"])

    result = construct_d4(d2, d3, supplied)

    assert result.terminal is None
    assert result.d4.k_total == 1
    assert result.d4.episodes[0].left_censored is False


def test_grid_validation_rejects_int64_wraparound():
    limits = np.iinfo(np.int64)
    d2, d3 = inputs(["INVALID", "LOW"])

    wrapped = np.array(
        [
            (limits.min // STEP + 1) * STEP,
            (limits.max // STEP) * STEP,
        ],
        dtype=np.int64,
    )

    bad_d2 = replace(
        d2.d2,
        g_first=int(wrapped[0]),
        g_last=int(wrapped[-1]),
        endpoint_ms=wrapped,
    )
    bad_d3 = replace(d3.d3, endpoint_ms=wrapped.copy())

    result = construct_d4(
        replace(d2, d2=bad_d2),
        replace(d3, d3=bad_d3),
    )

    assert result.d4 is None
    assert result.terminal is not None


def test_d4_preserves_authoritative_upstream_d2_d3_i48():
    """I48 / A43: D4 must not mutate or rebuild authoritative D2/D3."""
    d2, d3 = inputs(["INVALID", "HIGH", "HIGH", "LOW"])

    d2_endpoints_before = d2.d2.endpoint_ms.copy()
    d3_endpoints_before = d3.d3.endpoint_ms.copy()
    d3_admissible_before = d3.d3.admissible.copy()
    d3_states_before = d3.d3.state
    d3_reasons_before = d3.d3.reason

    d2_object = d2.d2
    d3_object = d3.d3

    result = construct_d4(d2, d3)

    assert result.terminal is None
    assert result.d4 is not None

    assert d2.d2 is d2_object
    assert d3.d3 is d3_object

    np.testing.assert_array_equal(d2.d2.endpoint_ms, d2_endpoints_before)
    np.testing.assert_array_equal(d3.d3.endpoint_ms, d3_endpoints_before)
    np.testing.assert_array_equal(d3.d3.admissible, d3_admissible_before)

    assert d3.d3.state == d3_states_before
    assert d3.d3.reason == d3_reasons_before

    assert not np.shares_memory(result.d4.endpoint_ms, d2.d2.endpoint_ms)
    assert not np.shares_memory(result.d4.endpoint_ms, d3.d3.endpoint_ms)
    assert not np.shares_memory(
        result.d4.episode_id_by_endpoint, d3.d3.admissible
    )


def test_malformed_prehistory_type_fails_closed_i22():
    """Malformed prehistory must produce I22, not an uncaught exception."""
    d2, d3 = inputs(["HIGH", "LOW"])

    result = construct_d4(
        d2,
        d3,
        prehistory={"window": "4h"},
    )

    assert result.d4 is None
    assert result.terminal is not None
    assert result.terminal.tag == "INTEGRITY_FAILURE"
    assert result.terminal.invariant == "I22"
