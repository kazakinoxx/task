import pytest

from src2.parts.calibration import (
    CalibrationAbortedError,
    CalibrationRunners,
    compute_calibration_auto_increase_amount,
    run_calibration_loop,
)
from src2.state.experiment_state import ExperimentState
from src2.utils.constants import MAX_CALIBRATION_CONSECUTIVE_LOW_TAP_FAILURES
from src2.utils.trial_history import TrialHistory
from src2.utils.types import CalibrationPartType


def test_compute_auto_increase_amount_uses_calibration_part2_seed():
    state = ExperimentState()
    state.push_calibration_part2_tap_count(20)  # seed becomes 20
    amount = compute_calibration_auto_increase_amount(CalibrationPartType.CALIBRATION_PART_2.value, state)
    assert amount > 0


def make_runners(tapping_outcomes, countdown_outcomes=None):
    tapping_iter = iter(tapping_outcomes)
    countdown_iter = iter(countdown_outcomes or [{'task': 'countdown', 'keyTappedEarlyFlag': False}] * len(tapping_outcomes))
    calls = {'release_keys': 0, 'success_screen': 0, 'loading_bar': 0}

    def countdown():
        return next(countdown_iter)

    def tapping(auto_increase_amount, key_tapped_early_flag):
        record = next(tapping_iter)
        return record

    def release_keys():
        calls['release_keys'] += 1
        return {'errorOccurred': False}

    def success_screen():
        calls['success_screen'] += 1
        return {'task': 'success', 'success': True}

    def loading_bar():
        calls['loading_bar'] += 1

    return CalibrationRunners(countdown, tapping, release_keys, success_screen, loading_bar), calls


def test_calibration_loop_runs_until_required_successes_reached():
    state = ExperimentState()  # default requiredTrialsCalibration[calibrationPart2] = 3
    history = TrialHistory()
    tapping_outcomes = [
        {'tapCount': 15, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
        {'tapCount': 18, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
        {'tapCount': 20, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
    ]
    runners, calls = make_runners(tapping_outcomes)

    run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)

    assert state.get_current_successes(CalibrationPartType.CALIBRATION_PART_2.value) == 3
    assert calls['loading_bar'] == 3
    assert state.get_calibration_part2_final_mts() == max(18, 20)


def test_calibration_loop_ignores_non_genuine_trials():
    state = ExperimentState()
    history = TrialHistory()
    # First trial has keysReleasedFlag=True (not genuine) -- shouldn't count
    # toward successes; loop needs 3 genuine successes total.
    tapping_outcomes = [
        {'tapCount': 15, 'keysReleasedFlag': True, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
        {'tapCount': 15, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
        {'tapCount': 15, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
        {'tapCount': 15, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
    ]
    runners, calls = make_runners(tapping_outcomes)

    run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)

    assert state.get_current_successes(CalibrationPartType.CALIBRATION_PART_2.value) == 3
    assert calls['loading_bar'] == 4  # ran 4 iterations total (1 ignored + 3 counted)


def test_calibration_loop_aborts_after_consecutive_low_tap_failures():
    state = ExperimentState()
    # default minimumCalibrationMedianTaps is 10; tapCount=1 is well below it
    history = TrialHistory()
    tapping_outcomes = [
        {'tapCount': 1, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}}
    ] * MAX_CALIBRATION_CONSECUTIVE_LOW_TAP_FAILURES
    runners, calls = make_runners(tapping_outcomes)

    with pytest.raises(CalibrationAbortedError):
        run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)


def test_calibration_loop_skips_release_keys_when_keys_not_held():
    state = ExperimentState()
    history = TrialHistory()
    tapping_outcomes = [
        {'tapCount': 15, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': False}},
    ] * 3
    runners, calls = make_runners(tapping_outcomes)

    run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)
    assert calls['release_keys'] == 0


def test_calibration_loop_shows_release_keys_when_keys_held():
    state = ExperimentState()
    history = TrialHistory()
    tapping_outcomes = [
        {'tapCount': 15, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'keysState': {'s': True}},
    ] * 3
    runners, calls = make_runners(tapping_outcomes)

    run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)
    assert calls['release_keys'] == 3
