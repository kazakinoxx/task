import pytest

from src2.config.settings_schema import AllSettingsType
from src2.state.experiment_state import ExperimentState
from src2.utils.calculations import (
    auto_increase_amount_calculation,
    calculate_median_tap_count,
    calculate_total_points,
    calculate_total_reward,
    get_bounds_variation,
    get_hold_keys,
    get_progress_bar_status,
    get_reward_yitter,
    get_tap_key,
    sort_enum_array,
)
from src2.utils.trial_history import TrialHistory
from src2.utils.types import BoundsType, RewardType


def test_auto_increase_amount_calculation_matches_formula():
    # median=20 taps, trial_duration=5000ms, decrease rate=100ms, decrease amount=2, sync delay [0,0]
    result = auto_increase_amount_calculation(100, 5000, 100, 2, 20, (0, 0))
    # effective_presses = 20 - 0 = 20; numerator = 100 + (5000/100)*2 = 200
    assert result == pytest.approx(200 / 20)


def test_auto_increase_amount_calculation_with_delay_reduces_effective_presses():
    result_no_delay = auto_increase_amount_calculation(100, 5000, 100, 2, 20, (0, 0))
    result_with_delay = auto_increase_amount_calculation(100, 5000, 100, 2, 20, (0, 1000))
    assert result_with_delay > result_no_delay


def test_calculate_median_tap_count_filters_failed_trials():
    history = TrialHistory()
    history.add({'task': 'calibrationPart2', 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'tapCount': 10})
    history.add({'task': 'calibrationPart2', 'keysReleasedFlag': True, 'keyTappedEarlyFlag': False, 'tapCount': 99})
    history.add({'task': 'calibrationPart2', 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'tapCount': 20})
    median = calculate_median_tap_count('calibrationPart2', 5, history)
    assert median == 15  # median of [10, 20]


def test_calculate_total_reward_adds_previous_reward():
    history = TrialHistory()
    history.add({'task': 'block', 'success': True, 'reward': 10})
    history.add({'task': 'block', 'success': True, 'reward': 5})
    history.add({'task': 'block', 'success': False, 'reward': 20})
    state = ExperimentState()
    state.set_previous_reward(3)
    assert calculate_total_reward(history, state) == 3 + 15


def test_calculate_total_points_uses_task_settings():
    settings = AllSettingsType()
    settings.taskSettings.taskBlockRepetitions = 1
    settings.taskSettings.taskBlocksIncluded = [d for d in ['sync', 'shortasync']]
    settings.taskSettings.taskBoundsIncluded = ['easy']
    settings.taskSettings.taskRewardsIncluded = ['low', 'high']
    settings.taskSettings.taskPermutationRepetitions = 1
    state = ExperimentState(settings)
    # total_trial = 1 * 2 * 1 * 2 * 1 = 4; avg reward = (1+20)/2 = 10.5
    assert calculate_total_points(state) == pytest.approx(4 * 10.5)


def test_sort_enum_array_dedupes_and_sorts():
    result = sort_enum_array(['hard', 'easy', 'easy', 'medium'], {'easy': 0, 'medium': 1, 'hard': 2})
    assert result == ['easy', 'medium', 'hard']


def test_get_reward_yitter_returns_base_value():
    assert get_reward_yitter(RewardType.HIGH.value) == 20


def test_get_bounds_variation_preserves_width():
    lo, hi = get_bounds_variation(BoundsType.MEDIUM.value)
    assert hi - lo == pytest.approx(75 - 45)


def test_get_hold_keys_and_tap_key_depend_on_preferred_hand():
    state = ExperimentState()
    state.set_preferred_hand('right')
    assert get_hold_keys(state) == ['s']
    assert get_tap_key(state) == 'l'

    state.set_preferred_hand('left')
    assert get_hold_keys(state) == ['l']
    assert get_tap_key(state) == 's'


def test_get_progress_bar_status_phases():
    state = ExperimentState()
    state.set_instruction_phase('practice')
    assert get_progress_bar_status(state) == 0.05
    state.set_instruction_phase('final-calibration')
    assert get_progress_bar_status(state) == 0.9
