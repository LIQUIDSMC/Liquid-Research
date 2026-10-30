"""Focused G01 tests for Experiment-v2 D2 boundary construction."""
from dataclasses import replace

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.contracts import (
    WindowD0Terminal,
    WindowIntegrityFailure,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d1_d0 import (
    D1Constructed,
    D1D0Result,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d2 import (
    construct_d2,
)

DELTA = 300_000


def _input(times, ids=None):
    times = np.asarray(times, dtype=np.int64)
    if ids is None:
        ids = np.arange(len(times), dtype=np.int64)
    d1 = D1Constructed(
        window="4h",
        observation_time_ms=times,
        observation_trade_id=np.asarray(ids, dtype=np.int64),
        observation_day=("day",) * len(times),
        day_statuses=(),
    )
    return D1D0Result(
        window="4h",
        day_statuses=(),
        d1=d1,
        terminal=None,
    )


def test_inclusive_continuous_grid():
    result = construct_d2(_input([1, 3 * DELTA + 1]))
    assert result.terminal is None
    assert result.d2.g_first == 0
    assert result.d2.g_last == 3 * DELTA
    assert result.d2.endpoint_ms.tolist() == [
        0, DELTA, 2 * DELTA, 3 * DELTA
    ]
    assert not result.d2.endpoint_ms.flags.writeable


def test_exact_grid_timestamp_uses_predecessor():
    result = construct_d2(_input([DELTA]))
    assert result.d2.endpoint_ms.tolist() == [0]


def test_single_cell_is_valid():
    result = construct_d2(_input([1, 2]))
    assert result.d2.endpoint_ms.tolist() == [0]


def test_d1_order_does_not_change_extrema():
    result = construct_d2(_input([3 * DELTA + 1, 1]))
    assert result.d2.endpoint_ms.tolist() == [
        0, DELTA, 2 * DELTA, 3 * DELTA
    ]


def test_empty_population_fails_closed():
    result = construct_d2(_input([]))
    assert isinstance(result.terminal, WindowIntegrityFailure)
    assert result.d2 is None


def test_d0_terminal_preserved():
    terminal = WindowD0Terminal(
        tag="D0_TERMINAL",
        window="4h",
        reason="NO_TARGET_OBSERVATION_POPULATION",
        provenance="C2",
    )
    result = construct_d2(
        D1D0Result(
            window="4h",
            day_statuses=(),
            d1=None,
            terminal=terminal,
        )
    )
    assert result.d2 is None
    assert result.terminal is terminal


def test_missing_prerequisite_fails_closed():
    result = construct_d2(
        D1D0Result(
            window="4h",
            day_statuses=(),
            d1=None,
            terminal=None,
        )
    )
    assert isinstance(result.terminal, WindowIntegrityFailure)


def test_mismatched_window_fails_closed():
    source = _input([1])
    result = construct_d2(replace(source, window="1h"))
    assert isinstance(result.terminal, WindowIntegrityFailure)


def test_wrong_timestamp_dtype_fails_closed():
    source = _input([1])
    malformed = replace(
        source.d1,
        observation_time_ms=np.array([1.0]),
    )
    result = construct_d2(replace(source, d1=malformed))
    assert isinstance(result.terminal, WindowIntegrityFailure)


def test_duplicate_identity_fails_closed():
    result = construct_d2(_input([1, 1], ids=[7, 7]))
    assert isinstance(result.terminal, WindowIntegrityFailure)


def test_unrepresentable_predecessor_fails_closed():
    result = construct_d2(_input([np.iinfo(np.int64).min]))
    assert isinstance(result.terminal, WindowIntegrityFailure)


def test_unrepresentable_upper_bound_fails_closed():
    result = construct_d2(_input([np.iinfo(np.int64).max]))
    assert isinstance(result.terminal, WindowIntegrityFailure)


def test_upstream_integrity_failure_preserved():
    terminal = WindowIntegrityFailure(
        tag="INTEGRITY_FAILURE",
        window="4h",
        invariant="SOURCE_HISTORY_EVIDENCE",
        provenance="upstream validation failed",
    )
    result = construct_d2(
        D1D0Result(
            window="4h",
            day_statuses=(),
            d1=None,
            terminal=terminal,
        )
    )
    assert result.d2 is None
    assert result.terminal is terminal


def test_oversized_endpoint_domain_fails_before_allocation():
    count = (64 * 1024 * 1024 // np.dtype("int64").itemsize) + 1
    result = construct_d2(_input([1, (count - 1) * DELTA + 1]))
    assert result.d2 is None
    assert isinstance(result.terminal, WindowIntegrityFailure)
    assert result.terminal.provenance == "D2 endpoint allocation budget exceeded"
