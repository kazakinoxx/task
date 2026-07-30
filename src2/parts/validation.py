"""Validation phase -- port of
src/modules/experiment/parts/validation.ts and
src/modules/experiment/jspsych/validation-trial.ts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

from src2.utils.calculations import auto_increase_amount_calculation
from src2.utils.constants import (
    AUTO_DECREASE_AMOUNT,
    AUTO_DECREASE_RATE,
    EXPECTED_MAXIMUM_PERCENTAGE,
    MAX_EXTRA_VALIDATION_ATTEMPTS,
    MAX_VALIDATION_ATTEMPTS_PER_LEVEL,
    MAX_VALIDATION_FAILURES,
    TRIAL_DURATION,
    UPDATE_MEDIAN_TAPS_THRESHOLD,
)
from src2.utils.trial_history import (
    TrialHistory,
    check_flag,
    check_keys,
    check_last_agency_trial_success,
    check_mercury_height,
)
from src2.utils.types import BoundsType, CalibrationPartType, ValidationPartType

class ValidationFailedError(Exception):
    """Raised when validation should end the experiment early -- mirrors
    the original's `finishExperimentEarly(...)` call, triggered from
    either validationTrialExtra's on_timeline_finish (see
    should_finish_early_after_extra_validation) or
    validationResultScreen's on_finish (see resolve_validation_result).
    Sibling to parts/calibration.py's CalibrationAbortedError."""


DEFAULT_VALIDATION_BOUNDS = {
    ValidationPartType.VALIDATION_EASY.value: (5, 35),
    ValidationPartType.VALIDATION_MEDIUM.value: (35, 65),
    ValidationPartType.VALIDATION_HARD.value: (65, 95),
    ValidationPartType.VALIDATION_EXTRA.value: (65, 95),
}

VALIDATION_BOUNDS_TYPE = {
    ValidationPartType.VALIDATION_EASY.value: BoundsType.EASY.value,
    ValidationPartType.VALIDATION_MEDIUM.value: BoundsType.MEDIUM.value,
    ValidationPartType.VALIDATION_HARD.value: BoundsType.HARD.value,
    ValidationPartType.VALIDATION_EXTRA.value: BoundsType.HARD.value,
}


@dataclass
class ValidationRunners:
    countdown: Callable[[], dict]
    tapping: Callable[[float, bool, Tuple[float, float]], dict]
    release_keys: Callable[[], dict]
    success_screen: Callable[[], dict]
    loading_bar: Callable[[], None]


def compute_validation_auto_increase_amount(state) -> float:
    """Port of the `autoIncreaseAmount()` callback in
    createValidationTrial -- always keyed off calibrationPart2's median,
    regardless of validation level."""
    median = state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value]
    return auto_increase_amount_calculation(
        EXPECTED_MAXIMUM_PERCENTAGE, TRIAL_DURATION, AUTO_DECREASE_RATE, AUTO_DECREASE_AMOUNT, median, (0, 0)
    )


def handle_validation_finish(data: dict, validation_step: str, state, history: TrialHistory) -> None:
    """Port of handleValidationFinish."""
    if (
        not data['success']
        and not check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
        and not check_flag(history, 'task-plugin', 'keysReleasedFlag')
    ):
        state.increase_validation_failures(validation_step)
        failures = state.get_state()['validationState']['failures'][validation_step]
        if (
            validation_step != ValidationPartType.VALIDATION_EXTRA.value
            and failures >= MAX_VALIDATION_ATTEMPTS_PER_LEVEL
        ):
            state.set_extra_validation_required(True)
        elif (
            validation_step == ValidationPartType.VALIDATION_EXTRA.value
            and failures >= MAX_EXTRA_VALIDATION_ATTEMPTS
        ):
            state.set_validation_success(False)


