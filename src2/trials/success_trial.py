"""Success/failure feedback screen -- port of
src/modules/experiment/trials/success-trial.ts (`SuccessScreenPlugin` and
its successScreen/successScreenFreezeFrame/successScreenFreezeFrameValidation
helper builders).

Reason messages are resolved here as reason CODES (e.g.
'KEY_TAPPED_EARLY'), not translated text -- the i18n layer (milestone 9)
maps codes to display strings, keeping this module free of any
presentation-language dependency.
"""

from __future__ import annotations

from typing import Optional

from src2.utils.constants import (
    MINIMUM_CALIBRATION_MEDIAN,
    SUCCESS_SCREEN_DURATION,
    SUCCESS_SCREEN_DURATION_FREEZE_FRAME,
    SUCCESS_SCREEN_FREE_TRIAL_DURATION,
)
from src2.utils.trial_history import (
    TrialHistory,
    check_flag,
    check_last_agency_trial_success,
    check_last_trial_success,
    check_taps,
)


def success_screen_variant(success: bool, show_freeze_frame: bool, has_reason_message: bool, skip: bool) -> str:
    """Port of the stimulusHTML branch selection in SuccessScreenPlugin.trial()."""
    if show_freeze_frame and has_reason_message:
        return 'freeze_frame_success' if success else 'freeze_frame_failure'
    if skip:
        return 'skip'
    return 'basic_success' if success else 'basic_failure'


def build_success_trial_record(success: bool) -> dict:
    """Port of endTrial's trialData -- the only fields actually recorded."""
    return {'task': 'success', 'success': success}


def resolve_basic_success_screen_params(history: TrialHistory, skip: bool = False) -> dict:
    """Port of the `successScreen` helper. A skipped (free) trial holds the
    screen for SUCCESS_SCREEN_FREE_TRIAL_DURATION, a normal one for
    SUCCESS_SCREEN_DURATION -- mirroring `trial_duration: skip ?
    SUCCESS_SCREEN_FREE_TRIAL_DURATION : SUCCESS_SCREEN_DURATION`."""
    success = check_flag(history, 'task-plugin', 'success')
    return {
        'task': 'success',
        'success': success,
        'skip': skip,
        'show_freeze_frame': False,
        'reason_code': None,
        'trial_duration': (SUCCESS_SCREEN_FREE_TRIAL_DURATION if skip else SUCCESS_SCREEN_DURATION) / 1000.0,
    }


def _resolve_reason_code(history: TrialHistory, main_task: bool) -> str:
    """Port of the reasonMessage() resolution in `successScreenFreezeFrame`."""
    if check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag'):
        return 'KEY_TAPPED_EARLY'
    if check_flag(history, 'task-plugin', 'keysReleasedFlag'):
        return 'KEY_RELEASED_EARLY'
    if not main_task and check_taps(history) <= MINIMUM_CALIBRATION_MEDIAN:
        return 'NOT_ENOUGH_TAPS'
    return 'SUCCESSFUL_FIRST_TRIAL'


def resolve_success_screen_params(
    history: TrialHistory, show_freeze_frame: bool, main_task: bool = False
) -> dict:
    """Port of the `successScreenFreezeFrame` helper."""
    last_trial_success = check_last_trial_success(history, MINIMUM_CALIBRATION_MEDIAN)
    needs_freeze_frame = show_freeze_frame or not last_trial_success
    return {
        'task': 'success',
        'success': last_trial_success,
        'show_freeze_frame': needs_freeze_frame,
        'reason_code': _resolve_reason_code(history, main_task) if needs_freeze_frame else None,
        'trial_duration': (
            SUCCESS_SCREEN_DURATION_FREEZE_FRAME if needs_freeze_frame else SUCCESS_SCREEN_DURATION
        )
        / 1000.0,
    }


def resolve_success_screen_params_validation(history: TrialHistory, show_freeze_frame: bool) -> dict:
    """Port of the `successScreenFreezeFrameValidation` helper."""
    last_trial_success = check_last_agency_trial_success(history)
    needs_freeze_frame = show_freeze_frame or not last_trial_success

    reason_code: Optional[str] = None
    if needs_freeze_frame:
        if check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag'):
            reason_code = 'KEY_TAPPED_EARLY'
        elif check_flag(history, 'task-plugin', 'keysReleasedFlag'):
            reason_code = 'KEY_RELEASED_EARLY'
        elif not check_flag(history, 'task-plugin', 'success'):
            reason_code = 'TRIAL_NOT_SUCCESSFUL'

    return {
        'task': 'success',
        'success': last_trial_success,
        'show_freeze_frame': needs_freeze_frame,
        'reason_code': reason_code,
        'trial_duration': (
            SUCCESS_SCREEN_DURATION_FREEZE_FRAME if needs_freeze_frame else SUCCESS_SCREEN_DURATION
        )
        / 1000.0,
    }
