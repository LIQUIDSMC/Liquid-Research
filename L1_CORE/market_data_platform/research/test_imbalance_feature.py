"""
Market Data Platform -- Imbalance-Only Extractor Equivalence Tests
market_data_platform/research/test_imbalance_feature.py

Proves compute_imbalance_only() is exactly equivalent to the
imbalance/sample-position outputs of compute_screen() across
representative and boundary cases.

Run: python3 -m L1_CORE.market_data_platform.research.test_imbalance_feature
"""
import numpy as np

from L1_CORE.market_data_platform.research.imbalance_feature import (
    compute_imbalance_only,
    validate_imbalance_inputs,
)
from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    compute_screen,
    SAMPLE_EVERY_NTH,
)


def _make_fixture(n_trades, base_time_ms=0):
    trade_time = base_time_ms + np.arange(n_trades, dtype=np.int64)
    trade_id = np.arange(n_trades, dtype=np.int64)
    price = 100.0 + np.arange(n_trades, dtype=np.float64)
    quantity = np.ones(n_trades, dtype=np.float64)
    is_buyer_maker = np.array([i % 2 == 0 for i in range(n_trades)])
    return trade_time, trade_id, price, quantity, is_buyer_maker


def _assert_full_equivalence(new_result, old_result, label):
    assert np.array_equal(new_result["sample_trade_time"], old_result["sample_trade_time"]), \
        f"{label}: sample_trade_time mismatch"
    assert np.array_equal(new_result["sample_trade_id"], old_result["sample_trade_id"]), \
        f"{label}: sample_trade_id mismatch"
    assert np.array_equal(new_result["imbalance"], old_result["imbalance"]), \
        f"{label}: imbalance mismatch"


def test_normal_fixture_equivalence():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(100)
    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    _assert_full_equivalence(new_result, old_result, "normal fixture (n=100)")
    print("PASS: normal representative fixture -- full equivalence")


def test_same_timestamp_causal_ordering_equivalence():
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
    is_buyer_maker[18] = False
    quantity[20] = 700.0
    is_buyer_maker[20] = True

    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    _assert_full_equivalence(new_result, old_result, "same-timestamp causal ordering")
    print("PASS: same-timestamp causal ordering -- full equivalence")


def test_sparse_early_window_equivalence():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    _assert_full_equivalence(new_result, old_result, "sparse/early window")
    print("PASS: sparse/early window -- full equivalence (imbalance unaffected by momentum's NaN)")


def test_zero_volume_window_equivalence():
    """
    Directly exercises the total_vol == 0 branch (imbalance -> 0.0).
    The extractor's own validator permits zero quantity (confirmed:
    it enforces only length/ordering, no positivity requirement), so
    this is a legitimate, directly-testable case, not a fabricated
    scenario the kernel would reject.
    """
    n = 40
    trade_time = np.arange(n, dtype=np.int64) * 1000
    trade_id = np.arange(n, dtype=np.int64)
    price = np.full(n, 100.0)
    quantity = np.zeros(n, dtype=np.float64)
    is_buyer_maker = np.array([i % 2 == 0 for i in range(n)])

    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)

    assert np.all(new_result["imbalance"] == 0.0), "expected all-zero imbalance under zero volume"
    _assert_full_equivalence(new_result, old_result, "zero-volume branch")
    print("PASS: zero-volume branch (total_vol == 0 -> imbalance 0.0) -- full equivalence")


