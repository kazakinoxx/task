"""EBDM task core -- port of src/modules/experiment/parts/task-core.ts
and the task-block-building functions in
src/modules/experiment/jspsych/trials.ts.

As with the other parts/*.py modules, trial execution is injected via
small runner dataclasses so the sequencing/control-flow logic here is
unit-testable without PsychoPy. Two behavioral quirks in the original
are preserved faithfully and documented where they occur:

1. In `run_generate_task_trial`, a trial with no procedural error (no
   early tap, no premature release) and no random-skip shows NO success/
   failure screen at all before the loading bar -- feedback is only
   shown for procedural errors or random-skip trials. This appears
   intentional (avoid trial-by-trial bias in an effort-based-decision
   task) so it's preserved as designed.
2. In `resolve_break_allow_skip`, the break trial's own `allowSkip`
   parity (index % 2 == 0) is the OPPOSITE parity of the condition that
   gates whether the break shows at all (index % 2 == 1) in the
   original `generateTaskTrialBlock`. Since a break only ever renders on
   an odd index, `allowSkip` (which needs an even index) is always False
   in practice -- the skip button code path is effectively dead. This
   looks like an off-by-one bug in the original, replicated here as-is
   per the line-by-line fidelity requirement rather than "fixed".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from src2.utils.calculations import (
    calculate_total_points,
    calculate_total_reward,
    get_bounds_variation,
    get_progress_bar_status,
    get_reward_yitter,
)
from src2.utils.constants import (
    AUTO_DECREASE_AMOUNT,
    AUTO_DECREASE_RATE,
    BOUNDS_DEFINITIONS,
    CURRENCY,
    DELAY_DEFINITIONS,
    DEMO_TRIAL_SET,
    EXPECTED_MAXIMUM_PERCENTAGE,
    MAIN_TASK_BREAK_DURATION,
    TOTAL_REWARD_MONEY,
    TRIAL_DURATION,
)
from src2.utils.randomization import shuffle
import random as _random_module

from src2.utils.calculations import auto_increase_amount_calculation
from src2.utils.trial_history import TrialHistory, check_flag, check_keys
from src2.utils.types import CalibrationPartType


# ---------------------------------------------------------------------------
# Trial-order / permutation generation (pure)
# ---------------------------------------------------------------------------


def _has_triple_repeat(arr: List[str]) -> bool:
    return any(arr[i] == arr[i - 1] == arr[i - 2] for i in range(2, len(arr)))


def generate_trial_order(state) -> List[str]:
    """Port of generateTrialOrder -- shuffles taskBlocksIncluded once per
    repetition, concatenated, retrying until no delay type appears three
    times in a row."""
    task_settings = state.get_task_settings()
    while True:
        order: List[str] = []
        for _ in range(task_settings.taskBlockRepetitions):
            order.extend(shuffle(list(task_settings.taskBlocksIncluded)))
        if not _has_triple_repeat(order):
            return order


def get_num_trials_per_block(state) -> int:
    """Port of getNumTrialsPerBlock."""
    task_settings = state.get_task_settings()
    return (
        task_settings.taskPermutationRepetitions
        * len(task_settings.taskBoundsIncluded)
        * len(task_settings.taskRewardsIncluded)
    )


def generate_task_block_permutations(state) -> List[dict]:
    """Port of the Array.from(...).flat() permutation-shuffling in
    createTaskBlockTrials -- each of the taskPermutationRepetitions
    copies of the full (bounds x reward) cross-product is shuffled
    independently, then concatenated (not shuffled together as one big
    pool)."""
    task_settings = state.get_task_settings()
    combos = [
        {'bounds': b, 'reward': r}
        for b in task_settings.taskBoundsIncluded
        for r in task_settings.taskRewardsIncluded
    ]
    result: List[dict] = []
    for _ in range(task_settings.taskPermutationRepetitions):
        result.extend(shuffle(combos))
    return result


def resolve_random_skip(state) -> bool:
    """Port of `Math.random() <= randomSkipChance / 100`."""
    return _random_module.random() <= state.get_task_settings().randomSkipChance / 100


def resolve_actual_trial_params(bounds: str, reward: str, delay: str) -> dict:
    """Port of the actualReward/actualBounds/actualDelay computation in
    createTaskBlockTrials."""
    return {
        'reward': get_reward_yitter(reward),
        'bounds': get_bounds_variation(bounds),
        'delay': DELAY_DEFINITIONS[delay],
    }


def compute_task_trial_auto_increase_amount(state, delay: Tuple[float, float]) -> float:
    """Port of the `autoIncreaseAmount()` callback in generateTaskTrial --
    always keyed off calibrationPart2's median, like validation."""
    median = state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value]
    return auto_increase_amount_calculation(
        EXPECTED_MAXIMUM_PERCENTAGE, TRIAL_DURATION, AUTO_DECREASE_RATE, AUTO_DECREASE_AMOUNT, median, delay
    )


