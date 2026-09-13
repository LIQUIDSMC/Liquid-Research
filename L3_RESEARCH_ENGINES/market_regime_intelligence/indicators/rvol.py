"""
LRS-4 Experiment v1 — trailing realized-volatility construction.

Scope:
    frozen 5-minute GridReturnResult
        -> trailing W return-slot accounting
        -> local coverage diagnostics
        -> contiguous-invalid-run diagnostic
        -> raw observed realized variance
        -> realized volatility

Out of scope:
    threshold-learning history
    rolling empirical median
    HIGH/LOW state assignment
    episodes
    Gate 2
    K7
    conditioned outcomes
"""

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
    GridReturnResult,
)


RVOL_VALID = "VALID"
INSUFFICIENT_TRAILING_RETURN_COVERAGE = (
    "INSUFFICIENT_TRAILING_RETURN_COVERAGE"
)
EXCESSIVE_CONTIGUOUS_RETURN_GAP = (
    "EXCESSIVE_CONTIGUOUS_RETURN_GAP"
)


@dataclass(frozen=True)
class RvolWindowSpec:
    name: str
    window_ms: int
    expected_returns: int
    min_valid_returns: int
    max_contiguous_invalid_returns: int


WINDOW_SPECS: Dict[str, RvolWindowSpec] = {
    "1h": RvolWindowSpec(
        name="1h",
        window_ms=60 * 60 * 1000,
        expected_returns=12,
        min_valid_returns=9,
        max_contiguous_invalid_returns=3,
    ),
    "4h": RvolWindowSpec(
        name="4h",
        window_ms=4 * 60 * 60 * 1000,
        expected_returns=48,
        min_valid_returns=36,
        max_contiguous_invalid_returns=12,
    ),
    "24h": RvolWindowSpec(
        name="24h",
        window_ms=24 * 60 * 60 * 1000,
        expected_returns=288,
        min_valid_returns=216,
        max_contiguous_invalid_returns=72,
    ),
}