def test_large_deterministic_fixture_equivalence():
    """
    1000+ trades with NONUNIFORM but deterministic spacing (no
    randomness), specifically designed so the 10s trailing window
    continuously rolls forward across many distinct lb_ptr
    positions -- a uniform 1ms-spacing fixture of this size would
    span only ~1.2s total, never advancing the window pointer at
    all, which would silently fail to exercise the window-shift
    logic despite claiming to.
    """
    n = 1237
    increments = 100 + (np.arange(n, dtype=np.int64) % 17) * 137
    trade_time = np.cumsum(increments).astype(np.int64)
    trade_id = np.arange(n, dtype=np.int64)
    price = 100.0 + np.arange(n, dtype=np.float64) * 0.01
    quantity = 1.0 + (np.arange(n, dtype=np.float64) % 7) * 0.5
    is_buyer_maker = (np.arange(n) % 3 == 0)

    total_span_s = (trade_time[-1] - trade_time[0]) / 1000.0

    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)
    _assert_full_equivalence(new_result, old_result, f"large deterministic fixture (n={n})")
    print(f"PASS: large deterministic fixture (n={n}, span={total_span_s:.1f}s, "
          f"{len(new_result['imbalance'])} samples) -- full equivalence, window rolls forward")


def test_fewer_than_sample_interval_trades():
    n = 19
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(n)

    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)

    assert len(new_result["imbalance"]) == 0, f"expected 0 samples for n={n}, got {len(new_result['imbalance'])}"
    _assert_full_equivalence(new_result, old_result, f"n={n} (< SAMPLE_EVERY_NTH)")
    print(f"PASS: n={n} (< {SAMPLE_EVERY_NTH}) correctly produces zero samples, matches kernel exactly")


def test_exactly_sample_interval_trades():
    n = 20
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(n)

    new_result = compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker)
    old_result = compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker)

    assert len(new_result["imbalance"]) == 1, f"expected exactly 1 sample for n={n}, got {len(new_result['imbalance'])}"
    assert new_result["sample_trade_id"][0] == 19, "expected the single sample to be at index 19 (trade_id=19)"
    _assert_full_equivalence(new_result, old_result, f"n={n} (== SAMPLE_EVERY_NTH)")
    print(f"PASS: n={n} (== {SAMPLE_EVERY_NTH}) produces exactly one sample at index 19, matches kernel exactly")


def test_validator_accepts_valid_input():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    validate_imbalance_inputs(trade_time, trade_id, quantity, is_buyer_maker)
    print("PASS: validate_imbalance_inputs accepts valid sorted input")


def test_validator_rejects_length_mismatch():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    try:
        validate_imbalance_inputs(trade_time, trade_id[:-1], quantity, is_buyer_maker)
        raise AssertionError("Expected ValueError for length mismatch")
    except ValueError as e:
        assert "length" in str(e)
    print("PASS: validate_imbalance_inputs rejects length mismatch")


def test_validator_rejects_decreasing_time():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    trade_time[10] = trade_time[9] - 1
    try:
        validate_imbalance_inputs(trade_time, trade_id, quantity, is_buyer_maker)
        raise AssertionError("Expected ValueError for decreasing trade_time")
    except ValueError as e:
        assert "nondecreasing" in str(e)
    print("PASS: validate_imbalance_inputs rejects decreasing trade_time")


def test_validator_rejects_decreasing_trade_id_on_tie():
    trade_time, trade_id, price, quantity, is_buyer_maker = _make_fixture(50)
    trade_time[10] = trade_time[9]
    trade_id[10] = trade_id[9] - 1
    try:
        validate_imbalance_inputs(trade_time, trade_id, quantity, is_buyer_maker)
        raise AssertionError("Expected ValueError for decreasing trade_id on tie")
    except ValueError as e:
        assert "trade_id" in str(e)
    print("PASS: validate_imbalance_inputs rejects decreasing trade_id on tie")


if __name__ == "__main__":
    test_normal_fixture_equivalence()
    test_same_timestamp_causal_ordering_equivalence()
    test_sparse_early_window_equivalence()
    test_zero_volume_window_equivalence()
    test_large_deterministic_fixture_equivalence()
    test_fewer_than_sample_interval_trades()
    test_exactly_sample_interval_trades()
    test_validator_accepts_valid_input()
    test_validator_rejects_length_mismatch()
    test_validator_rejects_decreasing_time()
    test_validator_rejects_decreasing_trade_id_on_tie()
    print("\nALL TESTS PASSED")
