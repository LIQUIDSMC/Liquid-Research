"""
LRS-4 Experiment v1 — causal RVOL threshold learning.

Scope:
    RvolResult
        + explicit source-history authorization
        -> exact H_L(G) membership
        -> threshold-history availability diagnostics
        -> filtered causal trailing median theta_W(G)

Out of scope:
    operational source-evidence discovery
    S0,s derivation
    acquisition-break discovery
    HIGH/LOW state assignment
    fallback routing
    episodes
    Gate 2
    K7
    conditioned outcomes
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.rvol import (
    RvolResult,
)


@dataclass(frozen=True)
class ThresholdHistorySpec:
    window_name: str
    learning_history_ms: int
    nominal_members: int
    min_valid_members: int
    max_contiguous_invalid_members: int


THRESHOLD_HISTORY_SPECS: Dict[str, ThresholdHistorySpec] = {
    "1h": ThresholdHistorySpec(
        window_name="1h",
        learning_history_ms=5 * 60 * 60 * 1000,
        nominal_members=60,
        min_valid_members=45,
        max_contiguous_invalid_members=15,
    ),
    "4h": ThresholdHistorySpec(
        window_name="4h",
        learning_history_ms=20 * 60 * 60 * 1000,
        nominal_members=240,
        min_valid_members=180,
        max_contiguous_invalid_members=60,
    ),
    "24h": ThresholdHistorySpec(
        window_name="24h",
        learning_history_ms=120 * 60 * 60 * 1000,
        nominal_members=1440,
        min_valid_members=1080,
        max_contiguous_invalid_members=360,
    ),
}


@dataclass(frozen=True)
class ThresholdLearningResult:
    window_name: str
    learning_history_ms: int
    nominal_members: int
    min_valid_members: int
    max_allowed_contiguous_invalid_members: int

    endpoint_ms: np.ndarray

    source_history_authorized: np.ndarray
    learning_history_complete: np.ndarray

    valid_rvol_count: np.ndarray
    invalid_rvol_count: np.ndarray
    max_contiguous_invalid_rvol: np.ndarray

    aggregate_availability_pass: np.ndarray
    contiguous_concentration_pass: np.ndarray

    threshold: np.ndarray
    threshold_valid: np.ndarray


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _max_false_run(values: np.ndarray) -> int:
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


def _validate_inputs(
    rvol: RvolResult,
    source_history_authorized: np.ndarray,
) -> None:
    n = rvol.endpoint_ms.size

    if rvol.window_name not in THRESHOLD_HISTORY_SPECS:
        raise ValueError(
            f"Unsupported frozen RVOL window {rvol.window_name!r}"
        )

    arrays = (
        rvol.history_complete,
        rvol.valid_return_count,
        rvol.invalid_return_count,
        rvol.coverage_fraction,
        rvol.max_contiguous_invalid_returns,
        rvol.aggregate_coverage_pass,
        rvol.contiguous_gap_pass,
        rvol.realized_variance,
        rvol.rvol,
        rvol.rvol_valid,
    )

    if any(array.size != n for array in arrays):
        raise ValueError(
            "RvolResult arrays do not share one common length"
        )

    if source_history_authorized.ndim != 1:
        raise ValueError(
            "source_history_authorized must be one-dimensional"
        )

    if source_history_authorized.size != n:
        raise ValueError(
            "source_history_authorized length must match RvolResult"
        )

    if source_history_authorized.dtype != np.bool_:
        raise TypeError(
            "source_history_authorized must have boolean dtype"
        )

    if n > 1:
        deltas = np.diff(rvol.endpoint_ms)

        if not np.all(deltas == GRID_INTERVAL_MS):
            raise ValueError(
                "RvolResult endpoints are not consecutive frozen "
                "5-minute grid points"
            )

    valid_values = rvol.rvol[rvol.rvol_valid]

    if valid_values.size:
        if not np.all(np.isfinite(valid_values)):
            raise ValueError(
                "RvolResult marks non-finite RVOL value(s) as valid"
            )

        if np.any(valid_values < 0.0):
            raise ValueError(
                "RvolResult marks negative RVOL value(s) as valid"
            )


def learn_causal_threshold(
    rvol: RvolResult,
    source_history_authorized: np.ndarray,
) -> ThresholdLearningResult:
    """
    Learn the frozen causal trailing median threshold.

    Frozen learning-history domain:

        H_L(G) = {g : G-L <= g < G}

    Therefore current RVOL_W(G) is NEVER included in theta_W(G).

    Exact nominal member counts:
        1h  -> L=5h   -> 60 prior grid endpoints
        4h  -> L=20h  -> 240 prior grid endpoints
        24h -> L=120h -> 1440 prior grid endpoints

    Threshold-history validity:
        valid RVOL members >= 75% nominal
        max contiguous INVALID RVOL members <= 25% nominal

    Median semantics:
        use VALID RVOL members only
        no forward-fill
        no imputation
        no shrinking L
        no backward search beyond H_L(G)

    Source-history ordering:
        threshold validity is evaluated only where the explicit
        source_history_authorized mask is True.

    This function does NOT derive that mask. S0,s and confirmed source
    breaks belong to the separate source-history layer.
    """
    source_history_authorized = np.asarray(
        source_history_authorized
    )

    _validate_inputs(
        rvol,
        source_history_authorized,
    )

    spec = THRESHOLD_HISTORY_SPECS[rvol.window_name]

    n = rvol.endpoint_ms.size
    n_nominal = spec.nominal_members

    learning_history_complete = np.zeros(n, dtype=bool)

    valid_rvol_count = np.zeros(n, dtype=np.int64)
    invalid_rvol_count = np.zeros(n, dtype=np.int64)
    max_invalid_run = np.full(n, -1, dtype=np.int64)

    aggregate_pass = np.zeros(n, dtype=bool)
    contiguous_pass = np.zeros(n, dtype=bool)

    threshold = np.full(n, np.nan, dtype=np.float64)
    threshold_valid = np.zeros(n, dtype=bool)

    for i in range(n):
        # Exact H_L(G): the N immediately preceding grid endpoints.
        # Current endpoint i is excluded.
        if i < n_nominal:
            continue

        learning_history_complete[i] = True

        # Frozen maturity ordering:
        # do not evaluate threshold validity before source-history
        # authorization has been established.
        if not source_history_authorized[i]:
            continue

        start = i - n_nominal
        stop = i

        window_valid = rvol.rvol_valid[start:stop]

        if window_valid.size != n_nominal:
            raise RuntimeError(
                "Internal threshold-history cardinality invariant violated"
            )

        n_valid = int(np.count_nonzero(window_valid))
        n_invalid = n_nominal - n_valid
        longest_invalid = _max_false_run(window_valid)

        valid_rvol_count[i] = n_valid
        invalid_rvol_count[i] = n_invalid
        max_invalid_run[i] = longest_invalid

        availability_ok = n_valid >= spec.min_valid_members
        concentration_ok = (
            longest_invalid
            <= spec.max_contiguous_invalid_members
        )

        aggregate_pass[i] = availability_ok
        contiguous_pass[i] = concentration_ok

        if not availability_ok or not concentration_ok:
            continue

        values = rvol.rvol[start:stop][window_valid]

        if values.size != n_valid:
            raise RuntimeError(
                "Threshold valid-member count disagrees with extracted RVOL"
            )

        if not np.all(np.isfinite(values)):
            raise RuntimeError(
                "Threshold learner encountered non-finite valid RVOL"
            )

        # Frozen E4 threshold is the causal trailing sample median.
        # Do not import the separate bootstrap Type-7 convention here.
        theta = float(np.median(values))

        if not np.isfinite(theta):
            raise RuntimeError(
                "Threshold learner produced non-finite median"
            )

        threshold[i] = theta
        threshold_valid[i] = True

    return ThresholdLearningResult(
        window_name=spec.window_name,
        learning_history_ms=spec.learning_history_ms,
        nominal_members=spec.nominal_members,
        min_valid_members=spec.min_valid_members,
        max_allowed_contiguous_invalid_members=(
            spec.max_contiguous_invalid_members
        ),
        endpoint_ms=_freeze_array(rvol.endpoint_ms.copy()),
        source_history_authorized=_freeze_array(
            source_history_authorized.copy()
        ),
        learning_history_complete=_freeze_array(
            learning_history_complete
        ),
        valid_rvol_count=_freeze_array(valid_rvol_count),
        invalid_rvol_count=_freeze_array(invalid_rvol_count),
        max_contiguous_invalid_rvol=_freeze_array(max_invalid_run),
        aggregate_availability_pass=_freeze_array(aggregate_pass),
        contiguous_concentration_pass=_freeze_array(contiguous_pass),
        threshold=_freeze_array(threshold),
        threshold_valid=_freeze_array(threshold_valid),
    )
