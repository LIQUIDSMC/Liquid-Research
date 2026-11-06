"""Experiment-v2 Phase 2: D1 population construction and D0 gate.

No regime classification, Gate 2, fallback, or historical execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WindowD0Terminal,
    WindowIntegrityFailure,
    WINDOWS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
    SourceHistoryAuthorizationResult,
    authorize_source_history,
)


@dataclass(frozen=True)
class D1DayInput:
    research_day: str
    sample_trade_time: np.ndarray
    sample_trade_id: np.ndarray
    common_eligible: np.ndarray


@dataclass(frozen=True)
class D1DayStatus:
    research_day: str
    candidate_count: int
    candidate_endpoints: tuple[int, ...]
    source_history_eligible: bool | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class D1Constructed:
    window: str
    observation_time_ms: np.ndarray
    observation_trade_id: np.ndarray
    observation_day: tuple[str, ...]
    day_statuses: tuple[D1DayStatus, ...]

    @property
    def observation_count(self) -> int:
        return len(self.observation_time_ms)


@dataclass(frozen=True)
class D1D0Result:
    window: str
    day_statuses: tuple[D1DayStatus, ...]
    d1: D1Constructed | None
    terminal: WindowD0Terminal | WindowIntegrityFailure | None


def _failure(window: str, invariant: str, detail: str) -> D1D0Result:
    return D1D0Result(
        window=window,
        day_statuses=(),
        d1=None,
        terminal=WindowIntegrityFailure(
            tag="INTEGRITY_FAILURE",
            window=window,
            invariant=invariant,
            provenance=detail,
        ),
    )


def _freeze(values: np.ndarray) -> np.ndarray:
    result = np.array(values, copy=True)
    result.setflags(write=False)
    return result


def construct_d1_d0(
    *,
    window: str,
    days: tuple[D1DayInput, ...],
    authorization_by_day: Mapping[str, SourceHistoryAuthorizationResult],
    available_endpoint_by_day: Mapping[str, np.ndarray],
) -> D1D0Result:
    """Construct candidate days independently of regime and outcomes.

    available_endpoint_by_day is the independently established frozen
    completed-grid coverage used to verify strict-C10 predecessor presence.
    Authorization is W-specific and evaluated over unique candidate endpoints.
    """
    if window not in WINDOWS:
        raise ValueError(f"Unsupported window: {window!r}")

    statuses = []
    retained_times = []
    retained_ids = []
    retained_days = []
    total_candidates = 0
    seen_days = set()

    for day in days:
        if day.research_day in seen_days:
            return _failure(window, "I06_I07", "Duplicate research-day input")
        seen_days.add(day.research_day)

        times = np.asarray(day.sample_trade_time)
        ids = np.asarray(day.sample_trade_id)
        mask = np.asarray(day.common_eligible)

        if (
            times.ndim != 1 or ids.ndim != 1 or mask.ndim != 1
            or not (len(times) == len(ids) == len(mask))
            or times.dtype != np.dtype("int64")
            or ids.dtype != np.dtype("int64")
            or mask.dtype != np.dtype("bool")
        ):
            return _failure(
                window, "I06_I07", f"Malformed canonical arrays: {day.research_day}"
            )

        if len(times) > 1 and np.any(np.diff(times) < 0):
            return _failure(
                window, "I06_I07", f"Unsorted observations: {day.research_day}"
            )

        # Canonical observation identity is (trade_time, trade_id).
        # Equal timestamps with distinct trade IDs remain valid.
        identities = set(zip(times.tolist(), ids.tolist()))
        if len(identities) != len(times):
            return _failure(
                window, "I06_I07",
                f"Duplicate canonical observation identity: {day.research_day}"
            )

        candidate_times = times[mask]
        candidate_ids = ids[mask]
        n = len(candidate_times)
        total_candidates += n

        if n == 0:
            statuses.append(D1DayStatus(
                day.research_day, 0, (), None, ()
            ))
            continue

        if day.research_day not in available_endpoint_by_day:
            return _failure(
                window, "STRICT_C10",
                f"Missing completed-grid coverage: {day.research_day}"
            )

        available = np.asarray(available_endpoint_by_day[day.research_day])
        if (
            available.ndim != 1
            or available.dtype != np.dtype("int64")
            or (len(available) > 1 and
                not np.all(np.diff(available) == GRID_INTERVAL_MS))
            or np.any(available % GRID_INTERVAL_MS != 0)
        ):
            return _failure(
                window, "STRICT_C10",
                f"Invalid completed-grid coverage: {day.research_day}"
            )

        # Reject timestamps whose strict predecessor cannot be represented
        # safely in signed int64 arithmetic.
        if np.any(candidate_times == np.iinfo(np.int64).min):
            return _failure(
                window, "STRICT_C10",
                f"Unrepresentable predecessor timestamp: {day.research_day}"
            )

        # Exact-grid observations consume the preceding endpoint.
        endpoints = ((candidate_times - 1) // GRID_INTERVAL_MS) * GRID_INTERVAL_MS
        unique_endpoints = np.unique(endpoints)

        if not np.all(np.isin(unique_endpoints, available)):
            return _failure(
                window, "STRICT_C10",
                f"Missing required predecessor: {day.research_day}"
            )

        authorization = authorization_by_day.get(day.research_day)
        if (
            not isinstance(authorization, SourceHistoryAuthorizationResult)
            or authorization.window_name != window
        ):
            return _failure(
                window, "SOURCE_HISTORY_EVIDENCE",
                f"Missing or mismatched authorization: {day.research_day}"
            )

        authorized_endpoints = np.asarray(authorization.endpoint_ms)
        authorized_flags = np.asarray(authorization.authorized)

        if (
            authorized_endpoints.ndim != 1
            or authorized_flags.ndim != 1
            or len(authorized_endpoints) != len(authorized_flags)
            or len(authorized_endpoints) != len(authorization.reason)
            or authorized_endpoints.dtype != np.dtype("int64")
            or authorized_flags.dtype != np.dtype("bool")
            or np.any(authorized_endpoints % GRID_INTERVAL_MS != 0)
            or (len(authorized_endpoints) > 1 and
                not np.all(np.diff(authorized_endpoints) == GRID_INTERVAL_MS))
        ):
            return _failure(
                window, "SOURCE_HISTORY_EVIDENCE",
                f"Malformed authorization: {day.research_day}"
            )

        # Verify supplied evidence against the canonical K1.3-B authority.
        # An inconsistent result is an integrity failure, never D0-C1.
        try:
            canonical = authorize_source_history(
                endpoint_ms=authorized_endpoints,
                source_start_ms=authorization.source_start_ms,
                window_name=window,
                confirmed_breaks=authorization.confirmed_breaks,
            )

            metadata_matches = (
                authorization.source_start_ms == canonical.source_start_ms
                and authorization.source_start_grid_ceiling_ms
                == canonical.source_start_grid_ceiling_ms
                and authorization.raw_history_ms == canonical.raw_history_ms
                and authorization.leading_maturity_endpoint_ms
                == canonical.leading_maturity_endpoint_ms
            )

            evidence_matches = (
                metadata_matches
                and np.array_equal(
                    authorized_flags, canonical.authorized
                )
                and authorization.reason == canonical.reason
                and authorization.confirmed_breaks == canonical.confirmed_breaks
            )
        except (TypeError, ValueError, OverflowError, AttributeError):
            evidence_matches = False

        if not evidence_matches:
            return _failure(
                window, "SOURCE_HISTORY_EVIDENCE",
                f"Inconsistent canonical authorization: {day.research_day}"
            )

        index = np.searchsorted(authorized_endpoints, unique_endpoints)
        if np.any(index >= len(authorized_endpoints)):
            return _failure(
                window, "SOURCE_HISTORY_EVIDENCE",
                f"Missing authorization endpoint: {day.research_day}"
            )
        if np.any(authorized_endpoints[index] != unique_endpoints):
            return _failure(
                window, "SOURCE_HISTORY_EVIDENCE",
                f"Missing authorization endpoint: {day.research_day}"
            )

        eligible = bool(np.all(authorized_flags[index]))
        reasons = []
        if not eligible:
            for i in index:
                if not authorized_flags[i]:
                    for reason in authorization.reason[int(i)]:
                        if reason not in reasons:
                            reasons.append(reason)

        statuses.append(D1DayStatus(
            research_day=day.research_day,
            candidate_count=n,
            candidate_endpoints=tuple(int(x) for x in unique_endpoints),
            source_history_eligible=eligible,
            reasons=tuple(reasons),
        ))

        if eligible:
            retained_times.extend(int(x) for x in candidate_times)
            retained_ids.extend(int(x) for x in candidate_ids)
            retained_days.extend([day.research_day] * n)

    if not retained_times:
        provenance = "C1" if total_candidates else "C2"
        return D1D0Result(
            window=window,
            day_statuses=tuple(statuses),
            d1=None,
            terminal=WindowD0Terminal(
                tag="D0_TERMINAL",
                window=window,
                reason="NO_TARGET_OBSERVATION_POPULATION",
                provenance=provenance,
            ),
        )

    d1 = D1Constructed(
        window=window,
        observation_time_ms=_freeze(
            np.asarray(retained_times, dtype=np.int64)
        ),
        observation_trade_id=_freeze(
            np.asarray(retained_ids, dtype=np.int64)
        ),
        observation_day=tuple(retained_days),
        day_statuses=tuple(statuses),
    )

    return D1D0Result(
        window=window,
        day_statuses=tuple(statuses),
        d1=d1,
        terminal=None,
    )
