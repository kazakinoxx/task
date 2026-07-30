import pytest

from src2.trials.success_trial import (
    build_success_trial_record,
    resolve_basic_success_screen_params,
    resolve_success_screen_params,
    resolve_success_screen_params_validation,
    success_screen_variant,
)
from src2.utils.constants import MINIMUM_CALIBRATION_MEDIAN, SUCCESS_SCREEN_DURATION, SUCCESS_SCREEN_DURATION_FREEZE_FRAME
from src2.utils.trial_history import TrialHistory


def test_success_screen_variant_basic():
    assert success_screen_variant(True, False, False, False) == 'basic_success'
    assert success_screen_variant(False, False, False, False) == 'basic_failure'


def test_success_screen_variant_skip_overrides_basic():
    assert success_screen_variant(True, False, False, True) == 'skip'


def test_success_screen_variant_freeze_frame_requires_reason_message():
    assert success_screen_variant(True, True, True, False) == 'freeze_frame_success'
    assert success_screen_variant(False, True, True, False) == 'freeze_frame_failure'
    # no reason message -> falls through to basic
    assert success_screen_variant(True, True, False, False) == 'basic_success'


def test_build_success_trial_record():
    assert build_success_trial_record(True) == {'task': 'success', 'success': True}
    assert build_success_trial_record(False) == {'task': 'success', 'success': False}


def test_resolve_basic_success_screen_params_reads_last_tapping_trial():
    history = TrialHistory()
    history.add({'trial_type': 'task-plugin', 'success': True})
    params = resolve_basic_success_screen_params(history)
    assert params['success'] is True
    assert params['trial_duration'] == SUCCESS_SCREEN_DURATION / 1000.0


def test_resolve_success_screen_params_reports_key_tapped_early():
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': True})
    history.add({'trial_type': 'task-plugin', 'keysReleasedFlag': False, 'keyTappedEarlyFlag': True, 'tapCount': 20})
    params = resolve_success_screen_params(history, show_freeze_frame=False, main_task=True)
    assert params['success'] is False
    assert params['show_freeze_frame'] is True
    assert params['reason_code'] == 'KEY_TAPPED_EARLY'
    assert params['trial_duration'] == SUCCESS_SCREEN_DURATION_FREEZE_FRAME / 1000.0


def test_resolve_success_screen_params_reports_not_enough_taps_for_non_main_task():
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': False})
    history.add(
        {
            'trial_type': 'task-plugin',
            'keysReleasedFlag': False,
            'keyTappedEarlyFlag': False,
            'tapCount': MINIMUM_CALIBRATION_MEDIAN - 1,
        }
    )
    params = resolve_success_screen_params(history, show_freeze_frame=False, main_task=False)
    assert params['reason_code'] == 'NOT_ENOUGH_TAPS'


def test_resolve_success_screen_params_success_when_all_checks_pass():
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': False})
    history.add(
        {
            'trial_type': 'task-plugin',
            'keysReleasedFlag': False,
            'keyTappedEarlyFlag': False,
            'tapCount': MINIMUM_CALIBRATION_MEDIAN + 5,
        }
    )
    params = resolve_success_screen_params(history, show_freeze_frame=False, main_task=True)
    assert params['success'] is True
    assert params['show_freeze_frame'] is False
    assert params['reason_code'] is None
    assert params['trial_duration'] == SUCCESS_SCREEN_DURATION / 1000.0


def test_resolve_success_screen_params_validation_variant():
    history = TrialHistory()
    history.add({'trial_type': 'countdown-trial', 'keyTappedEarlyFlag': False})
    history.add({'trial_type': 'task-plugin', 'keysReleasedFlag': True, 'success': False})
    params = resolve_success_screen_params_validation(history, show_freeze_frame=False)
    assert params['success'] is False
    assert params['reason_code'] == 'KEY_RELEASED_EARLY'
