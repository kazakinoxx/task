"""ExperimentState -- port of
src/modules/experiment/jspsych/experiment-state-class.ts.

Runtime state is kept as a plain dict (mirroring the JS `State` object)
so it can be checkpointed to JSON directly without a serialization layer.
Settings are held as the AllSettingsType dataclass built in milestone 1.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional

from src2.config.defaults import BOUNDS_SORT_ORDER, DELAY_SORT_ORDER, REWARD_SORT_ORDER
from src2.config.settings_schema import AllSettingsType, TaskSettingsType
from src2.utils.calculations import sort_enum_array
from src2.utils.constants import CALIBRATION_DEFAULT_SEED_TAPS
from src2.utils.types import CalibrationPartType, ExtendedKeySettings, ValidationPartType

_CALIBRATION_PARTS = [p.value for p in CalibrationPartType]
_VALIDATION_PARTS = [p.value for p in ValidationPartType]


def _default_median_taps() -> dict:
    return {part: 10 for part in _CALIBRATION_PARTS}


def _default_current_trials_calibration() -> dict:
    return {part: 0 for part in _CALIBRATION_PARTS}


def _default_calibration_parts_passed() -> dict:
    return {part: False for part in _CALIBRATION_PARTS}


def _default_validation_failures() -> dict:
    return {part: 0 for part in _VALIDATION_PARTS}


def _default_validation_state() -> dict:
    return {
        'failures': _default_validation_failures(),
        'validationSuccess': True,
        'extraValidationRequired': False,
        'validationHardFailures': 0,
        'validationTargetFailures': 0,
    }


def _initial_state() -> dict:
    return {
        'tappingHand': 'right',
        'medianTaps': _default_median_taps(),
        'currentCalibrationStepSuccesses': _default_current_trials_calibration(),
        'calibrationPartsPassed': _default_calibration_parts_passed(),
        'validationState': _default_validation_state(),
        'failedMinimumDemoTapsTrial': 0,
        'previousReward': 0,
        'completedBlockCount': 1,
        'numberOfPracticeLoopsCompleted': 0,
        'calibrationPart2TapCounts': [],
        'finalCalibrationPart2TapCounts': [],
        'phase': 'introduction',
        'userID': '',
        'patchStatus': 'success',
        'previousTrials': None,
    }


class ExperimentState:
    def __init__(self, settings: Optional[AllSettingsType] = None):
        self._state = _initial_state()
        self._settings = settings if settings is not None else AllSettingsType()

    # -- state / settings getters -----------------------------------------

    def get_state(self) -> dict:
        return self._state

    def get_settings(self) -> AllSettingsType:
        return self._settings

    def get_general_settings(self):
        return self._settings.generalSettings

    def get_practice_settings(self):
        return self._settings.practiceSettings

    def get_calibration_settings(self):
        return self._settings.calibrationSettings

    def get_agency_task_settings(self):
        return self._settings.agencyTaskSettings

    def get_validation_settings(self):
        return self._settings.validationSettings

    def get_task_settings(self) -> TaskSettingsType:
        """Port of getTaskSettings -- returns a copy with each included-type
        list deduplicated and sorted per the canonical order."""
        base = self._settings.taskSettings
        return dataclasses.replace(
            base,
            taskBoundsIncluded=sort_enum_array(base.taskBoundsIncluded, BOUNDS_SORT_ORDER),
            taskRewardsIncluded=sort_enum_array(base.taskRewardsIncluded, REWARD_SORT_ORDER),
            taskBlocksIncluded=sort_enum_array(base.taskBlocksIncluded, DELAY_SORT_ORDER),
        )

    def get_photo_diode_settings(self):
        return self._settings.photoDiodeSettings

    def get_key_settings(self) -> ExtendedKeySettings:
        key_settings = dataclasses.asdict(self._settings.keySettings)
        key_settings['preferredHand'] = self._state['tappingHand']
        return key_settings  # type: ignore[return-value]

    def get_next_step_settings(self):
        return self._settings.nextStepSettings

    # -- calibration progress ----------------------------------------------

    def get_current_successes(self, calibration_part: Optional[str] = None) -> int:
        if calibration_part == CalibrationPartType.FINAL_CALIBRATION_PART_2.value:
            return len(self._state['finalCalibrationPart2TapCounts'])
        return len(self._state['calibrationPart2TapCounts'])

    def get_required_successes(self, calibration_part: str) -> int:
        return self._settings.calibrationSettings.requiredTrialsCalibration[calibration_part]

    # -- misc getters/setters ----------------------------------------------

    def get_patch_status(self) -> str:
        return self._state['patchStatus']

    def set_patch_status(self, status: str) -> None:
        self._state['patchStatus'] = status

    def get_preferred_hand(self) -> str:
        return self._state['tappingHand']

    def set_preferred_hand(self, hand: str) -> None:
        self._state['tappingHand'] = hand

    def set_previous_trials(self, trials: list) -> None:
        self._state['previousTrials'] = trials

    def set_previous_reward(self, reward: float) -> None:
        self._state['previousReward'] = reward

    def set_user_id(self, user_id: str) -> None:
        self._state['userID'] = user_id

    def update_median_taps(self, calibration_part: str, value: float) -> None:
        self._state['medianTaps'][calibration_part] = value

    def increase_validation_failures(self, validation_part: str) -> None:
        self._state['validationState']['failures'][validation_part] += 1

    def increase_validation_target_failures(self) -> None:
        self._state['validationState']['validationTargetFailures'] += 1

    def increase_validation_hard_failures(self) -> None:
        self._state['validationState']['validationHardFailures'] += 1

    def set_calibration_passed(self, calibration_part: str) -> None:
        self._state['calibrationPartsPassed'][calibration_part] = True

    def set_extra_validation_required(self, required: bool) -> None:
        self._state['validationState']['extraValidationRequired'] = required

    def set_validation_success(self, successful: bool) -> None:
        self._state['validationState']['validationSuccess'] = successful

    def set_font_size(self, font_size: str) -> None:
        self._settings.generalSettings.fontSize = font_size

    def increment_completed_blocks(self) -> None:
        self._state['completedBlockCount'] += 1

    def increment_number_practice_loops_completed(self) -> None:
        self._state['numberOfPracticeLoopsCompleted'] += 1

    def increment_calibration_successes(self, calibration_part: str) -> None:
        self._state['currentCalibrationStepSuccesses'][calibration_part] += 1

    def update_calibration_successes(self, calibration_part: str, successes: int) -> None:
        self._state['currentCalibrationStepSuccesses'][calibration_part] = successes

    def set_median_taps(self, median_taps: dict) -> None:
        self._state['medianTaps'] = median_taps

    def set_instruction_phase(self, phase: str) -> None:
        self._state['phase'] = phase

    # -- adaptive calibration seeding ---------------------------------------
    # These are NOT statistical medians despite the "median taps" naming --
    # see the module docstring in utils/calculations.py.

    def push_calibration_part2_tap_count(self, tap_count: int) -> None:
        self._state['calibrationPart2TapCounts'].append(tap_count)
        new_median = self.get_calibration_part2_seed()
        self._state['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value] = new_median

    def get_calibration_part2_seed(self) -> float:
        """Adaptive seed for the NEXT CalibrationPart2 trial:
        - 0 trials so far -> CALIBRATION_DEFAULT_SEED_TAPS (20)
        - 1 trial  -> that trial's tap count
        - >=2 trials -> max(second-to-last, last)
        """
        counts = self._state['calibrationPart2TapCounts']
        if len(counts) == 0:
            return CALIBRATION_DEFAULT_SEED_TAPS
        if len(counts) == 1:
            return counts[0]
        return max(counts[-2], counts[-1])

    def get_calibration_part2_final_mts(self) -> float:
        """Final MTS after all 3 CalibrationPart2 trials: max(T2, T3).
        Returns 0 if fewer than 3 trials recorded."""
        counts = self._state['calibrationPart2TapCounts']
        if len(counts) < 3:
            return 0
        return max(counts[1], counts[2])

    def push_final_calibration_part2_tap_count(self, tap_count: int) -> None:
        self._state['finalCalibrationPart2TapCounts'].append(tap_count)
        new_median = self.get_final_calibration_part2_seed()
        self._state['medianTaps'][CalibrationPartType.FINAL_CALIBRATION_PART_2.value] = new_median

    def get_final_calibration_part2_seed(self) -> float:
        counts = self._state['finalCalibrationPart2TapCounts']
        if len(counts) == 0:
            return self.get_calibration_part2_final_mts()
        if len(counts) == 1:
            return counts[0]
        return max(counts[-2], counts[-1])

    def get_final_calibration_part2_final_mts(self) -> float:
        counts = self._state['finalCalibrationPart2TapCounts']
        if len(counts) < 3:
            return 0
        return max(counts[1], counts[2])

    def clear_calibration_part2_tap_counts(self) -> None:
        self._state['calibrationPart2TapCounts'] = []

    def reset_state(self) -> None:
        self._state = _initial_state()
        self._state['numberOfPracticeLoopsCompleted'] = 1
        # NB: the original TS resetState() assigns
        # `medianTaps: defaultCurrentTrialsCalibration` (all zeros) instead
        # of `defaultMedianTaps` (all tens) -- almost certainly a bug, but
        # replicated here for line-by-line fidelity with existing behavior.
        self._state['medianTaps'] = _default_current_trials_calibration()
