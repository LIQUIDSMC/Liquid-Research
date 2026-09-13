"""
LRS-4 Experiment v1 — structural lock tests for regime episodes.
"""

from dataclasses import FrozenInstanceError

import numpy as np

from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.episodes import (
    build_regime_episodes,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.grid_returns import (
    GRID_INTERVAL_MS,
)
from L3_RESEARCH_ENGINES.market_regime_intelligence.indicators.regime_state import (
    REGIME_HIGH,
    REGIME_INVALID,
    REGIME_LOW,
    RegimeStateResult,
)


def _make_regime(states, endpoint_ms=None):
    n = len(states)

    if endpoint_ms is None:
        endpoint_ms = (
            np.arange(n, dtype=np.int64) * GRID_INTERVAL_MS
        )
    else:
        endpoint_ms = np.asarray(endpoint_ms, dtype=np.int64)

    state_valid = np.array(
        [state != REGIME_INVALID for state in states],
        dtype=bool,
    )

    dummy_float = np.ones(n, dtype=np.float64)
    dummy_bool = np.ones(n, dtype=bool)

    return RegimeStateResult(
        window_name="1h",
        endpoint_ms=endpoint_ms,
        rvol=dummy_float.copy(),
        threshold=dummy_float.copy(),
        rvol_valid=dummy_bool.copy(),
        threshold_valid=dummy_bool.copy(),
        state_valid=state_valid,
        state=tuple(states),
    )


def test_invalid_breaks_same_state_continuity():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_HIGH,
            REGIME_INVALID,
            REGIME_HIGH,
            REGIME_HIGH,
        ]
    )

    result = build_regime_episodes(regime)

    assert np.array_equal(
        result.episode_id_by_endpoint,
        np.array([0, 0, -1, 1, 1], dtype=np.int64),
    )

    assert len(result.episodes) == 2

    first, second = result.episodes

    assert first.state == REGIME_HIGH
    assert first.start_index == 0
    assert first.end_index == 1
    assert first.endpoint_count == 2

    assert second.state == REGIME_HIGH
    assert second.start_index == 3
    assert second.end_index == 4
    assert second.endpoint_count == 2

    print("PASS: INVALID breaks HIGH continuity into separate episodes")


def test_state_change_terminates_episode():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_HIGH,
            REGIME_LOW,
            REGIME_LOW,
            REGIME_HIGH,
        ]
    )

    result = build_regime_episodes(regime)

    assert np.array_equal(
        result.episode_id_by_endpoint,
        np.array([0, 0, 1, 1, 2], dtype=np.int64),
    )

    assert tuple(ep.state for ep in result.episodes) == (
        REGIME_HIGH,
        REGIME_LOW,
        REGIME_HIGH,
    )

    assert tuple(ep.endpoint_count for ep in result.episodes) == (
        2,
        2,
        1,
    )

    print("PASS: HIGH/LOW state changes terminate episodes deterministically")


def test_leading_and_trailing_invalid_create_no_phantom_episodes():
    regime = _make_regime(
        [
            REGIME_INVALID,
            REGIME_INVALID,
            REGIME_LOW,
            REGIME_LOW,
            REGIME_INVALID,
        ]
    )

    result = build_regime_episodes(regime)

    assert np.array_equal(
        result.episode_id_by_endpoint,
        np.array([-1, -1, 0, 0, -1], dtype=np.int64),
    )

    assert len(result.episodes) == 1

    episode = result.episodes[0]

    assert episode.state == REGIME_LOW
    assert episode.start_index == 2
    assert episode.end_index == 3
    assert episode.endpoint_count == 2

    print("PASS: leading/trailing INVALID endpoints create no episodes")


def test_all_invalid_produces_zero_episodes():
    regime = _make_regime(
        [
            REGIME_INVALID,
            REGIME_INVALID,
            REGIME_INVALID,
        ]
    )

    result = build_regime_episodes(regime)

    assert len(result.episodes) == 0
    assert np.array_equal(
        result.episode_id_by_endpoint,
        np.array([-1, -1, -1], dtype=np.int64),
    )

    print("PASS: all-INVALID sequence produces zero episodes")


def test_single_valid_endpoint_forms_one_episode():
    regime = _make_regime([REGIME_HIGH])

    result = build_regime_episodes(regime)

    assert len(result.episodes) == 1

    episode = result.episodes[0]

    assert episode.episode_id == 0
    assert episode.state == REGIME_HIGH
    assert episode.start_index == 0
    assert episode.end_index == 0
    assert episode.endpoint_count == 1
    assert episode.start_endpoint_ms == 0
    assert episode.end_endpoint_ms == 0

    print("PASS: one valid endpoint forms one one-endpoint episode")


