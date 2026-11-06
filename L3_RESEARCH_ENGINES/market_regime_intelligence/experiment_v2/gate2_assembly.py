"""Experiment-v2 Gate-2 evidence assembly from authoritative D1/D3/D4.

No Instrument Path routing, final observation projection, or research access.
"""

from dataclasses import dataclass

import numpy as np

from .contracts import (
    Gate2Evidence,
    WindowGate2Completed,
    WindowIntegrityFailure,
)
from .d1_d0 import D1Constructed
from .d3 import D3Constructed
from .d4 import D4Constructed
from .gate2_numeric import (
    ObservationDiagnostics,
    evaluate_observation_diagnostics,
)
from .gate2_episodes import (
    EpisodeDiagnostics,
    evaluate_episode_diagnostics,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


STRUCTURAL = frozenset({
    "SEVERE_REGIME_IMBALANCE",
    "EXCESSIVE_REGIME_INELIGIBILITY",
    "EXCESSIVE_INELIGIBILITY_CONCENTRATION",
    "INSUFFICIENT_STATE_EPISODE_SUPPORT",
})
EPISTEMIC = "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING"
TURNOVER = "EXCESSIVE_EPISODE_TURNOVER"
PERSISTENCE = "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE"
CONFLICT = "CONFLICTING_DIRECTIONAL_FAILURES"


@dataclass(frozen=True)
class Gate2AssemblyResult:
    window: str
    completed: WindowGate2Completed | None
    integrity: WindowIntegrityFailure | None
    observations: ObservationDiagnostics | None
    episodes: EpisodeDiagnostics | None


def _integrity(window: str, detail: str) -> Gate2AssemblyResult:
    return Gate2AssemblyResult(
        window=window,
        completed=None,
        integrity=WindowIntegrityFailure(
            tag="INTEGRITY_FAILURE",
            window=window,
            invariant="GATE2_D1_D3_D4_RECONCILIATION",
            provenance=detail,
        ),
        observations=None,
        episodes=None,
    )


def assemble_gate2(
    d1: D1Constructed,
    d3: D3Constructed,
    d4: D4Constructed,
) -> Gate2AssemblyResult:
    """Assemble a completed current-window Gate 2, or fail closed."""

    window = getattr(d1, "window", None)
    if window not in ("1h", "4h", "24h"):
        raise ValueError("A valid D1 window is required")

    try:
        if not (
            isinstance(d1, D1Constructed)
            and isinstance(d3, D3Constructed)
            and isinstance(d4, D4Constructed)
        ):
            raise ValueError("Authoritative constructed inputs required")

        if d1.window != d3.window or d1.window != d4.window:
            raise ValueError("Window identity mismatch")

        if not np.array_equal(d3.endpoint_ms, d4.endpoint_ms):
            raise ValueError("D3/D4 endpoint domains differ")

        endpoints = d3.endpoint_ms
        admissible = d3.admissible
        states = d3.state
        ids = d4.episode_id_by_endpoint

        if (
            not isinstance(endpoints, np.ndarray)
            or endpoints.ndim != 1
            or endpoints.dtype != np.dtype("int64")
            or endpoints.size == 0
            or not isinstance(admissible, np.ndarray)
            or admissible.shape != endpoints.shape
            or admissible.dtype != np.dtype("bool")
            or not isinstance(ids, np.ndarray)
            or ids.shape != endpoints.shape
            or ids.dtype != np.dtype("int64")
            or not isinstance(states, tuple)
            or len(states) != len(endpoints)
        ):
            raise ValueError("Malformed D3/D4 reconciliation arrays")

        for index, (valid, state, episode_id) in enumerate(
            zip(admissible, states, ids)
        ):
            if valid:
                if state not in ("HIGH", "LOW"):
                    raise ValueError("Admissible endpoint has invalid state")
                if episode_id < 0 or episode_id >= len(d4.episodes):
                    raise ValueError("Admissible endpoint lacks episode")
                episode = d4.episodes[int(episode_id)]
                if (
                    episode.state != state
                    or not episode.start_index <= index <= episode.end_index
                ):
                    raise ValueError("D3 state and D4 episode disagree")
            elif episode_id != -1:
                raise ValueError("Inadmissible endpoint has episode")

        if d4.t_classified_ms != (
            int(np.count_nonzero(admissible)) * GRID_INTERVAL_MS
        ):
            raise ValueError("Classified time does not reconcile")

        observations = evaluate_observation_diagnostics(d1, d3)
        episodes = evaluate_episode_diagnostics(d4)

        if (
            episodes.k_total == 0
            and observations.n_eligible > 0
        ):
            raise ValueError(
                "Zero structural episodes with eligible observations"
            )

        reasons = set(observations.reasons | episodes.reasons)
        both = TURNOVER in reasons and PERSISTENCE in reasons
        if both:
            reasons.add(CONFLICT)
        elif CONFLICT in reasons:
            raise ValueError("Unpaired directional conflict")

        if reasons & STRUCTURAL or both:
            disposition = "STRUCTURALLY_INSUFFICIENT"
        elif EPISTEMIC in reasons:
            disposition = "EPISTEMICALLY_INDETERMINATE"
        elif PERSISTENCE in reasons:
            disposition = "STRUCTURALLY_INSUFFICIENT"
        elif TURNOVER in reasons:
            disposition = "PATHOLOGICALLY_FRAGMENTED"
        else:
            disposition = "VIABLE"

        if not reasons:
            action = "PROCEED_TO_STAGE_2"
        elif reasons & STRUCTURAL or EPISTEMIC in reasons or both:
            action = "TERMINATE_INSTRUMENT_V1"
        elif window != "4h":
            action = "TERMINATE_INSTRUMENT_V1"
        elif TURNOVER in reasons:
            action = "EVALUATE_24H_FALLBACK"
        elif PERSISTENCE in reasons:
            action = "EVALUATE_1H_FALLBACK"
        else:
            raise ValueError("Unresolved Gate-2 reason configuration")

        evidence = Gate2Evidence(
            window=window,
            reasons=frozenset(reasons),
            action=action,
            disposition=disposition,
        )

        return Gate2AssemblyResult(
            window=window,
            completed=WindowGate2Completed(
                tag="GATE2_COMPLETED",
                evidence=evidence,
            ),
            integrity=None,
            observations=observations,
            episodes=episodes,
        )

    except (ValueError, TypeError, AttributeError, IndexError) as exc:
        return _integrity(window, str(exc))
