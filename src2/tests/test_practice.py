from src2.parts.practice import run_hold_key_practice_block, run_success_failure_loop, run_tapping_practice_block
from src2.utils.constants import MINIMUM_CALIBRATION_MEDIAN
from src2.utils.trial_history import TrialHistory


def test_run_success_failure_loop_stops_at_min_successes():
    calls = []

    def run_iteration():
        calls.append(1)

    outcomes = iter([True, True])

    def is_success():
        return next(outcomes)

    success_count, failure_count = run_success_failure_loop(2, 3, run_iteration, is_success)
    assert success_count == 2
    assert failure_count == 0
    assert len(calls) == 2


def test_run_success_failure_loop_stops_at_max_failures():
    outcomes = iter([False, False, False])

    def is_success():
        return next(outcomes)

    success_count, failure_count = run_success_failure_loop(2, 3, lambda: None, is_success)
    assert success_count == 0
    assert failure_count == 3


def test_run_success_failure_loop_mixed_outcomes():
    outcomes = iter([True, False, True])

    def is_success():
        return next(outcomes)

    success_count, failure_count = run_success_failure_loop(2, 3, lambda: None, is_success)
    assert success_count == 2
    assert failure_count == 1


def test_hold_key_practice_block_counts_successes_and_failures():
    history = TrialHistory()
    outcomes = iter([False, True, True])  # fail, success, success -> stop (2 successes)

    def run_trial():
        success = next(outcomes)
        return {'task': 'hold-key-practice', 'success': success}

    result = run_hold_key_practice_block(history, run_trial)
    assert result == {'successCount': 2, 'failureCount': 1}
    assert len(history) == 3


def test_tapping_practice_block_uses_check_last_trial_success():
    history = TrialHistory()
    # Three scripted iterations: fail (early tap), then two successes ->
    # stops once successCount reaches HOLD_KEY_MIN_SUCCESSES (2).
    iterations = [
        {'countdown': {'keyTappedEarlyFlag': True}, 'tapping': {'keysReleasedFlag': False, 'tapCount': 20}},
        {'countdown': {'keyTappedEarlyFlag': False}, 'tapping': {'keysReleasedFlag': False, 'tapCount': MINIMUM_CALIBRATION_MEDIAN + 5}},
        {'countdown': {'keyTappedEarlyFlag': False}, 'tapping': {'keysReleasedFlag': False, 'tapCount': MINIMUM_CALIBRATION_MEDIAN + 5}},
    ]
    it = iter(iterations)
    current = {}

    def run_countdown():
        nonlocal current
        current = next(it)
        return current['countdown']

    def run_tapping():
        return current['tapping']

    def run_success_screen():
        return {'task': 'success', 'success': True}

    loading_bar_calls = []

    def run_loading_bar():
        loading_bar_calls.append(1)

    result = run_tapping_practice_block(history, run_countdown, run_tapping, run_success_screen, run_loading_bar)
    assert result == {'successCount': 2, 'failureCount': 1}
    assert len(loading_bar_calls) == 3
