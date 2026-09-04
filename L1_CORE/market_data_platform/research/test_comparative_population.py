"""
Market Data Platform -- Comparative-Population Contract Fixture
market_data_platform/research/test_comparative_population.py

Proves build_comparative_population() enforces the frozen
apples-to-apples rule: at a given horizon, both candidate features
must be evaluated on exactly the same observations.

Constructs three observation types directly (bypassing
compute_screen(), since we need precise control over which fields
are NaN):
  A: momentum NaN, return_5s valid  -> excluded from BOTH at all horizons
  B: momentum valid, return_5s valid, return_15s valid -> included at 5s and 15s
  C: momentum valid, return_5s NaN, return_15s valid -> excluded at 5s, included at 15s

Run: python3 -m L1_CORE.market_data_platform.research.test_comparative_population
"""
import numpy as np

from L1_CORE.market_data_platform.research.run_trade_flow_vs_momentum_screen import (
    build_comparative_population,
)


def _make_result_fixture():
    sample_trade_time = np.array([1000, 2000, 3000], dtype=np.int64)
    sample_trade_id = np.array([1, 2, 3], dtype=np.int64)
    imbalance = np.array([0.5, 0.2, -0.1])
    momentum = np.array([np.nan, 0.01, 0.02])  # A: NaN, B/C: valid
    common_eligible = ~np.isnan(momentum)

    return_5s = np.array([0.001, 0.002, np.nan])   # A: valid, B: valid, C: NaN
    return_15s = np.array([0.003, 0.004, 0.005])   # all valid

    return {
        "sample_trade_time": sample_trade_time,
        "sample_trade_id": sample_trade_id,
        "imbalance": imbalance,
        "momentum": momentum,
        "common_eligible": common_eligible,
        "return_5s": return_5s,
        "return_15s": return_15s,
    }


def test_5s_excludes_A_and_C_includes_only_B():
    result = _make_result_fixture()
    pop = build_comparative_population(result, 5)

    assert pop["n"] == 1, f"expected n=1 (only B), got {pop['n']}"
    assert pop["sample_trade_id"][0] == 2, "expected only observation B (trade_id=2) at 5s"
    print("PASS: at 5s horizon, A and C correctly excluded; only B included")


def test_15s_excludes_A_includes_B_and_C():
    result = _make_result_fixture()
    pop = build_comparative_population(result, 15)

    assert pop["n"] == 2, f"expected n=2 (B and C), got {pop['n']}"
    assert set(pop["sample_trade_id"]) == {2, 3}, (
        f"expected observations B (id=2) and C (id=3) at 15s, got {set(pop['sample_trade_id'])}"
    )
    print("PASS: at 15s horizon, A correctly excluded; B and C both included")


def test_imbalance_and_momentum_share_identical_population():
    result = _make_result_fixture()

    for horizon in [5, 15]:
        pop = build_comparative_population(result, horizon)
        assert len(pop["imbalance"]) == len(pop["momentum"]) == pop["n"], (
            f"horizon {horizon}s: imbalance/momentum/n length mismatch: "
            f"{len(pop['imbalance'])}, {len(pop['momentum'])}, {pop['n']}"
        )
        assert len(pop["sample_trade_id"]) == pop["n"]

    print("PASS: imbalance and momentum share identical population size at each horizon (single shared mask)")


def test_mask_matches_manual_expectation():
    result = _make_result_fixture()

    pop_5s = build_comparative_population(result, 5)
    expected_mask_5s = np.array([False, True, False])
    assert np.array_equal(pop_5s["mask"], expected_mask_5s), (
        f"5s mask mismatch: expected {expected_mask_5s}, got {pop_5s['mask']}"
    )

    pop_15s = build_comparative_population(result, 15)
    expected_mask_15s = np.array([False, True, True])
    assert np.array_equal(pop_15s["mask"], expected_mask_15s), (
        f"15s mask mismatch: expected {expected_mask_15s}, got {pop_15s['mask']}"
    )
    print("PASS: comparative population mask exactly matches manual A/B/C expectation at both horizons")


if __name__ == "__main__":
    test_5s_excludes_A_and_C_includes_only_B()
    test_15s_excludes_A_includes_B_and_C()
    test_imbalance_and_momentum_share_identical_population()
    test_mask_matches_manual_expectation()
    print("\nALL TESTS PASSED")
