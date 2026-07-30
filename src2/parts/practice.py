"""Practice phase -- port of src/modules/experiment/parts/practice.ts.

Both `holdKeyPracticeBlock` and `tappingPracticeBlock` in the original
share the exact same "loop until N successes or M failures" shape (a
do-while jsPsych nested-timeline loop), just with different success
predicates -- `run_success_failure_loop` captures that shared pattern
once instead of duplicating it.

`run_iteration` / `is_success` are injected callables so the control
flow here is unit-testable without any PsychoPy/rendering dependency;
the real trial runners (tapping_task_trial, hold_key_practice_trial,
etc.) get wired in by experiment_runner.py (milestone 10).
"""

from __future__ import annotations

from typing import Callable, Tuple

from src2.utils.constants import HOLD_KEY_MAX_FAILURES, HOLD_KEY_MIN_SUCCESSES, MINIMUM_CALIBRATION_MEDIAN
from src2.utils.trial_history import TrialHistory, check_last_trial_success


def run_success_failure_loop(
    min_successes: int,
    max_failures: int,
    run_iteration: Callable[[], None],
    is_success: Callable[[], bool],
) -> Tuple[int, int]:
    """Port of the shared `successCount < N && failureCount < M` do-while
    loop pattern used by both practice blocks (and, distinctly, by
    task-core's practice-trial-count settings elsewhere)."""
    success_count = 0
    failure_count = 0
    while True:
        run_iteration()
        if is_success():
            success_count += 1
        else:
            failure_count += 1
        if success_count >= min_successes or failure_count >= max_failures:
            break
    return success_count, failure_count


def run_hold_key_practice_block(history: TrialHistory, run_hold_key_practice_trial: Callable[[], dict]) -> dict:
    """Port of `holdKeyPracticeBlock`."""

    def iteration() -> None:
        record = run_hold_key_practice_trial()
        history.add({**record, 'trial_type': 'hold-key-practice'})

    def is_success() -> bool:
        last = history.last_value()
        return bool(last and last.get('task') == 'hold-key-practice' and last.get('success'))

    success_count, failure_count = run_success_failure_loop(
        HOLD_KEY_MIN_SUCCESSES, HOLD_KEY_MAX_FAILURES, iteration, is_success
    )
    return {'successCount': success_count, 'failureCount': failure_count}


def run_tapping_practice_block(
    history: TrialHistory,
    run_countdown: Callable[[], dict],
    run_practice_tapping: Callable[[], dict],
    run_success_screen: Callable[[], dict],
    run_loading_bar: Callable[[], None],
) -> dict:
    """Port of `tappingPracticeBlock`."""

    def iteration() -> None:
        countdown_record = run_countdown()
        history.add({**countdown_record, 'trial_type': 'countdown-trial'})
        tapping_record = run_practice_tapping()
        history.add({**tapping_record, 'trial_type': 'task-plugin'})
        success_record = run_success_screen()
        history.add({**success_record, 'trial_type': 'success-screen-plugin'})
        run_loading_bar()

    def is_success() -> bool:
        return check_last_trial_success(history, MINIMUM_CALIBRATION_MEDIAN)

    success_count, failure_count = run_success_failure_loop(
        HOLD_KEY_MIN_SUCCESSES, HOLD_KEY_MAX_FAILURES, iteration, is_success
    )
    return {'successCount': success_count, 'failureCount': failure_count}