def test_episode_ids_are_chronological_and_zero_based():
    regime = _make_regime(
        [
            REGIME_LOW,
            REGIME_INVALID,
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    result = build_regime_episodes(regime)

    assert tuple(ep.episode_id for ep in result.episodes) == (
        0,
        1,
        2,
    )

    assert np.array_equal(
        result.episode_id_by_endpoint,
        np.array([0, -1, 1, 2], dtype=np.int64),
    )

    print("PASS: episode IDs are deterministic, chronological, and zero-based")


def test_episode_endpoint_metadata_is_exact():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_HIGH,
            REGIME_HIGH,
        ]
    )

    result = build_regime_episodes(regime)

    episode = result.episodes[0]

    assert episode.start_endpoint_ms == 0
    assert episode.end_endpoint_ms == 2 * GRID_INTERVAL_MS
    assert episode.endpoint_count == 3

    print("PASS: episode endpoint metadata matches exact grid boundaries")


def test_nonconsecutive_endpoints_fail_closed():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_HIGH,
            REGIME_HIGH,
        ],
        endpoint_ms=np.array(
            [
                0,
                GRID_INTERVAL_MS,
                3 * GRID_INTERVAL_MS,
            ],
            dtype=np.int64,
        ),
    )

    try:
        build_regime_episodes(regime)
        raise AssertionError("Expected nonconsecutive endpoints to fail")
    except ValueError as exc:
        assert "not consecutive" in str(exc)

    print("PASS: nonconsecutive grid fails closed")


def test_unknown_state_fails_closed():
    regime = _make_regime(
        [
            REGIME_HIGH,
            "UNKNOWN",
        ]
    )

    # Repair state_valid so the failure is specifically unknown state.
    object.__setattr__(
        regime,
        "state_valid",
        np.array([True, True], dtype=bool),
    )

    try:
        build_regime_episodes(regime)
        raise AssertionError("Expected unknown state to fail")
    except ValueError as exc:
        assert "Unknown regime state" in str(exc)

    print("PASS: unknown regime state fails closed")


def test_state_valid_true_with_invalid_state_fails_closed():
    regime = _make_regime([REGIME_INVALID])

    object.__setattr__(
        regime,
        "state_valid",
        np.array([True], dtype=bool),
    )

    try:
        build_regime_episodes(regime)
        raise AssertionError(
            "Expected state_valid=True + INVALID to fail"
        )
    except ValueError as exc:
        assert "cannot coexist" in str(exc)

    print("PASS: state_valid=True cannot coexist with INVALID")


def test_state_valid_false_with_valid_state_fails_closed():
    regime = _make_regime([REGIME_HIGH])

    object.__setattr__(
        regime,
        "state_valid",
        np.array([False], dtype=bool),
    )

    try:
        build_regime_episodes(regime)
        raise AssertionError(
            "Expected state_valid=False + HIGH to fail"
        )
    except ValueError as exc:
        assert "must correspond to INVALID" in str(exc)

    print("PASS: state_valid=False requires INVALID state")


def test_state_length_mismatch_fails_closed():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_LOW,
        ]
    )

    object.__setattr__(
        regime,
        "state",
        (REGIME_HIGH,),
    )

    try:
        build_regime_episodes(regime)
        raise AssertionError("Expected state-length mismatch to fail")
    except ValueError as exc:
        assert "state length" in str(exc)

    print("PASS: state/endpoints length mismatch fails closed")


def test_result_and_episode_objects_are_immutable():
    regime = _make_regime(
        [
            REGIME_HIGH,
            REGIME_HIGH,
        ]
    )

    result = build_regime_episodes(regime)

    try:
        result.window_name = "4h"
        raise AssertionError("Expected EpisodeResult mutation to fail")
    except FrozenInstanceError:
        pass

    assert result.endpoint_ms.flags.writeable is False
    assert result.episode_id_by_endpoint.flags.writeable is False
    assert isinstance(result.state, tuple)
    assert isinstance(result.episodes, tuple)

    try:
        result.episode_id_by_endpoint[0] = 99
        raise AssertionError("Expected read-only episode IDs to fail")
    except ValueError:
        pass

    episode = result.episodes[0]

    try:
        episode.state = REGIME_LOW
        raise AssertionError("Expected RegimeEpisode mutation to fail")
    except FrozenInstanceError:
        pass

    print("PASS: episode result and episode records are immutable")


if __name__ == "__main__":
    test_invalid_breaks_same_state_continuity()
    test_state_change_terminates_episode()
    test_leading_and_trailing_invalid_create_no_phantom_episodes()
    test_all_invalid_produces_zero_episodes()
    test_single_valid_endpoint_forms_one_episode()
    test_episode_ids_are_chronological_and_zero_based()
    test_episode_endpoint_metadata_is_exact()
    test_nonconsecutive_endpoints_fail_closed()
    test_unknown_state_fails_closed()
    test_state_valid_true_with_invalid_state_fails_closed()
    test_state_valid_false_with_valid_state_fails_closed()
    test_state_length_mismatch_fails_closed()
    test_result_and_episode_objects_are_immutable()

    print(
        "\nALL LRS-4 EPISODE STRUCTURAL TESTS PASSED"
    )
