"""
LRS-4 Experiment v1 — observation-to-regime-endpoint assignment.

Frozen causal rule:

For an inherited LRS-3 observation at trade time T, consume the latest
completed 5-minute regime endpoint G satisfying strictly:

    G < T

Exact-grid observations therefore consume the immediately preceding
endpoint, never the endpoint at the same timestamp.

If the selected endpoint state is VALID, the observation inherits the
endpoint's HIGH/LOW regime state.

If the selected endpoint state is INVALID, the observation is
LRS4_REGIME_INELIGIBLE.

The algorithm must never search backward past an INVALID endpoint to
recover an older valid state. A later valid endpoint restores eligibility
prospectively.

This module performs assignment only.

Out of scope:
- LRS-3 observation eligibility
- source-history population bookkeeping
- Instrument Path fallback logic
- Gate 2
- K7
- conditioned outcomes
"""

from dataclasses import dataclass

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.regime_state import (
    REGIME_HIGH,
    REGIME_INVALID,
    REGIME_LOW,
    RegimeStateResult,
)


LRS4_ELIGIBLE = "LRS4_ELIGIBLE"
LRS4_REGIME_INELIGIBLE = "LRS4_REGIME_INELIGIBLE"

NO_PRECEDING_COMPLETED_ENDPOINT = "NO_PRECEDING_COMPLETED_ENDPOINT"
ASSIGNED_ENDPOINT_INVALID = "ASSIGNED_ENDPOINT_INVALID"