@dataclass(frozen=True)
class RvolResult:
    """
    Immutable trailing-RVOL evidence for one frozen W.

    `history_complete` means the result object contains all nominal return
    slots required for the W-length trailing window ending at that endpoint.

    `valid_return_count` and `max_contiguous_invalid_returns` are diagnostics
    over those nominal W/5m return slots.

    RV/RVOL are populated only when the frozen local coverage conditions pass.
    """

    window_name: str
    window_ms: int
    expected_returns: int
    min_valid_returns: int
    max_allowed_contiguous_invalid_returns: int

    endpoint_ms: np.ndarray

    history_complete: np.ndarray
    valid_return_count: np.ndarray
    invalid_return_count: np.ndarray
    coverage_fraction: np.ndarray
    max_contiguous_invalid_returns: np.ndarray

    aggregate_coverage_pass: np.ndarray
    contiguous_gap_pass: np.ndarray

    realized_variance: np.ndarray
    rvol: np.ndarray
    rvol_valid: np.ndarray
    rvol_reasons: Tuple[Tuple[str, ...], ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _max_false_run(values: np.ndarray) -> int:
    """
    Maximum contiguous run of False values in a 1-D boolean vector.
    """
    max_run = 0
    current_run = 0

    for value in values:
        if bool(value):
            current_run = 0
        else:
            current_run += 1
            if current_run > max_run:
                max_run = current_run

    return max_run


def _validate_grid_result(grid: GridReturnResult) -> None:
    n = grid.endpoint_ms.size

    arrays = (
        grid.price,
        grid.source_trade_time,
        grid.source_trade_id,
        grid.trade_age_ms,
        grid.endpoint_valid,
        grid.log_return,
        grid.return_valid,
    )

    if any(array.size != n for array in arrays):
        raise ValueError(
            "GridReturnResult arrays do not share one common length"
        )

    if len(grid.endpoint_reason) != n:
        raise ValueError(
            "GridReturnResult endpoint_reason length mismatch"
        )

    if len(grid.return_reason) != n:
        raise ValueError(
            "GridReturnResult return_reason length mismatch"
        )

    if grid.grid_interval_ms != GRID_INTERVAL_MS:
        raise ValueError(
            "RVOL requires the frozen Experiment-v1 5-minute grid"
        )

    if n > 1:
        deltas = np.diff(grid.endpoint_ms)
        if not np.all(deltas == GRID_INTERVAL_MS):
            raise ValueError(
                "GridReturnResult endpoints are not consecutive 5-minute "
                "grid points"
            )

    valid_returns = grid.log_return[grid.return_valid]

    if valid_returns.size and not np.all(np.isfinite(valid_returns)):
        raise ValueError(
            "GridReturnResult marks non-finite return(s) as valid"
        )


def compute_rvol(
    grid: GridReturnResult,
    window_name: str,
) -> RvolResult:
    """
    Compute frozen Experiment-v1 trailing realized volatility.

    For endpoint G_i and W containing N=W/5m expected return slots:

        window = [r_{i-N+1}, ..., r_i]

    but only when i >= N.

    The i >= N requirement is deliberate: N returns require N+1 grid
    endpoints. This prevents partial warm-up and preserves the frozen
    full-causal-history requirement.

    Local eligibility requires BOTH:

        valid return count >= 75% of N

    and:

        maximum contiguous invalid-return run <= 25% of N

    Exact frozen counts:
        1h  -> N=12,  valid>=9,   max invalid run<=3
        4h  -> N=48,  valid>=36,  max invalid run<=12
        24h -> N=288, valid>=216, max invalid run<=72

    Missing returns are not interpolated, bridged, zero-filled, or
    exposure-scaled.

    For an eligible window:

        RV_W(G)    = sum(r_g^2) over observed valid returns in W
        RVOL_W(G) = sqrt(RV_W(G))
    """
    _validate_grid_result(grid)

    try:
        spec = WINDOW_SPECS[window_name]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported frozen RVOL window {window_name!r}; "
            f"expected one of {tuple(WINDOW_SPECS)}"
        ) from exc

    n_grid = grid.endpoint_ms.size
    n_expected = spec.expected_returns

    history_complete = np.zeros(n_grid, dtype=bool)
    valid_return_count = np.zeros(n_grid, dtype=np.int64)
    invalid_return_count = np.zeros(n_grid, dtype=np.int64)
    coverage_fraction = np.full(n_grid, np.nan, dtype=np.float64)
    max_invalid_run = np.full(n_grid, -1, dtype=np.int64)

    aggregate_coverage_pass = np.zeros(n_grid, dtype=bool)
    contiguous_gap_pass = np.zeros(n_grid, dtype=bool)

    realized_variance = np.full(n_grid, np.nan, dtype=np.float64)
    rvol = np.full(n_grid, np.nan, dtype=np.float64)
    rvol_valid = np.zeros(n_grid, dtype=bool)

    # No D4/D5 failure code is assigned until a complete W-length
    # causal return window exists. history_complete=False is authoritative
    # during warm-up/source-history immaturity.
    reasons = [
        tuple()
        for _ in range(n_grid)
    ]

    for i in range(n_grid):
        # N returns require N+1 endpoints. Because return[0] has no
        # preceding endpoint inside the object, the earliest fully
        # constructible W-window ends at index N.
        if i < n_expected:
            continue

        history_complete[i] = True

        start = i - n_expected + 1
        stop = i + 1

        window_valid = grid.return_valid[start:stop]

        if window_valid.size != n_expected:
            raise RuntimeError(
                "Internal RVOL window-length invariant violated"
            )

        n_valid = int(np.count_nonzero(window_valid))
        n_invalid = n_expected - n_valid
        longest_invalid = _max_false_run(window_valid)

        valid_return_count[i] = n_valid
        invalid_return_count[i] = n_invalid
        coverage_fraction[i] = n_valid / n_expected
        max_invalid_run[i] = longest_invalid

        coverage_ok = n_valid >= spec.min_valid_returns
        gap_ok = (
            longest_invalid
            <= spec.max_contiguous_invalid_returns
        )

        aggregate_coverage_pass[i] = coverage_ok
        contiguous_gap_pass[i] = gap_ok

        triggered_reasons = []

        if not coverage_ok:
            triggered_reasons.append(
                INSUFFICIENT_TRAILING_RETURN_COVERAGE
            )

        if not gap_ok:
            triggered_reasons.append(
                EXCESSIVE_CONTIGUOUS_RETURN_GAP
            )

        if triggered_reasons:
            # Frozen D4-D5 requires both codes to be retained when both
            # conditions trigger. Do not impose artificial precedence.
            reasons[i] = tuple(triggered_reasons)
            continue

        window_returns = grid.log_return[start:stop]
        observed_returns = window_returns[window_valid]

        if observed_returns.size != n_valid:
            raise RuntimeError(
                "RVOL valid-return count disagrees with extracted returns"
            )

        if not np.all(np.isfinite(observed_returns)):
            raise RuntimeError(
                "RVOL encountered non-finite return marked valid"
            )

        rv = float(np.sum(np.square(observed_returns), dtype=np.float64))

        if not np.isfinite(rv) or rv < 0.0:
            raise RuntimeError(
                "RVOL produced invalid realized variance"
            )

        value = float(np.sqrt(rv))

        if not np.isfinite(value):
            raise RuntimeError(
                "RVOL produced non-finite realized volatility"
            )

        realized_variance[i] = rv
        rvol[i] = value
        rvol_valid[i] = True
        reasons[i] = (RVOL_VALID,)

    return RvolResult(
        window_name=spec.name,
        window_ms=spec.window_ms,
        expected_returns=spec.expected_returns,
        min_valid_returns=spec.min_valid_returns,
        max_allowed_contiguous_invalid_returns=(
            spec.max_contiguous_invalid_returns
        ),
        endpoint_ms=_freeze_array(grid.endpoint_ms.copy()),
        history_complete=_freeze_array(history_complete),
        valid_return_count=_freeze_array(valid_return_count),
        invalid_return_count=_freeze_array(invalid_return_count),
        coverage_fraction=_freeze_array(coverage_fraction),
        max_contiguous_invalid_returns=_freeze_array(max_invalid_run),
        aggregate_coverage_pass=_freeze_array(
            aggregate_coverage_pass
        ),
        contiguous_gap_pass=_freeze_array(contiguous_gap_pass),
        realized_variance=_freeze_array(realized_variance),
        rvol=_freeze_array(rvol),
        rvol_valid=_freeze_array(rvol_valid),
        rvol_reasons=tuple(reasons),
    )
