"""Calibration phase -- port of
src/modules/experiment/parts/calibration.ts and
src/modules/experiment/jspsych/calibration-trial.ts.

Only CalibrationPart2 and FinalCalibrationPart2 are ever driven through
this loop in the original (buildCalibration/buildFinalCalibration only
ever call calibrationTrial with those two part types) -- CalibrationPart1
/FinalCalibrationPart1 exist as CalibrationPartType enum values and in
ExperimentState's per-part bookkeeping, but are otherwise unused/dead in
the current experiment flow, so no loop is ported for them here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src2.utils.calculations import auto_increase_amount_calculation
from src2.utils.constants import (
    AUTO_DECREASE_AMOUNT,
    AUTO_DECREASE_RATE,
    EXPECTED_MAXIMUM_PERCENTAGE_FOR_CALIBRATION,
    MAX_CALIBRATION_CONSECUTIVE_LOW_TAP_FAILURES,
    TRIAL_DURATION,
)
from src2.utils.trial_history import TrialHistory, check_flag, check_keys
from src2.utils.types import CalibrationPartType


class CalibrationAbortedError(Exception):
    """Raised when MAX_CALIBRATION_CONSECUTIVE_LOW_TAP_FAILURES is hit --
    mirrors the original's `finishExperimentEarly(...)` call."""

    def __init__(self, calibration_part: str):
        super().__init__(f'Calibration aborted early during {calibration_part}')
        self.calibration_part = calibration_part


@dataclass
class CalibrationRunners:
    countdown: Callable[[], dict]
    tapping: Callable[[float, bool], dict]  # (auto_increase_amount, key_tapped_early_flag) -> record
    release_keys: Callable[[], dict]
    success_screen: Callable[[], dict]
    loading_bar: Callable[[], None]


def compute_calibration_auto_increase_amount(calibration_part: str, state) -> float:
    """Port of the `autoIncreaseAmount()` callback in calibration-trial.ts."""
    if calibration_part == CalibrationPartType.CALIBRATION_PART_2.value:
        median = state.get_calibration_part2_seed()
    elif calibration_part == CalibrationPartType.FINAL_CALIBRATION_PART_2.value:
        median = state.get_final_calibration_part2_seed()
    else:
        median = state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_1.value]
    return auto_increase_amount_calculation(
        EXPECTED_MAXIMUM_PERCENTAGE_FOR_CALIBRATION,
        TRIAL_DURATION,
        AUTO_DECREASE_RATE,
        AUTO_DECREASE_AMOUNT,
        median,
        (0, 0),
    )


def run_calibration_loop(calibration_part: str, state, history: TrialHistory, runners: CalibrationRunners) -> None:
    """Port of the calibrationTrial timeline/loop_function. Raises
    CalibrationAbortedError if the participant can't reach the minimum
    tap threshold too many times in a row."""
    consecutive_low_tap_failures = 0

    while state.get_required_successes(calibration_part) > state.get_current_successes(calibration_part):
        countdown_record = runners.countdown()
        history.add({**countdown_record, 'trial_type': 'countdown-trial'})

        key_tapped_early_flag = check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
        auto_increase_amount = compute_calibration_auto_increase_amount(calibration_part, state)
        tapping_record = runners.tapping(auto_increase_amount, key_tapped_early_flag)
        history.add({**tapping_record, 'trial_type': 'task-plugin'})

        genuine_trial = not tapping_record['keysReleasedFlag'] and not tapping_record['keyTappedEarlyFlag']
        below_minimum = (
            tapping_record['tapCount'] < state.get_calibration_settings().minimumCalibrationMedianTaps
        )
        if genuine_trial:
            if below_minimum:
                consecutive_low_tap_failures += 1
                if consecutive_low_tap_failures >= MAX_CALIBRATION_CONSECUTIVE_LOW_TAP_FAILURES:
                    raise CalibrationAbortedError(calibration_part)
            else:
                consecutive_low_tap_failures = 0
                if calibration_part == CalibrationPartType.FINAL_CALIBRATION_PART_2.value:
                    state.push_final_calibration_part2_tap_count(tapping_record['tapCount'])
                elif calibration_part == CalibrationPartType.CALIBRATION_PART_2.value:
                    state.push_calibration_part2_tap_count(tapping_record['tapCount'])

        if check_keys(history):
            release_record = runners.release_keys()
            history.add({**release_record, 'trial_type': 'release-keys'})

        success_record = runners.success_screen()
        history.add({**success_record, 'trial_type': 'success-screen-plugin'})

        runners.loading_bar()
