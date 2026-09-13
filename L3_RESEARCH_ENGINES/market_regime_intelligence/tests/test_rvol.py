from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    ENDPOINT_VALID,
    GRID_INTERVAL_MS,
    RETURN_NO_PRECEDING_ENDPOINT,
    RETURN_VALID,
    GridReturnResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.rvol import (
    EXCESSIVE_CONTIGUOUS_RETURN_GAP,
    INSUFFICIENT_TRAILING_RETURN_COVERAGE,
    RVOL_VALID,
    WINDOW_SPECS,
    compute_rvol,
)


def _grid_with_returns(
    return_values,
    return_valid,
):
    """
    Build a structurally valid synthetic GridReturnResult.

    return_values / return_valid describe indices 1..N.
    Index 0 is the mandatory leading endpoint with no preceding return.
    """
    return_values = list(return_values)
    return_valid = list(return_valid)

    assert len(return_values) == len(return_valid)

    n_returns = len(return_values)
    n_grid = n_returns + 1

    endpoint_ms = np.arange(
        n_grid,
        dtype=np.int64,
    ) * GRID_INTERVAL_MS

    price = np.ones(n_grid, dtype=np.float64)
    source_trade_time = endpoint_ms.copy()
    source_trade_id = np.arange(
        1,
        n_grid + 1,
        dtype=np.int64,
    )
    trade_age_ms = np.zeros(n_grid, dtype=np.float64)

    endpoint_valid = np.ones(n_grid, dtype=bool)
    endpoint_reason = tuple(
        ENDPOINT_VALID
        for _ in range(n_grid)
    )

    log_return = np.full(
        n_grid,
        np.nan,
        dtype=np.float64,
    )
    valid_array = np.zeros(
        n_grid,
        dtype=bool,
    )

    reason = [RETURN_NO_PRECEDING_ENDPOINT]

    for i, (value, is_valid) in enumerate(
        zip(return_values, return_valid),
        start=1,
    ):
        if is_valid:
            log_return[i] = float(value)
            valid_array[i] = True
            reason.append(RETURN_VALID)
        else:
            reason.append("SYNTHETIC_INVALID_RETURN")

    return GridReturnResult(
        grid_interval_ms=GRID_INTERVAL_MS,
        endpoint_ms=endpoint_ms,
        price=price,
        source_trade_time=source_trade_time,
        source_trade_id=source_trade_id,
        trade_age_ms=trade_age_ms,
        endpoint_valid=endpoint_valid,
        endpoint_reason=endpoint_reason,
        log_return=log_return,
        return_valid=valid_array,
        return_reason=tuple(reason),
    )


def test_frozen_window_specs_are_exact():
    one_h = WINDOW_SPECS["1h"]
    four_h = WINDOW_SPECS["4h"]
    twenty_four_h = WINDOW_SPECS["24h"]

    assert one_h.expected_returns == 12
    assert one_h.min_valid_returns == 9
    assert one_h.max_contiguous_invalid_returns == 3

    assert four_h.expected_returns == 48
    assert four_h.min_valid_returns == 36
    assert four_h.max_contiguous_invalid_returns == 12

    assert twenty_four_h.expected_returns == 288
    assert twenty_four_h.min_valid_returns == 216
    assert twenty_four_h.max_contiguous_invalid_returns == 72

    print("PASS: frozen 1h/4h/24h RVOL window counts are exact")


