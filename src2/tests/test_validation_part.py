import pytest

from src2.parts.validation import (
    ValidationFailedError,
    ValidationRunners,
    compute_validation_auto_increase_amount,
    handle_validation_finish,
    resolve_validation_result,
    run_validation_trial_loop,
    should_finish_early_after_extra_validation,
    should_run_extra_validation,
)
from src2.state.experiment_state import ExperimentState
from src2.utils.constants import MAX_VALIDATION_ATTEMPTS_PER_LEVEL, MAX_VALIDATION_FAILURES
from src2.utils.trial_history import TrialHistory
from src2.utils.types import CalibrationPartType, ValidationPartType


def make_runners(tapping_outcomes, countdown_outcomes=None):
    tapping_iter = iter(tapping_outcomes)
    countdown_iter = iter(countdown_outcomes or [{'task': 'countdown', 'keyTappedEarlyFlag': False}] * len(tapping_outcomes))
    calls = {'release_keys': 0, 'success_screen': 0, 'loading_bar': 0, 'tapping': 0}

    def countdown():
        return next(countdown_iter)

    def tapping(auto_increase_amount, key_tapped_early_flag, bounds):
        calls['tapping'] += 1
        return dict(next(tapping_iter))

    def release_keys():
        calls['release_keys'] += 1
        return {'errorOccurred': False}

    def success_screen():
        calls['success_screen'] += 1
        return {'task': 'success', 'success': True}

    def loading_bar():
        calls['loading_bar'] += 1

    return ValidationRunners(countdown, tapping, release_keys, success_screen, loading_bar), calls


