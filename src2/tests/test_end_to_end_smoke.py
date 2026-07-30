"""End-to-end smoke test (milestone 10).

Drives the full ExperimentRunner -> parts/*.py orchestration chain with
deterministic, always-clean fake trial outcomes (no procedural errors,
always enough taps, interruption always answered) so every loop
terminates in the minimum number of iterations. This is the one test
that exercises every module's composition together, rather than each
module in isolation -- it would catch integration mistakes (wrong
runner signatures, wrong trial_type strings for TrialHistory filtering,
wrong field names) that per-module unit tests can't.

Settings are shrunk to the smallest configuration that still exercises
every phase (1 delay block, 1 bounds level, 1 reward level, 2 agency
trials) so the test runs in milliseconds rather than minutes.
"""

from __future__ import annotations

import json
from pathlib import Path

from src2.config.settings_schema import AllSettingsType
from src2.data.data_writer import DataWriter, RecordingTrialHistory
from src2.experiment_runner import PhaseRunners, run_experiment
from src2.parts.agency_task_core import (
    AgencyBreakRunners,
    AgencyCoreRunners,
    AgencyPracticeRunners,
    run_agency_core_block,
    run_agency_practice_trials,
)
from src2.parts.calibration import CalibrationRunners, run_calibration_loop
from src2.parts.introduction import IntroductionRunners, run_introduction
from src2.parts.practice import run_hold_key_practice_block, run_tapping_practice_block
from src2.parts.task_core import (
    AcceptanceRunners,
    TaskBlockScreenRunners,
    TaskTrialRunners,
    resolve_trial_block_sequence,
    run_task_trial_block,
)
from src2.parts.validation import (
    ValidationFailedError,
    ValidationRunners,
    resolve_validation_result,
    run_validation_trial_loop,
    should_finish_early_after_extra_validation,
    should_run_extra_validation,
)
from src2.state.experiment_state import ExperimentState
from src2.utils.types import BoundsType, CalibrationPartType, DelayType, RewardType, ValidationPartType


def _fake_countdown() -> dict:
    return {'task': 'countdown', 'keyTappedEarlyFlag': False}


def _fake_release_keys() -> dict:
    return {'errorOccurred': False}


def _fake_loading_bar(*_args) -> None:
    return None


def _fake_success_screen(*_args, **_kwargs) -> dict:
    return {'task': 'success', 'success': True}


def _fake_hold_key_practice() -> dict:
    return {'task': 'hold-key-practice', 'success': True}


def _clean_tap_fields(bounds) -> dict:
    mid = (bounds[0] + bounds[1]) / 2
    return {
        'tapCount': 25,
        'keysReleasedFlag': False,
        'keyTappedEarlyFlag': False,
        'success': True,
        'keysState': {'s': True},
        'mercuryHeight': mid,
        'bounds': list(bounds),
    }


def build_experiment(tmp_path: Path, settings: AllSettingsType) -> tuple[ExperimentState, DataWriter, RecordingTrialHistory]:
    state = ExperimentState(settings)
    data_writer = DataWriter('smoke_test_participant', tmp_path, settings)
    history = RecordingTrialHistory(data_writer)
    return state, data_writer, history


