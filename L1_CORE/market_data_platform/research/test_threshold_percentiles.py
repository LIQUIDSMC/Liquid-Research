"""
Market Data Platform -- Tail-Threshold Percentile Helper Tests
market_data_platform/research/test_threshold_percentiles.py

Proves compute_tail_thresholds() matches the frozen inverted_cdf
specification, fails closed on empty/non-finite/non-1-D input, and
-- most importantly -- that its P10/P90 tail counts match the actual
frozen rank_deciles() implementation's D0/D9 rank counts for unique
values, which is the actual empirical justification for choosing
inverted_cdf in the first place.

Run: python3 -m L1_CORE.market_data_platform.research.test_threshold_percentiles
"""
import numpy as np

from L1_CORE.market_data_platform.research.threshold_percentiles import (
    compute_tail_thresholds,
    PERCENTILE_METHOD,
)
from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    rank_deciles,
)


def test_known_unique_n10():
    values = np.arange(10, dtype=np.float64)
    result = compute_tail_thresholds(values)
    assert result["p10"] == 0.0, f"expected P10=0.0, got {result['p10']}"
    assert result["p90"] == 8.0, f"expected P90=8.0, got {result['p90']}"
    assert result["observation_count"] == 10
    print("PASS: known unique n=10 -- P10=0.0, P90=8.0 exactly")


def test_known_unique_n11():
    values = np.arange(11, dtype=np.float64)
    result = compute_tail_thresholds(values)
    assert result["p10"] == 1.0, f"expected P10=1.0, got {result['p10']}"
    assert result["p90"] == 9.0, f"expected P90=9.0, got {result['p90']}"
    assert result["observation_count"] == 11
    print("PASS: known unique n=11 -- validates ceil-rank behavior (P10=1.0, P90=9.0)")


def test_known_unique_n20():
    values = np.arange(20, dtype=np.float64)
    result = compute_tail_thresholds(values)
    assert result["p10"] == 1.0, f"expected P10=1.0, got {result['p10']}"
    assert result["p90"] == 17.0, f"expected P90=17.0, got {result['p90']}"
    assert result["observation_count"] == 20
    print("PASS: known unique n=20 -- validates original tail-count mapping (P10=1.0, P90=17.0)")


def test_tied_values_deterministic():
    values = np.array([-1, -1, -1, -0.5, 0, 0, 0, 0.5, 1, 1, 1], dtype=np.float64)
    result = compute_tail_thresholds(values)

    expected_p10, expected_p90 = np.percentile(values, [10, 90], method="inverted_cdf")
    assert result["p10"] == expected_p10
    assert result["p90"] == expected_p90
    print(f"PASS: tied values -- deterministic empirical-CDF behavior (P10={result['p10']}, P90={result['p90']})")


def test_single_observation():
    values = np.array([42.0])
    result = compute_tail_thresholds(values)
    assert result["p10"] == 42.0
    assert result["p90"] == 42.0
    assert result["observation_count"] == 1
    print("PASS: single observation -- defined output (P10=P90=the single value)")


def test_empty_population_fails_closed():
    try:
        compute_tail_thresholds(np.array([], dtype=np.float64))
        raise AssertionError("Expected ValueError for empty population")
    except ValueError as e:
        assert "empty" in str(e)
    print("PASS: empty population correctly fails closed")


def test_nan_fails_closed():
    values = np.array([0.1, 0.2, np.nan, 0.4])
    try:
        compute_tail_thresholds(values)
        raise AssertionError("Expected ValueError for NaN in population")
    except ValueError as e:
        assert "non-finite" in str(e)
    print("PASS: NaN in population correctly fails closed")


def test_infinity_fails_closed():
    values_pos_inf = np.array([0.1, 0.2, np.inf, 0.4])
    values_neg_inf = np.array([0.1, 0.2, -np.inf, 0.4])

    for label, values in [("+inf", values_pos_inf), ("-inf", values_neg_inf)]:
        try:
            compute_tail_thresholds(values)
            raise AssertionError(f"Expected ValueError for {label} in population")
        except ValueError as e:
            assert "non-finite" in str(e)

    print("PASS: +inf and -inf both correctly fail closed (not just NaN)")


def test_non_1d_population_fails_closed():
    values = np.array([[0.1, 0.2], [0.3, 0.4]])

    try:
        compute_tail_thresholds(values)
        raise AssertionError("Expected ValueError for non-1-D population")
    except ValueError as e:
        assert "1-D" in str(e)

    print("PASS: non-1-D population correctly fails closed")


def test_input_not_mutated():
    original = np.array([5.0, 3.0, 1.0, 4.0, 2.0])
    original_copy = original.copy()
    compute_tail_thresholds(original)
    assert np.array_equal(original, original_copy), "input array was mutated"
    print("PASS: input array is not mutated")


def test_explicit_inverted_cdf_matches_direct_numpy_call():
    assert PERCENTILE_METHOD == "inverted_cdf", f"expected inverted_cdf, got {PERCENTILE_METHOD!r}"

    values = np.array([7.0, 2.0, 9.0, 4.0, 1.0, 8.0, 3.0, 6.0, 5.0, 0.0])
    result = compute_tail_thresholds(values)
    direct_p10, direct_p90 = np.percentile(values, [10, 90], method="inverted_cdf")
    assert result["p10"] == direct_p10
    assert result["p90"] == direct_p90
    print("PASS: explicit inverted_cdf usage confirmed, matches direct np.percentile call exactly")


def test_tail_count_correspondence_with_rank_deciles():
    """
    THE key empirical justification test: for unique values, compares
    the scalar threshold's tail counts directly against the ACTUAL
    frozen rank_deciles() implementation's D0/D9 bucket sizes -- not
    a duplicated formula reproducing an assumption about what
    rank_deciles() does. This is the real, direct proof that
    inverted_cdf's scalar thresholds correspond to the original
    rank-based tail construction.
    """
    for n in [10, 11, 20, 37, 100]:
        values = np.arange(n, dtype=np.float64)
        trade_time = np.arange(n, dtype=np.int64)
        trade_id = np.arange(n, dtype=np.int64)

        result = compute_tail_thresholds(values)
        deciles = rank_deciles(values, trade_time, trade_id)

        d0_count = int(np.sum(deciles == 0))
        d9_count = int(np.sum(deciles == 9))

        threshold_short_count = int(np.sum(values <= result["p10"]))
        threshold_long_count = int(np.sum(values > result["p90"]))

        assert threshold_short_count == d0_count, (
            f"n={n}: scalar threshold <=P10 count ({threshold_short_count}) does not match "
            f"actual rank_deciles() D0 count ({d0_count})"
        )
        assert threshold_long_count == d9_count, (
            f"n={n}: scalar threshold >P90 count ({threshold_long_count}) does not match "
            f"actual rank_deciles() D9 count ({d9_count})"
        )

    print("PASS: tail counts match the ACTUAL rank_deciles() D0/D9 bucket sizes exactly, "
          "for n=10,11,20,37,100")


if __name__ == "__main__":
    test_known_unique_n10()
    test_known_unique_n11()
    test_known_unique_n20()
    test_tied_values_deterministic()
    test_single_observation()
    test_empty_population_fails_closed()
    test_nan_fails_closed()
    test_infinity_fails_closed()
    test_non_1d_population_fails_closed()
    test_input_not_mutated()
    test_explicit_inverted_cdf_matches_direct_numpy_call()
    test_tail_count_correspondence_with_rank_deciles()
    print("\nALL TESTS PASSED")