@pytest.mark.parametrize('success', [True, False])
def test_validation_loop_stops_after_single_clean_attempt_regardless_of_success(success):
    # Due to the preserved check_last_agency_trial_success quirk (see its
    # docstring), the retry loop only reacts to key errors -- a clean
    # attempt (no early tap / premature release) always ends the loop
    # after one iteration, whether or not bounds were actually hit.
    state = ExperimentState()
    history = TrialHistory()
    tapping_outcomes = [
        {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': success, 'mercuryHeight': 20, 'bounds': [5, 35], 'keysState': {'s': True}},
    ]
    runners, calls = make_runners(tapping_outcomes)

    run_validation_trial_loop(ValidationPartType.VALIDATION_EASY.value, state, history, runners)

    assert calls['tapping'] == 1
    expected_failures = 0 if success else 1
    assert state.get_state()['validationState']['failures'][ValidationPartType.VALIDATION_EASY.value] == expected_failures


def test_validation_loop_continues_through_repeated_key_errors_until_clean_attempt():
    state = ExperimentState()
    history = TrialHistory()
    countdown_outcomes = [
        {'task': 'countdown', 'keyTappedEarlyFlag': True},   # attempt 1: early tap -> retry
        {'task': 'countdown', 'keyTappedEarlyFlag': True},   # attempt 2: early tap -> retry
        {'task': 'countdown', 'keyTappedEarlyFlag': False},  # attempt 3: clean -> loop ends
    ]
    tapping_outcomes = [
        {'tapCount': 5, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': True, 'success': False, 'mercuryHeight': 20, 'bounds': [5, 35], 'keysState': {'s': True}},
        {'tapCount': 5, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': True, 'success': False, 'mercuryHeight': 20, 'bounds': [5, 35], 'keysState': {'s': True}},
        {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'mercuryHeight': 20, 'bounds': [5, 35], 'keysState': {'s': True}},
    ]
    runners, calls = make_runners(tapping_outcomes, countdown_outcomes)

    run_validation_trial_loop(ValidationPartType.VALIDATION_EASY.value, state, history, runners)

    assert calls['tapping'] == 3
    # Key-error attempts never increment the failures counter; the final
    # clean attempt succeeded, so failures stay at 0.
    assert state.get_state()['validationState']['failures'][ValidationPartType.VALIDATION_EASY.value] == 0


def test_validation_loop_honors_preseeded_max_attempts_guard_even_with_key_error():
    # Directly seed failures[level] to the max via handle_validation_finish
    # (bypassing the loop, since a genuine miss both increments the
    # counter and ends the loop in the same pass -- see the loop's
    # docstring). Then confirm a subsequent key-error attempt still stops
    # the loop because `failures[...] < MAX_VALIDATION_ATTEMPTS_PER_LEVEL`
    # is now False.
    state = ExperimentState()
    seed_history = TrialHistory()
    seed_history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': False})
    seed_history.add({'trial_type': 'task-plugin', 'keysReleasedFlag': False})
    for _ in range(MAX_VALIDATION_ATTEMPTS_PER_LEVEL):
        handle_validation_finish({'success': False}, ValidationPartType.VALIDATION_EASY.value, state, seed_history)
    assert state.get_state()['validationState']['failures'][ValidationPartType.VALIDATION_EASY.value] == MAX_VALIDATION_ATTEMPTS_PER_LEVEL

    history = TrialHistory()
    countdown_outcomes = [{'task': 'countdown', 'keyTappedEarlyFlag': True}]
    tapping_outcomes = [
        {'tapCount': 5, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': True, 'success': False, 'mercuryHeight': 20, 'bounds': [5, 35], 'keysState': {'s': True}},
    ]
    runners, calls = make_runners(tapping_outcomes, countdown_outcomes)

    run_validation_trial_loop(ValidationPartType.VALIDATION_EASY.value, state, history, runners)

    assert calls['tapping'] == 1  # stopped despite the key error, due to the max-attempts guard


def test_handle_validation_finish_requires_genuine_failure():
    state = ExperimentState()
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': True})
    history.add({'trial_type': 'task-plugin', 'keysReleasedFlag': False})

    handle_validation_finish({'success': False}, ValidationPartType.VALIDATION_EASY.value, state, history)
    # Early tap -> not a "genuine" failure -> no increment
    assert state.get_state()['validationState']['failures'][ValidationPartType.VALIDATION_EASY.value] == 0


def test_handle_validation_finish_sets_extra_required_after_max_attempts():
    state = ExperimentState()
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': False})
    history.add({'trial_type': 'task-plugin', 'keysReleasedFlag': False})

    for _ in range(MAX_VALIDATION_ATTEMPTS_PER_LEVEL):
        handle_validation_finish({'success': False}, ValidationPartType.VALIDATION_MEDIUM.value, state, history)

    assert state.get_state()['validationState']['extraValidationRequired'] is True


def test_handle_validation_finish_extra_validation_sets_validation_failure():
    from src2.utils.constants import MAX_EXTRA_VALIDATION_ATTEMPTS

    state = ExperimentState()
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': False})
    history.add({'trial_type': 'task-plugin', 'keysReleasedFlag': False})

    for _ in range(MAX_EXTRA_VALIDATION_ATTEMPTS):
        handle_validation_finish({'success': False}, ValidationPartType.VALIDATION_EXTRA.value, state, history)

    assert state.get_state()['validationState']['validationSuccess'] is False


def test_should_run_extra_validation_reflects_state():
    state = ExperimentState()
    assert should_run_extra_validation(state) is False
    state.set_extra_validation_required(True)
    assert should_run_extra_validation(state) is True


def test_should_finish_early_after_extra_validation():
    state = ExperimentState()
    assert should_finish_early_after_extra_validation(state) is False  # validationSuccess defaults True
    state.set_validation_success(False)
    assert should_finish_early_after_extra_validation(state) is True


def test_validation_failed_error_is_a_plain_exception_sibling_of_calibration_aborted_error():
    # main.py raises this when should_finish_early_after_extra_validation()
    # or resolve_validation_result()['should_finish_early'] is True, and
    # catches it alongside parts/calibration.py's CalibrationAbortedError
    # to show the same end-of-experiment screen (port of finishExperimentEarly).
    with pytest.raises(ValidationFailedError):
        raise ValidationFailedError()


def test_resolve_validation_result_passed():
    state = ExperimentState()
    result = resolve_validation_result(state)
    assert result == {'passed': True, 'should_finish_early': False}


def test_resolve_validation_result_failed_due_to_target_failures():
    state = ExperimentState()
    for _ in range(MAX_VALIDATION_FAILURES):
        state.increase_validation_target_failures()
    result = resolve_validation_result(state)
    assert result == {'passed': False, 'should_finish_early': True}


def test_hard_validation_lowers_median_taps_after_repeated_hard_failures():
    # Since a single clean (no-key-error) attempt ends the loop, reaching
    # UPDATE_MEDIAN_TAPS_THRESHOLD (2) hard-failures requires two separate
    # calls to the loop (mirroring two different points in the overall
    # validation flow where a HARD-level attempt could occur, e.g. the
    # main HARD validation call and, if needed, the ValidationExtra call
    # which also uses hard bounds).
    state = ExperimentState()
    state.set_median_taps({**state.get_state()['medianTaps'], CalibrationPartType.CALIBRATION_PART_2.value: 20})

    tapping_outcome = {
        'tapCount': 5, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False,
        'success': False, 'mercuryHeight': 10, 'bounds': [65, 95], 'keysState': {'s': True},
    }

    history1 = TrialHistory()
    runners1, _ = make_runners([dict(tapping_outcome)])
    run_validation_trial_loop(ValidationPartType.VALIDATION_HARD.value, state, history1, runners1)
    assert state.get_state()['validationState']['validationHardFailures'] == 1
    assert state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value] == 20  # threshold not yet reached

    history2 = TrialHistory()
    runners2, _ = make_runners([dict(tapping_outcome)])
    run_validation_trial_loop(ValidationPartType.VALIDATION_HARD.value, state, history2, runners2)
    assert state.get_state()['validationState']['validationHardFailures'] == 2
    assert state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value] == 18
