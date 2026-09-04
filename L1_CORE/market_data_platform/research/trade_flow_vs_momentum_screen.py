"""
Market Data Platform -- Trade-Flow Imbalance vs Momentum Research Screen
market_data_platform/research/trade_flow_vs_momentum_screen.py

Frozen methodology, approved 2026-09-04. Research screen only -- no
promotion thresholds, no strategy, no execution/paper-trading logic.

CLOCK: trade_time, tiebreak trade_id.

FEATURE A -- trade-flow imbalance, (T-10s, T] window, O(1) via
prefix sums. Boundary: trades exactly at T-10s are EXCLUDED
(pointer condition trade_time[lb_ptr] <= T - lookback_ms advances
past them).

FEATURE B -- momentum, reference = latest trade with
trade_time <= T-10s. Boundary: a trade exactly at T-10s IS a valid
reference (searchsorted side="right" then -1 includes it). This
asymmetry vs. Feature A's boundary is intentional and frozen.

OUTCOMES -- strict (T, T+h] interval for h in {5, 15, 30, 60}s,
resolved via two explicit searchsorted calls (first_after_T,
last_by_horizon) rather than index comparison, which is required
for correctness when multiple trades share an exact timestamp.

COMMON OBSERVATION RULE (frozen): trade-flow imbalance is always
computable (0.0 when no volume), but momentum is NaN whenever no
valid 10s-prior reference exists in this instrument-day's data
(early-day observations). Comparative analysis between the two
candidates MUST restrict to the observations where momentum is
defined, and further to where the specific forward-return horizon
being analyzed is defined. compute_screen() returns raw values for
every sampled observation (nothing is dropped at this layer) PLUS
an explicit common_eligible mask (momentum defined). Callers
computing comparative deciles at horizon h must use exactly:
    common_eligible & ~np.isnan(return_h)
for BOTH features before assigning deciles -- never decile trade-
flow and momentum on different observation populations.

This module performs no Parquet I/O and no pandas DataFrame
construction. Peak memory of this computation kernel itself (prefix
arrays, sample arrays, temporaries) must be empirically measured on
the largest real instrument-day before being described as Pi-safe.
"""

import numpy as np


LOOKBACK_SECONDS = 10.0
HORIZONS = [5, 15, 30, 60]
SAMPLE_EVERY_NTH = 20


def validate_sorted_arrays(trade_time, trade_id, price, quantity, is_buyer_maker):
    """
    Fail-fast validation of the caller's contract: all five arrays
    must be equal length and already sorted by (trade_time, trade_id)
    ascending.

    Raises:
        ValueError: on any length mismatch or ordering violation.
    """
    lengths = {len(trade_time), len(trade_id), len(price), len(quantity), len(is_buyer_maker)}
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


def _build_prefix_sum(quantity, side_mask):
    """
    Builds a single prefix-sum array in place, without holding both
    the buy-side and sell-side masked-quantity temporaries at once.
    prefix[i] = sum of quantity[j] for j < i where side_mask[j] is True.

    Receives:
        quantity (np.ndarray[float]): full quantity array.
        side_mask (np.ndarray[bool]): True for rows to include.

    Returns:
        np.ndarray[float], length n+1.
    """
    n = len(quantity)
    prefix = np.empty(n + 1, dtype=np.float64)
    prefix[0] = 0.0
    masked = np.where(side_mask, quantity, 0.0)
    np.cumsum(masked, out=prefix[1:])
    del masked
    return prefix


def compute_screen(trade_time, trade_id, price, quantity, is_buyer_maker):
    """
    Computes both candidate features and all forward-return outcomes
    for one instrument-day's trades.

    Receives:
        trade_time, trade_id, price, quantity, is_buyer_maker
        (np.ndarray): aligned, sorted by (trade_time, trade_id),
        pre-filtered to a single instrument. Validated via
        validate_sorted_arrays() before use.

    Returns:
        dict with keys: sample_trade_time, sample_trade_id,
        sample_price, imbalance, momentum, return_5s, return_15s,
        return_30s, return_60s, common_eligible (bool array, True
        where momentum is defined -- see module docstring for the
        comparative-analysis contract this establishes).
    """
    validate_sorted_arrays(trade_time, trade_id, price, quantity, is_buyer_maker)

    n = len(trade_time)
    sample_positions = np.arange(SAMPLE_EVERY_NTH - 1, n, SAMPLE_EVERY_NTH)
    n_samples = len(sample_positions)

    lookback_ms = int(LOOKBACK_SECONDS * 1000)
    horizon_ms = {h: int(h * 1000) for h in HORIZONS}

    buy_prefix = _build_prefix_sum(quantity, ~is_buyer_maker)
    sell_prefix = _build_prefix_sum(quantity, is_buyer_maker)

    out_imbalance = np.full(n_samples, np.nan)
    out_momentum = np.full(n_samples, np.nan)
    out_returns = {h: np.full(n_samples, np.nan) for h in HORIZONS}

    lb_ptr = 0

    for i, idx in enumerate(sample_positions):
        T = trade_time[idx]
        P_T = price[idx]

        while lb_ptr < idx and trade_time[lb_ptr] <= T - lookback_ms:
            lb_ptr += 1

        buy_vol = buy_prefix[idx + 1] - buy_prefix[lb_ptr]
        sell_vol = sell_prefix[idx + 1] - sell_prefix[lb_ptr]
        total_vol = buy_vol + sell_vol
        out_imbalance[i] = (buy_vol - sell_vol) / total_vol if total_vol > 0 else 0.0

        ref_idx = np.searchsorted(trade_time, T - lookback_ms, side="right") - 1
        if ref_idx >= 0:
            out_momentum[i] = (P_T / price[ref_idx]) - 1.0

        first_after_T = np.searchsorted(trade_time, T, side="right")
        for h in HORIZONS:
            last_by_horizon = np.searchsorted(trade_time, T + horizon_ms[h], side="right") - 1
            if last_by_horizon >= first_after_T:
                out_returns[h][i] = (price[last_by_horizon] / P_T) - 1.0

    common_eligible = ~np.isnan(out_momentum)

    result = {
        "sample_trade_time": trade_time[sample_positions],
        "sample_trade_id": trade_id[sample_positions],
        "sample_price": price[sample_positions],
        "imbalance": out_imbalance,
        "momentum": out_momentum,
        "common_eligible": common_eligible,
    }
    for h in HORIZONS:
        result[f"return_{h}s"] = out_returns[h]

    return result


def rank_deciles(values, trade_time, trade_id):
    """
    Deterministic rank-based decile assignment, order
    (value, trade_time, trade_id). See module docstring's COMMON
    OBSERVATION RULE -- callers comparing imbalance vs momentum must
    pre-filter both value arrays to the same eligible-observation
    mask before calling this, or the two deciles will be computed
    over different populations.

    Receives:
        values (np.ndarray): feature values, may contain NaN.
        trade_time, trade_id (np.ndarray): tiebreak keys, aligned.

    Returns:
        np.ndarray: decile (0-9) per observation, -1 for NaN values.
    """
    n = len(values)
    deciles = np.full(n, -1, dtype=int)
    valid_idx = np.where(~np.isnan(values))[0]

    if len(valid_idx) == 0:
        return deciles

    order = valid_idx[np.lexsort((
        trade_id[valid_idx],
        trade_time[valid_idx],
        values[valid_idx],
    ))]

    bucket_size = len(order) / 10.0
    for rank, i in enumerate(order):
        deciles[i] = min(int(rank / bucket_size), 9)

    return deciles