@dataclass(frozen=True)
class ObservationRegimeAssignmentResult:
    window_name: str

    observation_time_ms: np.ndarray

    assigned_endpoint_index: np.ndarray
    assigned_endpoint_ms: np.ndarray

    assigned_state: tuple[str, ...]

    eligible: np.ndarray
    population_status: tuple[str, ...]
    reason: tuple[tuple[str, ...], ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _validate_regime_state_result(
    regime: RegimeStateResult,
) -> None:
    if not isinstance(regime, RegimeStateResult):
        raise TypeError(
            "regime must be a RegimeStateResult"
        )

    endpoints = regime.endpoint_ms

    if endpoints.ndim != 1:
        raise ValueError(
            "regime endpoint_ms must be one-dimensional"
        )

    if endpoints.dtype.kind not in ("i", "u"):
        raise TypeError(
            "regime endpoint_ms must have integer dtype"
        )

    n = len(endpoints)

    if len(regime.state) != n:
        raise ValueError(
            "regime state length must match endpoint count"
        )

    if len(regime.state_valid) != n:
        raise ValueError(
            "regime state_valid length must match endpoint count"
        )

    if n:
        if np.any(endpoints % GRID_INTERVAL_MS != 0):
            raise ValueError(
                "regime endpoint_ms contains non-grid-aligned timestamp(s)"
            )

    if n > 1:
        deltas = np.diff(endpoints)

        if not np.all(deltas == GRID_INTERVAL_MS):
            raise ValueError(
                "regime endpoint_ms must be consecutive frozen "
                "5-minute grid points"
            )

    allowed_states = {
        REGIME_HIGH,
        REGIME_LOW,
        REGIME_INVALID,
    }

    for index, state in enumerate(regime.state):
        if state not in allowed_states:
            raise ValueError(
                f"Unknown regime state {state!r} at endpoint index {index}"
            )

        state_valid = bool(regime.state_valid[index])

        if state_valid and state == REGIME_INVALID:
            raise ValueError(
                "state_valid=True cannot coexist with INVALID state"
            )

        if not state_valid and state != REGIME_INVALID:
            raise ValueError(
                "state_valid=False requires INVALID state"
            )


def assign_observations_to_regime(
    observation_time_ms: np.ndarray,
    regime: RegimeStateResult,
) -> ObservationRegimeAssignmentResult:
    """
    Assign inherited LRS-3 observations to the latest completed regime
    endpoint satisfying strictly G < T.

    Implementation detail:

        np.searchsorted(endpoint_ms, T, side="left") - 1

    side="left" is required because an exact-grid T must NOT consume the
    endpoint at T itself.

    No backward recovery is permitted. If the immediately selected
    endpoint is INVALID, the observation remains regime-ineligible.
    """
    _validate_regime_state_result(regime)

    observations = np.asarray(observation_time_ms)

    if observations.ndim != 1:
        raise ValueError(
            "observation_time_ms must be one-dimensional"
        )

    if observations.dtype.kind not in ("i", "u"):
        raise TypeError(
            "observation_time_ms must have integer dtype"
        )

    observations = observations.astype(
        np.int64,
        copy=False,
    )

    if observations.size > 1:
        if np.any(np.diff(observations) < 0):
            raise ValueError(
                "observation_time_ms must be nondecreasing"
            )

    endpoints = regime.endpoint_ms.astype(
        np.int64,
        copy=False,
    )

    n_obs = len(observations)

    assigned_index = np.full(
        n_obs,
        -1,
        dtype=np.int64,
    )

    assigned_endpoint = np.full(
        n_obs,
        -1,
        dtype=np.int64,
    )

    eligible = np.zeros(
        n_obs,
        dtype=bool,
    )

    assigned_state = []
    population_status = []
    reasons = []

    if len(endpoints) == 0:
        for _ in range(n_obs):
            assigned_state.append(REGIME_INVALID)
            population_status.append(
                LRS4_REGIME_INELIGIBLE
            )
            reasons.append(
                (NO_PRECEDING_COMPLETED_ENDPOINT,)
            )

        return ObservationRegimeAssignmentResult(
            window_name=regime.window_name,
            observation_time_ms=_freeze_array(
                observations.copy()
            ),
            assigned_endpoint_index=_freeze_array(
                assigned_index
            ),
            assigned_endpoint_ms=_freeze_array(
                assigned_endpoint
            ),
            assigned_state=tuple(assigned_state),
            eligible=_freeze_array(eligible),
            population_status=tuple(population_status),
            reason=tuple(reasons),
        )

    candidate_indices = (
        np.searchsorted(
            endpoints,
            observations,
            side="left",
        )
        - 1
    )

    for obs_index, endpoint_index in enumerate(
        candidate_indices
    ):
        endpoint_index = int(endpoint_index)

        if endpoint_index < 0:
            assigned_state.append(REGIME_INVALID)
            population_status.append(
                LRS4_REGIME_INELIGIBLE
            )
            reasons.append(
                (NO_PRECEDING_COMPLETED_ENDPOINT,)
            )
            continue

        endpoint_time = int(
            endpoints[endpoint_index]
        )

        observation_time = int(
            observations[obs_index]
        )

        if not endpoint_time < observation_time:
            raise RuntimeError(
                "Causal assignment integrity failure: assigned endpoint "
                "does not satisfy strict G < T"
            )

        assigned_index[obs_index] = endpoint_index
        assigned_endpoint[obs_index] = endpoint_time

        state = regime.state[endpoint_index]

        assigned_state.append(state)

        if bool(regime.state_valid[endpoint_index]):
            if state not in (
                REGIME_HIGH,
                REGIME_LOW,
            ):
                raise RuntimeError(
                    "Valid assigned endpoint does not contain HIGH/LOW state"
                )

            eligible[obs_index] = True
            population_status.append(
                LRS4_ELIGIBLE
            )
            reasons.append(())
        else:
            if state != REGIME_INVALID:
                raise RuntimeError(
                    "Invalid assigned endpoint does not contain INVALID state"
                )

            eligible[obs_index] = False
            population_status.append(
                LRS4_REGIME_INELIGIBLE
            )
            reasons.append(
                (ASSIGNED_ENDPOINT_INVALID,)
            )

    return ObservationRegimeAssignmentResult(
        window_name=regime.window_name,
        observation_time_ms=_freeze_array(
            observations.copy()
        ),
        assigned_endpoint_index=_freeze_array(
            assigned_index
        ),
        assigned_endpoint_ms=_freeze_array(
            assigned_endpoint
        ),
        assigned_state=tuple(assigned_state),
        eligible=_freeze_array(
            eligible
        ),
        population_status=tuple(
            population_status
        ),
        reason=tuple(reasons),
    )
