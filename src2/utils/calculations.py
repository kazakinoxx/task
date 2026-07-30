"""Calculation helpers.

Port of the remaining (non-randomization, non-history-query) functions in
src/modules/experiment/utils/utils.ts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from src2.utils.constants import BOUNDS_DEFINITIONS, DEFAULT_BOUNDS_VARIATION, REWARD_DEFINITIONS
from src2.utils.randomization import random_number_bm
from src2.utils.trial_history import TrialHistory

if TYPE_CHECKING:
    from src2.state.experiment_state import ExperimentState


def auto_increase_amount_calculation(
    expected_maximum_percentage: float,
    trial_duration: float,
    auto_decrease_rate: float,
    auto_decrease_amount: float,
    median: float,
    delay: tuple[float, float],
) -> float:
    """
    Port of autoIncreaseAmountCalculation.

    Note: the `medianTaps` value stored in tapping-task-trial output is
    NOT a statistical median of past tap counts -- it's this re-derived
    "effective required tap count" from the auto-increase amount. See
    ExperimentState.get_calibration_part2_seed for the actual
    median-like adaptive seed logic.
    """
    # --- Guard against invalid inputs ---
    if median <= 0:
        # No taps recorded; return a safe default (e.g., a high value that will not cause
        # further issues, or raise an exception). Returning 0.0 would make the auto-increase
        # effectively zero, which might be okay; but we choose a large value to avoid
        # division by zero and to signify that the increase amount should be huge.
        return 1000.0  # or 0.0, depending on how the caller uses it

    taps_per_second = median / trial_duration
    avg_delay_sec = (delay[0] + delay[1]) / 2 / 1000
    lost_taps = avg_delay_sec * taps_per_second
    effective_presses = median - lost_taps

    # --- Division by zero / negative effective_presses ---
    if effective_presses <= 0:
        # No effective taps; again return a large default or raise an exception.
        # This could happen if delay is extremely long relative to tap rate.
        return 1000.0

    return (
        expected_maximum_percentage
        + (trial_duration / auto_decrease_rate) * auto_decrease_amount
    ) / effective_presses


def calculate_median_tap_count(
    task_type: str, num_trials: int, history: TrialHistory
) -> Optional[float]:
    """Port of calculateMedianTapCount -- true statistical median of the
    last `num_trials` successful (no early release/tap) trials of the
    given task type."""
    filtered = (
        history.filter(task=task_type)
        .filter(keysReleasedFlag=False, keyTappedEarlyFlag=False)
        .last(num_trials)
    )
    return filtered.select('tapCount').median()


def calculate_total_reward(history: TrialHistory, state: 'ExperimentState') -> float:
    """Port of calculateTotalReward."""
    successful_trials = history.filter(task='block', success=True)
    current_reward = successful_trials.select('reward').sum()
    return state.get_state()['previousReward'] + current_reward


def calculate_total_points(state: 'ExperimentState') -> float:
    """Port of calculateTotalPoints."""
    task_settings = state.get_task_settings()
    total_trial = (
        task_settings.taskBlockRepetitions
        * len(task_settings.taskBlocksIncluded)
        * len(task_settings.taskBoundsIncluded)
        * len(task_settings.taskRewardsIncluded)
        * task_settings.taskPermutationRepetitions
    )
    rewards = [REWARD_DEFINITIONS[r] for r in task_settings.taskRewardsIncluded]
    average_reward = sum(rewards) / len(rewards) if rewards else 0
    return total_trial * average_reward


def sort_enum_array(arr: List[str], sort_order: Dict[str, int]) -> List[str]:
    """Port of sortEnumArray -- de-duplicates (keeping first occurrence)
    then sorts by the given sort order."""
    included = set()
    filtered = []
    for item in arr:
        if item not in included:
            included.add(item)
            filtered.append(item)
    return sorted(filtered, key=lambda x: sort_order[x])


def get_reward_yitter(reward: str) -> float:
    """Port of getRewardYitter (note: despite the name, this just looks up
    the base reward value -- no jitter is actually applied here in the
    original)."""
    return REWARD_DEFINITIONS[reward]


def get_bounds_variation(bounds: str) -> tuple[float, float]:
    """Port of getBoundsVariation -- applies +/-3 noise to the bounds
    center while preserving the bounds width."""
    standard_bounds = BOUNDS_DEFINITIONS[bounds]
    dif_bounds = standard_bounds[1] - standard_bounds[0]
    center = (standard_bounds[0] + standard_bounds[1]) / 2
    lo = center - DEFAULT_BOUNDS_VARIATION
    hi = center + DEFAULT_BOUNDS_VARIATION
    new_center = random_number_bm(lo, hi)
    return (new_center - dif_bounds / 2, new_center + dif_bounds / 2)


def get_hold_keys(state: 'ExperimentState') -> List[str]:
    """Port of getHoldKeys."""
    key_settings = state.get_key_settings()
    if key_settings['preferredHand'] == 'left':
        return [key_settings['rightIndex'].lower()]
    return [key_settings['leftIndex'].lower()]


def get_tap_key(state: 'ExperimentState') -> str:
    """Port of getTapKey."""
    key_settings = state.get_key_settings()
    if key_settings['preferredHand'] == 'left':
        return key_settings['leftIndex'].lower()
    return key_settings['rightIndex'].lower()


def resolve_link(link: str, participant_name: str) -> str:
    """Port of resolveLink -- substitutes the literal `{id}` placeholder
    with the participant's name/id, used by getEndPage (experiment.ts)."""
    if '{id}' in link:
        return link.replace('{id}', participant_name)
    return link


def get_progress_bar_status(state: 'ExperimentState', trial_block: Optional[int] = None) -> float:
    """Port of getProgressBarStatus."""
    phase = state.get_state()['phase']
    if phase == 'practice':
        return 0.05
    if phase == 'calibration':
        return 0.1
    if phase == 'validation':
        return 0.15
    if phase == 'EBDM':
        if trial_block:
            task_settings = state.get_task_settings()
            denom = task_settings.taskBlockRepetitions * len(task_settings.taskBlocksIncluded)
            return 0.2 + (trial_block / denom) * 0.9
        return 0.15
    if phase == 'final-calibration':
        return 0.9
    return 0
