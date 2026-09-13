"""
LRS-4 Experiment v1 — structural lock tests for leading source history.
"""

from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
    SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,
    SOURCE_HISTORY_SPECS,
    authorize_leading_source_history,
    ceil_to_grid,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)


HOUR_MS = 60 * 60 * 1000


def test_frozen_window_specific_raw_history_is_exact():
    assert SOURCE_HISTORY_SPECS["1h"].raw_history_ms == 6 * HOUR_MS
    assert SOURCE_HISTORY_SPECS["4h"].raw_history_ms == 24 * HOUR_MS
    assert SOURCE_HISTORY_SPECS["24h"].raw_history_ms == 144 * HOUR_MS

    print("PASS: frozen 6W raw-history requirements are window-specific")


def test_exact_grid_source_start_is_unchanged():
    source_start = 12 * GRID_INTERVAL_MS

    assert ceil_to_grid(source_start) == source_start

    print("PASS: exact-grid S0 remains unchanged")


def test_off_grid_source_start_ceilings_forward():
    source_start = (
        12 * GRID_INTERVAL_MS
        + 1
    )

    expected = 13 * GRID_INTERVAL_MS

    assert ceil_to_grid(source_start) == expected

    print("PASS: off-grid S0 ceilings to next frozen 5m endpoint")


def test_maturity_boundary_equality_passes():
    source_start = 0
    maturity = 6 * HOUR_MS

    endpoints = np.array(
        [
            maturity - GRID_INTERVAL_MS,
            maturity,
            maturity + GRID_INTERVAL_MS,
        ],
        dtype=np.int64,
    )

    result = authorize_leading_source_history(
        endpoints,
        source_start,
        "1h",
    )

    assert result.authorized.tolist() == [
        False,
        True,
        True,
    ]

    assert result.reason[0] == (
        SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,
    )
    assert result.reason[1] == ()
    assert result.reason[2] == ()

    print("PASS: G == G_SH-mature is authorized")


def test_off_grid_source_start_affects_maturity_exactly():
    source_start = 1

    source_ceiling = GRID_INTERVAL_MS
    maturity = source_ceiling + 6 * HOUR_MS

    endpoints = np.array(
        [
            maturity - GRID_INTERVAL_MS,
            maturity,
        ],
        dtype=np.int64,
    )

    result = authorize_leading_source_history(
        endpoints,
        source_start,
        "1h",
    )

    assert result.source_start_grid_ceiling_ms == source_ceiling
    assert result.maturity_endpoint_ms == maturity
    assert result.authorized.tolist() == [
        False,
        True,
    ]

    print("PASS: off-grid S0 ceiling propagates exactly into maturity floor")


def test_each_window_uses_its_own_maturity_floor():
    source_start = 0

    cases = {
        "1h": 6 * HOUR_MS,
        "4h": 24 * HOUR_MS,
        "24h": 144 * HOUR_MS,
    }

    for window_name, maturity in cases.items():
        endpoints = np.array(
            [
                maturity - GRID_INTERVAL_MS,
                maturity,
            ],
            dtype=np.int64,
        )

        result = authorize_leading_source_history(
            endpoints,
            source_start,
            window_name,
        )

        assert result.maturity_endpoint_ms == maturity
        assert result.authorized.tolist() == [
            False,
            True,
        ]

    print("PASS: 1h/4h/24h maturity floors remain distinct")


def test_1h_does_not_require_universal_144h_history():
    source_start = 0

    endpoint = np.array(
        [6 * HOUR_MS],
        dtype=np.int64,
    )

    result = authorize_leading_source_history(
        endpoint,
        source_start,
        "1h",
    )

    assert result.authorized[0] is np.True_
    assert result.maturity_endpoint_ms == 6 * HOUR_MS

    print("PASS: 1h branch does not inherit universal 144h requirement")


def test_4h_does_not_require_universal_144h_history():
    source_start = 0

    endpoint = np.array(
        [24 * HOUR_MS],
        dtype=np.int64,
    )

    result = authorize_leading_source_history(
        endpoint,
        source_start,
        "4h",
    )

    assert result.authorized[0] is np.True_
    assert result.maturity_endpoint_ms == 24 * HOUR_MS

    print("PASS: 4h branch does not inherit universal 144h requirement")


