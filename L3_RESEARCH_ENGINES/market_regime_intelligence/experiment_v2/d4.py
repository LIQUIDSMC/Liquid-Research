"""Experiment-v2 D4: structural episode topology and boundary censoring.

Pre-D2 evidence is an upstream-audited input. Structural validation here
does not independently establish the truth of its provenance.
"""

from dataclasses import dataclass

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WINDOWS,
    WindowD0Terminal,
    WindowIntegrityFailure,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d2 import (
    D2Result,
    D2Constructed,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d3 import (
    D3Result,
    D3Constructed,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


STATE_CHANGE = "STATE_CHANGE"
D3_INADMISSIBILITY = "D3_INADMISSIBILITY"
D2_BOUNDARY = "D2_BOUNDARY"


@dataclass(frozen=True)
class AuditedPrehistory:
    window: str
    endpoint_ms: np.ndarray
    state: tuple[str, ...]
    earliest_auditable_endpoint_ms: int
    provenance: str


@dataclass(frozen=True)
class D4Episode:
    episode_id: int
    state: str
    start_index: int
    end_index: int
    start_endpoint_ms: int
    end_endpoint_ms: int
    endpoint_count: int
    observed_duration_ms: int
    left_boundary_cause: str
    right_boundary_cause: str
    left_censored: bool
    right_censored: bool


@dataclass(frozen=True)
class D4Constructed:
    window: str
    endpoint_ms: np.ndarray
    episode_id_by_endpoint: np.ndarray
    episodes: tuple[D4Episode, ...]
    k_high: int
    k_low: int
    k_total: int
    t_classified_ms: int


@dataclass(frozen=True)
class D4Result:
    window: str
    d4: D4Constructed | None
    terminal: WindowD0Terminal | WindowIntegrityFailure | None


def _failure(window: str, invariant: str, detail: str) -> D4Result:
    return D4Result(
        window=window,
        d4=None,
        terminal=WindowIntegrityFailure(
            tag="INTEGRITY_FAILURE",
            window=window,
            invariant=invariant,
            provenance=detail,
        ),
    )


def _valid_grid(endpoints: np.ndarray) -> bool:
    if (
        not isinstance(endpoints, np.ndarray)
        or endpoints.ndim != 1
        or endpoints.dtype != np.dtype("int64")
        or endpoints.size == 0
    ):
        return False
    if np.any(endpoints % GRID_INTERVAL_MS != 0):
        return False
    return all(
        int(endpoints[i]) - int(endpoints[i - 1]) == GRID_INTERVAL_MS
        for i in range(1, endpoints.size)
    )


def _trace_left(
    prehistory: AuditedPrehistory,
    g_first: int,
    first_state: str,
) -> tuple[bool, bool]:
    """Return (evidence_valid, left_censored)."""
    if not isinstance(prehistory, AuditedPrehistory):
        return False, False
    if (
        prehistory.window not in WINDOWS
        or type(prehistory.provenance) is not str
        or not prehistory.provenance.strip()
        or not _valid_grid(prehistory.endpoint_ms)
        or not isinstance(prehistory.state, tuple)
        or len(prehistory.state) != prehistory.endpoint_ms.size
        or any(s not in ("HIGH", "LOW", "INVALID") for s in prehistory.state)
        or type(prehistory.earliest_auditable_endpoint_ms) is not int
    ):
        return False, False

    endpoints = prehistory.endpoint_ms
    if (
        int(endpoints[0]) != prehistory.earliest_auditable_endpoint_ms
        or int(endpoints[-1]) != g_first - GRID_INTERVAL_MS
    ):
        return False, False

    for state in reversed(prehistory.state):
        if state == "INVALID" or state != first_state:
            return True, False

    return True, True


def construct_d4(
    d2_result: D2Result,
    d3_result: D3Result,
    prehistory: AuditedPrehistory | None = None,
) -> D4Result:
    """Construct D4 solely from fixed D2, authoritative D3 and pre-D2 evidence."""
    if not isinstance(d2_result, D2Result):
        raise TypeError("d2_result must be D2Result")
    if not isinstance(d3_result, D3Result):
        raise TypeError("d3_result must be D3Result")

    window = d2_result.window
    if window not in WINDOWS:
        raise ValueError("Unsupported D2 window")
    if d3_result.window != window:
        return _failure(window, "I19", "D2/D3 window mismatch")

    if (
        isinstance(d3_result.terminal, WindowIntegrityFailure)
        and d3_result.terminal.window == window
        and d3_result.d3 is None
        and (
            (
                isinstance(d2_result.d2, D2Constructed)
                and d2_result.d2.window == window
                and d2_result.terminal is None
            )
            or (
                d2_result.d2 is None
                and d2_result.terminal == d3_result.terminal
            )
        )
    ):
        return D4Result(window=window, d4=None, terminal=d3_result.terminal)

    if d2_result.d2 is None or d3_result.d3 is None:
        if (
            d2_result.d2 is None
            and d3_result.d3 is None
            and isinstance(
                d2_result.terminal,
                (WindowD0Terminal, WindowIntegrityFailure),
            )
            and d3_result.terminal == d2_result.terminal
            and d2_result.terminal.window == window
        ):
            return D4Result(window=window, d4=None, terminal=d2_result.terminal)
        return _failure(window, "I19", "Missing or inconsistent upstream result")

    if d2_result.terminal is not None or d3_result.terminal is not None:
        return _failure(window, "I19", "Upstream success/terminal conflict")

    d2 = d2_result.d2
    d3 = d3_result.d3

    if (
        not isinstance(d2, D2Constructed)
        or not isinstance(d3, D3Constructed)
        or d2.window != window
        or d3.window != window
        or not _valid_grid(d2.endpoint_ms)
        or not np.array_equal(d2.endpoint_ms, d3.endpoint_ms)
        or int(d2.endpoint_ms[0]) != d2.g_first
        or int(d2.endpoint_ms[-1]) != d2.g_last
    ):
        return _failure(window, "I19", "Invalid fixed D2/D3 temporal domain")

    endpoints = d2.endpoint_ms
    n = endpoints.size

    if (
        not isinstance(d3.admissible, np.ndarray)
        or d3.admissible.shape != (n,)
        or d3.admissible.dtype != np.dtype("bool")
        or not isinstance(d3.state, tuple)
        or len(d3.state) != n
        or not isinstance(d3.reason, tuple)
        or len(d3.reason) != n
    ):
        return _failure(window, "I20", "Malformed D3 classification")

    for i in range(n):
        if d3.admissible[i]:
            if d3.state[i] not in ("HIGH", "LOW") or d3.reason[i] != ():
                return _failure(window, "I20", "Invalid admissible D3 cell")
        elif d3.state[i] != "INVALID" or not d3.reason[i]:
            return _failure(window, "I21", "Invalid inadmissible D3 cell")

    if d3.admissible[0]:
        if (
            not isinstance(prehistory, AuditedPrehistory)
            or prehistory.window != window
        ):
            return _failure(window, "I22", "Missing aligned audited prehistory")
        valid, left_censored = _trace_left(
            prehistory, int(endpoints[0]), d3.state[0]
        )
        if not valid:
            return _failure(window, "I22", "Malformed pre-D2 trace")
    else:
        left_censored = False
        if prehistory is not None:
            if (
                not isinstance(prehistory, AuditedPrehistory)
                or prehistory.window != window
            ):
                return _failure(window, "I22", "Mismatched prehistory")
            valid, _ = _trace_left(
                prehistory, int(endpoints[0]), "HIGH"
            )
            if not valid:
                return _failure(window, "I22", "Malformed pre-D2 trace")

    ids = np.full(n, -1, dtype=np.int64)
    episodes = []
    i = 0

    while i < n:
        if not d3.admissible[i]:
            i += 1
            continue

        start = i
        state = d3.state[i]
        while (
            i + 1 < n
            and d3.admissible[i + 1]
            and d3.state[i + 1] == state
        ):
            i += 1
        end = i

        if start == 0:
            left_cause = D2_BOUNDARY
            is_left_censored = left_censored
        elif not d3.admissible[start - 1]:
            left_cause = D3_INADMISSIBILITY
            is_left_censored = False
        else:
            left_cause = STATE_CHANGE
            is_left_censored = False

        if end == n - 1:
            right_cause = D2_BOUNDARY
            is_right_censored = True
        elif not d3.admissible[end + 1]:
            right_cause = D3_INADMISSIBILITY
            is_right_censored = False
        else:
            right_cause = STATE_CHANGE
            is_right_censored = False

        episode_id = len(episodes)
        ids[start:end + 1] = episode_id
        count = end - start + 1

        episodes.append(
            D4Episode(
                episode_id=episode_id,
                state=state,
                start_index=start,
                end_index=end,
                start_endpoint_ms=int(endpoints[start]),
                end_endpoint_ms=int(endpoints[end]),
                endpoint_count=count,
                observed_duration_ms=count * GRID_INTERVAL_MS,
                left_boundary_cause=left_cause,
                right_boundary_cause=right_cause,
                left_censored=is_left_censored,
                right_censored=is_right_censored,
            )
        )
        i += 1

    k_high = sum(e.state == "HIGH" for e in episodes)
    k_low = sum(e.state == "LOW" for e in episodes)

    endpoint_copy = endpoints.copy()
    endpoint_copy.setflags(write=False)
    ids.setflags(write=False)

    return D4Result(
        window=window,
        d4=D4Constructed(
            window=window,
            endpoint_ms=endpoint_copy,
            episode_id_by_endpoint=ids,
            episodes=tuple(episodes),
            k_high=k_high,
            k_low=k_low,
            k_total=len(episodes),
            t_classified_ms=int(np.count_nonzero(d3.admissible))
            * GRID_INTERVAL_MS,
        ),
        terminal=None,
    )
