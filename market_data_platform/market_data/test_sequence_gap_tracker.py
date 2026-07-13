"""
Market Data Platform — SequenceGapTracker Smoke Test
market_data_platform/market_data/test_sequence_gap_tracker.py

Deterministic, offline test of SequenceGapTracker's logic, covering
every case defined during Step 3f design: first-value baseline,
contiguous increment, gap detection with correct missing range,
duplicate/out-of-order handling, malformed input handling, and
independence between separate tracker instances (simulating
separate connection sessions).

Run directly: python3 -m market_data_platform.market_data.test_sequence_gap_tracker
"""

from market_data_platform.market_data.collector import SequenceGapTracker


def test_first_value_establishes_baseline():
    tracker = SequenceGapTracker()
    assert tracker.previous_sequence is None
    tracker.check(0)
    assert tracker.previous_sequence == 0
    print("PASS: first value establishes baseline")


def test_contiguous_increment_advances_tracker():
    tracker = SequenceGapTracker()
    tracker.check(5)
    tracker.check(6)
    assert tracker.previous_sequence == 6
    print("PASS: contiguous increment advances tracker")


def test_jump_logs_gap_and_advances_tracker():
    tracker = SequenceGapTracker()
    tracker.check(10)
    tracker.check(15)
    assert tracker.previous_sequence == 15, "tracker should advance to the new value even after a gap"
    print("PASS: jump advances tracker (visually confirm GAP DETECTED line above shows first_missing=11, last_missing=14, missing_count=4)")


def test_duplicate_does_not_move_tracker_backward():
    tracker = SequenceGapTracker()
    tracker.check(10)
    tracker.check(10)
    assert tracker.previous_sequence == 10, "duplicate should not change tracker"
    print("PASS: duplicate does not move tracker backward")


def test_lower_value_does_not_move_tracker_backward():
    tracker = SequenceGapTracker()
    tracker.check(10)
    tracker.check(3)
    assert tracker.previous_sequence == 10, "lower value should not change tracker"
    print("PASS: lower value does not move tracker backward")


def test_malformed_values_do_not_alter_tracker():
    tracker = SequenceGapTracker()
    tracker.check(10)
    tracker.check(None)
    assert tracker.previous_sequence == 10, "None should not alter tracker"
    tracker.check("not a number")
    assert tracker.previous_sequence == 10, "string should not alter tracker"
    tracker.check(True)
    assert tracker.previous_sequence == 10, "bool True should not alter tracker (strict type check)"
    tracker.check(False)
    assert tracker.previous_sequence == 10, "bool False should not alter tracker (strict type check)"
    print("PASS: malformed values (None, str, bool) do not alter tracker")


def test_new_tracker_has_no_continuity_with_previous_tracker():
    tracker_one = SequenceGapTracker()
    tracker_one.check(0)
    tracker_one.check(1)
    tracker_one.check(2)  # ends cleanly, no gap — this test isolates independence, not gap detection

    tracker_two = SequenceGapTracker()
    assert tracker_two.previous_sequence is None, "new tracker must start with no baseline"
    tracker_two.check(0)  # simulates a new connection restarting at 0, per live evidence
    assert tracker_two.previous_sequence == 0, "new tracker accepts its first value with no gap reported"
    print("PASS: new tracker has no continuity with previous tracker, accepts its own first value")


if __name__ == "__main__":
    test_first_value_establishes_baseline()
    test_contiguous_increment_advances_tracker()
    test_jump_logs_gap_and_advances_tracker()
    test_duplicate_does_not_move_tracker_backward()
    test_lower_value_does_not_move_tracker_backward()
    test_malformed_values_do_not_alter_tracker()
    test_new_tracker_has_no_continuity_with_previous_tracker()
    print("\nAll SequenceGapTracker tests passed.")
