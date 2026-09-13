"""
LRS-4 Experiment v1 — deterministic 5-minute grid price/return construction.

Scope:
    validated/sorted trade interval
        -> 5-minute grid endpoints
        -> causal previous-tick price P(G)
        -> endpoint validity/staleness
        -> consecutive log returns

Out of scope:
    RVOL
    trailing-window coverage
    threshold learning
    HIGH/LOW state assignment
    episodes
    Gate 2
    K7
    conditioned outcomes
"""

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.data.trade_loader import (
    TradeIntervalResult,
)


GRID_INTERVAL_MS = 5 * 60 * 1000

ENDPOINT_VALID = "VALID"
ENDPOINT_NO_ELIGIBLE_TRADE = "NO_ELIGIBLE_TRADE"
ENDPOINT_STALE_PRICE = "STALE_PRICE"

RETURN_VALID = "VALID"
RETURN_NO_PRECEDING_ENDPOINT = "NO_PRECEDING_GRID_ENDPOINT"
RETURN_CURRENT_ENDPOINT_INVALID = "CURRENT_ENDPOINT_INVALID"
RETURN_PREVIOUS_ENDPOINT_INVALID = "PREVIOUS_ENDPOINT_INVALID"


@dataclass(frozen=True)
class GridReturnResult:
    """
    Immutable evidence object for one explicit 5-minute grid interval.

    Invalid numeric values are represented by NaN. Invalidity is never
    inferred from NaN alone; explicit validity arrays and reason codes
    are authoritative.
    """

    grid_interval_ms: int
    endpoint_ms: np.ndarray

    price: np.ndarray
    source_trade_time: np.ndarray
    source_trade_id: np.ndarray
    trade_age_ms: np.ndarray

    endpoint_valid: np.ndarray
    endpoint_reason: Tuple[str, ...]

    log_return: np.ndarray
    return_valid: np.ndarray
    return_reason: Tuple[str, ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    """Make returned NumPy evidence arrays read-only."""
    array.setflags(write=False)
    return array


def _validate_grid_bounds(
    first_grid_ms: int,
    last_grid_ms: int,
) -> Tuple[int, int]:
    if not isinstance(first_grid_ms, (int, np.integer)):
        raise TypeError("first_grid_ms must be an integer timestamp")

    if not isinstance(last_grid_ms, (int, np.integer)):
        raise TypeError("last_grid_ms must be an integer timestamp")

    first_grid_ms = int(first_grid_ms)
    last_grid_ms = int(last_grid_ms)

    if last_grid_ms < first_grid_ms:
        raise ValueError(
            "last_grid_ms must be greater than or equal to first_grid_ms"
        )

    # Experiment-v1 uses a fixed UTC clock-time 5-minute grid.
    if first_grid_ms % GRID_INTERVAL_MS != 0:
        raise ValueError(
            "first_grid_ms is not aligned to the 5-minute UTC grid"
        )

    if last_grid_ms % GRID_INTERVAL_MS != 0:
        raise ValueError(
            "last_grid_ms is not aligned to the 5-minute UTC grid"
        )

    return first_grid_ms, last_grid_ms


def _validate_trade_input(trades: TradeIntervalResult) -> None:
    n = trades.row_count

    if (
        trades.trade_time.size != n
        or trades.trade_id.size != n
        or trades.price.size != n
    ):
        raise ValueError(
            "TradeIntervalResult array lengths disagree with row_count"
        )

    if n == 0:
        return

    if not np.all(np.isfinite(trades.price)):
        raise ValueError("Trade input contains non-finite price value(s)")

    if np.any(trades.price <= 0.0):
        raise ValueError("Trade input contains non-positive price value(s)")

    # The data layer promises deterministic lexicographic ordering.
    # Re-verify it here rather than silently correcting malformed input.
    expected_order = np.lexsort(
        (
            trades.trade_id,
            trades.trade_time,
        )
    )

    if not np.array_equal(
        expected_order,
        np.arange(n, dtype=expected_order.dtype),
    ):
        raise ValueError(
            "Trade input is not sorted by (trade_time, trade_id)"
        )


def build_grid_returns(
    trades: TradeIntervalResult,
    first_grid_ms: int,
    last_grid_ms: int,
) -> GridReturnResult:
    """
    Construct Experiment-v1 5-minute endpoint prices and returns.

    Endpoint semantics
    ------------------
    For each grid endpoint G:

        P(G) = price of the last trade with trade_time <= G

    If multiple trades share the same trade_time, deterministic input
    ordering by (trade_time, trade_id) means the highest trade_id at that
    timestamp is the final eligible trade.

    Endpoint validity
    -----------------
    A selected previous-tick price is valid iff:

        G - source_trade_time <= 5 minutes

    Exactly 5 minutes old is valid.

    No trade <= G:
        endpoint INVALID / NO_ELIGIBLE_TRADE

    Most recent trade older than 5 minutes:
        endpoint INVALID / STALE_PRICE

    Return semantics
    ----------------
    For endpoint index i > 0:

        r(G_i) = log(P(G_i) / P(G_{i-1}))

    only when BOTH immediately consecutive endpoints are valid.

    Invalid grid intervals are never bridged.

    The first returned endpoint has no preceding endpoint inside this
    result object, so its return is explicitly invalid. Callers needing
    an earlier return must request the preceding grid endpoint as part
    of the grid interval.
    """
    first_grid_ms, last_grid_ms = _validate_grid_bounds(
        first_grid_ms,
        last_grid_ms,
    )
    _validate_trade_input(trades)

    endpoint_ms = np.arange(
        first_grid_ms,
        last_grid_ms + GRID_INTERVAL_MS,
        GRID_INTERVAL_MS,
        dtype=np.int64,
    )

    n_grid = endpoint_ms.size

    price = np.full(n_grid, np.nan, dtype=np.float64)
    source_trade_time = np.full(n_grid, -1, dtype=np.int64)
    source_trade_id = np.full(n_grid, -1, dtype=np.int64)
    trade_age_ms = np.full(n_grid, np.nan, dtype=np.float64)

    endpoint_valid = np.zeros(n_grid, dtype=bool)
    endpoint_reason = [ENDPOINT_NO_ELIGIBLE_TRADE] * n_grid

    log_return = np.full(n_grid, np.nan, dtype=np.float64)
    return_valid = np.zeros(n_grid, dtype=bool)
    return_reason = [RETURN_NO_PRECEDING_ENDPOINT] * n_grid

    trade_time = trades.trade_time

    for i, grid_ms in enumerate(endpoint_ms):
        # right-side insertion yields the index AFTER all trades with
        # trade_time <= G. Subtract one for the last eligible trade.
        source_index = int(
            np.searchsorted(
                trade_time,
                grid_ms,
                side="right",
            )
        ) - 1

        if source_index < 0:
            endpoint_reason[i] = ENDPOINT_NO_ELIGIBLE_TRADE
            continue

        selected_trade_time = int(trades.trade_time[source_index])
        selected_trade_id = int(trades.trade_id[source_index])
        selected_price = float(trades.price[source_index])

        age_ms = int(grid_ms) - selected_trade_time

        if age_ms < 0:
            raise RuntimeError(
                "Internal causality violation: selected trade occurs "
                "after grid endpoint"
            )

        source_trade_time[i] = selected_trade_time
        source_trade_id[i] = selected_trade_id
        trade_age_ms[i] = float(age_ms)

        if age_ms > GRID_INTERVAL_MS:
            endpoint_reason[i] = ENDPOINT_STALE_PRICE
            continue

        price[i] = selected_price
        endpoint_valid[i] = True
        endpoint_reason[i] = ENDPOINT_VALID

    for i in range(1, n_grid):
        if not endpoint_valid[i]:
            return_reason[i] = RETURN_CURRENT_ENDPOINT_INVALID
            continue

        if not endpoint_valid[i - 1]:
            return_reason[i] = RETURN_PREVIOUS_ENDPOINT_INVALID
            continue

        value = np.log(price[i] / price[i - 1])

        if not np.isfinite(value):
            raise RuntimeError(
                "Finite positive endpoint prices produced non-finite "
                "log return"
            )

        log_return[i] = float(value)
        return_valid[i] = True
        return_reason[i] = RETURN_VALID

    return GridReturnResult(
        grid_interval_ms=GRID_INTERVAL_MS,
        endpoint_ms=_freeze_array(endpoint_ms),
        price=_freeze_array(price),
        source_trade_time=_freeze_array(source_trade_time),
        source_trade_id=_freeze_array(source_trade_id),
        trade_age_ms=_freeze_array(trade_age_ms),
        endpoint_valid=_freeze_array(endpoint_valid),
        endpoint_reason=tuple(endpoint_reason),
        log_return=_freeze_array(log_return),
        return_valid=_freeze_array(return_valid),
        return_reason=tuple(return_reason),
    )