def run_validation_trial_loop(
    validation_name: str, state, history: TrialHistory, runners: ValidationRunners
) -> None:
    """Port of createValidationTrial's timeline + loop_function.

    NOTE (preserved quirk, not a porting error): the retry condition uses
    `check_last_agency_trial_success`, which -- due to an apparent bug in
    the original (see its docstring in utils/trial_history.py) -- only
    reacts to key errors (early tap / premature release), not to whether
    the participant actually hit the target bounds. Concretely: any
    attempt with no key error ends the loop immediately, regardless of
    success/failure, so `failures[validation_name]` can only ever be
    incremented once per call to this function under normal play (a
    genuine bounds-miss both increments the counter *and* ends the loop
    in the same iteration). The `failures[...] < MAX_VALIDATION_ATTEMPTS_PER_LEVEL`
    guard below is preserved as-is but is effectively unreachable through
    this path alone in current gameplay -- replicated faithfully rather
    than "fixed" per the line-by-line fidelity requirement."""
    while True:
        countdown_record = runners.countdown()
        history.add({**countdown_record, 'trial_type': 'countdown-trial'})

        key_tapped_early_flag = check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
        auto_increase_amount = compute_validation_auto_increase_amount(state)
        bounds = DEFAULT_VALIDATION_BOUNDS[validation_name]
        tapping_record = runners.tapping(auto_increase_amount, key_tapped_early_flag, bounds)
        tapping_record['task'] = validation_name  # port of `data.task = validationName;`
        history.add({**tapping_record, 'trial_type': 'task-plugin'})

        handle_validation_finish(tapping_record, validation_name, state, history)

        if check_keys(history):
            release_record = runners.release_keys()
            history.add({**release_record, 'trial_type': 'release-keys'})

        success_record = runners.success_screen()
        history.add({**success_record, 'trial_type': 'success-screen-plugin'})

        runners.loading_bar()

        # -- loop_function --
        if (
            not check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
            and not check_flag(history, 'task-plugin', 'keysReleasedFlag')
            and not check_flag(history, 'task-plugin', 'success')
        ):
            state.increase_validation_target_failures()

        if (
            not check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
            and not check_flag(history, 'task-plugin', 'keysReleasedFlag')
            and check_mercury_height(history)
            and validation_name == ValidationPartType.VALIDATION_HARD.value
        ):
            state.increase_validation_hard_failures()

        median_taps = state.get_state()['medianTaps']
        if (
            state.get_state()['validationState']['validationHardFailures'] >= UPDATE_MEDIAN_TAPS_THRESHOLD
            and validation_name == ValidationPartType.VALIDATION_HARD.value
            and median_taps[CalibrationPartType.CALIBRATION_PART_2.value] >= 15
        ):
            median_taps[CalibrationPartType.CALIBRATION_PART_2.value] -= 2
            state.set_median_taps(median_taps)

        should_continue = (
            not check_last_agency_trial_success(history)
            and state.get_state()['validationState']['failures'][validation_name] < MAX_VALIDATION_ATTEMPTS_PER_LEVEL
        )
        if not should_continue:
            break


def should_run_extra_validation(state) -> bool:
    """Port of the conditional_function gating validationTrialExtra."""
    return state.get_state()['validationState']['extraValidationRequired']


def should_finish_early_after_extra_validation(state) -> bool:
    """Port of validationTrialExtra's on_timeline_finish."""
    return not state.get_state()['validationState']['validationSuccess']


def resolve_validation_result(state) -> dict:
    """Port of validationResultScreen's stimulus/on_finish logic."""
    validation_state = state.get_state()['validationState']
    passed = (
        validation_state['validationTargetFailures'] < MAX_VALIDATION_FAILURES
        and validation_state['validationSuccess']
    )
    should_finish_early = (
        validation_state['validationTargetFailures'] >= MAX_VALIDATION_FAILURES
        or not validation_state['validationSuccess']
    )
    return {'passed': passed, 'should_finish_early': should_finish_early}
