"""Synthetic regression tests for frozen G5-G6 diagnostics."""

from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d4 import (
    D4Constructed,
    D4Episode,
    D2_BOUNDARY,
    D3_INADMISSIBILITY,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_episodes import (
    evaluate_episode_diagnostics,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS as STEP,
)


def make_case(lengths, *, final_invalid=False):
    if not lengths:
        endpoints = np.arange(12, dtype=np.int64) * STEP
        return D4Constructed(
            window="4h",
            endpoint_ms=endpoints,
            episode_id_by_endpoint=np.full(12, -1, dtype=np.int64),
            episodes=(),
            k_high=0,
            k_low=0,
            k_total=0,
            t_classified_ms=0,
        )

    total = sum(lengths) + len(lengths) - 1 + int(final_invalid)
    endpoints = np.arange(total, dtype=np.int64) * STEP
    ids = np.full(total, -1, dtype=np.int64)
    episodes = []
    position = 0

    for i, length in enumerate(lengths):
        start = position
        end = start + length - 1
        ids[start:end + 1] = i

        episodes.append(D4Episode(
            episode_id=i,
            state="HIGH" if i % 2 == 0 else "LOW",
            start_index=start,
            end_index=end,
            start_endpoint_ms=int(endpoints[start]),
            end_endpoint_ms=int(endpoints[end]),
            endpoint_count=length,
            observed_duration_ms=length * STEP,
            left_boundary_cause=(
                D2_BOUNDARY if start == 0 else D3_INADMISSIBILITY
            ),
            right_boundary_cause=(
                D2_BOUNDARY if end == total - 1 else D3_INADMISSIBILITY
            ),
            left_censored=False,
            right_censored=end == total - 1,
        ))
        position = end + 2

    return D4Constructed(
        window="4h",
        endpoint_ms=endpoints,
        episode_id_by_endpoint=ids,
        episodes=tuple(episodes),
        k_high=sum(e.state == "HIGH" for e in episodes),
        k_low=sum(e.state == "LOW" for e in episodes),
        k_total=len(episodes),
        t_classified_ms=sum(lengths) * STEP,
    )


def test_z2_zero_structural_episodes():
    result = evaluate_episode_diagnostics(make_case([]))
    assert result.high_support_status == "FAIL"
    assert result.low_support_status == "FAIL"
    assert result.turnover_status == (
        "NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES"
    )
    assert result.persistence_status == (
        "NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES"
    )
    assert result.p_short_lb is None
    assert result.p_long_time_lb is None
    assert result.reasons == frozenset({
        "INSUFFICIENT_STATE_EPISODE_SUPPORT"
    })


def test_exact_duration_boundaries_uncensored():
    result = evaluate_episode_diagnostics(
        make_case([24, 96], final_invalid=True)
    )
    assert result.turnover_status == "PASS"
    assert result.persistence_status == "PASS"
    assert result.p_short_lb == Fraction(0)
    assert result.p_short_ub == Fraction(0)
    assert result.p_long_time_lb == Fraction(0)
    assert result.p_long_time_ub == Fraction(0)


def test_exact_2w_right_censored_is_indeterminate():
    result = evaluate_episode_diagnostics(make_case([24, 96]))
    assert result.turnover_status == "PASS"
    assert result.persistence_status == (
        "INDETERMINATE_FROM_BOUNDARY_CENSORING"
    )
    assert result.p_long_time_lb == Fraction(0)
    assert result.p_long_time_ub == Fraction(4, 5)
    assert (
        "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING"
        in result.reasons
    )


def test_definite_turnover():
    result = evaluate_episode_diagnostics(
        make_case([1] * 6, final_invalid=True)
    )
    assert result.turnover_status == "FAIL"
    assert result.p_short_lb == Fraction(1)
    assert "EXCESSIVE_EPISODE_TURNOVER" in result.reasons


def test_definite_persistence():
    result = evaluate_episode_diagnostics(
        make_case([1] * 5 + [120])
    )
    assert result.persistence_status == "FAIL"
    assert "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE" in result.reasons


def test_one_cell_right_censored_is_ambiguous():
    result = evaluate_episode_diagnostics(make_case([1]))
    assert result.turnover_status == (
        "INDETERMINATE_FROM_BOUNDARY_CENSORING"
    )
    assert result.persistence_status == (
        "INDETERMINATE_FROM_BOUNDARY_CENSORING"
    )
    assert result.p_short_lb == Fraction(0)
    assert result.p_short_ub == Fraction(1)
    assert result.p_long_time_lb == Fraction(0)
    assert result.p_long_time_ub == Fraction(1)


def test_rejects_duration_mismatch():
    d4 = make_case([3], final_invalid=True)
    episode = replace(
        d4.episodes[0],
        observed_duration_ms=2 * STEP,
    )
    with pytest.raises(ValueError):
        evaluate_episode_diagnostics(
            replace(d4, episodes=(episode,))
        )


def test_rejects_episode_id_mismatch():
    d4 = make_case([3], final_invalid=True)
    ids = d4.episode_id_by_endpoint.copy()
    ids[1] = -1
    with pytest.raises(ValueError):
        evaluate_episode_diagnostics(
            replace(d4, episode_id_by_endpoint=ids)
        )


def test_rejects_summary_mismatch():
    d4 = make_case([3], final_invalid=True)
    with pytest.raises(ValueError):
        evaluate_episode_diagnostics(
            replace(d4, t_classified_ms=0)
        )


@pytest.mark.parametrize(
    ("corruption", "expected_invariant", "expected_provenance"),
    [
        (
            "duration",
            "I24",
            "D4 episode duration or identity mismatch",
        ),
        (
            "summary",
            "I25",
            "D4 summary reconciliation failure",
        ),
    ],
)
def test_a123_episode_integrity_identity(
    corruption, expected_invariant, expected_provenance
):
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import Gate2IntegrityError

    d4 = make_case([3], final_invalid=True)

    if corruption == "duration":
        bad_episode = replace(
            d4.episodes[0],
            observed_duration_ms=2 * STEP,
        )
        d4 = replace(d4, episodes=(bad_episode,))
    else:
        d4 = replace(d4, t_classified_ms=0)

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(d4)

    assert captured.value.invariant == expected_invariant
    assert captured.value.provenance == expected_provenance

def test_a123_i23_right_censor_identity():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import Gate2IntegrityError

    d4 = make_case([3])
    episode = replace(d4.episodes[0], right_censored=False)
    bad_d4 = replace(d4, episodes=(episode,))

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I23"
    assert captured.value.provenance == "Invalid right censoring"
def test_a123_i22_left_censor_identity():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import Gate2IntegrityError

    d4 = make_case([3, 3], final_invalid=True)
    episode = replace(d4.episodes[1], left_censored=True)
    bad_d4 = replace(d4, episodes=(d4.episodes[0], episode))

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I22"
    assert captured.value.provenance == "Invalid left censoring"

@pytest.mark.parametrize(
    ("side", "expected_provenance"),
    [
        ("left", "Invalid left boundary cause"),
        ("right", "Invalid right boundary cause"),
    ],
)
def test_a123_i20_boundary_cause_identity(side, expected_provenance):
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import Gate2IntegrityError

    d4 = make_case([3], final_invalid=True)
    episode = d4.episodes[0]

    if side == "left":
        episode = replace(
            episode,
            left_boundary_cause=D3_INADMISSIBILITY,
        )
    else:
        episode = replace(
            episode,
            right_boundary_cause=D2_BOUNDARY,
        )

    bad_d4 = replace(d4, episodes=(episode,))

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I20"
    assert captured.value.provenance == expected_provenance

@pytest.mark.parametrize(
    "defect",
    ["same_state", "wrong_boundary"],
)
def test_a123_i20_episode_transition_identity(defect):
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d4 import (
        STATE_CHANGE,
    )
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import (
        Gate2IntegrityError,
    )

    d4 = make_case([3], final_invalid=True)
    first = d4.episodes[0]

    second = replace(
        first,
        episode_id=1,
        state="LOW",
        start_index=3,
        end_index=5,
        start_endpoint_ms=3 * STEP,
        end_endpoint_ms=5 * STEP,
        left_boundary_cause=STATE_CHANGE,
        right_boundary_cause=D2_BOUNDARY,
        left_censored=False,
        right_censored=True,
    )

    first = replace(
        first,
        right_boundary_cause=STATE_CHANGE,
    )

    if defect == "same_state":
        second = replace(second, state=first.state)
    else:
        second = replace(
            second,
            left_boundary_cause=D3_INADMISSIBILITY,
        )

    endpoints = np.arange(6, dtype=np.int64) * STEP
    ids = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)

    bad_d4 = replace(
        d4,
        endpoint_ms=endpoints,
        episode_id_by_endpoint=ids,
        episodes=(first, second),
        k_high=1,
        k_low=1,
        k_total=2,
        t_classified_ms=6 * STEP,
    )

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I20"
    assert captured.value.provenance == "Invalid episode transition"

