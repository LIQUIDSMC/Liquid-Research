"""Synthetic regression tests for Experiment-v2 D1/D0 construction."""

from dataclasses import replace

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WindowIntegrityFailure,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d1_d0 import (
    D1DayInput,
    construct_d1_d0,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
    authorize_source_history,
)

STEP = 300_000
MATURE = 86_400_000
DAY = "SYNTHETIC_DAY"
WINDOW = "4h"


def _day(times, ids=None, eligible=None):
    times = np.asarray(times, dtype=np.int64)
    if ids is None:
        ids = np.arange(len(times), dtype=np.int64)
    if eligible is None:
        eligible = np.ones(len(times), dtype=np.bool_)
    return D1DayInput(
        research_day=DAY,
        sample_trade_time=times,
        sample_trade_id=np.asarray(ids, dtype=np.int64),
        common_eligible=np.asarray(eligible, dtype=np.bool_),
    )


def _authorization(endpoints, source_start=0):
    return authorize_source_history(
        endpoint_ms=np.asarray(endpoints, dtype=np.int64),
        source_start_ms=source_start,
        window_name=WINDOW,
    )


def _construct(days, coverage, authorization):
    return construct_d1_d0(
        window=WINDOW,
        days=days,
        authorization_by_day={DAY: authorization},
        available_endpoint_by_day={
            DAY: np.asarray(coverage, dtype=np.int64)
        },
    )


def _assert_failure(result, invariant):
    assert isinstance(result.terminal, WindowIntegrityFailure)
    assert result.terminal.invariant == invariant
    assert result.d1 is None


def test_authorized_d1_construction():
    result = _construct(
        (_day([MATURE + 1]),),
        [MATURE],
        _authorization([MATURE]),
    )
    assert result.terminal is None
    assert result.d1.observation_count == 1
    assert not result.d1.observation_time_ms.flags.writeable


def test_exact_grid_uses_strict_predecessor():
    result = _construct(
        (_day([MATURE + STEP]),),
        [MATURE],
        _authorization([MATURE]),
    )
    assert result.terminal is None
    assert result.day_statuses[0].candidate_endpoints == (MATURE,)


def test_d0_c1_insufficient_source_history():
    result = _construct(
        (_day([STEP + 1]),),
        [STEP],
        _authorization([STEP]),
    )
    assert result.d1 is None
    assert result.terminal.tag == "D0_TERMINAL"
    assert result.terminal.reason == "NO_TARGET_OBSERVATION_POPULATION"
    assert result.terminal.provenance == "C1"


def test_d0_c2_empty_candidate_population():
    result = _construct(
        (_day([MATURE + 1], eligible=[False]),),
        [],
        _authorization([]),
    )
    assert result.d1 is None
    assert result.terminal.tag == "D0_TERMINAL"
    assert result.terminal.reason == "NO_TARGET_OBSERVATION_POPULATION"
    assert result.terminal.provenance == "C2"


def test_duplicate_canonical_identity_fails():
    result = _construct(
        (_day([MATURE + 1, MATURE + 1], ids=[7, 7]),),
        [MATURE],
        _authorization([MATURE]),
    )
    _assert_failure(result, "I06_I07")


def test_unsorted_observations_fail():
    result = _construct(
        (_day([MATURE + 2, MATURE + 1], ids=[1, 2]),),
        [MATURE],
        _authorization([MATURE]),
    )
    _assert_failure(result, "I06_I07")


def test_missing_strict_predecessor_fails():
    result = _construct(
        (_day([MATURE + 1]),),
        [],
        _authorization([MATURE]),
    )
    _assert_failure(result, "STRICT_C10")
    assert result.terminal.tag == "INTEGRITY_FAILURE"
    assert result.terminal.provenance == (
        f"Missing required predecessor: {DAY}"
    )


def test_inconsistent_authorization_fails():
    authorization = _authorization([MATURE])
    authorization = replace(
        authorization,
        authorized=np.array([False], dtype=np.bool_),
    )
    result = _construct(
        (_day([MATURE + 1]),),
        [MATURE],
        authorization,
    )
    _assert_failure(result, "SOURCE_HISTORY_EVIDENCE")


