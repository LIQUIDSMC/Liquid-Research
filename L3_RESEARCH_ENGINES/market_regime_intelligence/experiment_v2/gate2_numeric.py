"""Experiment-v2 Gate-2 numeric diagnostics.

Increment 1: authoritative D1/D3 observation reconciliation and G1-G4.
No episode morphology, routing, or completed Gate-2 evidence is emitted.
"""

from dataclasses import dataclass
import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d1_d0 import D1Constructed
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d3 import D3Constructed
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import GRID_INTERVAL_MS


@dataclass(frozen=True)
class ObservationDiagnostics:
    window: str
    n_d1: int
    n_eligible: int
    n_ineligible: int
    n_high: int
    n_low: int
    d_available: int
    ineligibility_rate: float
    concentration_status: tuple[str, ...]
    concentration: float | None
    minority_status: str
    p_min: float | None
    reasons: frozenset[str]


def evaluate_observation_diagnostics(
    d1: D1Constructed,
    d3: D3Constructed,
) -> ObservationDiagnostics:
    """Evaluate frozen current-window G-NUMERIC.1-.4 diagnostics.

    Raises ValueError for malformed or irreconcilable authoritative inputs.
    This function does not translate integrity failures into Gate-2 reasons.
    """
    if not isinstance(d1, D1Constructed) or not isinstance(d3, D3Constructed):
        raise TypeError("D1Constructed and D3Constructed required")
    if d1.window != d3.window or d1.window not in ("1h", "4h", "24h"):
        raise ValueError("Window identity mismatch")

    times = d1.observation_time_ms
    ids = d1.observation_trade_id
    days = d1.observation_day
    endpoints = d3.endpoint_ms
    admissible = d3.admissible
    states = d3.state

    if (
        not isinstance(times, np.ndarray)
        or times.ndim != 1
        or times.dtype != np.dtype("int64")
        or times.size == 0
        or not isinstance(ids, np.ndarray)
        or ids.shape != times.shape
        or ids.dtype != np.dtype("int64")
        or not isinstance(days, tuple)
        or len(days) != len(times)
        or not isinstance(endpoints, np.ndarray)
        or endpoints.ndim != 1
        or endpoints.dtype != np.dtype("int64")
        or endpoints.size == 0
        or not isinstance(admissible, np.ndarray)
        or admissible.shape != endpoints.shape
        or admissible.dtype != np.dtype("bool")
        or not isinstance(states, tuple)
        or len(states) != len(endpoints)
    ):
        raise ValueError("Malformed authoritative observation or grid arrays")

    if np.any(times == np.iinfo(np.int64).min):
        raise ValueError("Unrepresentable strict-C10 predecessor")
    if np.any(endpoints % GRID_INTERVAL_MS != 0):
        raise ValueError("Unaligned D3 endpoint")
    if any(
        int(endpoints[i]) - int(endpoints[i - 1]) != GRID_INTERVAL_MS
        for i in range(1, len(endpoints))
    ):
        raise ValueError("Non-contiguous D3 endpoint domain")

    if len(set(zip(times.tolist(), ids.tolist()))) != len(times):
        raise ValueError("Duplicate canonical observation identity")

    mapped = ((times - 1) // GRID_INTERVAL_MS) * GRID_INTERVAL_MS
    indices = np.searchsorted(endpoints, mapped)
    if np.any(indices >= len(endpoints)):
        raise ValueError("Observation endpoint outside D3 domain")
    if not np.array_equal(endpoints[indices], mapped):
        raise ValueError("Missing authoritative observation endpoint")

    if any(
        (bool(admissible[i]) and states[i] not in ("HIGH", "LOW"))
        or (not bool(admissible[i]) and states[i] != "INVALID")
        for i in range(len(endpoints))
    ):
        raise ValueError("Contradictory D3 admissibility and state")

    statuses = d1.day_statuses
    if not isinstance(statuses, tuple):
        raise ValueError("Malformed day statuses")
    available = {}
    seen_days = set()
    for status in statuses:
        if (
            type(status.research_day) is not str
            or not status.research_day
            or type(status.candidate_count) is not int
            or status.candidate_count < 0
            or not isinstance(status.candidate_endpoints, tuple)
            or not isinstance(status.reasons, tuple)
        ):
            raise ValueError("Malformed research-day status")

        day = status.research_day
        if day in seen_days:
            raise ValueError("Duplicate research-day status")
        seen_days.add(day)

        if (
            any(type(x) is not int for x in status.candidate_endpoints)
            or tuple(sorted(set(status.candidate_endpoints)))
            != status.candidate_endpoints
            or any(x % GRID_INTERVAL_MS for x in status.candidate_endpoints)
            or any(type(reason) is not str for reason in status.reasons)
        ):
            raise ValueError("Malformed day endpoints or reasons")

        if status.candidate_count == 0:
            if (
                status.candidate_endpoints
                or status.source_history_eligible is not None
                or status.reasons
            ):
                raise ValueError("Contradictory zero-candidate day")
        elif not status.candidate_endpoints:
            raise ValueError("Candidate day lacks endpoints")

        if status.source_history_eligible is True:
            if status.reasons:
                raise ValueError("Eligible day carries exclusion reasons")
            available[day] = status.candidate_count
        elif status.source_history_eligible is False:
            if status.candidate_count == 0 or not status.reasons:
                raise ValueError("Contradictory excluded day")
        elif status.source_history_eligible is not None:
            raise ValueError("Malformed day authorization")
        elif status.candidate_count != 0:
            raise ValueError("Candidate day has undefined authorization")

    exposure = {day: 0 for day in available}
    observed_endpoints = {day: set() for day in available}
    ineligible_by_day = {day: 0 for day in available}
    high = low = 0

    for position, (day, index) in enumerate(zip(days, indices)):
        if day not in available:
            raise ValueError("D1 observation lacks eligible day status")
        exposure[day] += 1
        observed_endpoints[day].add(int(mapped[position]))
        if not admissible[index]:
            ineligible_by_day[day] += 1
        elif states[index] == "HIGH":
            high += 1
        else:
            low += 1

    if any(exposure[day] != available[day] for day in available):
        raise ValueError("D1 observation/day exposure reconciliation failure")

    eligible_statuses = {
        status.research_day: status
        for status in statuses
        if status.source_history_eligible is True
    }
    if any(
        tuple(sorted(observed_endpoints[day]))
        != eligible_statuses[day].candidate_endpoints
        for day in available
    ):
        raise ValueError("D1 observation/day endpoint reconciliation failure")

    n_d1 = len(times)
    n_eligible = high + low
    n_ineligible = n_d1 - n_eligible
    d_available = len(available)
    rate = n_ineligible / n_d1
    reasons = set()

    if rate > 0.20:
        reasons.add("EXCESSIVE_REGIME_INELIGIBILITY")

    concentration = None
    if n_ineligible == 0:
        concentration_status = ("NOT_APPLICABLE_ZERO_INELIGIBILITY",)
    else:
        activation = []
        if d_available < 10:
            activation.append("NOT_EVALUATED_INSUFFICIENT_DAY_SUPPORT")
        if n_ineligible < 2 * d_available:
            activation.append("NOT_EVALUATED_INSUFFICIENT_INELIGIBILITY_COUNT")
        concentration_status = (
            ("EVALUATED",) if not activation else tuple(activation)
        )
        concentration = 0.5 * sum(
            abs(ineligible_by_day[day] / n_ineligible - exposure[day] / n_d1)
            for day in available
        )
        if not activation and concentration > 0.30:
            reasons.add("EXCESSIVE_INELIGIBILITY_CONCENTRATION")

    if n_eligible == 0:
        minority_status = "NOT_APPLICABLE_ZERO_ELIGIBLE_OBSERVATIONS"
        p_min = None
    else:
        p_min = min(high, low) / n_eligible
        minority_status = "PASS" if p_min >= 0.10 else "FAIL"
        if minority_status == "FAIL":
            reasons.add("SEVERE_REGIME_IMBALANCE")

    return ObservationDiagnostics(
        window=d1.window,
        n_d1=n_d1,
        n_eligible=n_eligible,
        n_ineligible=n_ineligible,
        n_high=high,
        n_low=low,
        d_available=d_available,
        ineligibility_rate=rate,
        concentration_status=concentration_status,
        concentration=concentration,
        minority_status=minority_status,
        p_min=p_min,
        reasons=frozenset(reasons),
    )