def test_before_maturity_reason_code_is_exact():
    endpoint = np.array(
        [0],
        dtype=np.int64,
    )

    result = authorize_leading_source_history(
        endpoint,
        0,
        "24h",
    )

    assert result.authorized[0] is np.False_
    assert result.reason[0] == (
        SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,
    )

    print("PASS: pre-maturity endpoint uses frozen leading-boundary reason")


def test_unsupported_window_fails_closed():
    try:
        authorize_leading_source_history(
            np.array([0], dtype=np.int64),
            0,
            "2h",
        )
        raise AssertionError("Expected unsupported window to fail")
    except ValueError as exc:
        assert "Unsupported frozen source-history window" in str(exc)

    print("PASS: unsupported source-history window fails closed")


def test_non_integer_endpoint_dtype_fails_closed():
    try:
        authorize_leading_source_history(
            np.array([0.0, 300000.0], dtype=np.float64),
            0,
            "1h",
        )
        raise AssertionError("Expected float endpoint dtype to fail")
    except TypeError as exc:
        assert "integer dtype" in str(exc)

    print("PASS: non-integer endpoint dtype fails closed")


def test_non_grid_aligned_endpoint_fails_closed():
    try:
        authorize_leading_source_history(
            np.array([1], dtype=np.int64),
            0,
            "1h",
        )
        raise AssertionError("Expected non-grid endpoint to fail")
    except ValueError as exc:
        assert "non-grid-aligned" in str(exc)

    print("PASS: non-grid-aligned endpoint fails closed")


def test_nonconsecutive_endpoints_fail_closed():
    endpoints = np.array(
        [
            0,
            GRID_INTERVAL_MS,
            3 * GRID_INTERVAL_MS,
        ],
        dtype=np.int64,
    )

    try:
        authorize_leading_source_history(
            endpoints,
            0,
            "1h",
        )
        raise AssertionError("Expected nonconsecutive endpoints to fail")
    except ValueError as exc:
        assert "consecutive frozen 5-minute" in str(exc)

    print("PASS: nonconsecutive source-history grid fails closed")


def test_result_and_arrays_are_immutable():
    result = authorize_leading_source_history(
        np.array(
            [
                6 * HOUR_MS,
                6 * HOUR_MS + GRID_INTERVAL_MS,
            ],
            dtype=np.int64,
        ),
        0,
        "1h",
    )

    try:
        result.window_name = "4h"
        raise AssertionError(
            "Expected LeadingBoundaryAuthorizationResult mutation to fail"
        )
    except FrozenInstanceError:
        pass

    assert result.endpoint_ms.flags.writeable is False
    assert result.authorized.flags.writeable is False
    assert isinstance(result.reason, tuple)

    try:
        result.authorized[0] = False
        raise AssertionError("Expected read-only authorized array to fail")
    except ValueError:
        pass

    print("PASS: leading-boundary evidence object and arrays are immutable")


if __name__ == "__main__":
    test_frozen_window_specific_raw_history_is_exact()
    test_exact_grid_source_start_is_unchanged()
    test_off_grid_source_start_ceilings_forward()
    test_maturity_boundary_equality_passes()
    test_off_grid_source_start_affects_maturity_exactly()
    test_each_window_uses_its_own_maturity_floor()
    test_1h_does_not_require_universal_144h_history()
    test_4h_does_not_require_universal_144h_history()
    test_before_maturity_reason_code_is_exact()
    test_unsupported_window_fails_closed()
    test_non_integer_endpoint_dtype_fails_closed()
    test_non_grid_aligned_endpoint_fails_closed()
    test_nonconsecutive_endpoints_fail_closed()
    test_result_and_arrays_are_immutable()

    print(
        "\nALL LRS-4 LEADING SOURCE-HISTORY STRUCTURAL TESTS PASSED"
    )


def test_resolved_break_starts_at_stop_boundary():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        SOURCE_HISTORY_BREAK_CONFIRMED,
        authorize_source_history,
    )

    source_start = 0

    # Use endpoints well after leading maturity so this isolates break logic.
    stop = 10 * HOUR_MS
    restored = 11 * HOUR_MS

    endpoints = np.arange(
        stop - GRID_INTERVAL_MS,
        stop + 2 * GRID_INTERVAL_MS,
        GRID_INTERVAL_MS,
        dtype=np.int64,
    )

    result = authorize_source_history(
        endpoint_ms=endpoints,
        source_start_ms=source_start,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=stop,
                restored_ms=restored,
            ),
        ),
    )

    assert result.authorized.tolist() == [
        True,
        False,
        False,
    ]

    assert result.reason[0] == ()
    assert result.reason[1] == (
        SOURCE_HISTORY_BREAK_CONFIRMED,
    )

    print("PASS: resolved break begins exactly at T_stop")