def test_a123_i21_episode_gap_identity():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d4 import (
        STATE_CHANGE,
    )
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import (
        Gate2IntegrityError,
    )

    d4 = make_case([3, 3], final_invalid=True)

    assert len(d4.episodes) == 2
    assert d4.episodes[1].start_index > d4.episodes[0].end_index + 1
    assert d4.episodes[1].left_boundary_cause == D3_INADMISSIBILITY

    second = replace(
        d4.episodes[1],
        left_boundary_cause=STATE_CHANGE,
    )
    bad_d4 = replace(
        d4,
        episodes=(d4.episodes[0], second),
    )

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I21"
    assert captured.value.provenance == "Invalid episode gap boundary"

@pytest.mark.parametrize("topology", ["gap", "adjacent"])
def test_a123_i20_right_boundary_transition_identity(topology):
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d4 import (
        STATE_CHANGE,
    )
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import (
        Gate2IntegrityError,
    )

    if topology == "gap":
        d4 = make_case([3, 3], final_invalid=True)
        first = replace(
            d4.episodes[0],
            right_boundary_cause=STATE_CHANGE,
        )
        bad_d4 = replace(
            d4,
            episodes=(first, d4.episodes[1]),
        )
    else:
        d4 = make_case([3], final_invalid=True)
        first = replace(
            d4.episodes[0],
            right_boundary_cause=D3_INADMISSIBILITY,
        )
        second = replace(
            d4.episodes[0],
            episode_id=1,
            state="LOW",
            start_index=3,
            end_index=5,
            start_endpoint_ms=3 * STEP,
            end_endpoint_ms=5 * STEP,
            left_boundary_cause=STATE_CHANGE,
            right_boundary_cause=D2_BOUNDARY,
            left_censored=False,
            right_censored=True,
        )

        bad_d4 = replace(
            d4,
            endpoint_ms=np.arange(6, dtype=np.int64) * STEP,
            episode_id_by_endpoint=np.array(
                [0, 0, 0, 1, 1, 1], dtype=np.int64
            ),
            episodes=(first, second),
            k_high=1,
            k_low=1,
            k_total=2,
            t_classified_ms=6 * STEP,
        )

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I20"
    assert captured.value.provenance == "Invalid right boundary transition"

def test_a123_i21_gap_endpoint_reconciliation():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_integrity import (
        Gate2IntegrityError,
    )

    d4 = make_case([3, 3], final_invalid=True)

    gap_index = d4.episodes[0].end_index + 1

    assert gap_index < d4.episodes[1].start_index
    assert d4.episode_id_by_endpoint[gap_index] == -1

    ids = d4.episode_id_by_endpoint.copy()
    ids[gap_index] = 0

    bad_d4 = replace(d4, episode_id_by_endpoint=ids)

    with pytest.raises(Gate2IntegrityError) as captured:
        evaluate_episode_diagnostics(bad_d4)

    assert captured.value.invariant == "I21"
    assert captured.value.provenance == (
        "D4 endpoint-to-episode reconciliation failure"
    )
