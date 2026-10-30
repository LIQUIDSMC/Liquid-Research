"""Experiment-v2 D3: authoritative endpoint environmental admissibility."""

from dataclasses import dataclass

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WindowD0Terminal,
    WindowIntegrityFailure,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d2 import (
    D2Result,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
    SourceHistoryAuthorizationResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.threshold_learning import (
    ThresholdLearningResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.regime_state import (
    RegimeStateResult,
)


@dataclass(frozen=True)
class D3Constructed:
    window: str
    endpoint_ms: np.ndarray
    admissible: np.ndarray
    state: tuple[str, ...]
    reason: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class D3Result:
    window: str
    d3: D3Constructed | None
    terminal: WindowD0Terminal | WindowIntegrityFailure | None


def _failure(window: str, invariant: str, detail: str) -> D3Result:
    return D3Result(
        window=window,
        d3=None,
        terminal=WindowIntegrityFailure(
            tag="INTEGRITY_FAILURE",
            window=window,
            invariant=invariant,
            provenance=detail,
        ),
    )


def construct_d3(
    d2_result: D2Result,
    source_history: SourceHistoryAuthorizationResult | None,
    regime: RegimeStateResult | None,
    threshold: ThresholdLearningResult | None,
) -> D3Result:
    """Consume one authoritative upstream artifact of each required type."""
    if not isinstance(d2_result, D2Result):
        raise TypeError("d2_result must be D2Result")

    window = d2_result.window

    if d2_result.d2 is None:
        if (
            isinstance(d2_result.terminal, (WindowD0Terminal, WindowIntegrityFailure))
            and d2_result.terminal.window == window
        ):
            return D3Result(window=window, d3=None, terminal=d2_result.terminal)
        return _failure(window, "I14", "Missing successful D2 prerequisite")

    if d2_result.terminal is not None:
        return _failure(window, "I14", "D2 and terminal both present")

    if not isinstance(source_history, SourceHistoryAuthorizationResult):
        return _failure(window, "I15", "Missing authoritative source history")

    if not isinstance(regime, RegimeStateResult):
        return _failure(window, "I15", "Missing authoritative regime state")

    if not isinstance(threshold, ThresholdLearningResult):
        return _failure(window, "I15", "Missing authoritative threshold evidence")

    endpoints = d2_result.d2.endpoint_ms
    if not isinstance(endpoints, np.ndarray) or endpoints.ndim != 1:
        return _failure(window, "I14", "Malformed D2 endpoint domain")
    n = len(endpoints)

    if (
        d2_result.d2.window != window
        or source_history.window_name != window
        or regime.window_name != window
        or threshold.window_name != window
    ):
        return _failure(window, "I15", "Window identity mismatch")

    if (
        not isinstance(endpoints, np.ndarray)
        or endpoints.ndim != 1
        or endpoints.dtype != np.dtype("int64")
        or n == 0
    ):
        return _failure(window, "I14", "Malformed D2 endpoint domain")

    if (
        not isinstance(source_history.endpoint_ms, np.ndarray)
        or not isinstance(regime.endpoint_ms, np.ndarray)
        or not isinstance(threshold.endpoint_ms, np.ndarray)
        or not np.array_equal(endpoints, source_history.endpoint_ms)
        or not np.array_equal(endpoints, regime.endpoint_ms)
        or not np.array_equal(endpoints, threshold.endpoint_ms)
    ):
        return _failure(window, "I14", "Incomplete or mismatched endpoint domain")

    if (
        not isinstance(source_history.authorized, np.ndarray)
        or source_history.authorized.shape != (n,)
        or source_history.authorized.dtype != np.dtype("bool")
        or not isinstance(regime.state_valid, np.ndarray)
        or regime.state_valid.shape != (n,)
        or regime.state_valid.dtype != np.dtype("bool")
        or len(source_history.reason) != n
        or len(regime.state) != n
    ):
        return _failure(window, "I14", "Malformed endpoint classification arrays")

    # Validate inherited authority before assigning any D3 classification.
    boolean_arrays = (
        regime.rvol_valid,
        regime.threshold_valid,
        regime.state_valid,
        threshold.source_history_authorized,
        threshold.threshold_valid,
    )
    numeric_arrays = (regime.rvol, regime.threshold, threshold.threshold)
    if any(
        not isinstance(a, np.ndarray)
        or a.shape != (n,)
        or a.dtype != np.dtype("bool")
        for a in boolean_arrays
    ):
        return _failure(window, "I15", "Malformed inherited validity masks")

    if any(
        not isinstance(a, np.ndarray)
        or a.shape != (n,)
        or not np.issubdtype(a.dtype, np.number)
        for a in numeric_arrays
    ):
        return _failure(window, "I15", "Malformed inherited numeric arrays")

    if not np.array_equal(
        threshold.source_history_authorized, source_history.authorized
    ):
        return _failure(window, "I15", "Threshold source-history mask mismatch")

    if not np.array_equal(threshold.threshold_valid, regime.threshold_valid):
        return _failure(window, "I15", "Threshold validity mismatch")

    if not np.array_equal(
        threshold.threshold, regime.threshold, equal_nan=True
    ):
        return _failure(window, "I15", "Threshold values mismatch")

    if np.any(threshold.threshold_valid & ~source_history.authorized):
        return _failure(window, "I15", "Unauthorized threshold marked valid")

    expected_valid = regime.rvol_valid & regime.threshold_valid
    if not np.array_equal(regime.state_valid, expected_valid):
        return _failure(window, "I15", "Regime validity conjunction mismatch")

    for i in range(n):
        if not regime.state_valid[i]:
            if regime.state[i] != "INVALID":
                return _failure(window, "I15", "Invalid regime carries state")
            continue
        rv = float(regime.rvol[i])
        theta = float(regime.threshold[i])
        if not (
            np.isfinite(rv) and rv >= 0
            and np.isfinite(theta) and theta >= 0
        ):
            return _failure(window, "I15", "Non-finite or negative valid input")
        expected_state = "HIGH" if rv > theta else "LOW"
        if regime.state[i] != expected_state:
            return _failure(window, "I15", "Regime classification mismatch")

    admissible = np.zeros(n, dtype=np.bool_)
    states = []
    reasons = []

    for i in range(n):
        if not source_history.authorized[i]:
            states.append("INVALID")
            reasons.append(
                ("SOURCE_HISTORY_UNAUTHORIZED",) + tuple(source_history.reason[i])
            )
            continue

        if not regime.state_valid[i]:
            states.append("INVALID")
            causes = []
            if not regime.rvol_valid[i]:
                causes.append("RVOL_INVALID")
            if not regime.threshold_valid[i]:
                causes.append("THRESHOLD_INVALID")
            reasons.append(tuple(causes) or ("REGIME_STATE_INVALID",))
            continue

        if regime.state[i] not in ("HIGH", "LOW"):
            return _failure(window, "I15", "Valid regime has invalid state")

        admissible[i] = True
        states.append(regime.state[i])
        reasons.append(())

    endpoint_copy = np.array(endpoints, copy=True)
    endpoint_copy.setflags(write=False)
    admissible.setflags(write=False)

    return D3Result(
        window=window,
        d3=D3Constructed(
            window=window,
            endpoint_ms=endpoint_copy,
            admissible=admissible,
            state=tuple(states),
            reason=tuple(reasons),
        ),
        terminal=None,
    )
