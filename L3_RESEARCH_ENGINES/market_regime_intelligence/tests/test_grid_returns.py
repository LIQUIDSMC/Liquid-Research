from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.data.trade_loader import (
    TradeIntervalResult,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    ENDPOINT_NO_ELIGIBLE_TRADE,
    ENDPOINT_STALE_PRICE,
    ENDPOINT_VALID,
    GRID_INTERVAL_MS,
    RETURN_CURRENT_ENDPOINT_INVALID,
    RETURN_NO_PRECEDING_ENDPOINT,
    RETURN_PREVIOUS_ENDPOINT_INVALID,
    RETURN_VALID,
    build_grid_returns,
)


def _trades(rows):
    """
    rows:
        iterable of (trade_time, trade_id, price)

    Input order must already satisfy deterministic
    (trade_time, trade_id) ordering unless a test intentionally violates it.
    """
    rows = list(rows)

    return TradeIntervalResult(
        instrument_id="BTC-USD",
        start_ms=0,
        end_ms=10**15,
        trade_time=np.asarray(
            [row[0] for row in rows],
            dtype=np.int64,
        ),
        trade_id=np.asarray(
            [row[1] for row in rows],
            dtype=np.int64,
        ),
        price=np.asarray(
            [row[2] for row in rows],
            dtype=np.float64,
        ),
        row_count=len(rows),
    )


def test_trade_exactly_at_grid_endpoint_is_eligible():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g, 100, 101.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g,
        g,
    )

    assert result.endpoint_valid.tolist() == [True]
    assert result.endpoint_reason == (ENDPOINT_VALID,)
    assert result.source_trade_time.tolist() == [g]
    assert result.source_trade_id.tolist() == [100]
    assert result.trade_age_ms.tolist() == [0.0]
    assert result.price.tolist() == [101.0]

    print("PASS: trade exactly at G is causally eligible")


def test_trade_exactly_five_minutes_old_is_valid():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g - GRID_INTERVAL_MS, 100, 101.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g,
        g,
    )

    assert result.endpoint_valid.tolist() == [True]
    assert result.endpoint_reason == (ENDPOINT_VALID,)
    assert result.trade_age_ms.tolist() == [float(GRID_INTERVAL_MS)]
    assert result.price.tolist() == [101.0]

    print("PASS: trade exactly 5m old remains endpoint-valid")


def test_trade_older_than_five_minutes_is_stale():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g - GRID_INTERVAL_MS - 1, 100, 101.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g,
        g,
    )

    assert result.endpoint_valid.tolist() == [False]
    assert result.endpoint_reason == (ENDPOINT_STALE_PRICE,)
    assert np.isnan(result.price[0])
    assert result.source_trade_time.tolist() == [
        g - GRID_INTERVAL_MS - 1
    ]
    assert result.trade_age_ms.tolist() == [
        float(GRID_INTERVAL_MS + 1)
    ]

    print("PASS: trade older than 5m by 1ms is stale")


def test_no_eligible_trade_before_grid_endpoint():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g + 1, 100, 101.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g,
        g,
    )

    assert result.endpoint_valid.tolist() == [False]
    assert result.endpoint_reason == (ENDPOINT_NO_ELIGIBLE_TRADE,)
    assert np.isnan(result.price[0])
    assert result.source_trade_time.tolist() == [-1]
    assert result.source_trade_id.tolist() == [-1]
    assert np.isnan(result.trade_age_ms[0])

    print("PASS: no trade at or before G produces explicit invalid endpoint")


def test_same_timestamp_uses_highest_trade_id():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g, 10, 100.0),
            (g, 20, 101.0),
            (g, 30, 102.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g,
        g,
    )

    assert result.endpoint_valid.tolist() == [True]
    assert result.source_trade_id.tolist() == [30]
    assert result.price.tolist() == [102.0]

    print(
        "PASS: same-timestamp previous-tick selection uses highest trade_id"
    )