def test_resolved_break_recovery_boundary_equality_passes():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        SOURCE_HISTORY_BREAK_CONFIRMED,
        authorize_source_history,
    )

    source_start = 0

    stop = 10 * HOUR_MS
    restored = 11 * HOUR_MS

    recovery = restored + 6 * HOUR_MS

    endpoints = np.array(
        [
            recovery - GRID_INTERVAL_MS,
            recovery,
            recovery + GRID_INTERVAL_MS,
        ],
        dtype=np.int64,
    )

    result = authorize_source_history(
        endpoint_ms=endpoints,
        source_start_ms=source_start,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=stop,
                restored_ms=restored,
            ),
        ),
    )

    assert result.authorized.tolist() == [
        False,
        True,
        True,
    ]

    assert result.reason[0] == (
        SOURCE_HISTORY_BREAK_CONFIRMED,
    )
    assert result.reason[1] == ()
    assert result.reason[2] == ()

    print("PASS: G == break recovery endpoint is authorized")


def test_off_grid_restoration_ceilings_before_recovery():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        SOURCE_HISTORY_BREAK_CONFIRMED,
        authorize_source_history,
    )

    source_start = 0

    stop = 10 * HOUR_MS
    restored = (
        11 * HOUR_MS
        + 1
    )

    restored_ceiling = (
        11 * HOUR_MS
        + GRID_INTERVAL_MS
    )

    recovery = (
        restored_ceiling
        + 6 * HOUR_MS
    )

    endpoints = np.array(
        [
            recovery - GRID_INTERVAL_MS,
            recovery,
        ],
        dtype=np.int64,
    )

    result = authorize_source_history(
        endpoint_ms=endpoints,
        source_start_ms=source_start,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=stop,
                restored_ms=restored,
            ),
        ),
    )

    assert result.authorized.tolist() == [
        False,
        True,
    ]

    assert result.reason[0] == (
        SOURCE_HISTORY_BREAK_CONFIRMED,
    )
    assert result.reason[1] == ()

    print("PASS: off-grid restoration ceilings before 6W recovery")


def test_unresolved_break_is_open_ended():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        SOURCE_HISTORY_BREAK_END_UNRESOLVED,
        authorize_source_history,
    )

    source_start = 0
    stop = 10 * HOUR_MS

    endpoints = np.array(
        [
            stop - GRID_INTERVAL_MS,
            stop,
            stop + GRID_INTERVAL_MS,
            stop + 100 * HOUR_MS,
        ],
        dtype=np.int64,
    )

    # The last jump violates the consecutive-grid contract, so evaluate
    # the nearby boundary and far-future point separately.
    near = authorize_source_history(
        endpoint_ms=endpoints[:3],
        source_start_ms=source_start,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=stop,
                restored_ms=None,
            ),
        ),
    )

    assert near.authorized.tolist() == [
        True,
        False,
        False,
    ]

    assert near.reason[1] == (
        SOURCE_HISTORY_BREAK_END_UNRESOLVED,
    )
    assert near.reason[2] == (
        SOURCE_HISTORY_BREAK_END_UNRESOLVED,
    )

    far = authorize_source_history(
        endpoint_ms=np.array(
            [stop + 100 * HOUR_MS],
            dtype=np.int64,
        ),
        source_start_ms=source_start,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=stop,
                restored_ms=None,
            ),
        ),
    )

    assert far.authorized[0] is np.False_
    assert far.reason[0] == (
        SOURCE_HISTORY_BREAK_END_UNRESOLVED,
    )

    print("PASS: unresolved break remains open-ended")


def test_break_recovery_remains_window_specific():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        authorize_source_history,
    )

    source_start = 0
    stop = 200 * HOUR_MS
    restored = 201 * HOUR_MS

    cases = {
        "1h": 6 * HOUR_MS,
        "4h": 24 * HOUR_MS,
        "24h": 144 * HOUR_MS,
    }

    for window_name, raw_history in cases.items():
        recovery = restored + raw_history

        endpoints = np.array(
            [
                recovery - GRID_INTERVAL_MS,
                recovery,
            ],
            dtype=np.int64,
        )

        result = authorize_source_history(
            endpoint_ms=endpoints,
            source_start_ms=source_start,
            window_name=window_name,
            confirmed_breaks=(
                AcquisitionBreak(
                    stop_ms=stop,
                    restored_ms=restored,
                ),
            ),
        )

        assert result.authorized.tolist() == [
            False,
            True,
        ]

    print("PASS: break recovery uses window-specific 6W history")


