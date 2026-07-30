from src2.state.experiment_state import ExperimentState
from src2.state.reload import ReloadObject, apply_reload_object, reload_object_from_dict


def test_apply_reload_object_sets_median_taps_hand_and_reward():
    state = ExperimentState()
    reload_object = ReloadObject(
        phase='EBDM', medianTaps={'calibrationPart2': 18}, totalReward=12, preferredHand='left'
    )
    apply_reload_object(state, reload_object)
    assert state.get_state()['medianTaps'] == {'calibrationPart2': 18}
    assert state.get_preferred_hand() == 'left'
    assert state.get_state()['previousReward'] == 12


def test_apply_reload_object_does_not_set_phase():
    # Matches experiment.ts's reload block, which never writes state.phase
    # directly -- phase is only read from the reload object itself for
    # the should-show-EBDM/Agency branch decisions.
    state = ExperimentState()
    assert state.get_state()['phase'] == 'introduction'
    reload_object = ReloadObject(phase='agency', medianTaps={}, totalReward=0, preferredHand='')
    apply_reload_object(state, reload_object)
    assert state.get_state()['phase'] == 'introduction'  # unchanged


def test_apply_reload_object_skips_falsy_total_reward():
    state = ExperimentState()
    state.set_previous_reward(5)
    reload_object = ReloadObject(phase='EBDM', medianTaps={'calibrationPart2': 10}, totalReward=0, preferredHand='right')
    apply_reload_object(state, reload_object)
    assert state.get_state()['previousReward'] == 5  # untouched, since totalReward=0 is falsy


def test_apply_reload_object_restores_previous_trials_for_ado():
    state = ExperimentState()
    reload_object = ReloadObject(
        phase='agency', medianTaps={}, totalReward=0, preferredHand='',
        previousTrials=[{'delay': 250, 'response': 'y', 'responseNumeric': 1}],
    )
    apply_reload_object(state, reload_object)
    assert state.get_state()['previousTrials'] == [{'delay': 250, 'response': 'y', 'responseNumeric': 1}]


def test_reload_object_from_dict_defaults_previous_trials_to_empty_list():
    data = {'phase': 'EBDM', 'medianTaps': {}, 'totalReward': 0, 'preferredHand': 'right'}
    reload_object = reload_object_from_dict(data)
    assert reload_object.previousTrials == []
    assert reload_object.remainingTrialBlocks is None