# ---------------------------------------------------------------------------
# generateTaskTrial (single demo-or-block trial, with countdown/release/
# feedback/loading-bar sequencing)
# ---------------------------------------------------------------------------


@dataclass
class TaskTrialRunners:
    countdown: Callable[[], dict]
    tapping: Callable[[float, bool, Tuple[float, float], Tuple[float, float], float, bool, str], dict]
    release_keys: Callable[[], dict]
    freeze_frame_failure_screen: Callable[[], dict]
    skip_screen: Callable[[], dict]
    loading_bar: Callable[[bool], None]


def run_generate_task_trial(
    state,
    history: TrialHistory,
    runners: TaskTrialRunners,
    bounds: Tuple[float, float],
    reward: float,
    delay: Tuple[float, float],
    block_type: str,
    demo: bool,
    random_skip: bool,
) -> dict:
    """Port of generateTaskTrial."""
    task_label = 'demo' if demo else 'block'

    if not random_skip:
        countdown_record = runners.countdown()
        history.add({**countdown_record, 'trial_type': 'countdown-trial'})

    # NOTE: matches the original's on_start, which unconditionally calls
    # checkFlag(CountdownTask, 'keyTappedEarlyFlag') even when randomSkip
    # is True and no fresh countdown trial just ran -- in that case this
    # reads whatever countdown trial happened most recently (possibly
    # from an earlier, unrelated trial). Harmless to the recorded
    # `success` value (random_skip forces success regardless), but the
    # stale flag value itself does get stored in this trial's data,
    # replicated here rather than "fixed" to always be False.
    key_tapped_early_flag = check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
    auto_increase_amount = compute_task_trial_auto_increase_amount(state, delay)

    tapping_record = runners.tapping(
        auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_skip, task_label
    )
    tapping_record.setdefault('blockType', block_type)
    history.add({**tapping_record, 'trial_type': 'task-plugin'})

    if check_keys(history) and not random_skip:
        release_record = runners.release_keys()
        history.add({**release_record, 'trial_type': 'release-keys'})

    procedural_error = check_flag(history, 'task-plugin', 'keyTappedEarlyFlag') or check_flag(
        history, 'task-plugin', 'keysReleasedFlag'
    )
    if procedural_error and not random_skip:
        screen_record = runners.freeze_frame_failure_screen()
        history.add({**screen_record, 'trial_type': 'success-screen-plugin'})
    elif random_skip:
        screen_record = runners.skip_screen()
        history.add({**screen_record, 'trial_type': 'success-screen-plugin'})
    # else: no feedback screen at all -- see module docstring, point 1.

    if demo:
        runners.loading_bar(True)
    else:
        runners.loading_bar(not random_skip)

    return tapping_record


# ---------------------------------------------------------------------------
# createTaskBlockDemo
# ---------------------------------------------------------------------------