def test_leading_boundary_and_break_reasons_can_coexist():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        SOURCE_HISTORY_BREAK_CONFIRMED,
        SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,
        authorize_source_history,
    )

    source_start = 0

    stop = 1 * HOUR_MS
    restored = 2 * HOUR_MS

    endpoint = np.array(
        [1 * HOUR_MS],
        dtype=np.int64,
    )

    result = authorize_source_history(
        endpoint_ms=endpoint,
        source_start_ms=source_start,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=stop,
                restored_ms=restored,
            ),
        ),
    )

    assert result.authorized[0] is np.False_

    assert result.reason[0] == (
        SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT,
        SOURCE_HISTORY_BREAK_CONFIRMED,
    )

    print("PASS: leading-boundary and break reasons are retained together")


def test_invalid_break_interval_fails_closed():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        authorize_source_history,
    )

    try:
        authorize_source_history(
            endpoint_ms=np.array(
                [10 * HOUR_MS],
                dtype=np.int64,
            ),
            source_start_ms=0,
            window_name="1h",
            confirmed_breaks=(
                AcquisitionBreak(
                    stop_ms=10 * HOUR_MS,
                    restored_ms=10 * HOUR_MS,
                ),
            ),
        )
        raise AssertionError(
            "Expected zero-length break to fail"
        )
    except ValueError as exc:
        assert "strictly greater than stop_ms" in str(exc)

    print("PASS: invalid acquisition-break interval fails closed")


def test_unsorted_breaks_fail_closed():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        authorize_source_history,
    )

    try:
        authorize_source_history(
            endpoint_ms=np.array(
                [30 * HOUR_MS],
                dtype=np.int64,
            ),
            source_start_ms=0,
            window_name="1h",
            confirmed_breaks=(
                AcquisitionBreak(
                    stop_ms=20 * HOUR_MS,
                    restored_ms=21 * HOUR_MS,
                ),
                AcquisitionBreak(
                    stop_ms=10 * HOUR_MS,
                    restored_ms=11 * HOUR_MS,
                ),
            ),
        )
        raise AssertionError(
            "Expected unsorted breaks to fail"
        )
    except ValueError as exc:
        assert "ordered by nondecreasing stop_ms" in str(exc)

    print("PASS: unsorted acquisition breaks fail closed")


def test_complete_source_history_result_is_immutable():
    from L3_RESEARCH_ENGINES.market_regime_intelligence.data.source_history import (
        AcquisitionBreak,
        authorize_source_history,
    )

    result = authorize_source_history(
        endpoint_ms=np.array(
            [
                20 * HOUR_MS,
                20 * HOUR_MS + GRID_INTERVAL_MS,
            ],
            dtype=np.int64,
        ),
        source_start_ms=0,
        window_name="1h",
        confirmed_breaks=(
            AcquisitionBreak(
                stop_ms=10 * HOUR_MS,
                restored_ms=11 * HOUR_MS,
            ),
        ),
    )

    try:
        result.window_name = "4h"
        raise AssertionError(
            "Expected SourceHistoryAuthorizationResult mutation to fail"
        )
    except FrozenInstanceError:
        pass

    assert result.endpoint_ms.flags.writeable is False
    assert result.authorized.flags.writeable is False
    assert isinstance(result.reason, tuple)
    assert isinstance(result.confirmed_breaks, tuple)

    try:
        result.authorized[0] = False
        raise AssertionError(
            "Expected read-only authorization array to fail"
        )
    except ValueError:
        pass

    print("PASS: complete source-history evidence object is immutable")


if __name__ == "__main__":
    print("\n--- ACQUISITION-BREAK TESTS ---")

    test_resolved_break_starts_at_stop_boundary()
    test_resolved_break_recovery_boundary_equality_passes()
    test_off_grid_restoration_ceilings_before_recovery()
    test_unresolved_break_is_open_ended()
    test_break_recovery_remains_window_specific()
    test_leading_boundary_and_break_reasons_can_coexist()
    test_invalid_break_interval_fails_closed()
    test_unsorted_breaks_fail_closed()
    test_complete_source_history_result_is_immutable()

    print(
        "\nALL LRS-4 ACQUISITION-BREAK SOURCE-HISTORY TESTS PASSED"
    )
