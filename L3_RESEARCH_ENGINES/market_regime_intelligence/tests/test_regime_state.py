"""
LRS-4 Experiment v1 — structural lock tests for regime-state classification.
"""

from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.regime_state import (
    REGIME_HIGH,
    REGIME_INVALID,
    REGIME_LOW,
    classify_regime_state,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.rvol import (
    RvolResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.threshold_learning import (
    ThresholdLearningResult,
)


def _make_rvol(
    values,
    valid,
    window_name="1h",
    endpoint_ms=None,
):
    values = np.asarray(values, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool)
    n = values.size

    if endpoint_ms is None:
        endpoint_ms = (
            np.arange(n, dtype=np.int64) * GRID_INTERVAL_MS
        )
    else:
        endpoint_ms = np.asarray(endpoint_ms, dtype=np.int64)

    dummy_bool = np.zeros(n, dtype=bool)
    dummy_int = np.zeros(n, dtype=np.int64)
    dummy_float = np.zeros(n, dtype=np.float64)

    return RvolResult(
        window_name=window_name,
        window_ms=60 * 60 * 1000,
        expected_returns=12,
        min_valid_returns=9,
        max_allowed_contiguous_invalid_returns=3,
        endpoint_ms=endpoint_ms,
        history_complete=dummy_bool.copy(),
        valid_return_count=dummy_int.copy(),
        invalid_return_count=dummy_int.copy(),
        coverage_fraction=dummy_float.copy(),
        max_contiguous_invalid_returns=dummy_int.copy(),
        aggregate_coverage_pass=dummy_bool.copy(),
        contiguous_gap_pass=dummy_bool.copy(),
        realized_variance=dummy_float.copy(),
        rvol=values,
        rvol_valid=valid,
        rvol_reasons=tuple(("VALID",) for _ in range(n)),
    )


def _make_threshold(
    values,
    valid,
    window_name="1h",
    endpoint_ms=None,
):
    values = np.asarray(values, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool)
    n = values.size

    if endpoint_ms is None:
        endpoint_ms = (
            np.arange(n, dtype=np.int64) * GRID_INTERVAL_MS
        )
    else:
        endpoint_ms = np.asarray(endpoint_ms, dtype=np.int64)

    dummy_bool = np.zeros(n, dtype=bool)
    dummy_int = np.zeros(n, dtype=np.int64)

    return ThresholdLearningResult(
        window_name=window_name,
        learning_history_ms=5 * 60 * 60 * 1000,
        nominal_members=60,
        min_valid_members=45,
        max_allowed_contiguous_invalid_members=15,
        endpoint_ms=endpoint_ms,
        source_history_authorized=dummy_bool.copy(),
        learning_history_complete=dummy_bool.copy(),
        valid_rvol_count=dummy_int.copy(),
        invalid_rvol_count=dummy_int.copy(),
        max_contiguous_invalid_rvol=dummy_int.copy(),
        aggregate_availability_pass=dummy_bool.copy(),
        contiguous_concentration_pass=dummy_bool.copy(),
        threshold=values,
        threshold_valid=valid,
    )


def test_high_low_and_equality_boundary():
    rvol = _make_rvol(
        [2.0, 1.0, 0.5],
        [True, True, True],
    )
    threshold = _make_threshold(
        [1.0, 1.0, 1.0],
        [True, True, True],
    )

    result = classify_regime_state(rvol, threshold)

    assert result.state == (
        REGIME_HIGH,
        REGIME_LOW,
        REGIME_LOW,
    )

    print("PASS: HIGH/LOW rule exact; equality belongs to LOW")


def test_invalid_rvol_produces_invalid_state():
    result = classify_regime_state(
        _make_rvol(
            [2.0],
            [False],
        ),
        _make_threshold(
            [1.0],
            [True],
        ),
    )

    assert result.state == (REGIME_INVALID,)
    assert result.state_valid[0] is np.False_

    print("PASS: invalid RVOL produces INVALID state")


def test_invalid_threshold_produces_invalid_state():
    result = classify_regime_state(
        _make_rvol(
            [2.0],
            [True],
        ),
        _make_threshold(
            [1.0],
            [False],
        ),
    )

    assert result.state == (REGIME_INVALID,)
    assert result.state_valid[0] is np.False_

    print("PASS: invalid threshold produces INVALID state")


def test_both_invalid_produce_invalid_state():
    result = classify_regime_state(
        _make_rvol(
            [2.0],
            [False],
        ),
        _make_threshold(
            [1.0],
            [False],
        ),
    )

    assert result.state == (REGIME_INVALID,)
    assert result.state_valid[0] is np.False_

    print("PASS: jointly invalid inputs remain INVALID")


def test_window_name_mismatch_fails_closed():
    rvol = _make_rvol(
        [1.0],
        [True],
        window_name="1h",
    )
    threshold = _make_threshold(
        [1.0],
        [True],
        window_name="4h",
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected window mismatch to fail")
    except ValueError as exc:
        assert "window names differ" in str(exc)

    print("PASS: window-name mismatch fails closed")


def test_endpoint_mismatch_fails_closed():
    rvol = _make_rvol(
        [1.0, 1.0],
        [True, True],
        endpoint_ms=np.array(
            [0, GRID_INTERVAL_MS],
            dtype=np.int64,
        ),
    )

    threshold = _make_threshold(
        [1.0, 1.0],
        [True, True],
        endpoint_ms=np.array(
            [0, 2 * GRID_INTERVAL_MS],
            dtype=np.int64,
        ),
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected endpoint mismatch to fail")
    except ValueError as exc:
        assert "endpoints differ" in str(exc)

    print("PASS: endpoint mismatch fails closed")


def test_length_mismatch_fails_closed():
    rvol = _make_rvol(
        [1.0, 1.0],
        [True, True],
    )
    threshold = _make_threshold(
        [1.0],
        [True],
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected length mismatch to fail")
    except ValueError as exc:
        assert "lengths differ" in str(exc)

    print("PASS: input length mismatch fails closed")


def test_nonfinite_valid_rvol_fails_closed():
    rvol = _make_rvol(
        [np.nan],
        [True],
    )
    threshold = _make_threshold(
        [1.0],
        [True],
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected non-finite RVOL to fail")
    except ValueError as exc:
        assert "non-finite RVOL" in str(exc)

    print("PASS: non-finite valid RVOL fails closed")


def test_negative_valid_rvol_fails_closed():
    rvol = _make_rvol(
        [-0.1],
        [True],
    )
    threshold = _make_threshold(
        [1.0],
        [True],
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected negative RVOL to fail")
    except ValueError as exc:
        assert "negative RVOL" in str(exc)

    print("PASS: negative valid RVOL fails closed")


def test_nonfinite_valid_threshold_fails_closed():
    rvol = _make_rvol(
        [1.0],
        [True],
    )
    threshold = _make_threshold(
        [np.inf],
        [True],
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected non-finite threshold to fail")
    except ValueError as exc:
        assert "non-finite" in str(exc)

    print("PASS: non-finite valid threshold fails closed")


def test_negative_valid_threshold_fails_closed():
    rvol = _make_rvol(
        [1.0],
        [True],
    )
    threshold = _make_threshold(
        [-0.1],
        [True],
    )

    try:
        classify_regime_state(rvol, threshold)
        raise AssertionError("Expected negative threshold to fail")
    except ValueError as exc:
        assert "negative" in str(exc)

    print("PASS: negative valid threshold fails closed")


def test_invalid_numeric_slots_do_not_trigger_validation():
    result = classify_regime_state(
        _make_rvol(
            [np.nan],
            [False],
        ),
        _make_threshold(
            [np.nan],
            [False],
        ),
    )

    assert result.state == (REGIME_INVALID,)

    print("PASS: invalid numeric slots remain diagnostically INVALID")


def test_state_valid_is_exact_boolean_intersection():
    rvol = _make_rvol(
        [2.0, 2.0, 2.0, 2.0],
        [True, True, False, False],
    )
    threshold = _make_threshold(
        [1.0, 1.0, 1.0, 1.0],
        [True, False, True, False],
    )

    result = classify_regime_state(rvol, threshold)

    assert np.array_equal(
        result.state_valid,
        np.array([True, False, False, False]),
    )

    assert result.state == (
        REGIME_HIGH,
        REGIME_INVALID,
        REGIME_INVALID,
        REGIME_INVALID,
    )

    print("PASS: state validity is exact RVOL-valid AND threshold-valid")


def test_result_and_arrays_are_immutable():
    result = classify_regime_state(
        _make_rvol(
            [2.0],
            [True],
        ),
        _make_threshold(
            [1.0],
            [True],
        ),
    )

    try:
        result.window_name = "4h"
        raise AssertionError(
            "Expected frozen RegimeStateResult mutation to fail"
        )
    except FrozenInstanceError:
        pass

    arrays = (
        result.endpoint_ms,
        result.rvol,
        result.threshold,
        result.rvol_valid,
        result.threshold_valid,
        result.state_valid,
    )

    for array in arrays:
        assert array.flags.writeable is False

    try:
        result.rvol[0] = 999.0
        raise AssertionError("Expected read-only RVOL mutation to fail")
    except ValueError:
        pass

    assert isinstance(result.state, tuple)

    print("PASS: regime-state evidence object and arrays are immutable")


if __name__ == "__main__":
    test_high_low_and_equality_boundary()
    test_invalid_rvol_produces_invalid_state()
    test_invalid_threshold_produces_invalid_state()
    test_both_invalid_produce_invalid_state()
    test_window_name_mismatch_fails_closed()
    test_endpoint_mismatch_fails_closed()
    test_length_mismatch_fails_closed()
    test_nonfinite_valid_rvol_fails_closed()
    test_negative_valid_rvol_fails_closed()
    test_nonfinite_valid_threshold_fails_closed()
    test_negative_valid_threshold_fails_closed()
    test_invalid_numeric_slots_do_not_trigger_validation()
    test_state_valid_is_exact_boolean_intersection()
    test_result_and_arrays_are_immutable()

    print(
        "\nALL LRS-4 REGIME-STATE STRUCTURAL TESTS PASSED"
    )