def make_phase_runners(state: ExperimentState, history: RecordingTrialHistory) -> PhaseRunners:
    def run_introduction_phase() -> None:
        runners = IntroductionRunners(
            show_begin=lambda: {'task': 'experiment_begin'},
            show_sit_comfortably=lambda: {'task': 'sit_comfortably'},
            show_tutorial_intro=lambda: {'task': 'tutorial_introduction'},
            ask_preferred_hand=lambda: {'response': 1},  # right hand
        )
        run_introduction(state, history, runners)

    def run_practice() -> None:
        run_hold_key_practice_block(history, _fake_hold_key_practice)

        def practice_tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label):
            return _clean_tap_fields((0, 100))

        run_tapping_practice_block(history, _fake_countdown, lambda: practice_tapping(0, False, (0, 0), (0, 100), 0, False, 'practice'), _fake_success_screen, _fake_loading_bar)

    def run_calibration() -> None:
        def tapping(auto_increase_amount, key_tapped_early_flag):
            return _clean_tap_fields((50, 50))

        runners = CalibrationRunners(_fake_countdown, tapping, _fake_release_keys, _fake_success_screen, _fake_loading_bar)
        run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)

    def run_validation() -> None:
        def tapping(auto_increase_amount, key_tapped_early_flag, bounds):
            return _clean_tap_fields(bounds)

        for level in (ValidationPartType.VALIDATION_EASY, ValidationPartType.VALIDATION_MEDIUM, ValidationPartType.VALIDATION_HARD):
            runners = ValidationRunners(_fake_countdown, tapping, _fake_release_keys, _fake_success_screen, _fake_loading_bar)
            run_validation_trial_loop(level.value, state, history, runners)

        if should_run_extra_validation(state):
            runners = ValidationRunners(_fake_countdown, tapping, _fake_release_keys, _fake_success_screen, _fake_loading_bar)
            run_validation_trial_loop(ValidationPartType.VALIDATION_EXTRA.value, state, history, runners)
            if should_finish_early_after_extra_validation(state):
                raise ValidationFailedError()

        history.add({'task': 'validation_amf_likert', 'trial_type': 'survey-likert', 'additional': True, 'validation': True})

        result = resolve_validation_result(state)
        history.add({'task': 'validation_result', 'trial_type': 'html-button-response', **result})

        if result['should_finish_early']:
            raise ValidationFailedError()

    def run_task_core(remaining_trial_blocks) -> None:
        trial_block, start_index = resolve_trial_block_sequence(state, remaining_trial_blocks)

        def tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label):
            return {**_clean_tap_fields(bounds), 'task': task_label}

        def acceptance(bounds, original_bounds, reward, delay):
            return {
                'task': 'accept', 'accepted': True, 'response': 0,
                'bounds': list(bounds), 'originalBounds': list(original_bounds),
                'reward': reward, 'delay': list(delay),
            }

        task_runners = TaskTrialRunners(_fake_countdown, tapping, _fake_release_keys, _fake_success_screen, _fake_success_screen, _fake_loading_bar)
        acceptance_runners = AcceptanceRunners(acceptance, _fake_loading_bar)

        def make_screen_runners() -> TaskBlockScreenRunners:
            return TaskBlockScreenRunners(
                demo_intro=lambda: {'task': 'demo_intro'},
                likert_1=lambda: {'response': {'QUESTION_1': 4, 'QUESTION_2': 4}},
                reminder=lambda: {'task': 'remember_direction'},
                likert_intro=lambda: {'task': 'likert_intro'},
                likert_2=lambda: {'response': {}},
                likert_final=lambda: {'response': {}, 'additional': True, 'validation': True},
                break_screen=lambda allow_skip: history.add({'task': 'break', 'trial_type': 'html-button-response'}),
            )

        for i, delay in enumerate(trial_block):
            index = start_index + i
            run_task_trial_block(state, history, delay, index, task_runners, acceptance_runners, make_screen_runners())

    def run_final_calibration() -> None:
        def tapping(auto_increase_amount, key_tapped_early_flag):
            return _clean_tap_fields((50, 50))

        runners = CalibrationRunners(_fake_countdown, tapping, _fake_release_keys, _fake_success_screen, _fake_loading_bar)
        run_calibration_loop(CalibrationPartType.FINAL_CALIBRATION_PART_2.value, state, history, runners)

    def run_agency_task_core() -> None:
        def practice_tapping():
            record = _clean_tap_fields((30, 50))
            record.update({'task': 'practice', 'interruptionResponse': 'y', 'delayOriginal': 0})
            return record

        practice_runners = AgencyPracticeRunners(_fake_countdown, practice_tapping, _fake_release_keys, _fake_loading_bar)
        run_agency_practice_trials(state, history, practice_runners)

        def core_tapping(selected_delay):
            record = _clean_tap_fields((30, 50))
            record.update({'task': 'core', 'interruptionResponse': 'y', 'delayOriginal': selected_delay})
            return record

        core_runners = AgencyCoreRunners(_fake_countdown, core_tapping, _fake_release_keys, _fake_loading_bar)
        break_runners = AgencyBreakRunners(lambda break_number, allow_skip: history.add({'task': 'agency_break', 'trial_type': 'html-button-response'}))
        run_agency_core_block(state, history, core_runners, break_runners)

    return PhaseRunners(
        run_device_connect=lambda: None,
        run_introduction=run_introduction_phase,
        run_practice=run_practice,
        run_calibration=run_calibration,
        run_validation=run_validation,
        run_continue_message=lambda: None,
        run_task_core=run_task_core,
        run_final_calibration=run_final_calibration,
        run_agency_task_core=run_agency_task_core,
        run_end_of_agency_break=lambda: None,
        run_end_page=lambda: None,
    )


def _make_smoke_settings() -> AllSettingsType:
    settings = AllSettingsType()
    settings.taskSettings.taskBlockRepetitions = 1
    settings.taskSettings.taskBlocksIncluded = [DelayType.SYNC.value]
    settings.taskSettings.taskBoundsIncluded = [BoundsType.EASY.value]
    settings.taskSettings.taskRewardsIncluded = [RewardType.LOW.value]
    settings.taskSettings.taskPermutationRepetitions = 1
    settings.agencyTaskSettings.numberOfTrials = 2
    settings.agencyTaskSettings.numberOfPracticeTrials = 1
    settings.agencyTaskSettings.breakFrequency = 10
    # Calibration settings are intentionally left at their defaults (3
    # required trials each for CalibrationPart2/FinalCalibrationPart2):
    # ExperimentState.get_calibration_part2_final_mts() computes
    # max(2nd, 3rd tap count) and is hardcoded to expect exactly 3
    # trials regardless of the requiredTrialsCalibration setting. Fewer
    # than 3 trials leaves the final-calibration seed at 0, which is a
    # pre-existing division-by-zero edge case in auto_increase_amount_
    # calculation present in both the original app and this port (not
    # something to route around here).
    return settings


