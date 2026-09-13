"""
LRS-4 Experiment v1 — contiguous regime-episode construction.

Scope:
RegimeStateResult
-> deterministic contiguous HIGH / LOW episodes

Frozen continuity rule:
- HIGH continues only across immediately consecutive HIGH endpoints.
- LOW continues only across immediately consecutive LOW endpoints.
- State change terminates the current episode.
- INVALID terminates the current episode and is never itself an episode.
- A later valid state begins a new episode.
- No backward bridging across INVALID.

Out of scope:
observation-at-T assignment
instrument-day aggregation
fallback routing
Gate 2
K7
bootstrap inference
conditioned outcomes
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


@dataclass(frozen=True)
class RegimeEpisode:
    episode_id: int
    state: str
    start_index: int
    end_index: int
    start_endpoint_ms: int
    end_endpoint_ms: int
    endpoint_count: int


@dataclass(frozen=True)
class EpisodeResult:
    window_name: str
    endpoint_ms: np.ndarray
    state: tuple[str, ...]
    episode_id_by_endpoint: np.ndarray
    episodes: tuple[RegimeEpisode, ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _validate_input(regime: RegimeStateResult) -> None:
    n = regime.endpoint_ms.size

    if len(regime.state) != n:
        raise ValueError(
            "RegimeStateResult state length does not match endpoints"
        )

    if regime.state_valid.size != n:
        raise ValueError(
            "RegimeStateResult state_valid length does not match endpoints"
        )

    if n > 1:
        deltas = np.diff(regime.endpoint_ms)

        if not np.all(deltas == GRID_INTERVAL_MS):
            raise ValueError(
                "RegimeStateResult endpoints are not consecutive frozen "
                "5-minute grid points"
            )

    allowed = {
        REGIME_HIGH,
        REGIME_LOW,
        REGIME_INVALID,
    }

    for i, state in enumerate(regime.state):
        if state not in allowed:
            raise ValueError(
                f"Unknown regime state at index {i}: {state!r}"
            )

        if bool(regime.state_valid[i]):
            if state == REGIME_INVALID:
                raise ValueError(
                    "state_valid=True cannot coexist with INVALID state"
                )
        else:
            if state != REGIME_INVALID:
                raise ValueError(
                    "state_valid=False must correspond to INVALID state"
                )


def build_regime_episodes(
    regime: RegimeStateResult,
) -> EpisodeResult:
    """
    Build deterministic contiguous HIGH/LOW regime episodes.

    Episode IDs are zero-based and assigned chronologically.

    INVALID endpoints receive episode_id -1 and break continuity.
    """
    _validate_input(regime)

    n = regime.endpoint_ms.size

    episode_ids = np.full(
        n,
        -1,
        dtype=np.int64,
    )

    episodes = []

    current_state = None
    current_start = None
    current_episode_id = None

    def close_episode(end_index: int) -> None:
        nonlocal current_state
        nonlocal current_start
        nonlocal current_episode_id

        if current_state is None:
            return

        episodes.append(
            RegimeEpisode(
                episode_id=int(current_episode_id),
                state=current_state,
                start_index=int(current_start),
                end_index=int(end_index),
                start_endpoint_ms=int(
                    regime.endpoint_ms[current_start]
                ),
                end_endpoint_ms=int(
                    regime.endpoint_ms[end_index]
                ),
                endpoint_count=int(
                    end_index - current_start + 1
                ),
            )
        )

        current_state = None
        current_start = None
        current_episode_id = None

    for i, state in enumerate(regime.state):
        if state == REGIME_INVALID:
            close_episode(i - 1)
            continue

        if current_state is None:
            current_episode_id = len(episodes)
            current_state = state
            current_start = i
            episode_ids[i] = current_episode_id
            continue

        if state == current_state:
            episode_ids[i] = current_episode_id
            continue

        # Valid state changed HIGH <-> LOW.
        close_episode(i - 1)

        current_episode_id = len(episodes)
        current_state = state
        current_start = i
        episode_ids[i] = current_episode_id

    if current_state is not None:
        close_episode(n - 1)

    return EpisodeResult(
        window_name=regime.window_name,
        endpoint_ms=_freeze_array(
            regime.endpoint_ms.copy()
        ),
        state=tuple(regime.state),
        episode_id_by_endpoint=_freeze_array(
            episode_ids
        ),
        episodes=tuple(episodes),
    )
