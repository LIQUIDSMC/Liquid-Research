"""Synthetic regression tests for Experiment-v2 Gate-2 numeric diagnostics."""

from dataclasses import replace

import numpy as np
import pytest

from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d1_d0 import (
    D1Constructed,
    D1DayStatus,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.d3 import (
    D3Constructed,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.experiment_v2.gate2_numeric import (
    evaluate_observation_diagnostics,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS as STEP,
)


def make_case(states, days=None):
    n = len(states)
    if days is None:
        days = ["day-1"] * n

    endpoints = np.arange(n, dtype=np.int64) * STEP
    unique_days = list(dict.fromkeys(days))

    statuses = tuple(
        D1DayStatus(
            research_day=day,
            candidate_count=days.count(day),
            candidate_endpoints=tuple(
                int(endpoints[i])
                for i in range(n)
                if days[i] == day
            ),
            source_history_eligible=True,
            reasons=(),
        )
        for day in unique_days
    )

    d1 = D1Constructed(
        window="4h",
        observation_time_ms=endpoints + 1,
        observation_trade_id=np.arange(n, dtype=np.int64),
        observation_day=tuple(days),
        day_statuses=statuses,
    )

    admissible = np.array(
        [state != "INVALID" for state in states], dtype=np.bool_
    )

    d3 = D3Constructed(
        window="4h",
        endpoint_ms=endpoints,
        admissible=admissible,
        state=tuple(states),
        reason=tuple(
            () if valid else ("SYNTHETIC_INVALID",)
            for valid in admissible
        ),
    )
    return d1, d3


def evaluate(states, days=None):
    return evaluate_observation_diagnostics(*make_case(states, days))


def test_g1_exact_twenty_percent_passes():
    result = evaluate(["HIGH"] * 4 + ["INVALID"])
    assert result.ineligibility_rate == 0.20
    assert "EXCESSIVE_REGIME_INELIGIBILITY" not in result.reasons


def test_g1_above_twenty_percent_fails():
    result = evaluate(["HIGH"] * 3 + ["INVALID"] * 2)
    assert "EXCESSIVE_REGIME_INELIGIBILITY" in result.reasons


def test_g4_zero_eligible_is_not_applicable():
    result = evaluate(["INVALID"] * 5)
    assert result.n_eligible == 0
    assert result.p_min is None
    assert result.minority_status == "NOT_APPLICABLE_ZERO_ELIGIBLE_OBSERVATIONS"
    assert "SEVERE_REGIME_IMBALANCE" not in result.reasons


def test_g2_zero_ineligibility_is_not_applicable():
    result = evaluate(["HIGH", "LOW"] * 5)
    assert result.concentration_status == (
        "NOT_APPLICABLE_ZERO_INELIGIBILITY",
    )
    assert result.concentration is None


def test_g2_retains_both_activation_failures():
    result = evaluate(["HIGH"] * 4 + ["INVALID"])
    assert set(result.concentration_status) == {
        "NOT_EVALUATED_INSUFFICIENT_DAY_SUPPORT",
        "NOT_EVALUATED_INSUFFICIENT_INELIGIBILITY_COUNT",
    }


def test_g4_exact_ten_percent_passes():
    result = evaluate(["HIGH"] * 9 + ["LOW"])
    assert result.p_min == 0.10
    assert result.minority_status == "PASS"


def test_interleaved_days_reconcile():
    result = evaluate(
        ["HIGH", "LOW", "HIGH", "LOW"],
        days=["day-a", "day-b", "day-a", "day-b"],
    )
    assert result.d_available == 2
    assert result.n_high == 2
    assert result.n_low == 2


def test_missing_d1_day_exposure_fails_closed():
    d1, d3 = make_case(["HIGH", "LOW"])
    bad_status = replace(d1.day_statuses[0], candidate_count=3)
    bad_d1 = replace(d1, day_statuses=(bad_status,))
    with pytest.raises(ValueError, match="reconciliation"):
        evaluate_observation_diagnostics(bad_d1, d3)


def test_missing_d1_candidate_endpoint_fails_closed():
    d1, d3 = make_case(["HIGH", "LOW"])
    bad_status = replace(
        d1.day_statuses[0],
        candidate_endpoints=(0,),
    )
    bad_d1 = replace(d1, day_statuses=(bad_status,))
    with pytest.raises(ValueError, match="endpoint reconciliation"):
        evaluate_observation_diagnostics(bad_d1, d3)
