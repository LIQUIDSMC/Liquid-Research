"""
Market Data Platform -- Additive Imbalance-Only Feature Extractor
market_data_platform/research/imbalance_feature.py

Does not modify or call compute_screen(). Reuses existing constants
and _build_prefix_sum from the validated kernel
(trade_flow_vs_momentum_screen.py), while independently implementing
only the sampling/window/imbalance subset required for causal
feature extraction -- no price, no momentum, no forward returns, no
common_eligible. Correctness is established by equivalence tests
against compute_screen()["imbalance"] (see
test_imbalance_feature.py), not by inspection alone.

Built for the threshold-stability study's causal feature-population
requirement: a live threshold cannot depend on forward outcomes, and
(per explicit design decision) does not carry forward
common_eligible, since that filter exists to make imbalance and
momentum comparable -- a constraint intrinsic to the comparative
screen, not to the imbalance feature itself.

Given the same validated numeric inputs used by the research loader,
every sampled position receives either the computed imbalance ratio
or 0.0 when total trailing volume is zero -- confirmed directly from
compute_screen()'s source (no invalidity branch exists for
imbalance). This function does not itself enforce upstream numeric
validity (e.g. finite quantity) -- that responsibility remains with
the loader, consistent with validate_sorted_arrays()'s existing
scope, which likewise does not check finiteness.

Validator contract reproduced exactly from validate_sorted_arrays()
(confirmed by direct source inspection), restricted to the four
arrays this extractor actually uses (no price): equal-length arrays,
trade_time nondecreasing, trade_id nondecreasing among any equal
trade_time values, no dimensionality or finiteness checks (matching
the existing validator's actual scope, not inventing a stricter one).
"""

import numpy as np

from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
    _build_prefix_sum,
    LOOKBACK_SECONDS,
    SAMPLE_EVERY_NTH,
)


def validate_imbalance_inputs(trade_time, trade_id, quantity, is_buyer_maker):
    """
    Independent validator reproducing the exact ordering contract of
    validate_sorted_arrays() (confirmed by direct source inspection),
    restricted to the four arrays this extractor uses -- not a reuse
    of that function (which requires price, unused here), and not an
    expansion of its actual scope (no dimensionality or finiteness
    checks, matching the original exactly).

    Raises:
        ValueError: on any length mismatch or ordering violation.
    """
    lengths = {len(trade_time), len(trade_id), len(quantity), len(is_buyer_maker)}
    if len(lengths) != 1:
        raise ValueError(f"All input arrays must have equal length, got lengths: {lengths}")

    if len(trade_time) < 2:
        return

    time_diffs = np.diff(trade_time)
    if (time_diffs < 0).any():
        bad = np.where(time_diffs < 0)[0][0]
        raise ValueError(
            f"trade_time is not nondecreasing at position {bad}: "
            f"{trade_time[bad]} -> {trade_time[bad + 1]}"
        )

    equal_time_mask = time_diffs == 0
    if equal_time_mask.any():
        equal_positions = np.where(equal_time_mask)[0]
        id_diffs = np.diff(trade_id)[equal_positions]
        if (id_diffs < 0).any():
            bad = equal_positions[np.where(id_diffs < 0)[0][0]]
            raise ValueError(
                f"trade_id is not nondecreasing among equal trade_time "
                f"values at position {bad}: {trade_id[bad]} -> {trade_id[bad + 1]}"
            )


def compute_imbalance_only(trade_time, trade_id, quantity, is_buyer_maker):
    """
    Computes ONLY the 10s trade-flow imbalance at every-20th-trade
    sampled positions, reproducing exactly the imbalance-computation
    subset of compute_screen()'s logic.

    Receives:
        trade_time, trade_id, quantity, is_buyer_maker (np.ndarray):
        pre-sorted by (trade_time, trade_id), single instrument.

    Returns:
        dict: sample_trade_time, sample_trade_id, imbalance --
        aligned, one entry per every-20th-trade sampled position.
        Empty arrays if fewer than SAMPLE_EVERY_NTH trades exist.
    """
    validate_imbalance_inputs(trade_time, trade_id, quantity, is_buyer_maker)

    n = len(trade_time)
    sample_positions = np.arange(SAMPLE_EVERY_NTH - 1, n, SAMPLE_EVERY_NTH)
    n_samples = len(sample_positions)

    lookback_ms = int(LOOKBACK_SECONDS * 1000)

    buy_prefix = _build_prefix_sum(quantity, ~is_buyer_maker)
    sell_prefix = _build_prefix_sum(quantity, is_buyer_maker)

    out_imbalance = np.empty(n_samples, dtype=np.float64)

    lb_ptr = 0
    for i, idx in enumerate(sample_positions):
        T = trade_time[idx]

        while lb_ptr < idx and trade_time[lb_ptr] <= T - lookback_ms:
            lb_ptr += 1

        buy_vol = buy_prefix[idx + 1] - buy_prefix[lb_ptr]
        sell_vol = sell_prefix[idx + 1] - sell_prefix[lb_ptr]
        total_vol = buy_vol + sell_vol
        out_imbalance[i] = (buy_vol - sell_vol) / total_vol if total_vol > 0 else 0.0

    return {
        "sample_trade_time": trade_time[sample_positions],
        "sample_trade_id": trade_id[sample_positions],
        "imbalance": out_imbalance,
    }
