"""
LRS-4 Experiment v1 — endpoint regime-state classification.

Scope:
current RVOL_W(G)
+ causal threshold theta_W(G)
-> HIGH / LOW / INVALID endpoint state

Frozen Experiment-v1 rule:
    RVOL_W(G) > theta_W(G)  -> HIGH
    RVOL_W(G) <= theta_W(G) -> LOW

State is INVALID unless both:
- current RVOL_W(G) is valid
- theta_W(G) is valid

Out of scope:
source-history derivation
observation-at-T assignment
episode construction
fallback routing
Gate 2
K7
conditioned outcomes
"""

from dataclasses import dataclass

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.rvol import (
    RvolResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.threshold_learning import (
    ThresholdLearningResult,
)


REGIME_HIGH = "HIGH"
REGIME_LOW = "LOW"
REGIME_INVALID = "INVALID"


@dataclass(frozen=True)
class RegimeStateResult:
    window_name: str
    endpoint_ms: np.ndarray
    rvol: np.ndarray
    threshold: np.ndarray
    rvol_valid: np.ndarray
    threshold_valid: np.ndarray
    state_valid: np.ndarray
    state: tuple[str, ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _validate_inputs(
    rvol: RvolResult,
    threshold: ThresholdLearningResult,
) -> None:
    n = rvol.endpoint_ms.size

    if threshold.endpoint_ms.size != n:
        raise ValueError(
            "RvolResult and ThresholdLearningResult lengths differ"
        )

    if rvol.window_name != threshold.window_name:
        raise ValueError(
            "RvolResult and ThresholdLearningResult window names differ"
        )

    if not np.array_equal(
        rvol.endpoint_ms,
        threshold.endpoint_ms,
    ):
        raise ValueError(
            "RvolResult and ThresholdLearningResult endpoints differ"
        )

    if rvol.rvol.size != n or rvol.rvol_valid.size != n:
        raise ValueError(
            "RvolResult arrays do not share one common length"
        )

    if threshold.threshold.size != n:
        raise ValueError(
            "ThresholdLearningResult threshold length mismatch"
        )

    if threshold.threshold_valid.size != n:
        raise ValueError(
            "ThresholdLearningResult threshold_valid length mismatch"
        )

    valid_rvol = rvol.rvol[rvol.rvol_valid]

    if valid_rvol.size:
        if not np.all(np.isfinite(valid_rvol)):
            raise ValueError(
                "RvolResult marks non-finite RVOL value(s) as valid"
            )

        if np.any(valid_rvol < 0.0):
            raise ValueError(
                "RvolResult marks negative RVOL value(s) as valid"
            )

    valid_threshold = threshold.threshold[
        threshold.threshold_valid
    ]

    if valid_threshold.size:
        if not np.all(np.isfinite(valid_threshold)):
            raise ValueError(
                "ThresholdLearningResult marks non-finite "
                "threshold value(s) as valid"
            )

        if np.any(valid_threshold < 0.0):
            raise ValueError(
                "ThresholdLearningResult marks negative "
                "threshold value(s) as valid"
            )


def classify_regime_state(
    rvol: RvolResult,
    threshold: ThresholdLearningResult,
) -> RegimeStateResult:
    """
    Apply the frozen Experiment-v1 HIGH/LOW endpoint classifier.

    HIGH:
        valid RVOL and valid threshold and RVOL > threshold

    LOW:
        valid RVOL and valid threshold and RVOL <= threshold

    INVALID:
        current RVOL invalid OR threshold invalid

    Equality belongs to LOW exactly.
    """
    _validate_inputs(rvol, threshold)

    n = rvol.endpoint_ms.size

    state_valid = (
        rvol.rvol_valid
        & threshold.threshold_valid
    )

    states = []

    for i in range(n):
        if not state_valid[i]:
            states.append(REGIME_INVALID)
            continue

        rv = float(rvol.rvol[i])
        theta = float(threshold.threshold[i])

        if rv > theta:
            states.append(REGIME_HIGH)
        else:
            states.append(REGIME_LOW)

    return RegimeStateResult(
        window_name=rvol.window_name,
        endpoint_ms=_freeze_array(rvol.endpoint_ms.copy()),
        rvol=_freeze_array(rvol.rvol.copy()),
        threshold=_freeze_array(threshold.threshold.copy()),
        rvol_valid=_freeze_array(rvol.rvol_valid.copy()),
        threshold_valid=_freeze_array(
            threshold.threshold_valid.copy()
        ),
        state_valid=_freeze_array(state_valid.copy()),
        state=tuple(states),
    )