def run_task_block_demo(
    state,
    history: TrialHistory,
    runners: TaskTrialRunners,
    delay: str,
) -> None:
    """Port of createTaskBlockDemo -- one demo trial per DEMO_TRIAL_SET
    bounds level, retried while a procedural error occurred."""
    actual_delay = DELAY_DEFINITIONS[delay]
    for bounds_type in DEMO_TRIAL_SET:
        bounds = BOUNDS_DEFINITIONS[bounds_type]
        while True:
            run_generate_task_trial(
                state, history, runners, bounds, 0, actual_delay, delay, demo=True, random_skip=False
            )
            key_tapped_early = check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
            keys_released = check_flag(history, 'task-plugin', 'keysReleasedFlag')
            if not (key_tapped_early or keys_released):
                break


# ---------------------------------------------------------------------------
# createTaskBlockTrials (acceptance + real trial + loading bar)
# ---------------------------------------------------------------------------


@dataclass
class AcceptanceRunners:
    acceptance: Callable[[Tuple[float, float], Tuple[float, float], float, Tuple[float, float]], dict]
    loading_bar: Callable[[bool], None]


def run_task_block_trials(
    state,
    history: TrialHistory,
    delay: str,
    acceptance_runners: AcceptanceRunners,
    task_runners: TaskTrialRunners,
) -> None:
    """Port of createTaskBlockTrials."""
    for combo in generate_task_block_permutations(state):
        bounds_type, reward_type = combo['bounds'], combo['reward']
        actual = resolve_actual_trial_params(bounds_type, reward_type, delay)
        random_skip = resolve_random_skip(state)

        acceptance_record = acceptance_runners.acceptance(
            actual['bounds'], BOUNDS_DEFINITIONS[bounds_type], actual['reward'], actual['delay']
        )
        history.add({**acceptance_record, 'trial_type': 'html-button-response'})

        if check_flag(history, 'html-button-response', 'accepted'):
            run_generate_task_trial(
                state,
                history,
                task_runners,
                actual['bounds'],
                actual['reward'],
                actual['delay'],
                delay,
                demo=False,
                random_skip=random_skip,
            )
        else:
            acceptance_runners.loading_bar(False)


# ---------------------------------------------------------------------------
# createRewardDisplayTrial
# ---------------------------------------------------------------------------


def resolve_reward_display(history: TrialHistory, state) -> dict:
    """Port of createRewardDisplayTrial's stimulus/on_finish."""
    total_successful_reward = calculate_total_reward(history, state)
    total_points = calculate_total_points(state)
    current_reward_money = round((total_successful_reward / total_points) * TOTAL_REWARD_MONEY, 2) if total_points else 0
    return {
        'task': 'display_reward',
        'totalReward': total_successful_reward,
        'totalPoints': total_points,
        'currentRewardMoney': current_reward_money,
        'currency': CURRENCY,
    }


def finish_reward_display(state) -> None:
    """Port of createRewardDisplayTrial's `state.incrementCompletedBlocks()`."""
    state.increment_completed_blocks()


# ---------------------------------------------------------------------------
# createBreakTrial + generateTaskTrialBlock's break-visibility gate
# ---------------------------------------------------------------------------


def resolve_break_allow_skip(index: int) -> bool:
    """Port of createBreakTrial's `allowSkip = index % 2 === 0`.

    NOTE: see module docstring, point 2 -- this is always False whenever
    `should_show_break` (below) is True, because the two conditions use
    opposite parities. Preserved as-is.
    """
    return index % 2 == 0


def should_show_break(state, index: int) -> bool:
    """Port of generateTaskTrialBlock's break-wrapper conditional_function."""
    task_settings = state.get_task_settings()
    total_blocks = (
        len(task_settings.taskCustomSequence)
        if task_settings.taskSequencingMode == 'custom'
        else len(task_settings.taskBlocksIncluded) * task_settings.taskBlockRepetitions
    )
    return index % 2 == 1 and index != total_blocks - 1


