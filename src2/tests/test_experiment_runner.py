import pytest

from src2.config.settings_schema import AllSettingsType
from src2.experiment_runner import PhaseRunners, resolve_should_show_agency, resolve_should_show_ebdm, run_experiment
from src2.state.experiment_state import ExperimentState
from src2.state.reload import ReloadObject


def make_state(**general_overrides) -> ExperimentState:
    settings = AllSettingsType()
    for key, value in general_overrides.items():
        setattr(settings.generalSettings, key, value)
    return ExperimentState(settings)


def make_recording_runners():
    calls = []

    def recorder(name):
        def fn(*args):
            calls.append((name, args[0] if args else None))
        return fn

    runners = PhaseRunners(
        run_device_connect=recorder('device_connect'),
        run_introduction=recorder('introduction'),
        run_practice=recorder('practice'),
        run_calibration=recorder('calibration'),
        run_validation=recorder('validation'),
        run_continue_message=recorder('continue_message'),
        run_task_core=recorder('task_core'),
        run_final_calibration=recorder('final_calibration'),
        run_agency_task_core=recorder('agency_task_core'),
        run_end_of_agency_break=recorder('end_of_agency_break'),
        run_end_page=recorder('end_page'),
    )
    return runners, calls


# ---------------------------------------------------------------------------
# should-show predicates
# ---------------------------------------------------------------------------


def test_should_show_ebdm_fresh_session_default_order():
    state = make_state()
    assert resolve_should_show_ebdm(state.get_general_settings(), None) is True


def test_should_show_ebdm_false_when_skipped():
    state = make_state(skipEBDMTask=True)
    assert resolve_should_show_ebdm(state.get_general_settings(), None) is False


def test_should_show_ebdm_resumed_at_ebdm_phase():
    state = make_state(taskOrder='EBDMFirst')
    reload_object = ReloadObject(phase='EBDM', medianTaps={}, totalReward=0, preferredHand='right')
    assert resolve_should_show_ebdm(state.get_general_settings(), reload_object) is True


def test_should_show_ebdm_resumed_at_agency_phase_ebdm_first_order():
    # Resuming into 'agency' under EBDMFirst order means EBDM already
    # finished -- should NOT show EBDM again.
    state = make_state(taskOrder='EBDMFirst')
    reload_object = ReloadObject(phase='agency', medianTaps={}, totalReward=0, preferredHand='right')
    assert resolve_should_show_ebdm(state.get_general_settings(), reload_object) is False


def test_should_show_ebdm_resumed_at_agency_phase_agency_first_order():
    # Under AgencyFirst order, resuming into 'agency' means EBDM hasn't
    # run yet -- should show EBDM after agency finishes.
    state = make_state(taskOrder='AgencyFirst')
    reload_object = ReloadObject(phase='agency', medianTaps={}, totalReward=0, preferredHand='right')
    assert resolve_should_show_ebdm(state.get_general_settings(), reload_object) is True


def test_should_show_agency_always_true_under_ebdm_first_order_regardless_of_reload():
    state = make_state(taskOrder='EBDMFirst')
    reload_object = ReloadObject(phase='EBDM', medianTaps={}, totalReward=0, preferredHand='right')
    assert resolve_should_show_agency(state.get_general_settings(), reload_object) is True


def test_should_show_agency_resumed_agency_first_order_requires_agency_phase():
    state = make_state(taskOrder='AgencyFirst')
    reload_ebdm_phase = ReloadObject(phase='EBDM', medianTaps={}, totalReward=0, preferredHand='right')
    reload_agency_phase = ReloadObject(phase='agency', medianTaps={}, totalReward=0, preferredHand='right')
    assert resolve_should_show_agency(state.get_general_settings(), reload_ebdm_phase) is False
    assert resolve_should_show_agency(state.get_general_settings(), reload_agency_phase) is True


def test_should_show_agency_false_when_skipped():
    state = make_state(skipAgencyTask=True, taskOrder='EBDMFirst')
    assert resolve_should_show_agency(state.get_general_settings(), None) is False


# ---------------------------------------------------------------------------
# full run_experiment sequencing
# ---------------------------------------------------------------------------


def test_fresh_session_default_order_runs_full_sequence_with_break():
    state = make_state(taskOrder='EBDMFirst', useDevice=False)
    runners, calls = make_recording_runners()
    run_experiment(state, None, runners)

    names = [c[0] for c in calls]
    assert names == [
        'introduction', 'practice', 'calibration', 'validation',
        'task_core', 'final_calibration', 'end_of_agency_break', 'agency_task_core',
        'end_page',
    ]


def test_fresh_session_agency_first_order_flips_sequence():
    state = make_state(taskOrder='AgencyFirst', useDevice=False)
    runners, calls = make_recording_runners()
    run_experiment(state, None, runners)

    names = [c[0] for c in calls]
    assert names == [
        'introduction', 'practice', 'calibration', 'validation',
        'agency_task_core', 'end_of_agency_break', 'task_core', 'final_calibration',
        'end_page',
    ]


def test_no_break_when_one_task_skipped():
    state = make_state(taskOrder='EBDMFirst', skipAgencyTask=True)
    runners, calls = make_recording_runners()
    run_experiment(state, None, runners)

    names = [c[0] for c in calls]
    assert 'end_of_agency_break' not in names
    assert 'agency_task_core' not in names
    assert 'task_core' in names


def test_device_connect_only_when_use_device_enabled():
    state = make_state(useDevice=True)
    runners, calls = make_recording_runners()
    run_experiment(state, None, runners)
    assert calls[0][0] == 'device_connect'

    state2 = make_state(useDevice=False)
    runners2, calls2 = make_recording_runners()
    run_experiment(state2, None, runners2)
    assert 'device_connect' not in [c[0] for c in calls2]


def test_resumed_session_shows_continue_message_not_intro_sequence():
    state = make_state(taskOrder='EBDMFirst')
    reload_object = ReloadObject(phase='EBDM', medianTaps={}, totalReward=0, preferredHand='right')
    runners, calls = make_recording_runners()
    run_experiment(state, reload_object, runners)

    names = [c[0] for c in calls]
    assert 'continue_message' in names
    assert 'introduction' not in names
    assert 'practice' not in names
    assert 'calibration' not in names
    assert 'validation' not in names
    assert 'task_core' in names   # EBDM phase -> still show EBDM
    assert 'agency_task_core' in names  # EBDMFirst order -> agency always shows


def test_resumed_session_remaining_trial_blocks_passed_through():
    state = make_state(taskOrder='EBDMFirst')
    remaining = ['sync', 'midasync']
    reload_object = ReloadObject(
        phase='EBDM', medianTaps={}, totalReward=0, preferredHand='right', remainingTrialBlocks=remaining
    )
    runners, calls = make_recording_runners()
    run_experiment(state, reload_object, runners)

    task_core_call = next(c for c in calls if c[0] == 'task_core')
    assert task_core_call[1] == remaining


def test_end_page_always_shown():
    # The end page is always shown as the final screen: run_end_page renders
    # either the next-step link or a generic "experiment has ended" message,
    # so it must run whether or not linkToNextPage is configured.
    settings = AllSettingsType()
    settings.nextStepSettings.linkToNextPage = True
    state = ExperimentState(settings)
    runners, calls = make_recording_runners()
    run_experiment(state, None, runners)
    assert calls[-1][0] == 'end_page'

    settings2 = AllSettingsType()
    state2 = ExperimentState(settings2)
    runners2, calls2 = make_recording_runners()
    run_experiment(state2, None, runners2)
    assert calls2[-1][0] == 'end_page'
