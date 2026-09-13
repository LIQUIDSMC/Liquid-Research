"""
LRS-4 Experiment v1 — causal source-history authorization.

This module implements structural source-history mechanics only.

Current scope:
- frozen 6W raw-history requirement
- ceiling of instrument-specific S0,s to the 5-minute grid
- endpoint-level leading-boundary maturity authorization

Later scope:
- confirmed acquisition-break intervals
- break recovery
- instrument-day/path-conditioned aggregation

Out of scope:
- discovery or inference of S0,s from operational evidence
- collector-log interpretation
- storage certification
- RVOL validity
- threshold validity
- fallback routing
- conditioned outcomes

S0,s must already have been established by qualifying K1.3-B
operational evidence before being supplied here.
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT = (
    "SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT"
)


@dataclass(frozen=True)
class SourceHistorySpec:
    window_name: str
    window_ms: int
    raw_history_ms: int


SOURCE_HISTORY_SPECS: Dict[str, SourceHistorySpec] = {
    "1h": SourceHistorySpec(
        window_name="1h",
        window_ms=1 * 60 * 60 * 1000,
        raw_history_ms=6 * 60 * 60 * 1000,
    ),
    "4h": SourceHistorySpec(
        window_name="4h",
        window_ms=4 * 60 * 60 * 1000,
        raw_history_ms=24 * 60 * 60 * 1000,
    ),
    "24h": SourceHistorySpec(
        window_name="24h",
        window_ms=24 * 60 * 60 * 1000,
        raw_history_ms=144 * 60 * 60 * 1000,
    ),
}


@dataclass(frozen=True)
class LeadingBoundaryAuthorizationResult:
    window_name: str
    source_start_ms: int
    source_start_grid_ceiling_ms: int
    raw_history_ms: int
    maturity_endpoint_ms: int
    endpoint_ms: np.ndarray
    authorized: np.ndarray
    reason: tuple[tuple[str, ...], ...]


def _freeze_array(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def ceil_to_grid(timestamp_ms: int) -> int:
    """
    Return the first frozen 5-minute grid endpoint >= timestamp_ms.

    Exact-grid timestamps remain unchanged.
    """
    timestamp_ms = int(timestamp_ms)

    quotient, remainder = divmod(
        timestamp_ms,
        GRID_INTERVAL_MS,
    )

    if remainder == 0:
        return timestamp_ms

    return (quotient + 1) * GRID_INTERVAL_MS


def authorize_leading_source_history(
    endpoint_ms: np.ndarray,
    source_start_ms: int,
    window_name: str,
) -> LeadingBoundaryAuthorizationResult:
    """
    Apply the frozen leading-boundary source-history maturity rule.

        G_SH-mature = ceil(S0,s)_grid + 6W

    An endpoint is authorized iff:

        G >= G_SH-mature

    Equality therefore passes.

    This function does not establish whether source_start_ms is
    evidentially qualified. That is a separate K1.3-B evidence task.
    """
    if window_name not in SOURCE_HISTORY_SPECS:
        raise ValueError(
            f"Unsupported frozen source-history window {window_name!r}"
        )

    endpoints = np.asarray(endpoint_ms)

    if endpoints.ndim != 1:
        raise ValueError(
            "endpoint_ms must be one-dimensional"
        )

    if endpoints.dtype.kind not in ("i", "u"):
        raise TypeError(
            "endpoint_ms must have integer dtype"
        )

    endpoints = endpoints.astype(np.int64, copy=False)

    if endpoints.size > 1:
        deltas = np.diff(endpoints)

        if not np.all(deltas == GRID_INTERVAL_MS):
            raise ValueError(
                "endpoint_ms must be consecutive frozen 5-minute "
                "grid points"
            )

    if endpoints.size:
        if np.any(endpoints % GRID_INTERVAL_MS != 0):
            raise ValueError(
                "endpoint_ms contains non-grid-aligned timestamp(s)"
            )

    source_start_ms = int(source_start_ms)

    spec = SOURCE_HISTORY_SPECS[window_name]

    source_ceiling = ceil_to_grid(source_start_ms)

    maturity_endpoint = (
        source_ceiling
        + spec.raw_history_ms
    )

    authorized = endpoints >= maturity_endpoint

    reasons = tuple(
        ()
        if bool(is_authorized)
        else (SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,)
        for is_authorized in authorized
    )

    return LeadingBoundaryAuthorizationResult(
        window_name=window_name,
        source_start_ms=source_start_ms,
        source_start_grid_ceiling_ms=source_ceiling,
        raw_history_ms=spec.raw_history_ms,
        maturity_endpoint_ms=maturity_endpoint,
        endpoint_ms=_freeze_array(endpoints.copy()),
        authorized=_freeze_array(authorized.copy()),
        reason=reasons,
    )


SOURCE_HISTORY_BREAK_CONFIRMED = (
    "SOURCE_HISTORY_BREAK_CONFIRMED"
)

SOURCE_HISTORY_BREAK_END_UNRESOLVED = (
    "SOURCE_HISTORY_BREAK_END_UNRESOLVED"
)


@dataclass(frozen=True)
class AcquisitionBreak:
    """
    Confirmed instrument-attributed acquisition source break.

    Interval semantics:
        [stop_ms, restored_ms)

    restored_ms=None means the acquisition restoration boundary
    remains unresolved and the break is open-ended.
    """

    stop_ms: int
    restored_ms: int | None = None


@dataclass(frozen=True)
class SourceHistoryAuthorizationResult:
    window_name: str
    source_start_ms: int
    source_start_grid_ceiling_ms: int
    raw_history_ms: int
    leading_maturity_endpoint_ms: int

    endpoint_ms: np.ndarray
    authorized: np.ndarray
    reason: tuple[tuple[str, ...], ...]

    confirmed_breaks: tuple[AcquisitionBreak, ...]


def _validate_breaks(
    confirmed_breaks: tuple[AcquisitionBreak, ...],
) -> tuple[AcquisitionBreak, ...]:
    normalized = []

    previous_stop = None

    for break_record in confirmed_breaks:
        if not isinstance(break_record, AcquisitionBreak):
            raise TypeError(
                "confirmed_breaks must contain AcquisitionBreak records"
            )

        stop_ms = int(break_record.stop_ms)

        restored_ms = (
            None
            if break_record.restored_ms is None
            else int(break_record.restored_ms)
        )

        if restored_ms is not None and restored_ms <= stop_ms:
            raise ValueError(
                "AcquisitionBreak restored_ms must be strictly "
                "greater than stop_ms"
            )

        if previous_stop is not None and stop_ms < previous_stop:
            raise ValueError(
                "confirmed_breaks must be ordered by nondecreasing stop_ms"
            )

        normalized.append(
            AcquisitionBreak(
                stop_ms=stop_ms,
                restored_ms=restored_ms,
            )
        )

        previous_stop = stop_ms

    return tuple(normalized)


def authorize_source_history(
    endpoint_ms: np.ndarray,
    source_start_ms: int,
    window_name: str,
    confirmed_breaks: tuple[AcquisitionBreak, ...] = (),
) -> SourceHistoryAuthorizationResult:
    """
    Apply complete endpoint-level K1.3-B source-history authorization.

    Ordering:

    1. Leading source-history maturity:
           G >= ceil(S0,s)_grid + 6W

    2. Confirmed acquisition source breaks.

       For a resolved break:
           B_s = [T_stop, T_restored)

       Recovery is authorized only when:
           G >= ceil(T_restored)_grid + 6W

       Therefore endpoints from T_stop through the endpoint immediately
       preceding the recovery boundary are source-history unauthorized.

       For an unresolved break end:
           all G >= T_stop remain unauthorized.

    This function consumes already-confirmed operational evidence.
    It does not discover, infer, or qualify source breaks.
    """
    leading = authorize_leading_source_history(
        endpoint_ms=endpoint_ms,
        source_start_ms=source_start_ms,
        window_name=window_name,
    )

    breaks = _validate_breaks(tuple(confirmed_breaks))

    endpoints = leading.endpoint_ms

    authorized = leading.authorized.copy()

    reasons = [
        list(reason_tuple)
        for reason_tuple in leading.reason
    ]

    raw_history_ms = leading.raw_history_ms

    for break_record in breaks:
        stop_ms = break_record.stop_ms
        restored_ms = break_record.restored_ms

        if restored_ms is None:
            affected = endpoints >= stop_ms

            for i in np.flatnonzero(affected):
                authorized[i] = False

                if (
                    SOURCE_HISTORY_BREAK_END_UNRESOLVED
                    not in reasons[i]
                ):
                    reasons[i].append(
                        SOURCE_HISTORY_BREAK_END_UNRESOLVED
                    )

            continue

        recovery_endpoint = (
            ceil_to_grid(restored_ms)
            + raw_history_ms
        )

        affected = (
            (endpoints >= stop_ms)
            & (endpoints < recovery_endpoint)
        )

        for i in np.flatnonzero(affected):
            authorized[i] = False

            if SOURCE_HISTORY_BREAK_CONFIRMED not in reasons[i]:
                reasons[i].append(
                    SOURCE_HISTORY_BREAK_CONFIRMED
                )

    return SourceHistoryAuthorizationResult(
        window_name=window_name,
        source_start_ms=leading.source_start_ms,
        source_start_grid_ceiling_ms=(
            leading.source_start_grid_ceiling_ms
        ),
        raw_history_ms=raw_history_ms,
        leading_maturity_endpoint_ms=(
            leading.maturity_endpoint_ms
        ),
        endpoint_ms=_freeze_array(endpoints.copy()),
        authorized=_freeze_array(authorized),
        reason=tuple(
            tuple(reason_list)
            for reason_list in reasons
        ),
        confirmed_breaks=breaks,
    )


LRS4_SOURCE_HISTORY_ELIGIBLE = (
    "LRS4_SOURCE_HISTORY_ELIGIBLE"
)

LRS4_SOURCE_HISTORY_INELIGIBLE = (
    "LRS4_SOURCE_HISTORY_INELIGIBLE"
)


@dataclass(frozen=True)
class WindowSourceHistoryStatus:
    """
    K1.2-A source-history status for one actually-entered Window Evaluation.
    """

    window_name: str
    consumed_endpoint_ms: np.ndarray
    eligible: bool
    provenance_reasons: tuple[str, ...]


@dataclass(frozen=True)
class InstrumentDaySourceHistoryStatus:
    """
    Governing realized-path source-history status for one instrument-day.
    """

    instrument_id: str
    research_day: str
    entered_windows: tuple[str, ...]
    window_statuses: tuple[WindowSourceHistoryStatus, ...]
    eligible: bool
    population_status: str
    provenance_reasons: tuple[str, ...]


def _ordered_unique_int64(
    values: np.ndarray,
) -> np.ndarray:
    """
    Return sorted unique int64 values.

    K1.2-A evaluates duplicate consumed endpoints once within W.
    """
    array = np.asarray(values)

    if array.ndim != 1:
        raise ValueError(
            "consumed endpoint collection must be one-dimensional"
        )

    if array.dtype.kind not in ("i", "u"):
        raise TypeError(
            "consumed endpoint collection must have integer dtype"
        )

    array = array.astype(np.int64, copy=False)

    if array.size == 0:
        return _freeze_array(
            np.array([], dtype=np.int64)
        )

    unique = np.unique(array)

    if np.any(unique % GRID_INTERVAL_MS != 0):
        raise ValueError(
            "consumed endpoint collection contains non-grid-aligned "
            "timestamp(s)"
        )

    return _freeze_array(
        unique.astype(np.int64, copy=False)
    )


def aggregate_instrument_day_source_history(
    *,
    instrument_id: str,
    research_day: str,
    entered_window_consumed_endpoints: dict[str, np.ndarray],
    source_history_by_window: dict[
        str,
        SourceHistoryAuthorizationResult,
    ],
) -> InstrumentDaySourceHistoryStatus:
    """
    Apply frozen K1.2-A endpoint-to-instrument-day aggregation.

    entered_window_consumed_endpoints contains ONLY Window Evaluations
    actually entered by the frozen Instrument Path.

    For each entered W:
        G_used,s,d,W = unique regime endpoints actually consumed by
        inherited LRS-3 observations for which W classification was
        actually evaluated.

    SH(s,d,W) is ELIGIBLE iff every consumed G is source-history
    authorized for that W.

    SH_path(s,d) is the AND across entered Window Evaluations.

    Unentered windows have no governing authority here.

    Supplementary independent per-window clearance diagnostics belong
    outside this governing aggregation.

    An entered window with zero consumed endpoints is rejected because
    the frozen SRC does not define a vacuous-eligibility interpretation.
    """
    if not isinstance(instrument_id, str) or not instrument_id:
        raise ValueError(
            "instrument_id must be a non-empty string"
        )

    if not isinstance(research_day, str) or not research_day:
        raise ValueError(
            "research_day must be a non-empty string"
        )

    if not entered_window_consumed_endpoints:
        raise ValueError(
            "At least one actually-entered Window Evaluation is required"
        )

    entered_windows = tuple(
        entered_window_consumed_endpoints.keys()
    )

    if len(set(entered_windows)) != len(entered_windows):
        raise ValueError(
            "entered Window Evaluations must be unique"
        )

    window_statuses = []

    governing_reasons = []

    for window_name in entered_windows:
        if window_name not in SOURCE_HISTORY_SPECS:
            raise ValueError(
                f"Unsupported frozen source-history window "
                f"{window_name!r}"
            )

        if window_name not in source_history_by_window:
            raise ValueError(
                f"Missing source-history authorization for entered "
                f"window {window_name!r}"
            )

        source_result = source_history_by_window[window_name]

        if not isinstance(
            source_result,
            SourceHistoryAuthorizationResult,
        ):
            raise TypeError(
                "source_history_by_window values must be "
                "SourceHistoryAuthorizationResult"
            )

        if source_result.window_name != window_name:
            raise ValueError(
                "source-history result/window mismatch"
            )

        consumed = _ordered_unique_int64(
            entered_window_consumed_endpoints[window_name]
        )

        if consumed.size == 0:
            raise ValueError(
                f"Entered window {window_name!r} has zero consumed "
                "endpoints; frozen K1.2-A does not authorize vacuous "
                "eligibility"
            )

        endpoint_to_index = {
            int(endpoint): index
            for index, endpoint
            in enumerate(source_result.endpoint_ms)
        }

        missing = [
            int(endpoint)
            for endpoint in consumed
            if int(endpoint) not in endpoint_to_index
        ]

        if missing:
            raise ValueError(
                f"Consumed endpoint(s) absent from source-history "
                f"authorization for window {window_name!r}: {missing}"
            )

        eligible = True
        window_reasons = []

        for endpoint in consumed:
            index = endpoint_to_index[int(endpoint)]

            if not bool(source_result.authorized[index]):
                eligible = False

                for reason in source_result.reason[index]:
                    if reason not in window_reasons:
                        window_reasons.append(reason)

                    if reason not in governing_reasons:
                        governing_reasons.append(reason)

        window_statuses.append(
            WindowSourceHistoryStatus(
                window_name=window_name,
                consumed_endpoint_ms=_freeze_array(
                    consumed.copy()
                ),
                eligible=eligible,
                provenance_reasons=tuple(window_reasons),
            )
        )

    path_eligible = all(
        status.eligible
        for status in window_statuses
    )

    population_status = (
        LRS4_SOURCE_HISTORY_ELIGIBLE
        if path_eligible
        else LRS4_SOURCE_HISTORY_INELIGIBLE
    )

    return InstrumentDaySourceHistoryStatus(
        instrument_id=instrument_id,
        research_day=research_day,
        entered_windows=entered_windows,
        window_statuses=tuple(window_statuses),
        eligible=path_eligible,
        population_status=population_status,
        provenance_reasons=tuple(governing_reasons),
    )