def test_full_fresh_session_end_to_end(tmp_path: Path):
    settings = _make_smoke_settings()
    state, data_writer, history = build_experiment(tmp_path, settings)
    runners = make_phase_runners(state, history)

    run_experiment(state, None, runners)
    session_path = data_writer.finalize()

    assert session_path.exists()
    with session_path.open(encoding='utf-8') as fh:
        result = json.load(fh)

    assert result['settings']['agencyTaskSettings']['numberOfTrials'] == 2
    trials = result['rawData']['trials']
    assert len(trials) > 20  # practice + calibration + validation + EBDM + agency all recorded

    task_types = {t.get('trial_type') for t in trials}
    assert 'task-plugin' in task_types
    assert 'countdown-trial' in task_types
    assert 'html-button-response' in task_types

    # Agency core trials should carry ADO delay + interruption response.
    agency_core_trials = [t for t in trials if t.get('task') == 'core']
    assert len(agency_core_trials) == 2
    assert all(t['interruptionResponse'] == 'y' for t in agency_core_trials)
    assert agency_core_trials[0]['delayOriginal'] == 0  # first SEED_DELAYS entry

    # EBDM block should have produced an accepted trial and a reward display.
    assert any(t.get('task') == 'block' for t in trials)
    assert any(t.get('task') == 'display_reward' for t in trials)

    # Calibration should have updated the median-taps seed away from default.
    assert state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value] == 25

    # Introduction should have recorded its screens and set the preferred hand.
    assert state.get_preferred_hand() == 'right'
    assert any(t.get('task') == 'preferred_hand' for t in trials)

    # Newly-wired task-core per-block screens (demo intro, reminder, likert
    # intro) and the validation AMF likert should all have been recorded.
    assert any(t.get('task') == 'demo_intro' for t in trials)
    assert any(t.get('task') == 'remember_direction' for t in trials)
    assert any(t.get('task') == 'likert_intro' for t in trials)
    assert any(t.get('task') == 'validation_amf_likert' for t in trials)
    assert any(t.get('trial_type') == 'survey-likert' for t in trials)


def test_resumed_session_end_to_end_skips_intro_and_reuses_checkpoint(tmp_path: Path):
    settings = _make_smoke_settings()

    # First run: fresh session, stop after calibration+validation by
    # checkpointing manually (simulating a crash before EBDM/agency).
    state1, data_writer1, history1 = build_experiment(tmp_path, settings)
    state1.set_preferred_hand('left')
    data_writer1.checkpoint(phase='EBDM', state=state1, remaining_trial_blocks=[DelayType.SYNC.value])

    # Second run: resume from the checkpoint.
    data_writer2 = DataWriter('smoke_test_participant', tmp_path, settings)
    reload_object = data_writer2.load_reload_object()
    assert reload_object is not None
    assert reload_object.phase == 'EBDM'

    state2 = ExperimentState(settings)
    from src2.state.reload import apply_reload_object

    apply_reload_object(state2, reload_object)
    # NOTE (discovered gap, present in both codebases, not fixed here):
    # ReloadObject only restores the derived `medianTaps` seed, not the
    # raw `calibrationPart2TapCounts` history that
    # get_calibration_part2_final_mts() needs. A session resumed past
    # calibration would hit the same division-by-zero in
    # auto_increase_amount_calculation when it later reaches final
    # calibration, in both the original TS app and this port, since
    # neither preserves that raw list across a reload. Simulating a
    # completed calibration here (as a fuller resume implementation
    # would need to) so this test can focus on verifying the
    # resume/branching behavior instead.
    for tap_count in (25, 25, 25):
        state2.push_calibration_part2_tap_count(tap_count)
    history2 = RecordingTrialHistory(data_writer2, trials=data_writer2.trials)
    runners2 = make_phase_runners(state2, history2)

    run_experiment(state2, reload_object, runners2)
    session_path = data_writer2.finalize()

    with session_path.open(encoding='utf-8') as fh:
        result = json.load(fh)

    trials = result['rawData']['trials']
    # Resuming into 'EBDM' phase under default EBDMFirst order shows EBDM
    # (still in progress) and agency (always shown under EBDMFirst), but
    # not introduction/practice/calibration/validation again.
    assert not any(t.get('task') == 'hold-key-practice' for t in trials)
    assert any(t.get('task') == 'block' for t in trials)
    assert any(t.get('task') == 'core' for t in trials)
    assert state2.get_preferred_hand() == 'left'
