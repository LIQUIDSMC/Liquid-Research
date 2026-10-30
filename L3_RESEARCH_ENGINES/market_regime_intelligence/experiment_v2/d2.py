"""Experiment-v2 G01: authoritative D2 temporal-domain construction.

D2 boundaries derive exclusively from successful D1 population extrema.
No regime, source-history, Gate-2, or outcome evaluation occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WINDOWS,
    WindowD0Terminal,
    WindowIntegrityFailure,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d1_d0 import (
    D1Constructed,
    D1D0Result,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


@dataclass(frozen=True)
class D2Constructed:
    window: str
    g_first: int
    g_last: int
    endpoint_ms: np.ndarray


@dataclass(frozen=True)
class D2Result:
    window: str
    d2: D2Constructed | None
    terminal: WindowD0Terminal | WindowIntegrityFailure | None


def _failure(window: str, detail: str) -> D2Result:
    return D2Result(
        window=window,
        d2=None,
        terminal=WindowIntegrityFailure(
            tag="INTEGRITY_FAILURE",
            window=window,
            invariant="D2_BOUNDARY",
            provenance=detail,
        ),
    )


def construct_d2(result: D1D0Result) -> D2Result:
    """Construct the immutable inclusive five-minute D2 endpoint domain."""
    if not isinstance(result, D1D0Result):
        raise TypeError("result must be D1D0Result")

    window = result.window
    if type(window) is not str or window not in WINDOWS:
        raise ValueError("Unsupported D1 window")

    if result.d1 is None:
        if isinstance(result.terminal, (WindowD0Terminal, WindowIntegrityFailure)):
            if result.terminal.window != window:
                return _failure(window, "Mismatched upstream terminal window")
            return D2Result(window=window, d2=None, terminal=result.terminal)
        return _failure(window, "Missing successful D1 prerequisite")

    if result.terminal is not None:
        return _failure(window, "D1 and terminal are simultaneously present")

    d1 = result.d1
    if not isinstance(d1, D1Constructed) or d1.window != window:
        return _failure(window, "Missing or mismatched D1 population")

    times = d1.observation_time_ms
    ids = d1.observation_trade_id
    days = d1.observation_day

    if (
        not isinstance(times, np.ndarray)
        or times.ndim != 1
        or times.dtype != np.dtype("int64")
        or times.size == 0
        or not isinstance(ids, np.ndarray)
        or ids.ndim != 1
        or ids.dtype != np.dtype("int64")
        or ids.size != times.size
        or not isinstance(days, tuple)
        or len(days) != times.size
    ):
        return _failure(window, "Malformed or empty D1 observation arrays")

    if not all(type(day) is str and day for day in days):
        return _failure(window, "Malformed D1 research-day identities")

    identities = set(zip(times.tolist(), ids.tolist()))
    if len(identities) != times.size:
        return _failure(window, "Duplicate D1 observation identity")

    interval = GRID_INTERVAL_MS
    limits = np.iinfo(np.int64)

    t_first = int(np.min(times))
    t_last = int(np.max(times))

    if t_first == limits.min:
        return _failure(window, "Unrepresentable strict-C10 predecessor")

    g_first = ((t_first - 1) // interval) * interval
    g_last = ((t_last - 1) // interval) * interval

    if (
        g_first < limits.min
        or g_last > limits.max
        or g_last < g_first
        or g_first % interval
        or g_last % interval
    ):
        return _failure(window, "Invalid D2 grid boundaries")

    if g_last > limits.max - interval:
        return _failure(window, "Unrepresentable D2 upper temporal bound")

    count = ((g_last - g_first) // interval) + 1

    if count <= 0 or count > np.iinfo(np.intp).max:
        return _failure(window, "Unrepresentable D2 endpoint count")

    # Engineering allocation guard; not a methodological D2 duration limit.
    max_endpoint_bytes = 64 * 1024 * 1024
    if count > max_endpoint_bytes // np.dtype("int64").itemsize:
        return _failure(window, "D2 endpoint allocation budget exceeded")

    try:
        endpoints = np.arange(
            g_first,
            g_last + interval,
            interval,
            dtype=np.int64,
        )
    except (ValueError, OverflowError, MemoryError):
        return _failure(window, "D2 endpoint allocation failed")

    if (
        endpoints.size != count
        or int(endpoints[0]) != g_first
        or int(endpoints[-1]) != g_last
        or (
            endpoints.size > 1
            and not np.all(np.diff(endpoints) == interval)
        )
    ):
        return _failure(window, "D2 endpoint continuity failure")

    endpoints.setflags(write=False)

    return D2Result(
        window=window,
        d2=D2Constructed(
            window=window,
            g_first=g_first,
            g_last=g_last,
            endpoint_ms=endpoints,
        ),
        terminal=None,
    )
