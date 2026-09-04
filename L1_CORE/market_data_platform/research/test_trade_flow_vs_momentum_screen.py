"""
Market Data Platform -- Fixture Tests for the Trade-Flow vs Momentum
Research Screen Kernel
market_data_platform/research/test_trade_flow_vs_momentum_screen.py

Deterministic, small, hand-constructed fixtures targeting the exact
frozen temporal boundaries: exactly T-10s, exactly T (including
same-millisecond causal ordering), duplicate timestamps at T,
exactly T+h (and specifically the LAST trade within the horizon),
and just after T+h.

Run: python3 -m L1_CORE.market_data_platform.research.test_trade_flow_vs_momentum_screen
"""
import numpy as np

from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    compute_screen,
    rank_deciles,
    validate_sorted_arrays,
)


def _make_fixture(n_trades, base_time_ms=0):
    trade_time = base_time_ms + np.arange(n_trades, dtype=np.int64)
    trade_id = np.arange(n_trades, dtype=np.int64)
    price = 100.0 + np.arange(n_trades, dtype=np.float64)
    quantity = np.ones(n_trades, dtype=np.float64)
    is_buyer_maker = np.array([i % 2 == 0 for i in range(n_trades)])
    return trade_time, trade_id, price, quantity, is_buyer_maker


def test_validate_sorted_arrays_accepts_valid_input():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    validate_sorted_arrays(trade_time, trade_id, price, quantity, is_buyer_maker)
    print("PASS: validate_sorted_arrays accepts valid sorted input")


def test_validate_sorted_arrays_rejects_length_mismatch():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    try:
        validate_sorted_arrays(trade_time, trade_id[:-1], price, quantity, is_buyer_maker)
        raise AssertionError("Expected ValueError for length mismatch")
    except ValueError as e:
        assert "length" in str(e)
    print("PASS: validate_sorted_arrays rejects length mismatch")


def test_validate_sorted_arrays_rejects_decreasing_time():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    trade_time[10] = trade_time[9] - 1
    try:
        validate_sorted_arrays(trade_time, trade_id, price, quantity, is_buyer_maker)
        raise AssertionError("Expected ValueError for decreasing trade_time")
    except ValueError as e:
        assert "nondecreasing" in str(e)
    print("PASS: validate_sorted_arrays rejects decreasing trade_time")


def test_validate_sorted_arrays_rejects_decreasing_trade_id_on_tie():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    trade_time[10] = trade_time[9]
    trade_id[10] = trade_id[9] - 1
    try:
        validate_sorted_arrays(trade_time, trade_id, price, quantity, is_buyer_maker)
        raise AssertionError("Expected ValueError for decreasing trade_id on tie")
    except ValueError as e:
        assert "trade_id" in str(e)
    print("PASS: validate_sorted_arrays rejects decreasing trade_id on tie")


def test_momentum_reference_exactly_at_T_minus_10s_is_valid():
    n = 40
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = 100.0 + np.arange(n, dtype=np.float64)
    quantity = np.ones(n, dtype=np.float64)
    is_buyer_maker = np.zeros(n, dtype=bool)

    T_idx = 19
    T = trade_time[T_idx]
    target_time = T - 10_000
    exact_idx = np.searchsorted(trade_time, target_time)
    assert trade_time[exact_idx] == target_time, "fixture construction assumption failed"

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    momentum = result["momentum"][0]
    expected_momentum = (price[T_idx] / price[exact_idx]) - 1.0
    assert not np.isnan(momentum), "momentum should be valid when a trade exists exactly at T-10s"
    assert abs(momentum - expected_momentum) < 1e-12, f"expected {expected_momentum}, got {momentum}"
    print("PASS: momentum reference exactly at T-10s is valid (inclusive boundary)")


def test_flow_window_boundary_discriminating_case():
    n = 40
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = np.full(n, 100.0)
    is_buyer_maker = np.zeros(n, dtype=bool)
    quantity = np.ones(n, dtype=np.float64)

    T_idx = 19
    T = trade_time[T_idx]
    target_time = T - 10_000
    exact_idx = np.searchsorted(trade_time, target_time)
    assert trade_time[exact_idx] == target_time

    is_buyer_maker[exact_idx] = True  # sell
    quantity[exact_idx] = 999.0

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    imbalance = result["imbalance"][0]
    assert imbalance == 1.0, (
        f"expected imbalance=1.0 (boundary sell excluded), got {imbalance} "
        f"-- the T-10s boundary trade appears to have been wrongly included"
    )
    print("PASS: flow window correctly EXCLUDES trade exactly at T-10s (discriminating case)")


