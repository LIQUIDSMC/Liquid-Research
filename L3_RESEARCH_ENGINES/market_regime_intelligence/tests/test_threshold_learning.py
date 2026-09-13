"""
LRS-4 Experiment v1 — structural lock tests for causal threshold learning.

Covers:
- K1.1 exact H_L(G) membership
- exact 1h / 4h / 24h frozen threshold-history specifications
- no current-value self-inclusion
- no partial warm-up
- K1.2 75% availability gate
- K1.2 25% contiguous-invalid gate
- filtered causal median semantics
- source-history authorization ordering
- fail-closed input validation
- immutable evidence outputs
"""

from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.rvol import (
    RvolResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.threshold_learning import (
    THRESHOLD_HISTORY_SPECS,
    learn_causal_threshold,
)


def _make_rvol_result(
    rvol_values,
    valid_mask,
    window_name="1h",
    endpoint_ms=None,
):
    n = len(rvol_values)

    if len(valid_mask) != n:
        raise ValueError("fixture rvol_values/valid_mask length mismatch")

    if endpoint_ms is None:
        endpoint_ms = np.arange(
            n,
            dtype=np.int64,
        ) * GRID_INTERVAL_MS
    else:
        endpoint_ms = np.asarray(endpoint_ms, dtype=np.int64)

    rvol_arr = np.asarray(rvol_values, dtype=np.float64)
    valid_arr = np.asarray(valid_mask, dtype=bool)

    dummy_bool = np.zeros(n, dtype=bool)
    dummy_int = np.zeros(n, dtype=np.int64)
    dummy_float = np.zeros(n, dtype=np.float64)
    reasons = tuple(("VALID",) for _ in range(n))

    spec = THRESHOLD_HISTORY_SPECS[window_name]

    return RvolResult(
        window_name=window_name,
        window_ms=spec.learning_history_ms // 5,
        expected_returns=1,
        min_valid_returns=1,
        max_allowed_contiguous_invalid_returns=1,
        endpoint_ms=endpoint_ms,
        history_complete=dummy_bool.copy(),
        valid_return_count=dummy_int.copy(),
        invalid_return_count=dummy_int.copy(),
        coverage_fraction=dummy_float.copy(),
        max_contiguous_invalid_returns=dummy_int.copy(),
        aggregate_coverage_pass=dummy_bool.copy(),
        contiguous_gap_pass=dummy_bool.copy(),
        realized_variance=dummy_float.copy(),
        rvol=rvol_arr,
        rvol_valid=valid_arr,
        rvol_reasons=reasons,
    )


def test_frozen_specs_are_exact():
    expected = {
        "1h": (5 * 60 * 60 * 1000, 60, 45, 15),
        "4h": (20 * 60 * 60 * 1000, 240, 180, 60),
        "24h": (120 * 60 * 60 * 1000, 1440, 1080, 360),
    }

    for name, expected_values in expected.items():
        spec = THRESHOLD_HISTORY_SPECS[name]

        actual = (
            spec.learning_history_ms,
            spec.nominal_members,
            spec.min_valid_members,
            spec.max_contiguous_invalid_members,
        )

        assert actual == expected_values, (name, actual, expected_values)

    print("PASS: frozen 1h/4h/24h threshold-history specs are exact")


def test_exact_history_excludes_current_endpoint():
    n = THRESHOLD_HISTORY_SPECS["1h"].nominal_members

    values = np.arange(1, n + 1, dtype=np.float64)
    values = np.concatenate((values, [999999.0]))

    valid = np.ones(n + 1, dtype=bool)

    result = learn_causal_threshold(
        _make_rvol_result(values, valid),
        np.ones(n + 1, dtype=bool),
    )

    expected = float(np.median(values[:n]))

    assert result.learning_history_complete[n]
    assert result.threshold_valid[n]
    assert result.valid_rvol_count[n] == n
    assert result.threshold[n] == expected

    print("PASS: exact H_L(G) contains prior N endpoints and excludes current G")


def test_current_outlier_cannot_change_own_threshold():
    n = THRESHOLD_HISTORY_SPECS["1h"].nominal_members

    base = np.ones(n + 1, dtype=np.float64)
    valid = np.ones(n + 1, dtype=bool)

    first = learn_causal_threshold(
        _make_rvol_result(base, valid),
        np.ones(n + 1, dtype=bool),
    )

    changed = base.copy()
    changed[n] = 1e15

    second = learn_causal_threshold(
        _make_rvol_result(changed, valid),
        np.ones(n + 1, dtype=bool),
    )

    assert first.threshold[n] == 1.0
    assert second.threshold[n] == 1.0

    print("PASS: current RVOL self-inclusion is impossible")


def test_no_partial_learning_history_warmup():
    n = THRESHOLD_HISTORY_SPECS["1h"].nominal_members

    result = learn_causal_threshold(
        _make_rvol_result(
            np.ones(n, dtype=np.float64),
            np.ones(n, dtype=bool),
        ),
        np.ones(n, dtype=bool),
    )

    assert not np.any(result.learning_history_complete)
    assert not np.any(result.threshold_valid)
    assert np.all(np.isnan(result.threshold))

    print("PASS: no partial threshold-learning warm-up permitted")


def test_exactly_45_of_60_valid_passes():
    n = 60

    valid = np.ones(n + 1, dtype=bool)

    # 15 invalid members, deliberately isolated.
    for index in range(0, 60, 4):
        valid[index] = False

    assert np.count_nonzero(valid[:n]) == 45

    values = np.ones(n + 1, dtype=np.float64)

    result = learn_causal_threshold(
        _make_rvol_result(values, valid),
        np.ones(n + 1, dtype=bool),
    )

    assert result.valid_rvol_count[n] == 45
    assert result.invalid_rvol_count[n] == 15
    assert result.aggregate_availability_pass[n]
    assert result.contiguous_concentration_pass[n]
    assert result.threshold_valid[n]

    print("PASS: exactly 45/60 valid threshold-history members passes")


def test_44_of_60_valid_fails_aggregate_only():
    n = 60

    valid = np.ones(n + 1, dtype=bool)

    # 16 isolated invalid members => 44 valid, maximum run = 1.
    for index in range(0, 48, 3):
        valid[index] = False

    assert np.count_nonzero(valid[:n]) == 44

    result = learn_causal_threshold(
        _make_rvol_result(
            np.ones(n + 1, dtype=np.float64),
            valid,
        ),
        np.ones(n + 1, dtype=bool),
    )

    assert result.valid_rvol_count[n] == 44
    assert result.aggregate_availability_pass[n] is np.False_
    assert result.contiguous_concentration_pass[n] is np.True_
    assert result.threshold_valid[n] is np.False_
    assert np.isnan(result.threshold[n])

    print("PASS: 44/60 fails aggregate availability only")


def test_exactly_15_contiguous_invalid_passes():
    n = 60

    valid = np.ones(n + 1, dtype=bool)
    valid[:15] = False

    result = learn_causal_threshold(
        _make_rvol_result(
            np.ones(n + 1, dtype=np.float64),
            valid,
        ),
        np.ones(n + 1, dtype=bool),
    )

    assert result.valid_rvol_count[n] == 45
    assert result.max_contiguous_invalid_rvol[n] == 15
    assert result.aggregate_availability_pass[n]
    assert result.contiguous_concentration_pass[n]
    assert result.threshold_valid[n]

    print("PASS: contiguous invalid run of exactly 15 passes")


def test_16_contiguous_invalid_fails_both_gates():
    n = 60

    valid = np.ones(n + 1, dtype=bool)
    valid[:16] = False

    result = learn_causal_threshold(
        _make_rvol_result(
            np.ones(n + 1, dtype=np.float64),
            valid,
        ),
        np.ones(n + 1, dtype=bool),
    )

    assert result.valid_rvol_count[n] == 44
    assert result.max_contiguous_invalid_rvol[n] == 16
    assert result.aggregate_availability_pass[n] is np.False_
    assert result.contiguous_concentration_pass[n] is np.False_
    assert result.threshold_valid[n] is np.False_

    print("PASS: contiguous invalid run of 16 fails both frozen gates")


def test_median_uses_valid_rvol_members_only():
    n = 60

    values = np.ones(n + 1, dtype=np.float64)
    valid = np.ones(n + 1, dtype=bool)

    # Invalid numerical values must have zero influence on theta.
    values[:5] = 999999.0
    valid[:5] = False

    result = learn_causal_threshold(
        _make_rvol_result(values, valid),
        np.ones(n + 1, dtype=bool),
    )

    assert result.valid_rvol_count[n] == 55
    assert result.threshold_valid[n]
    assert result.threshold[n] == 1.0

    print("PASS: filtered median uses VALID RVOL members only")


def test_exact_history_does_not_search_backward():
    n = 60

    # 61 prior values exist for target i=61.
    # Index 0 is attractive extra history but MUST NOT rescue an invalid
    # member inside exact indices 1..60.
    values = np.ones(n + 2, dtype=np.float64)
    valid = np.ones(n + 2, dtype=bool)

    # Within exact history for i=61, make 16 members invalid.
    valid[1:17] = False

    # Index 0 remains valid but is outside H_L(G) at i=61.
    assert valid[0]

    result = learn_causal_threshold(
        _make_rvol_result(values, valid),
        np.ones(n + 2, dtype=bool),
    )

    i = 61

    assert result.learning_history_complete[i]
    assert result.valid_rvol_count[i] == 44
    assert result.threshold_valid[i] is np.False_

    print("PASS: learner never searches backward beyond exact H_L(G)")


def test_source_history_unauthorized_skips_threshold_evaluation():
    n = 60

    values = np.ones(n + 1, dtype=np.float64)
    valid = np.ones(n + 1, dtype=bool)

    authorized = np.ones(n + 1, dtype=bool)
    authorized[n] = False

    result = learn_causal_threshold(
        _make_rvol_result(values, valid),
        authorized,
    )

    assert result.learning_history_complete[n]

    # Threshold-history validity was never evaluated.
    assert result.valid_rvol_count[n] == 0
    assert result.invalid_rvol_count[n] == 0
    assert result.max_contiguous_invalid_rvol[n] == -1
    assert result.aggregate_availability_pass[n] is np.False_
    assert result.contiguous_concentration_pass[n] is np.False_
    assert result.threshold_valid[n] is np.False_
    assert np.isnan(result.threshold[n])

    print("PASS: source-history authorization precedes threshold evaluation")


def test_rejects_non_boolean_source_authorization():
    rvol = _make_rvol_result(
        [1.0, 1.0],
        [True, True],
    )

    try:
        learn_causal_threshold(
            rvol,
            np.array([1, 1], dtype=np.int64),
        )
        raise AssertionError("Expected non-boolean authorization to fail")
    except TypeError as exc:
        assert "boolean dtype" in str(exc)

    print("PASS: non-boolean source-history authorization fails closed")


def test_rejects_mismatched_authorization_length():
    rvol = _make_rvol_result(
        [1.0, 1.0],
        [True, True],
    )

    try:
        learn_causal_threshold(
            rvol,
            np.array([True], dtype=bool),
        )
        raise AssertionError("Expected authorization length mismatch to fail")
    except ValueError as exc:
        assert "length" in str(exc)

    print("PASS: authorization length mismatch fails closed")


def test_rejects_nonconsecutive_grid():
    endpoint_ms = np.array(
        [
            0,
            GRID_INTERVAL_MS,
            3 * GRID_INTERVAL_MS,
        ],
        dtype=np.int64,
    )

    rvol = _make_rvol_result(
        [1.0, 1.0, 1.0],
        [True, True, True],
        endpoint_ms=endpoint_ms,
    )

    try:
        learn_causal_threshold(
            rvol,
            np.ones(3, dtype=bool),
        )
        raise AssertionError("Expected nonconsecutive grid to fail")
    except ValueError as exc:
        assert "not consecutive" in str(exc)

    print("PASS: nonconsecutive 5m grid fails closed")


def test_rejects_nonfinite_valid_rvol():
    rvol = _make_rvol_result(
        [1.0, np.nan],
        [True, True],
    )

    try:
        learn_causal_threshold(
            rvol,
            np.ones(2, dtype=bool),
        )
        raise AssertionError("Expected valid NaN RVOL to fail")
    except ValueError as exc:
        assert "non-finite" in str(exc)

    print("PASS: non-finite RVOL marked VALID fails closed")


def test_rejects_negative_valid_rvol():
    rvol = _make_rvol_result(
        [1.0, -0.1],
        [True, True],
    )

    try:
        learn_causal_threshold(
            rvol,
            np.ones(2, dtype=bool),
        )
        raise AssertionError("Expected negative valid RVOL to fail")
    except ValueError as exc:
        assert "negative" in str(exc)

    print("PASS: negative RVOL marked VALID fails closed")


def test_result_metadata_for_all_windows():
    for window_name in ("1h", "4h", "24h"):
        spec = THRESHOLD_HISTORY_SPECS[window_name]

        result = learn_causal_threshold(
            _make_rvol_result(
                [1.0],
                [True],
                window_name=window_name,
            ),
            np.ones(1, dtype=bool),
        )

        assert result.window_name == window_name
        assert result.learning_history_ms == spec.learning_history_ms
        assert result.nominal_members == spec.nominal_members
        assert result.min_valid_members == spec.min_valid_members
        assert (
            result.max_allowed_contiguous_invalid_members
            == spec.max_contiguous_invalid_members
        )

    print("PASS: 1h/4h/24h result metadata matches frozen specifications")


def test_result_and_arrays_are_immutable():
    n = 60

    result = learn_causal_threshold(
        _make_rvol_result(
            np.ones(n + 1, dtype=np.float64),
            np.ones(n + 1, dtype=bool),
        ),
        np.ones(n + 1, dtype=bool),
    )

    try:
        result.window_name = "4h"
        raise AssertionError(
            "Expected frozen ThresholdLearningResult mutation to fail"
        )
    except FrozenInstanceError:
        pass

    arrays = (
        result.endpoint_ms,
        result.source_history_authorized,
        result.learning_history_complete,
        result.valid_rvol_count,
        result.invalid_rvol_count,
        result.max_contiguous_invalid_rvol,
        result.aggregate_availability_pass,
        result.contiguous_concentration_pass,
        result.threshold,
        result.threshold_valid,
    )

    for array in arrays:
        assert array.flags.writeable is False

    try:
        result.threshold[n] = 999.0
        raise AssertionError("Expected read-only threshold mutation to fail")
    except ValueError:
        pass

    print("PASS: threshold-learning evidence object and arrays are immutable")


if __name__ == "__main__":
    test_frozen_specs_are_exact()
    test_exact_history_excludes_current_endpoint()
    test_current_outlier_cannot_change_own_threshold()
    test_no_partial_learning_history_warmup()
    test_exactly_45_of_60_valid_passes()
    test_44_of_60_valid_fails_aggregate_only()
    test_exactly_15_contiguous_invalid_passes()
    test_16_contiguous_invalid_fails_both_gates()
    test_median_uses_valid_rvol_members_only()
    test_exact_history_does_not_search_backward()
    test_source_history_unauthorized_skips_threshold_evaluation()
    test_rejects_non_boolean_source_authorization()
    test_rejects_mismatched_authorization_length()
    test_rejects_nonconsecutive_grid()
    test_rejects_nonfinite_valid_rvol()
    test_rejects_negative_valid_rvol()
    test_result_metadata_for_all_windows()
    test_result_and_arrays_are_immutable()

    print(
        "\nALL LRS-4 THRESHOLD-LEARNING STRUCTURAL TESTS PASSED"
    )
