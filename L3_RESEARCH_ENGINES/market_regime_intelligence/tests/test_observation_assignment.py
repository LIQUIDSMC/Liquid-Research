"""
LRS-4 Experiment v1 — structural lock tests for observation assignment.
"""

from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.observation_assignment import (
    ASSIGNED_ENDPOINT_INVALID,
    LRS4_ELIGIBLE,
    LRS4_REGIME_INELIGIBLE,
    NO_PRECEDING_COMPLETED_ENDPOINT,
    assign_observations_to_regime,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.regime_state import (
    REGIME_HIGH,
    REGIME_INVALID,
    REGIME_LOW,
    RegimeStateResult,
)


def _make_regime(states, start_ms=0, window_name="4h"):
    endpoint_ms = np.arange(
        len(states),
        dtype=np.int64,
    ) * GRID_INTERVAL_MS + start_ms

    state_valid = np.array(
        [
            state != REGIME_INVALID
            for state in states
        ],
        dtype=bool,
    )

    rvol = np.zeros(
        len(states),
        dtype=np.float64,
    )

    threshold = np.zeros(
        len(states),
        dtype=np.float64,
    )

    endpoint_ms.setflags(write=False)
    state_valid.setflags(write=False)
    rvol.setflags(write=False)
    threshold.setflags(write=False)

    return RegimeStateResult(
        window_name=window_name,
        endpoint_ms=endpoint_ms,
        rvol=rvol,
        threshold=threshold,
        rvol_valid=state_valid,
        threshold_valid=state_valid,
        state_valid=state_valid,
        state=tuple(states),
    )


def test_exact_grid_observation_uses_previous_endpoint():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    observation = np.array(
        [GRID_INTERVAL_MS],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [0]
    assert result.assigned_endpoint_ms.tolist() == [0]
    assert result.assigned_state == (REGIME_LOW,)
    assert result.eligible.tolist() == [True]

    print("PASS: exact-grid T consumes immediately preceding endpoint")


def test_just_after_grid_can_consume_that_endpoint():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
        ]
    )

    observation = np.array(
        [GRID_INTERVAL_MS + 1],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [1]
    assert result.assigned_endpoint_ms.tolist() == [
        GRID_INTERVAL_MS
    ]
    assert result.assigned_state == (REGIME_HIGH,)
    assert result.population_status == (
        LRS4_ELIGIBLE,
    )

    print("PASS: T just after G may consume G")


def test_before_second_grid_uses_first_endpoint():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
        ]
    )

    observation = np.array(
        [GRID_INTERVAL_MS - 1],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [0]
    assert result.assigned_state == (REGIME_LOW,)

    print("PASS: observation before next grid uses prior completed endpoint")


def test_invalid_selected_endpoint_makes_observation_ineligible():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_INVALID,
            REGIME_LOW,
        ]
    )

    observation = np.array(
        [
            2 * GRID_INTERVAL_MS - 1,
        ],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [1]
    assert result.assigned_state == (REGIME_INVALID,)
    assert result.eligible.tolist() == [False]
    assert result.population_status == (
        LRS4_REGIME_INELIGIBLE,
    )
    assert result.reason == (
        (ASSIGNED_ENDPOINT_INVALID,),
    )

    print("PASS: INVALID selected endpoint makes observation regime-ineligible")


def test_invalid_endpoint_never_backtracks_to_older_valid_state():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_INVALID,
            REGIME_LOW,
        ]
    )

    observation = np.array(
        [
            GRID_INTERVAL_MS + 1,
        ],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [1]
    assert result.assigned_endpoint_ms.tolist() == [
        GRID_INTERVAL_MS
    ]
    assert result.assigned_state == (REGIME_INVALID,)
    assert result.eligible.tolist() == [False]

    print("PASS: assignment never searches backward past INVALID endpoint")


def test_later_valid_endpoint_restores_eligibility_prospectively():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_INVALID,
            REGIME_LOW,
        ]
    )

    observations = np.array(
        [
            GRID_INTERVAL_MS + 1,
            2 * GRID_INTERVAL_MS + 1,
        ],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observations,
        regime,
    )

    assert result.assigned_state == (
        REGIME_INVALID,
        REGIME_LOW,
    )
    assert result.eligible.tolist() == [
        False,
        True,
    ]
    assert result.population_status == (
        LRS4_REGIME_INELIGIBLE,
        LRS4_ELIGIBLE,
    )

    print("PASS: later valid endpoint restores eligibility prospectively")