def test_flow_window_same_timestamp_causal_ordering():
    """
    Three trades share the EXACT same trade_time == T:
      index 18 (trade_id=18, before sample):  huge BUY
      index 19 (trade_id=19, the sampled trade)
      index 20 (trade_id=20, after sample):   huge SELL

    Same-T rows ordered BEFORE or AT the sample must be included in
    Feature A; same-T rows ordered AFTER the sample must NOT leak
    backward into its feature value.
    """
    n = 40
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = np.full(n, 100.0)
    quantity = np.ones(n, dtype=np.float64)
    is_buyer_maker = np.zeros(n, dtype=bool)

    T_idx = 19
    T = trade_time[T_idx]

    trade_time[18] = T
    trade_time[20] = T

    quantity[18] = 500.0
    is_buyer_maker[18] = False  # buy

    quantity[20] = 700.0
    is_buyer_maker[20] = True  # sell -- must not count

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    imbalance = result["imbalance"][0]

    assert imbalance == 1.0, (
        f"expected imbalance=1.0 (later same-T sell must not leak backward "
        f"into the sampled observation's flow window), got {imbalance}"
    )
    print("PASS: same-timestamp causal ordering -- later same-T row does not leak into Feature A")


def test_forward_return_boundary_properly_aligned():
    n = 40
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = 100.0 + np.arange(n, dtype=np.float64)
    quantity = np.ones(n, dtype=np.float64)
    is_buyer_maker = np.zeros(n, dtype=bool)

    T_idx = 19
    T = trade_time[T_idx]
    exact_idx = np.searchsorted(trade_time, T + 5_000)
    assert trade_time[exact_idx] == T + 5_000, "fixture construction assumption failed"

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    ret_5s = result["return_5s"][0]
    expected = (price[exact_idx] / price[T_idx]) - 1.0
    assert not np.isnan(ret_5s), "return_5s should be valid with a trade exactly at T+5s"
    assert abs(ret_5s - expected) < 1e-12, f"expected {expected}, got {ret_5s}"
    print("PASS: forward return correctly INCLUDES trade exactly at T+h (inclusive upper boundary)")


def test_forward_return_uses_last_trade_in_horizon_not_first_or_middle():
    """
    Frozen rule specifically says the LAST trade in (T, T+h], not
    merely "a" trade in that interval. Constructs three distinct
    trades inside a 5s horizon with different prices and confirms
    the final one is used. n=24 deliberately stops just short of a
    trade at exactly T+5s (that inclusive-boundary case is covered
    separately by test_forward_return_boundary_properly_aligned),
    so T+4s really is the last eligible trade here.
    """
    n = 24
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = np.full(n, 100.0)
    quantity = np.ones(n, dtype=np.float64)
    is_buyer_maker = np.zeros(n, dtype=bool)

    T_idx = 19
    T = trade_time[T_idx]

    idx_t1 = np.searchsorted(trade_time, T + 1_000)
    idx_t3 = np.searchsorted(trade_time, T + 3_000)
    idx_t4 = np.searchsorted(trade_time, T + 4_000)
    assert trade_time[idx_t1] == T + 1_000
    assert trade_time[idx_t3] == T + 3_000
    assert trade_time[idx_t4] == T + 4_000

    price[idx_t1] = 101.0
    price[idx_t3] = 150.0
    price[idx_t4] = 90.0  # the LAST trade within the 5s horizon

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    ret_5s = result["return_5s"][0]
    expected = (90.0 / price[T_idx]) - 1.0
    assert abs(ret_5s - expected) < 1e-12, (
        f"expected return based on price 90.0 (the LAST trade in the horizon), "
        f"got a return implying a different price -- ret_5s={ret_5s}, expected={expected}"
    )
    print("PASS: forward return uses the LAST trade within (T, T+h], not the first or middle one")


def test_forward_return_just_after_horizon_is_excluded():
    n = 21
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = 100.0 + np.arange(n, dtype=np.float64)
    quantity = np.ones(n, dtype=np.float64)
    is_buyer_maker = np.zeros(n, dtype=bool)

    T_idx = 19
    T = trade_time[T_idx]
    trade_time[20] = T + 5_001

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    ret_5s = result["return_5s"][0]
    assert np.isnan(ret_5s), f"expected NaN (no trade within (T, T+5s]), got {ret_5s}"
    print("PASS: forward return correctly EXCLUDES a trade just after the horizon (NaN)")