def test_no_partial_warmup():
    grid = _grid_with_returns(
        [0.01] * 12,
        [True] * 12,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    # 12 returns require 13 endpoints.
    # Only index 12 has a complete 1h causal window.
    assert result.history_complete[:12].tolist() == [
        False
    ] * 12
    assert result.history_complete[12] is np.bool_(True) or bool(
        result.history_complete[12]
    )

    for i in range(12):
        assert result.rvol_reasons[i] == ()
        assert result.rvol_valid[i] is np.bool_(False) or not bool(
            result.rvol_valid[i]
        )
        assert np.isnan(result.rvol[i])

    print(
        "PASS: incomplete trailing history is not mislabeled as "
        "D4/D5 coverage failure"
    )


def test_nine_of_twelve_with_three_contiguous_invalid_passes():
    values = [0.01] * 12

    valid = [
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

    grid = _grid_with_returns(
        values,
        valid,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    i = 12

    assert result.history_complete[i]
    assert result.valid_return_count[i] == 9
    assert result.invalid_return_count[i] == 3
    assert np.isclose(
        result.coverage_fraction[i],
        0.75,
    )
    assert result.max_contiguous_invalid_returns[i] == 3
    assert result.aggregate_coverage_pass[i]
    assert result.contiguous_gap_pass[i]
    assert result.rvol_valid[i]
    assert result.rvol_reasons[i] == (
        RVOL_VALID,
    )

    print(
        "PASS: exact 75% coverage and contiguous invalid run of 3 "
        "both pass by equality"
    )


def test_eight_of_twelve_scattered_invalids_fails_aggregate_only():
    values = [0.01] * 12

    valid = [
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        True,
        True,
        True,
        True,
    ]

    grid = _grid_with_returns(
        values,
        valid,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    i = 12

    assert result.valid_return_count[i] == 8
    assert result.invalid_return_count[i] == 4
    assert result.max_contiguous_invalid_returns[i] == 1

    assert not result.aggregate_coverage_pass[i]
    assert result.contiguous_gap_pass[i]

    assert not result.rvol_valid[i]
    assert np.isnan(result.realized_variance[i])
    assert np.isnan(result.rvol[i])

    assert result.rvol_reasons[i] == (
        INSUFFICIENT_TRAILING_RETURN_COVERAGE,
    )

    print(
        "PASS: four scattered invalid returns trigger aggregate "
        "coverage failure only"
    )


def test_four_contiguous_invalids_retain_both_failure_codes():
    values = [0.01] * 12

    valid = [
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

    grid = _grid_with_returns(
        values,
        valid,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    i = 12

    assert result.valid_return_count[i] == 8
    assert result.invalid_return_count[i] == 4
    assert result.max_contiguous_invalid_returns[i] == 4

    assert not result.aggregate_coverage_pass[i]
    assert not result.contiguous_gap_pass[i]
    assert not result.rvol_valid[i]

    assert result.rvol_reasons[i] == (
        INSUFFICIENT_TRAILING_RETURN_COVERAGE,
        EXCESSIVE_CONTIGUOUS_RETURN_GAP,
    )

    print(
        "PASS: simultaneous aggregate and contiguous-gap failures "
        "retain both frozen reason codes"
    )


def test_raw_observed_realized_variance_is_not_scaled():
    values = [
        0.01,
        0.02,
        0.03,
        0.04,
        0.05,
        0.06,
        0.07,
        0.08,
        0.09,
        0.10,
        0.11,
        0.12,
    ]

    # 9 observed returns and 3 contiguous missing returns.
    valid = [
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

    grid = _grid_with_returns(
        values,
        valid,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    i = 12

    observed = np.asarray(
        [
            value
            for value, is_valid in zip(values, valid)
            if is_valid
        ],
        dtype=np.float64,
    )

    expected_raw_rv = float(
        np.sum(
            observed ** 2,
            dtype=np.float64,
        )
    )

    expected_raw_rvol = float(
        np.sqrt(expected_raw_rv)
    )

    assert result.rvol_valid[i]
    assert np.isclose(
        result.realized_variance[i],
        expected_raw_rv,
    )
    assert np.isclose(
        result.rvol[i],
        expected_raw_rvol,
    )

    # Explicitly prove that the rejected N_expected/N_valid
    # exposure-scaling estimator is NOT being used.
    scaled_rv = expected_raw_rv * (12 / 9)

    assert not np.isclose(
        result.realized_variance[i],
        scaled_rv,
    )

    print(
        "PASS: RVOL uses raw observed squared returns with no "
        "coverage/exposure scaling"
    )


def test_all_valid_returns_compute_exact_rvol():
    values = np.asarray(
        [0.001 * i for i in range(1, 13)],
        dtype=np.float64,
    )

    grid = _grid_with_returns(
        values.tolist(),
        [True] * 12,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    i = 12

    expected_rv = float(
        np.sum(
            values ** 2,
            dtype=np.float64,
        )
    )

    assert result.valid_return_count[i] == 12
    assert result.invalid_return_count[i] == 0
    assert result.max_contiguous_invalid_returns[i] == 0

    assert np.isclose(
        result.realized_variance[i],
        expected_rv,
    )
    assert np.isclose(
        result.rvol[i],
        np.sqrt(expected_rv),
    )
    assert result.rvol_reasons[i] == (
        RVOL_VALID,
    )

    print("PASS: fully observed 1h RVOL equals exact sum-of-squares estimator")


def test_window_is_trailing_and_rolls_forward():
    # 13 returns => two complete 1h windows:
    # endpoint 12 sees returns 1..12
    # endpoint 13 sees returns 2..13
    values = [
        0.01,
        0.02,
        0.03,
        0.04,
        0.05,
        0.06,
        0.07,
        0.08,
        0.09,
        0.10,
        0.11,
        0.12,
        0.50,
    ]

    grid = _grid_with_returns(
        values,
        [True] * 13,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    expected_12 = np.sum(
        np.square(values[:12]),
        dtype=np.float64,
    )
    expected_13 = np.sum(
        np.square(values[1:13]),
        dtype=np.float64,
    )

    assert np.isclose(
        result.realized_variance[12],
        expected_12,
    )
    assert np.isclose(
        result.realized_variance[13],
        expected_13,
    )

    assert not np.isclose(
        result.realized_variance[12],
        result.realized_variance[13],
    )

    print("PASS: RVOL window rolls causally one 5m return at a time")


def test_unsupported_window_fails_closed():
    grid = _grid_with_returns(
        [0.01] * 12,
        [True] * 12,
    )

    try:
        compute_rvol(
            grid,
            "2h",
        )
        raise AssertionError(
            "Expected unsupported RVOL window to fail"
        )
    except ValueError as exc:
        assert "Unsupported frozen RVOL window" in str(exc)

    print("PASS: unsupported RVOL horizon fails closed")


def test_nonconsecutive_grid_fails_closed():
    grid = _grid_with_returns(
        [0.01] * 12,
        [True] * 12,
    )

    broken_endpoint_ms = grid.endpoint_ms.copy()
    broken_endpoint_ms[5] += 1

    broken = GridReturnResult(
        grid_interval_ms=grid.grid_interval_ms,
        endpoint_ms=broken_endpoint_ms,
        price=grid.price,
        source_trade_time=grid.source_trade_time,
        source_trade_id=grid.source_trade_id,
        trade_age_ms=grid.trade_age_ms,
        endpoint_valid=grid.endpoint_valid,
        endpoint_reason=grid.endpoint_reason,
        log_return=grid.log_return,
        return_valid=grid.return_valid,
        return_reason=grid.return_reason,
    )

    try:
        compute_rvol(
            broken,
            "1h",
        )
        raise AssertionError(
            "Expected nonconsecutive grid to fail"
        )
    except ValueError as exc:
        assert "not consecutive" in str(exc)

    print("PASS: RVOL rejects nonconsecutive grid endpoints")


def test_valid_return_marked_nonfinite_fails_closed():
    grid = _grid_with_returns(
        [0.01] * 12,
        [True] * 12,
    )

    broken_returns = grid.log_return.copy()
    broken_returns[5] = np.nan

    broken = GridReturnResult(
        grid_interval_ms=grid.grid_interval_ms,
        endpoint_ms=grid.endpoint_ms,
        price=grid.price,
        source_trade_time=grid.source_trade_time,
        source_trade_id=grid.source_trade_id,
        trade_age_ms=grid.trade_age_ms,
        endpoint_valid=grid.endpoint_valid,
        endpoint_reason=grid.endpoint_reason,
        log_return=broken_returns,
        return_valid=grid.return_valid,
        return_reason=grid.return_reason,
    )

    try:
        compute_rvol(
            broken,
            "1h",
        )
        raise AssertionError(
            "Expected nonfinite valid return to fail"
        )
    except ValueError as exc:
        assert "non-finite return" in str(exc)

    print("PASS: valid return cannot carry nonfinite numeric value")


def test_rvol_result_and_arrays_are_immutable():
    grid = _grid_with_returns(
        [0.01] * 12,
        [True] * 12,
    )

    result = compute_rvol(
        grid,
        "1h",
    )

    try:
        result.window_name = "4h"
        raise AssertionError(
            "Expected frozen RvolResult mutation to fail"
        )
    except FrozenInstanceError:
        pass

    try:
        result.rvol[12] = 999.0
        raise AssertionError(
            "Expected read-only RVOL result array mutation to fail"
        )
    except ValueError:
        pass

    assert result.endpoint_ms.flags.writeable is False
    assert result.history_complete.flags.writeable is False
    assert result.valid_return_count.flags.writeable is False
    assert result.coverage_fraction.flags.writeable is False
    assert result.realized_variance.flags.writeable is False
    assert result.rvol.flags.writeable is False
    assert result.rvol_valid.flags.writeable is False

    print("PASS: RVOL evidence object and arrays are immutable")


if __name__ == "__main__":
    test_frozen_window_specs_are_exact()
    test_no_partial_warmup()
    test_nine_of_twelve_with_three_contiguous_invalid_passes()
    test_eight_of_twelve_scattered_invalids_fails_aggregate_only()
    test_four_contiguous_invalids_retain_both_failure_codes()
    test_raw_observed_realized_variance_is_not_scaled()
    test_all_valid_returns_compute_exact_rvol()
    test_window_is_trailing_and_rolls_forward()
    test_unsupported_window_fails_closed()
    test_nonconsecutive_grid_fails_closed()
    test_valid_return_marked_nonfinite_fails_closed()
    test_rvol_result_and_arrays_are_immutable()

    print("\nALL LRS-4 RVOL STRUCTURAL TESTS PASSED")