def test_duplicate_research_day_fails():
    result = _construct(
        (_day([MATURE + 1]), _day([MATURE + 2])),
        [MATURE],
        _authorization([MATURE]),
    )
    _assert_failure(result, "I06_I07")


def test_duplicate_candidate_endpoints_are_deduplicated():
    result = _construct(
        (_day([MATURE + 1, MATURE + 2], ids=[11, 12]),),
        [MATURE],
        _authorization([MATURE]),
    )
    assert result.terminal is None
    assert result.d1.observation_count == 2
    assert result.day_statuses[0].candidate_count == 2
    assert result.day_statuses[0].candidate_endpoints == (MATURE,)
    assert result.day_statuses[0].source_history_eligible is True


def test_one_unauthorized_endpoint_excludes_entire_day():
    endpoints = [MATURE - STEP, MATURE]
    result = _construct(
        (_day([MATURE - STEP + 1, MATURE + 1]),),
        endpoints,
        _authorization(endpoints),
    )
    assert result.d1 is None
    assert result.terminal.tag == "D0_TERMINAL"
    assert result.terminal.reason == "NO_TARGET_OBSERVATION_POPULATION"
    assert result.terminal.provenance == "C1"
    assert result.day_statuses[0].candidate_count == 2
    assert result.day_statuses[0].source_history_eligible is False


def test_multiple_days_retain_only_qualified_day():
    first = _day([MATURE + 1])
    second = replace(
        _day([STEP + 1]),
        research_day="SECOND_DAY",
    )

    result = construct_d1_d0(
        window=WINDOW,
        days=(first, second),
        authorization_by_day={
            DAY: _authorization([MATURE]),
            "SECOND_DAY": _authorization([STEP]),
        },
        available_endpoint_by_day={
            DAY: np.array([MATURE], dtype=np.int64),
            "SECOND_DAY": np.array([STEP], dtype=np.int64),
        },
    )

    assert result.terminal is None
    assert result.d1.observation_count == 1
    assert result.d1.observation_day == (DAY,)
    assert tuple(
        status.source_history_eligible
        for status in result.day_statuses
    ) == (True, False)


def test_empty_candidate_day_has_undefined_source_history():
    result = _construct(
        (_day([MATURE + 1], eligible=[False]),),
        [],
        _authorization([]),
    )
    assert result.terminal.tag == "D0_TERMINAL"
    assert result.terminal.reason == "NO_TARGET_OBSERVATION_POPULATION"
    assert result.terminal.provenance == "C2"
    assert result.day_statuses[0].candidate_count == 0
    assert result.day_statuses[0].source_history_eligible is None
    assert result.day_statuses[0].candidate_endpoints == ()


def test_d0_c1_c2_share_reason_but_preserve_provenance():
    c1 = _construct(
        (_day([STEP + 1]),),
        [STEP],
        _authorization([STEP]),
    )
    c2 = _construct(
        (_day([MATURE + 1], eligible=[False]),),
        [],
        _authorization([]),
    )

    for result in (c1, c2):
        assert result.d1 is None
        assert result.terminal.tag == "D0_TERMINAL"
        assert result.terminal.reason == "NO_TARGET_OBSERVATION_POPULATION"

    assert c1.terminal.provenance == "C1"
    assert c2.terminal.provenance == "C2"


def test_physically_empty_candidate_input():
    result = _construct(
        (_day([]),),
        [],
        _authorization([]),
    )

    assert result.d1 is None
    assert result.terminal.tag == "D0_TERMINAL"
    assert result.terminal.reason == "NO_TARGET_OBSERVATION_POPULATION"
    assert result.terminal.provenance == "C2"
    assert result.day_statuses[0].candidate_count == 0
    assert result.day_statuses[0].candidate_endpoints == ()
    assert result.day_statuses[0].source_history_eligible is None
