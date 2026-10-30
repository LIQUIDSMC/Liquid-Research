"""Focused Experiment-v2 D3 admissibility tests."""

from dataclasses import replace

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d2 import (
    D2Constructed,
    D2Result,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d3 import (
    construct_d3,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
    SourceHistoryAuthorizationResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.threshold_learning import (
    ThresholdLearningResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.regime_state import (
    RegimeStateResult,
)


def _inputs():
    endpoints = np.array([0, 300000, 600000], dtype=np.int64)
    d2 = D2Result(
        window="4h",
        d2=D2Constructed("4h", 0, 600000, endpoints),
        terminal=None,
    )
    source = SourceHistoryAuthorizationResult(
        window_name="4h",
        source_start_ms=0,
        source_start_grid_ceiling_ms=0,
        raw_history_ms=0,
        leading_maturity_endpoint_ms=0,
        endpoint_ms=endpoints.copy(),
        authorized=np.array([True, False, True]),
        reason=((), ("SOURCE_BREAK",), ()),
        confirmed_breaks=(),
    )
    regime = RegimeStateResult(
        window_name="4h",
        endpoint_ms=endpoints.copy(),
        rvol=np.array([2.0, 3.0, np.nan]),
        threshold=np.array([1.0, np.nan, 1.0]),
        rvol_valid=np.array([True, True, False]),
        threshold_valid=np.array([True, False, True]),
        state_valid=np.array([True, False, False]),
        state=("HIGH", "INVALID", "INVALID"),
    )
    threshold = ThresholdLearningResult(
        window_name="4h",
        learning_history_ms=20 * 60 * 60 * 1000,
        nominal_members=240,
        min_valid_members=180,
        max_allowed_contiguous_invalid_members=60,
        endpoint_ms=endpoints.copy(),
        source_history_authorized=source.authorized.copy(),
        learning_history_complete=np.array([True, True, True]),
        valid_rvol_count=np.array([180, 0, 180]),
        invalid_rvol_count=np.array([60, 0, 60]),
        max_contiguous_invalid_rvol=np.array([1, -1, 1]),
        aggregate_availability_pass=np.array([True, False, True]),
        contiguous_concentration_pass=np.array([True, False, True]),
        threshold=regime.threshold.copy(),
        threshold_valid=regime.threshold_valid.copy(),
    )
    return d2, source, regime, threshold


def test_source_authorization_precedes_mechanical_state():
    result = construct_d3(*_inputs())
    assert result.terminal is None
    assert result.d3.admissible.tolist() == [True, False, False]
    assert result.d3.state == ("HIGH", "INVALID", "INVALID")
    assert "SOURCE_HISTORY_UNAUTHORIZED" in result.d3.reason[1]
    assert "RVOL_INVALID" in result.d3.reason[2]


def test_outputs_are_immutable():
    result = construct_d3(*_inputs())
    assert not result.d3.endpoint_ms.flags.writeable
    assert not result.d3.admissible.flags.writeable


def test_missing_endpoint_fails_closed():
    d2, source, regime, threshold = _inputs()
    source = replace(source, endpoint_ms=source.endpoint_ms[:-1])
    result = construct_d3(d2, source, regime, threshold)
    assert result.d3 is None
    assert result.terminal.tag == "INTEGRITY_FAILURE"


def test_window_mismatch_fails_closed():
    d2, source, regime, threshold = _inputs()
    result = construct_d3(d2, replace(source, window_name="1h"), regime, threshold)
    assert result.d3 is None
    assert result.terminal.tag == "INTEGRITY_FAILURE"


def test_one_cell_domain():
    d2, source, regime, threshold = _inputs()
    d2 = replace(
        d2,
        d2=D2Constructed("4h", 0, 0, d2.d2.endpoint_ms[:1]),
    )
    source = replace(
        source,
        endpoint_ms=source.endpoint_ms[:1],
        authorized=source.authorized[:1],
        reason=source.reason[:1],
    )
    regime = replace(
        regime,
        endpoint_ms=regime.endpoint_ms[:1],
        rvol=regime.rvol[:1],
        threshold=regime.threshold[:1],
        rvol_valid=regime.rvol_valid[:1],
        threshold_valid=regime.threshold_valid[:1],
        state_valid=regime.state_valid[:1],
        state=regime.state[:1],
    )
    threshold = replace(
        threshold,
        endpoint_ms=threshold.endpoint_ms[:1],
        source_history_authorized=threshold.source_history_authorized[:1],
        learning_history_complete=threshold.learning_history_complete[:1],
        valid_rvol_count=threshold.valid_rvol_count[:1],
        invalid_rvol_count=threshold.invalid_rvol_count[:1],
        max_contiguous_invalid_rvol=threshold.max_contiguous_invalid_rvol[:1],
        aggregate_availability_pass=threshold.aggregate_availability_pass[:1],
        contiguous_concentration_pass=threshold.contiguous_concentration_pass[:1],
        threshold=threshold.threshold[:1],
        threshold_valid=threshold.threshold_valid[:1],
    )
    result = construct_d3(d2, source, regime, threshold)
    assert result.terminal is None
    assert result.d3.admissible.tolist() == [True]


def test_threshold_authorization_mismatch_fails_closed():
    d2, source, regime, threshold = _inputs()
    bad = replace(
        threshold,
        source_history_authorized=np.array([True, True, True]),
    )
    result = construct_d3(d2, source, regime, bad)
    assert result.d3 is None
    assert result.terminal.invariant == "I15"


def test_unauthorized_valid_threshold_fails_closed():
    d2, source, regime, threshold = _inputs()
    bad = replace(
        threshold,
        threshold_valid=np.array([True, True, True]),
    )
    result = construct_d3(d2, source, regime, bad)
    assert result.d3 is None
    assert result.terminal.invariant == "I15"


def test_inconsistent_regime_validity_fails_closed():
    d2, source, regime, threshold = _inputs()
    bad = replace(
        regime,
        state_valid=np.array([True, True, False]),
    )
    result = construct_d3(d2, source, bad, threshold)
    assert result.d3 is None
    assert result.terminal.invariant == "I15"


def test_incorrect_high_low_state_fails_closed():
    d2, source, regime, threshold = _inputs()
    bad = replace(regime, state=("LOW", "INVALID", "INVALID"))
    result = construct_d3(d2, source, bad, threshold)
    assert result.d3 is None
    assert result.terminal.invariant == "I15"


def test_malformed_validity_mask_fails_closed():
    d2, source, regime, threshold = _inputs()
    bad = replace(regime, rvol_valid=np.array([True]))
    result = construct_d3(d2, source, bad, threshold)
    assert result.d3 is None
    assert result.terminal.invariant == "I15"
