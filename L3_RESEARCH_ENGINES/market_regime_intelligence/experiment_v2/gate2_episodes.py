"""Experiment-v2 Gate-2 G5-G6 structural episode diagnostics.

Consumes authoritative D4 topology. Does not reconstruct episodes,
inspect research outcomes, or emit completed Gate-2 routing evidence.
"""

from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d4 import (
    D4Constructed,
    D2_BOUNDARY,
    D3_INADMISSIBILITY,
    STATE_CHANGE,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


WINDOW_MS = {
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
}

ZERO_EPISODES = "NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES"
INDETERMINATE = "INDETERMINATE_FROM_BOUNDARY_CENSORING"


@dataclass(frozen=True)
class EpisodeDiagnostics:
    window: str
    k_high: int
    k_low: int
    k_total: int
    t_classified_ms: int
    high_support_status: str
    low_support_status: str
    turnover_status: str
    persistence_status: str
    p_short_lb: Fraction | None
    p_short_ub: Fraction | None
    p_long_time_lb: Fraction | None
    p_long_time_ub: Fraction | None
    reasons: frozenset[str]


def _validate(d4: D4Constructed) -> None:
    if not isinstance(d4, D4Constructed):
        raise TypeError("D4Constructed required")
    if d4.window not in WINDOW_MS:
        raise ValueError("Unsupported window")

    endpoints = d4.endpoint_ms
    ids = d4.episode_id_by_endpoint

    if (
        not isinstance(endpoints, np.ndarray)
        or endpoints.ndim != 1
        or endpoints.dtype != np.dtype("int64")
        or endpoints.size == 0
        or not isinstance(ids, np.ndarray)
        or ids.shape != endpoints.shape
        or ids.dtype.kind not in ("i", "u")
        or not isinstance(d4.episodes, tuple)
    ):
        raise ValueError("Malformed D4 topology arrays")

    if (
        np.any(endpoints % GRID_INTERVAL_MS != 0)
        or np.any(np.diff(endpoints) != GRID_INTERVAL_MS)
    ):
        raise ValueError("Noncanonical D4 grid")

    if (
        type(d4.k_high) is not int
        or type(d4.k_low) is not int
        or type(d4.k_total) is not int
        or type(d4.t_classified_ms) is not int
    ):
        raise ValueError("Malformed D4 summary types")

    episodes = d4.episodes
    if d4.k_total != len(episodes):
        raise ValueError("D4 episode count mismatch")

    valid_causes = {D2_BOUNDARY, D3_INADMISSIBILITY, STATE_CHANGE}
    classified_cells = 0
    high = low = 0
    previous_end = -1
    previous_state = None

    for i, episode in enumerate(episodes):
        if (
            type(episode.episode_id) is not int
            or episode.episode_id != i
            or episode.state not in ("HIGH", "LOW")
            or type(episode.start_index) is not int
            or type(episode.end_index) is not int
            or not (0 <= episode.start_index <= episode.end_index < len(endpoints))
            or episode.start_index <= previous_end
            or type(episode.endpoint_count) is not int
            or type(episode.observed_duration_ms) is not int
            or type(episode.start_endpoint_ms) is not int
            or type(episode.end_endpoint_ms) is not int
            or type(episode.left_censored) is not bool
            or type(episode.right_censored) is not bool
            or episode.left_boundary_cause not in valid_causes
            or episode.right_boundary_cause not in valid_causes
        ):
            raise ValueError("Malformed D4 episode")

        count = episode.end_index - episode.start_index + 1
        if (
            episode.endpoint_count != count
            or episode.observed_duration_ms != count * GRID_INTERVAL_MS
            or episode.start_endpoint_ms != int(endpoints[episode.start_index])
            or episode.end_endpoint_ms != int(endpoints[episode.end_index])
            or not np.all(ids[episode.start_index:episode.end_index + 1] == i)
        ):
            raise ValueError("D4 episode duration or identity mismatch")

        if episode.left_censored and (
            episode.start_index != 0
            or episode.left_boundary_cause != D2_BOUNDARY
        ):
            raise ValueError("Invalid left censoring")

        if episode.right_censored != (
            episode.end_index == len(endpoints) - 1
        ):
            raise ValueError("Invalid right censoring")

        if (
            episode.left_boundary_cause == D2_BOUNDARY
        ) != (episode.start_index == 0):
            raise ValueError("Invalid left boundary cause")

        if (
            episode.right_boundary_cause == D2_BOUNDARY
        ) != (episode.end_index == len(endpoints) - 1):
            raise ValueError("Invalid right boundary cause")

        if episode.start_index > 0:
            adjacent = episode.start_index == previous_end + 1
            if adjacent:
                if (
                    previous_state == episode.state
                    or episode.left_boundary_cause != STATE_CHANGE
                ):
                    raise ValueError("Invalid episode transition")
            elif episode.left_boundary_cause != D3_INADMISSIBILITY:
                raise ValueError("Invalid episode gap boundary")

        if episode.end_index < len(endpoints) - 1:
            next_is_episode = (
                i + 1 < len(episodes)
                and episodes[i + 1].start_index == episode.end_index + 1
            )
            expected = STATE_CHANGE if next_is_episode else D3_INADMISSIBILITY
            if episode.right_boundary_cause != expected:
                raise ValueError("Invalid right boundary transition")

        classified_cells += count
        high += episode.state == "HIGH"
        low += episode.state == "LOW"
        previous_end = episode.end_index
        previous_state = episode.state

    expected_ids = np.full(len(endpoints), -1, dtype=np.int64)
    for episode in episodes:
        expected_ids[episode.start_index:episode.end_index + 1] = episode.episode_id

    if not np.array_equal(ids, expected_ids):
        raise ValueError("D4 endpoint-to-episode reconciliation failure")

    if (
        d4.k_high != high
        or d4.k_low != low
        or d4.k_total != high + low
        or d4.t_classified_ms != classified_cells * GRID_INTERVAL_MS
    ):
        raise ValueError("D4 summary reconciliation failure")


def evaluate_episode_diagnostics(d4: D4Constructed) -> EpisodeDiagnostics:
    """Evaluate inherited G5-G6 without inferring censored durations."""

    _validate(d4)
    reasons = set()

    high_status = "PASS" if d4.k_high >= 5 else "FAIL"
    low_status = "PASS" if d4.k_low >= 5 else "FAIL"

    if high_status == "FAIL" or low_status == "FAIL":
        reasons.add("INSUFFICIENT_STATE_EPISODE_SUPPORT")

    if d4.k_total == 0:
        return EpisodeDiagnostics(
            window=d4.window,
            k_high=0,
            k_low=0,
            k_total=0,
            t_classified_ms=0,
            high_support_status=high_status,
            low_support_status=low_status,
            turnover_status=ZERO_EPISODES,
            persistence_status=ZERO_EPISODES,
            p_short_lb=None,
            p_short_ub=None,
            p_long_time_lb=None,
            p_long_time_ub=None,
            reasons=frozenset(reasons),
        )

    w = WINDOW_MS[d4.window]
    definitely_short = 0
    possibly_short = 0
    definitely_long_time = 0
    possibly_long_time = 0

    for episode in d4.episodes:
        duration = episode.observed_duration_ms
        censored = episode.left_censored or episode.right_censored

        if not censored:
            if 2 * duration < w:
                definitely_short += 1
                possibly_short += 1
            if duration > 2 * w:
                definitely_long_time += duration
                possibly_long_time += duration
        else:
            # Censoring provides a duration lower bound, not an upper bound.
            if 2 * duration < w:
                possibly_short += 1

            if duration > 2 * w:
                definitely_long_time += duration
                possibly_long_time += duration
            else:
                possibly_long_time += duration

    short_lb = Fraction(definitely_short, d4.k_total)
    short_ub = Fraction(possibly_short, d4.k_total)
    long_lb = Fraction(definitely_long_time, d4.t_classified_ms)
    long_ub = Fraction(possibly_long_time, d4.t_classified_ms)

    if short_lb > Fraction(1, 3):
        turnover_status = "FAIL"
        reasons.add("EXCESSIVE_EPISODE_TURNOVER")
    elif short_ub <= Fraction(1, 3):
        turnover_status = "PASS"
    else:
        turnover_status = INDETERMINATE

    if long_lb > Fraction(1, 2):
        persistence_status = "FAIL"
        reasons.add("TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE")
    elif long_ub <= Fraction(1, 2):
        persistence_status = "PASS"
    else:
        persistence_status = INDETERMINATE

    if INDETERMINATE in (turnover_status, persistence_status):
        reasons.add(
            "INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING"
        )

    if (
        "EXCESSIVE_EPISODE_TURNOVER" in reasons
        and "TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE" in reasons
    ):
        reasons.add("CONFLICTING_DIRECTIONAL_FAILURES")

    return EpisodeDiagnostics(
        window=d4.window,
        k_high=d4.k_high,
        k_low=d4.k_low,
        k_total=d4.k_total,
        t_classified_ms=d4.t_classified_ms,
        high_support_status=high_status,
        low_support_status=low_status,
        turnover_status=turnover_status,
        persistence_status=persistence_status,
        p_short_lb=short_lb,
        p_short_ub=short_ub,
        p_long_time_lb=long_lb,
        p_long_time_ub=long_ub,
        reasons=frozenset(reasons),
    )
