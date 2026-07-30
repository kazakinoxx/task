import pytest

from src2.config.settings_schema import AllSettingsType
from src2.parts.agency_task_core import (
    AgencyBreakRunners,
    AgencyCoreRunners,
    AgencyPracticeRunners,
    agency_break_number,
    resolve_agency_break_allow_skip,
    resolve_agency_trial_range,
    run_agency_core_block,
    run_agency_core_trial,
    run_agency_practice_trial,
    run_agency_practice_trials,
    should_insert_agency_break,
)
from src2.state.experiment_state import ExperimentState
from src2.utils.trial_history import TrialHistory


def make_state(**agency_overrides) -> ExperimentState:
    settings = AllSettingsType()
    for key, value in agency_overrides.items():
        setattr(settings.agencyTaskSettings, key, value)
    return ExperimentState(settings)


# ---------------------------------------------------------------------------
# practice trials
# ---------------------------------------------------------------------------


def test_run_agency_practice_trial_retries_until_question_answered():
    history = TrialHistory()
    outcomes = iter([None, 'y'])  # first trial unanswered, second answered
    calls = {'countdown': 0, 'tapping': 0, 'loading_bar': 0}

    def countdown():
        calls['countdown'] += 1
        return {'task': 'countdown', 'keyTappedEarlyFlag': False}

    def tapping():
        calls['tapping'] += 1
        return {
            'task': 'practice',
            'tapCount': 3,
            'keysReleasedFlag': False,
            'keyTappedEarlyFlag': False,
            'success': True,
            'keysState': {'s': True},
            'interruptionResponse': next(outcomes),
        }

    def release_keys():
        return {'errorOccurred': False}

    def loading_bar():
        calls['loading_bar'] += 1

    runners = AgencyPracticeRunners(countdown, tapping, release_keys, loading_bar)
    run_agency_practice_trial(history, runners)

    assert calls['tapping'] == 2
    assert calls['loading_bar'] == 2


def test_run_agency_practice_trials_runs_configured_count():
    state = make_state(numberOfPracticeTrials=3)
    history = TrialHistory()

    def countdown():
        return {'task': 'countdown', 'keyTappedEarlyFlag': False}

    def tapping():
        return {
            'task': 'practice', 'tapCount': 3, 'keysReleasedFlag': False,
            'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True},
            'interruptionResponse': 'y',
        }

    def release_keys():
        return {'errorOccurred': False}

    calls = {'loading_bar': 0}

    def loading_bar():
        calls['loading_bar'] += 1

    runners = AgencyPracticeRunners(countdown, tapping, release_keys, loading_bar)
    run_agency_practice_trials(state, history, runners)

    assert calls['loading_bar'] == 3  # one clean trial per practice block


# ---------------------------------------------------------------------------
# core trial (ADO delay reused across retries)
# ---------------------------------------------------------------------------


def test_run_agency_core_trial_reuses_same_delay_across_retries():
    state = ExperimentState()
    history = TrialHistory()
    outcomes = iter([None, None, 'n'])  # two unanswered retries, then answered
    delays_seen = []

    def countdown():
        return {'task': 'countdown', 'keyTappedEarlyFlag': False}

    def tapping(selected_delay):
        delays_seen.append(selected_delay)
        return {
            'task': 'core', 'tapCount': 6, 'keysReleasedFlag': False,
            'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True},
            'delayOriginal': selected_delay, 'interruptionResponse': next(outcomes),
        }

    def release_keys():
        return {'errorOccurred': False}

    calls = {'loading_bar': 0}

    def loading_bar():
        calls['loading_bar'] += 1

    runners = AgencyCoreRunners(countdown, tapping, release_keys, loading_bar)
    selected = run_agency_core_trial(state, history, runners)

    assert len(delays_seen) == 3
    assert all(d == selected for d in delays_seen)  # same delay reused every retry
    assert calls['loading_bar'] == 3
    # First-ever core trial with no seed history -> SEED_DELAYS[0] == 0
    assert selected == 0


# ---------------------------------------------------------------------------
# break scheduling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('break_number,expected', [(0, False), (1, True), (2, False), (3, True)])
def test_resolve_agency_break_allow_skip_parity(break_number, expected):
    assert resolve_agency_break_allow_skip(break_number) == expected


def test_should_insert_agency_break_and_break_number():
    assert should_insert_agency_break(0, 10) is False  # t=0 never triggers a break
    assert should_insert_agency_break(10, 10) is True
    assert should_insert_agency_break(15, 10) is False
    assert agency_break_number(20, 10) == 2


def test_resolve_agency_trial_range_fresh_session():
    state = ExperimentState()
    state.get_agency_task_settings().numberOfTrials = 40
    trial_range = resolve_agency_trial_range(state)
    assert list(trial_range) == list(range(0, 40))


def test_resolve_agency_trial_range_resumed_session():
    state = ExperimentState()
    state.get_agency_task_settings().numberOfTrials = 40
    state.set_previous_trials([{'delay': 0, 'response': 'y', 'responseNumeric': 1}] * 12)
    trial_range = resolve_agency_trial_range(state)
    assert list(trial_range) == list(range(12, 40))


# ---------------------------------------------------------------------------
# full block integration
# ---------------------------------------------------------------------------


def test_run_agency_core_block_inserts_breaks_at_correct_points():
    state = ExperimentState()
    state.get_agency_task_settings().numberOfTrials = 12
    state.get_agency_task_settings().breakFrequency = 5
    history = TrialHistory()

    def countdown():
        return {'task': 'countdown', 'keyTappedEarlyFlag': False}

    def tapping(selected_delay):
        return {
            'task': 'core', 'tapCount': 6, 'keysReleasedFlag': False,
            'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True},
            'delayOriginal': selected_delay, 'interruptionResponse': 'y',
        }

    def release_keys():
        return {'errorOccurred': False}

    def loading_bar():
        pass

    core_runners = AgencyCoreRunners(countdown, tapping, release_keys, loading_bar)

    breaks_seen = []

    def run_break(break_number, allow_skip):
        breaks_seen.append((break_number, allow_skip))

    break_runners = AgencyBreakRunners(run_break)

    delays = run_agency_core_block(state, history, core_runners, break_runners)

    assert len(delays) == 12
    # Breaks inserted at t=5 (break_number=1) and t=10 (break_number=2).
    assert breaks_seen == [(1, True), (2, False)]