def test_duplicate_timestamps_at_T_do_not_break_forward_return():
    n = 21
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = 100.0 + np.arange(n, dtype=np.float64)
    quantity = np.ones(n, dtype=np.float64)
    is_buyer_maker = np.zeros(n, dtype=bool)

    T_idx = 19
    T = trade_time[T_idx]
    trade_time[20] = T

    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    ret_5s = result["return_5s"][0]
    assert np.isnan(ret_5s), (
        f"expected NaN (duplicate timestamp at T is not > T, so not in (T, T+5s]), got {ret_5s}"
    )
    print("PASS: duplicate timestamp exactly at T correctly excluded from forward interval")


def test_common_eligible_mask_matches_momentum_validity():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(100)
    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    expected_mask = ~np.isnan(result["momentum"])
    assert np.array_equal(result["common_eligible"], expected_mask)
    print("PASS: common_eligible mask exactly matches momentum validity")


def test_early_observations_have_nan_momentum():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    assert np.isnan(result["momentum"][0]), "expected NaN momentum for an early, lookback-starved sample"
    assert not np.isnan(result["imbalance"][0]), "trade-flow imbalance should never be NaN"
    print("PASS: early observations correctly get NaN momentum, valid (non-NaN) imbalance")


def test_rank_deciles_no_silent_bin_collapse_on_duplicate_values():
    n = 100
    values = np.zeros(n)
    values[:10] = np.nan
    trade_time = np.arange(n, dtype=np.int64)
    trade_id = np.arange(n, dtype=np.int64)

    deciles = rank_deciles(values, trade_time, trade_id)
    assert (deciles[:10] == -1).all(), "NaN values should be excluded (-1)"
    valid_deciles = deciles[10:]
    assert set(valid_deciles) == set(range(10)), (
        f"expected all 10 deciles populated even with identical values, got {set(valid_deciles)}"
    )
    print("PASS: rank_deciles produces all 10 buckets even with fully duplicate feature values")


def test_rank_deciles_deterministic_tiebreak_order_via_actual_function():
    n = 100
    rng = np.random.RandomState(42)
    trade_time = np.repeat(np.arange(10, dtype=np.int64), 10)
    trade_id = np.tile(np.arange(10, dtype=np.int64), 10)
    shuffle_idx = rng.permutation(n)
    trade_time = trade_time[shuffle_idx]
    trade_id = trade_id[shuffle_idx]
    values = np.zeros(n)

    deciles_first = rank_deciles(values, trade_time, trade_id)
    deciles_second = rank_deciles(values, trade_time, trade_id)
    assert np.array_equal(deciles_first, deciles_second), "rank_deciles is not deterministic across repeated calls"

    true_order = np.lexsort((trade_id, trade_time))
    ordered_deciles = deciles_first[true_order]
    assert (np.diff(ordered_deciles) >= 0).all(), (
        f"decile assignment is not monotonically consistent with "
        f"(trade_time, trade_id) tiebreak order: {ordered_deciles}"
    )
    assert set(ordered_deciles) == set(range(10)), "expected all 10 deciles populated"
    print("PASS: rank_deciles() itself is deterministic and follows (trade_time, trade_id) tiebreak order")


if __name__ == "__main__":
    test_validate_sorted_arrays_accepts_valid_input()
    test_validate_sorted_arrays_rejects_length_mismatch()
    test_validate_sorted_arrays_rejects_decreasing_time()
    test_validate_sorted_arrays_rejects_decreasing_trade_id_on_tie()
    test_momentum_reference_exactly_at_T_minus_10s_is_valid()
    test_flow_window_boundary_discriminating_case()
    test_flow_window_same_timestamp_causal_ordering()
    test_forward_return_boundary_properly_aligned()
    test_forward_return_uses_last_trade_in_horizon_not_first_or_middle()
    test_forward_return_just_after_horizon_is_excluded()
    test_duplicate_timestamps_at_T_do_not_break_forward_return()
    test_common_eligible_mask_matches_momentum_validity()
    test_early_observations_have_nan_momentum()
    test_rank_deciles_no_silent_bin_collapse_on_duplicate_values()
    test_rank_deciles_deterministic_tiebreak_order_via_actual_function()
    print("\nALL TESTS PASSED")
