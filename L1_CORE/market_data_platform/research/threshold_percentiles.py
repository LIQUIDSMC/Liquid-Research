"""
Market Data Platform -- Tail-Threshold Percentile Helper
market_data_platform/research/threshold_percentiles.py

Pure percentile primitive. No dates, no instruments, no N-window
logic, no loading, no strategy signals -- computes thresholds from a
supplied historical population only. Dates/instruments/N and the
causal (strictly-prior-history) constraint are entirely the calling
runner's responsibility, not enforced here.

Frozen method: np.percentile(..., method="inverted_cdf"), passed
explicitly. For unique sorted values, its empirical-CDF cutpoints
align with the original rank_deciles() D0/D9 tail-count convention:
P10 corresponds to x[ceil(0.10*n)-1] and P90 to x[ceil(0.90*n)-1].
Scalar thresholds cannot reproduce rank_deciles() tie-splitting when
values equal the boundary; that limitation is handled/documented by
the threshold study, not by this helper.

Fail-closed: any non-finite value (NaN, +inf, -inf) in the input, or
an empty input, raises immediately. Does not filter or drop
non-finite values -- doing so could silently mask upstream
corruption and change the population without visibility. No
minimum-population floor is enforced (n=1 is permitted);
observation_count is always returned so real small-N behavior can be
observed empirically before any floor is considered.

Usage:
    from threshold_percentiles import compute_tail_thresholds
    result = compute_tail_thresholds(historical_imbalance_values)
    # result = {"p10": ..., "p90": ..., "observation_count": ...}
"""

import numpy as np

PERCENTILE_METHOD = "inverted_cdf"
LOWER_PERCENTILE = 10
UPPER_PERCENTILE = 90


def compute_tail_thresholds(values):
    """
    Computes the P10/P90 tail thresholds from a supplied 1-D
    historical population, using the frozen inverted_cdf method.

    Receives:
        values (np.ndarray or array-like): 1-D historical
        observations. Must be non-empty and entirely finite.

    Returns:
        dict: p10 (float), p90 (float), observation_count (int).

    Raises:
        ValueError: if values is empty, not 1-D, or contains any
        non-finite value (NaN, +inf, -inf). Does not mutate input.
    """
    values = np.asarray(values, dtype=np.float64)

    if values.ndim != 1:
        raise ValueError(f"values must be 1-D, got shape {values.shape}")

    if values.size == 0:
        raise ValueError("values is empty -- cannot compute percentiles from an empty population")

    nonfinite_mask = ~np.isfinite(values)
    if nonfinite_mask.any():
        count = int(nonfinite_mask.sum())
        raise ValueError(
            f"{count} non-finite value(s) (NaN/+inf/-inf) found in input population. "
            f"Refusing to compute thresholds -- this may indicate upstream corruption. "
            f"Population size: {values.size}."
        )

    p10, p90 = np.percentile(values, [LOWER_PERCENTILE, UPPER_PERCENTILE], method=PERCENTILE_METHOD)

    return {
        "p10": float(p10),
        "p90": float(p90),
        "observation_count": int(values.size),
    }