def test_first_endpoint_return_is_explicitly_unavailable():
    g0 = 10 * GRID_INTERVAL_MS
    g1 = g0 + GRID_INTERVAL_MS

    trades = _trades(
        [
            (g0, 10, 100.0),
            (g1, 20, 110.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g0,
        g1,
    )

    assert result.return_valid.tolist() == [False, True]
    assert result.return_reason == (
        RETURN_NO_PRECEDING_ENDPOINT,
        RETURN_VALID,
    )
    assert np.isnan(result.log_return[0])
    assert np.isclose(
        result.log_return[1],
        np.log(110.0 / 100.0),
    )

    print(
        "PASS: first returned endpoint has no synthetic preceding return"
    )


def test_invalid_previous_endpoint_prevents_return_bridge():
    g0 = 10 * GRID_INTERVAL_MS
    g1 = g0 + GRID_INTERVAL_MS
    g2 = g1 + GRID_INTERVAL_MS

    # Trade at g0 is valid at g0, but becomes >5m old at g1.
    # Fresh trade at g2 makes g2 valid again.
    trades = _trades(
        [
            (g0, 10, 100.0),
            (g2, 20, 110.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g0,
        g2,
    )

    assert result.endpoint_valid.tolist() == [
        True,
        True,
        True,
    ]

    # At g1 the g0 trade is exactly 5m old, so it is still valid.
    assert result.return_valid.tolist() == [
        False,
        True,
        True,
    ]

    assert np.isclose(result.log_return[1], 0.0)
    assert np.isclose(
        result.log_return[2],
        np.log(110.0 / 100.0),
    )

    print(
        "PASS: exactly-5m endpoint continuity remains valid as frozen"
    )


def test_invalid_gap_breaks_return_continuity():
    g0 = 10 * GRID_INTERVAL_MS
    g1 = g0 + GRID_INTERVAL_MS
    g2 = g1 + GRID_INTERVAL_MS
    g3 = g2 + GRID_INTERVAL_MS

    trades = _trades(
        [
            (g0, 10, 100.0),
            (g3, 20, 110.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g0,
        g3,
    )

    # g0 valid
    # g1 valid: source is exactly 5m old
    # g2 invalid: source is 10m old
    # g3 valid: fresh trade exactly at g3
    assert result.endpoint_valid.tolist() == [
        True,
        True,
        False,
        True,
    ]

    assert result.endpoint_reason == (
        ENDPOINT_VALID,
        ENDPOINT_VALID,
        ENDPOINT_STALE_PRICE,
        ENDPOINT_VALID,
    )

    assert result.return_valid.tolist() == [
        False,
        True,
        False,
        False,
    ]

    assert result.return_reason == (
        RETURN_NO_PRECEDING_ENDPOINT,
        RETURN_VALID,
        RETURN_CURRENT_ENDPOINT_INVALID,
        RETURN_PREVIOUS_ENDPOINT_INVALID,
    )

    assert np.isnan(result.log_return[2])
    assert np.isnan(result.log_return[3])

    print("PASS: invalid grid endpoint breaks return continuity; no bridging")


def test_current_invalid_endpoint_has_explicit_return_reason():
    g0 = 10 * GRID_INTERVAL_MS
    g1 = g0 + GRID_INTERVAL_MS
    g2 = g1 + GRID_INTERVAL_MS

    trades = _trades(
        [
            (g0, 10, 100.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g0,
        g2,
    )

    assert result.endpoint_valid.tolist() == [
        True,
        True,
        False,
    ]

    assert result.return_reason == (
        RETURN_NO_PRECEDING_ENDPOINT,
        RETURN_VALID,
        RETURN_CURRENT_ENDPOINT_INVALID,
    )

    print("PASS: invalid current endpoint has explicit return failure reason")


def test_grid_alignment_is_enforced():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades([])

    try:
        build_grid_returns(
            trades,
            g + 1,
            g + GRID_INTERVAL_MS,
        )
        raise AssertionError(
            "Expected nonaligned first grid endpoint to fail"
        )
    except ValueError as exc:
        assert "not aligned" in str(exc)

    try:
        build_grid_returns(
            trades,
            g,
            g + GRID_INTERVAL_MS + 1,
        )
        raise AssertionError(
            "Expected nonaligned last grid endpoint to fail"
        )
    except ValueError as exc:
        assert "not aligned" in str(exc)

    print("PASS: grid endpoints must lie exactly on frozen 5m UTC grid")


def test_reversed_grid_interval_fails():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades([])

    try:
        build_grid_returns(
            trades,
            g + GRID_INTERVAL_MS,
            g,
        )
        raise AssertionError(
            "Expected reversed grid interval to fail"
        )
    except ValueError as exc:
        assert "greater than or equal" in str(exc)

    print("PASS: reversed grid interval fails closed")


def test_unsorted_trade_input_fails_closed():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g, 20, 101.0),
            (g, 10, 100.0),
        ]
    )

    try:
        build_grid_returns(
            trades,
            g,
            g,
        )
        raise AssertionError(
            "Expected unsorted trade input to fail"
        )
    except ValueError as exc:
        assert "not sorted" in str(exc)

    print("PASS: grid constructor rejects unsorted trade input")


def test_result_object_and_arrays_are_immutable():
    g = 10 * GRID_INTERVAL_MS

    trades = _trades(
        [
            (g, 10, 100.0),
        ]
    )

    result = build_grid_returns(
        trades,
        g,
        g,
    )

    try:
        result.grid_interval_ms = 1
        raise AssertionError(
            "Expected frozen GridReturnResult mutation to fail"
        )
    except FrozenInstanceError:
        pass

    try:
        result.price[0] = 999.0
        raise AssertionError(
            "Expected read-only result array mutation to fail"
        )
    except ValueError:
        pass

    assert result.price.flags.writeable is False
    assert result.endpoint_ms.flags.writeable is False
    assert result.endpoint_valid.flags.writeable is False
    assert result.log_return.flags.writeable is False
    assert result.return_valid.flags.writeable is False

    print("PASS: grid-return evidence object and arrays are immutable")


if __name__ == "__main__":
    test_trade_exactly_at_grid_endpoint_is_eligible()
    test_trade_exactly_five_minutes_old_is_valid()
    test_trade_older_than_five_minutes_is_stale()
    test_no_eligible_trade_before_grid_endpoint()
    test_same_timestamp_uses_highest_trade_id()
    test_first_endpoint_return_is_explicitly_unavailable()
    test_invalid_previous_endpoint_prevents_return_bridge()
    test_invalid_gap_breaks_return_continuity()
    test_current_invalid_endpoint_has_explicit_return_reason()
    test_grid_alignment_is_enforced()
    test_reversed_grid_interval_fails()
    test_unsorted_trade_input_fails_closed()
    test_result_object_and_arrays_are_immutable()

    print("\nALL LRS-4 GRID/RETURN STRUCTURAL TESTS PASSED")
