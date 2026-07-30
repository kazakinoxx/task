"""Agency task core -- port of
src/modules/experiment/parts/agency-task-core.ts.

Unlike task-core.ts's break-visibility bug (see task_core.py), the
agency break's own `allowSkip` parity (breakNumber % 2 == 1) is not
gated by any conflicting outer condition here -- breaks are inserted
directly into the sequence at `t % breakFrequency == 0` (t > 0), so
`resolve_agency_break_allow_skip` behaves as intended.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from src2.ado.ado_selector import get_next_delay_level
from src2.utils.trial_history import TrialHistory, check_keys, check_last_agency_trial_question_answered


@dataclass
class AgencyPracticeRunners:
    countdown: Callable[[], dict]
    tapping: Callable[[], dict]  # delay is always 0 for practice
    release_keys: Callable[[], dict]
    loading_bar: Callable[[], None]


@dataclass
class AgencyCoreRunners:
    countdown: Callable[[], dict]
    tapping: Callable[[float], dict]  # (selected_delay) -> record
    release_keys: Callable[[], dict]
    loading_bar: Callable[[], None]


def run_agency_practice_trial(history: TrialHistory, runners: AgencyPracticeRunners) -> None:
    """Port of one iteration of createAgencyTappingPracticeTrials's
    Array.from(...) loop -- repeats the countdown/trial/release/loading-bar
    sequence until the agency question has been answered."""
    while True:
        countdown_record = runners.countdown()
        history.add({**countdown_record, 'trial_type': 'countdown-trial'})

        tapping_record = runners.tapping()
        history.add({**tapping_record, 'trial_type': 'task-plugin'})

        if check_keys(history):
            release_record = runners.release_keys()
            history.add({**release_record, 'trial_type': 'release-keys'})

        runners.loading_bar()

        if check_last_agency_trial_question_answered(history, 'practice'):
            break


def run_agency_practice_trials(
    state, history: TrialHistory, runners: AgencyPracticeRunners
) -> None:
    """Port of createAgencyTappingPracticeTrials -- runs
    numberOfPracticeTrials independent practice blocks."""
    number_of_practice_trials = state.get_agency_task_settings().numberOfPracticeTrials
    for _ in range(number_of_practice_trials):
        run_agency_practice_trial(history, runners)


def run_agency_core_trial(
    state, history: TrialHistory, runners: AgencyCoreRunners
) -> float:
    """Port of agencyCoreBlockTappingTask. The ADO-selected delay is
    computed ONCE per call (mirroring `on_timeline_start`), then reused
    across every retry of the inner countdown/trial/release/loading-bar
    sequence until the agency question has actually been answered.
    Returns the selected delay (useful for tests/telemetry)."""
    selected_delay = get_next_delay_level(history, state)

    while True:
        countdown_record = runners.countdown()
        history.add({**countdown_record, 'trial_type': 'countdown-trial'})

        tapping_record = runners.tapping(selected_delay)
        history.add({**tapping_record, 'trial_type': 'task-plugin'})

        if check_keys(history):
            release_record = runners.release_keys()
            history.add({**release_record, 'trial_type': 'release-keys'})

        runners.loading_bar()

        if check_last_agency_trial_question_answered(history, 'core'):
            break

    return selected_delay


def resolve_agency_break_allow_skip(break_number: int) -> bool:
    """Port of agencyTappingBreakTrial's `allowSkip = breakNumber % 2 === 1`."""
    return break_number % 2 == 1


def should_insert_agency_break(trial_index: int, break_frequency: int) -> bool:
    """Port of `if (t > 0 && t % breakFrequency === 0)` in
    buildCoreAgencyTappingTask."""
    return trial_index > 0 and trial_index % break_frequency == 0


def agency_break_number(trial_index: int, break_frequency: int) -> int:
    """Port of `Math.floor(t / breakFrequency)`."""
    return trial_index // break_frequency


def resolve_agency_trial_range(state) -> range:
    """Port of buildCoreAgencyTappingTask's starting_trial/numberOfTrials
    resolution -- resumes from where a prior session's ADO history left
    off (state.previousTrials), same source get_next_delay_level draws
    from."""
    previous_trials = state.get_state().get('previousTrials')
    starting_trial = len(previous_trials) if previous_trials else 0
    number_of_trials = state.get_agency_task_settings().numberOfTrials
    return range(starting_trial, number_of_trials)


@dataclass
class AgencyBreakRunners:
    run_break: Callable[[int, bool], None]  # (break_number, allow_skip) -> None


def run_agency_core_block(
    state,
    history: TrialHistory,
    core_runners: AgencyCoreRunners,
    break_runners: AgencyBreakRunners,
) -> List[float]:
    """Port of buildCoreAgencyTappingTask -- sequences breaks and core
    trials together. Returns the list of ADO-selected delays used, in
    order (for tests/telemetry)."""
    break_frequency = state.get_agency_task_settings().breakFrequency
    selected_delays: List[float] = []

    for t in resolve_agency_trial_range(state):
        if should_insert_agency_break(t, break_frequency):
            break_number = agency_break_number(t, break_frequency)
            break_runners.run_break(break_number, resolve_agency_break_allow_skip(break_number))
        selected_delays.append(run_agency_core_trial(state, history, core_runners))

    return selected_delays