def checkpoint_last_trial(history: TrialHistory, phase: str, block_number: int) -> None:
    """Port of the break-wrapper's on_timeline_start mutation of the last
    recorded trial (`lastTrial.checkpoint = ...; lastTrial.checkpointBlock = ...`)."""
    last_trial = history.last_value()
    if last_trial is not None:
        last_trial['checkpoint'] = phase
        last_trial['checkpointBlock'] = block_number


# ---------------------------------------------------------------------------
# buildTaskCore -- overall block-sequencing entry point
# ---------------------------------------------------------------------------


@dataclass
class TaskBlockScreenRunners:
    """Screens surrounding a delay block's trials that generateTaskTrialBlock
    (jspsych/trials.ts) shows but which involve no branching logic worth
    unit-testing on their own -- each is a single one-off screen, wired
    to a real PsychoPy render call in main.py. `break_screen` additionally
    covers createBreakTrial (jspsych/trials.ts), the EBDM task's own
    break screen, distinct from the agency task's break
    (parts/agency_task_core.py's `run_break`)."""

    demo_intro: Callable[[], dict]
    likert_1: Callable[[], dict]
    reminder: Callable[[], dict]
    likert_intro: Callable[[], dict]
    likert_2: Callable[[], dict]
    likert_final: Callable[[], dict]
    break_screen: Callable[[bool], None]  # (allow_skip) -> None


def run_task_trial_block(
    state,
    history: TrialHistory,
    delay: str,
    index: int,
    task_runners: TaskTrialRunners,
    acceptance_runners: AcceptanceRunners,
    screen_runners: TaskBlockScreenRunners,
) -> None:
    """Port of generateTaskTrialBlock's full per-delay-block sequence:
    demo intro -> demo trials -> Likert 1 -> reminder -> real trials ->
    Likert intro -> Likert 2 -> Likert final -> reward display -> break
    (conditional)."""
    demo_intro_record = screen_runners.demo_intro()
    history.add({**demo_intro_record, 'trial_type': 'html-button-response'})

    run_task_block_demo(state, history, task_runners, delay)

    likert_1_record = screen_runners.likert_1()
    history.add({**likert_1_record, 'trial_type': 'survey-likert'})

    reminder_record = screen_runners.reminder()
    history.add({**reminder_record, 'trial_type': 'html-button-response'})

    run_task_block_trials(state, history, delay, acceptance_runners, task_runners)

    likert_intro_record = screen_runners.likert_intro()
    history.add({**likert_intro_record, 'trial_type': 'html-button-response'})

    likert_2_record = screen_runners.likert_2()
    history.add({**likert_2_record, 'trial_type': 'survey-likert'})

    likert_final_record = screen_runners.likert_final()
    history.add({**likert_final_record, 'trial_type': 'survey-likert'})

    history.add({**resolve_reward_display(history, state), 'trial_type': 'html-button-response'})
    finish_reward_display(state)

    if should_show_break(state, index):
        checkpoint_last_trial(history, state.get_state()['phase'], index + 1)
        screen_runners.break_screen(resolve_break_allow_skip(index))


def resolve_trial_block_sequence(state, remaining_trial_blocks: Optional[List[str]] = None) -> Tuple[List[str], int]:
    """Port of buildTaskCore's trial-block/trialBlockStart resolution.
    Returns (trial_block, trial_block_start_index)."""
    task_settings = state.get_task_settings()
    is_custom = task_settings.taskSequencingMode == 'custom'

    trial_block_start = 0
    if remaining_trial_blocks is not None:
        total_blocks = (
            len(task_settings.taskCustomSequence)
            if is_custom
            else task_settings.taskBlockRepetitions * len(task_settings.taskBlocksIncluded)
        )
        trial_block_start = total_blocks - len(remaining_trial_blocks)

    if remaining_trial_blocks is not None:
        trial_block = remaining_trial_blocks
    elif is_custom:
        trial_block = list(task_settings.taskCustomSequence)
    else:
        trial_block = generate_trial_order(state)

    return trial_block, trial_block_start