def test_observation_at_first_endpoint_has_no_predecessor():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    observation = np.array(
        [0],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [-1]
    assert result.assigned_endpoint_ms.tolist() == [-1]
    assert result.assigned_state == (REGIME_INVALID,)
    assert result.eligible.tolist() == [False]
    assert result.population_status == (
        LRS4_REGIME_INELIGIBLE,
    )
    assert result.reason == (
        (NO_PRECEDING_COMPLETED_ENDPOINT,),
    )

    print("PASS: first-grid observation has no preceding completed endpoint")


def test_observation_before_first_endpoint_has_no_predecessor():
    start = 10 * GRID_INTERVAL_MS

    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_LOW,
        ],
        start_ms=start,
    )

    observation = np.array(
        [start - 1],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observation,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [-1]
    assert result.eligible.tolist() == [False]
    assert result.reason == (
        (NO_PRECEDING_COMPLETED_ENDPOINT,),
    )

    print("PASS: observation before regime grid has no predecessor")


def test_duplicate_observation_times_assign_deterministically():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    observations = np.array(
        [
            GRID_INTERVAL_MS + 1,
            GRID_INTERVAL_MS + 1,
            GRID_INTERVAL_MS + 1,
        ],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observations,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [
        1,
        1,
        1,
    ]
    assert result.assigned_state == (
        REGIME_HIGH,
        REGIME_HIGH,
        REGIME_HIGH,
    )
    assert result.eligible.tolist() == [
        True,
        True,
        True,
    ]

    print("PASS: duplicate observation times assign deterministically")


def test_multiple_boundary_observations_follow_strict_rule():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    observations = np.array(
        [
            GRID_INTERVAL_MS - 1,
            GRID_INTERVAL_MS,
            GRID_INTERVAL_MS + 1,
            2 * GRID_INTERVAL_MS,
            2 * GRID_INTERVAL_MS + 1,
        ],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observations,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [
        0,
        0,
        1,
        1,
        2,
    ]

    assert result.assigned_state == (
        REGIME_LOW,
        REGIME_LOW,
        REGIME_HIGH,
        REGIME_HIGH,
        REGIME_LOW,
    )

    print("PASS: strict G<T assignment holds across grid boundaries")


def test_empty_regime_grid_fails_observations_closed():
    regime = _make_regime([])

    observations = np.array(
        [
            0,
            GRID_INTERVAL_MS,
        ],
        dtype=np.int64,
    )

    result = assign_observations_to_regime(
        observations,
        regime,
    )

    assert result.assigned_endpoint_index.tolist() == [
        -1,
        -1,
    ]
    assert result.eligible.tolist() == [
        False,
        False,
    ]
    assert result.reason == (
        (NO_PRECEDING_COMPLETED_ENDPOINT,),
        (NO_PRECEDING_COMPLETED_ENDPOINT,),
    )

    print("PASS: empty regime grid fails observations closed")


def test_unsorted_observation_times_fail_closed():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
        ]
    )

    observations = np.array(
        [
            GRID_INTERVAL_MS + 1,
            1,
        ],
        dtype=np.int64,
    )

    try:
        assign_observations_to_regime(
            observations,
            regime,
        )
        raise AssertionError(
            "Expected decreasing observation times to fail"
        )
    except ValueError as exc:
        assert "must be nondecreasing" in str(exc)

    print("PASS: decreasing observation times fail closed")


def test_non_integer_observation_dtype_fails_closed():
    regime = _make_regime(
        [
            REGIME_LOW,
        ]
    )

    try:
        assign_observations_to_regime(
            np.array([1.0], dtype=np.float64),
            regime,
        )
        raise AssertionError(
            "Expected float observation times to fail"
        )
    except TypeError as exc:
        assert "integer dtype" in str(exc)

    print("PASS: non-integer observation timestamps fail closed")


def test_nonconsecutive_regime_grid_fails_closed():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    altered = regime.endpoint_ms.copy()
    altered[2] += GRID_INTERVAL_MS
    altered.setflags(write=False)

    malformed = RegimeStateResult(
        window_name=regime.window_name,
        endpoint_ms=altered,
        rvol=regime.rvol,
        threshold=regime.threshold,
        rvol_valid=regime.rvol_valid,
        threshold_valid=regime.threshold_valid,
        state_valid=regime.state_valid,
        state=regime.state,
    )

    try:
        assign_observations_to_regime(
            np.array(
                [3 * GRID_INTERVAL_MS],
                dtype=np.int64,
            ),
            malformed,
        )
        raise AssertionError(
            "Expected nonconsecutive regime grid to fail"
        )
    except ValueError as exc:
        assert "consecutive frozen 5-minute" in str(exc)

    print("PASS: nonconsecutive regime grid fails closed")


def test_state_valid_true_with_invalid_state_fails_closed():
    regime = _make_regime(
        [
            REGIME_INVALID,
        ]
    )

    invalid_mask = np.array(
        [True],
        dtype=bool,
    )
    invalid_mask.setflags(write=False)

    malformed = RegimeStateResult(
        window_name=regime.window_name,
        endpoint_ms=regime.endpoint_ms,
        rvol=regime.rvol,
        threshold=regime.threshold,
        rvol_valid=invalid_mask,
        threshold_valid=invalid_mask,
        state_valid=invalid_mask,
        state=(REGIME_INVALID,),
    )

    try:
        assign_observations_to_regime(
            np.array(
                [GRID_INTERVAL_MS],
                dtype=np.int64,
            ),
            malformed,
        )
        raise AssertionError(
            "Expected inconsistent valid/INVALID state to fail"
        )
    except ValueError as exc:
        assert "state_valid=True cannot coexist" in str(exc)

    print("PASS: inconsistent regime validity evidence fails closed")


def test_result_is_immutable():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_HIGH,
        ]
    )

    result = assign_observations_to_regime(
        np.array(
            [GRID_INTERVAL_MS + 1],
            dtype=np.int64,
        ),
        regime,
    )

    try:
        result.window_name = "1h"
        raise AssertionError(
            "Expected assignment result mutation to fail"
        )
    except FrozenInstanceError:
        pass

    assert result.observation_time_ms.flags.writeable is False
    assert result.assigned_endpoint_index.flags.writeable is False
    assert result.assigned_endpoint_ms.flags.writeable is False
    assert result.eligible.flags.writeable is False
    assert isinstance(result.assigned_state, tuple)
    assert isinstance(result.population_status, tuple)
    assert isinstance(result.reason, tuple)

    try:
        result.eligible[0] = False
        raise AssertionError(
            "Expected read-only eligibility array to fail"
        )
    except ValueError:
        pass

    print("PASS: observation-assignment result is immutable")


if __name__ == "__main__":
    test_exact_grid_observation_uses_previous_endpoint()
    test_just_after_grid_can_consume_that_endpoint()
    test_before_second_grid_uses_first_endpoint()
    test_invalid_selected_endpoint_makes_observation_ineligible()
    test_invalid_endpoint_never_backtracks_to_older_valid_state()
    test_later_valid_endpoint_restores_eligibility_prospectively()
    test_observation_at_first_endpoint_has_no_predecessor()
    test_observation_before_first_endpoint_has_no_predecessor()
    test_duplicate_observation_times_assign_deterministically()
    test_multiple_boundary_observations_follow_strict_rule()
    test_empty_regime_grid_fails_observations_closed()
    test_unsorted_observation_times_fail_closed()
    test_non_integer_observation_dtype_fails_closed()
    test_nonconsecutive_regime_grid_fails_closed()
    test_state_valid_true_with_invalid_state_fails_closed()
    test_result_is_immutable()

    print(
        "\nALL LRS-4 OBSERVATION-ASSIGNMENT STRUCTURAL TESTS PASSED"
    )
