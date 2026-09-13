"""
LRS-4 Experiment v1 — causal source-history authorization.

This module implements structural source-history mechanics only.

Current scope:
- frozen 6W raw-history requirement
- ceiling of instrument-specific S0,s to the 5-minute grid
- endpoint-level leading-boundary maturity authorization

Later scope:
- confirmed acquisition-break intervals
- break recovery
- instrument-day/path-conditioned aggregation

Out of scope:
- discovery or inference of S0,s from operational evidence
- collector-log interpretation
- storage certification
- RVOL validity
- threshold validity
- fallback routing
- conditioned outcomes

S0,s must already have been established by qualifying K1.3-B
operational evidence before being supplied here.
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT = (
    "SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT"
)


@dataclass(frozen=True)
class SourceHistorySpec:
    window_name: str
    window_ms: int
    raw_history_ms: int


SOURCE_HISTORY_SPECS: Dict[str, SourceHistorySpec] = {
    "1h": SourceHistorySpec(
        window_name="1h",
        window_ms=1 * 60 * 60 * 1000,
        raw_history_ms=6 * 60 * 60 * 1000,
    ),
    "4h": SourceHistorySpec(
        window_name="4h",
        window_ms=4 * 60 * 60 * 1000,
        raw_history_ms=24 * 60 * 60 * 1000,
    ),
    "24h": SourceHistorySpec(
        window_name="24h",
        window_ms=24 * 60 * 60 * 1000,
        raw_history_ms=144 * 60 * 60 * 1000,
    ),
}


@dataclass(frozen=True)
class LeadingBoundaryAuthorizationResult:
    window_name: str
    source_start_ms: int
    source_start_grid_ceiling_ms: int
    raw_history_ms: int
    maturity_endpoint_ms: int
    endpoint_ms: np.ndarray
    authorized: np.ndarray
    reason: tuple[tuple[str, ...], ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def ceil_to_grid(timestamp_ms: int) -> int:
    """
    Return the first frozen 5-minute grid endpoint >= timestamp_ms.

    Exact-grid timestamps remain unchanged.
    """
    timestamp_ms = int(timestamp_ms)

    quotient, remainder = divmod(
        timestamp_ms,
        GRID_INTERVAL_MS,
    )

    if remainder == 0:
        return timestamp_ms

    return (quotient + 1) * GRID_INTERVAL_MS


def authorize_leading_source_history(
    endpoint_ms: np.ndarray,
    source_start_ms: int,
    window_name: str,
) -> LeadingBoundaryAuthorizationResult:
    """
    Apply the frozen leading-boundary source-history maturity rule.

        G_SH-mature = ceil(S0,s)_grid + 6W

    An endpoint is authorized iff:

        G >= G_SH-mature

    Equality therefore passes.

    This function does not establish whether source_start_ms is
    evidentially qualified. That is a separate K1.3-B evidence task.
    """
    if window_name not in SOURCE_HISTORY_SPECS:
        raise ValueError(
            f"Unsupported frozen source-history window {window_name!r}"
        )

    endpoints = np.asarray(endpoint_ms)

    if endpoints.ndim != 1:
        raise ValueError(
            "endpoint_ms must be one-dimensional"
        )

    if endpoints.dtype.kind not in ("i", "u"):
        raise TypeError(
            "endpoint_ms must have integer dtype"
        )

    endpoints = endpoints.astype(np.int64, copy=False)

    if endpoints.size > 1:
        deltas = np.diff(endpoints)

        if not np.all(deltas == GRID_INTERVAL_MS):
            raise ValueError(
                "endpoint_ms must be consecutive frozen 5-minute "
                "grid points"
            )

    if endpoints.size:
        if np.any(endpoints % GRID_INTERVAL_MS != 0):
            raise ValueError(
                "endpoint_ms contains non-grid-aligned timestamp(s)"
            )

    source_start_ms = int(source_start_ms)

    spec = SOURCE_HISTORY_SPECS[window_name]

    source_ceiling = ceil_to_grid(source_start_ms)

    maturity_endpoint = (
        source_ceiling
        + spec.raw_history_ms
    )

    authorized = endpoints >= maturity_endpoint

    reasons = tuple(
        ()
        if bool(is_authorized)
        else (SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,)
        for is_authorized in authorized
    )

    return LeadingBoundaryAuthorizationResult(
        window_name=window_name,
        source_start_ms=source_start_ms,
        source_start_grid_ceiling_ms=source_ceiling,
        raw_history_ms=spec.raw_history_ms,
        maturity_endpoint_ms=maturity_endpoint,
        endpoint_ms=_freeze_array(endpoints.copy()),
        authorized=_freeze_array(authorized.copy()),
        reason=reasons,
    )
