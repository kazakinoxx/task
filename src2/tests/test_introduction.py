from src2.config.settings_schema import AllSettingsType
from src2.parts.introduction import IntroductionRunners, resolve_preferred_hand, run_introduction
from src2.state.experiment_state import ExperimentState
from src2.utils.trial_history import TrialHistory


def test_response_0_is_left_hand():
    assert resolve_preferred_hand(0) == 'left'


def test_response_1_is_right_hand():
    assert resolve_preferred_hand(1) == 'right'


def _fake_runners(response_index: int) -> IntroductionRunners:
    return IntroductionRunners(
        show_begin=lambda: {'task': 'experiment_begin'},
        show_sit_comfortably=lambda: {'task': 'sit_comfortably'},
        show_tutorial_intro=lambda: {'task': 'tutorial_introduction'},
        ask_preferred_hand=lambda: {'response': response_index},
    )


def test_run_introduction_sets_left_hand_and_records_history():
    state = ExperimentState(AllSettingsType())
    history = TrialHistory()

    run_introduction(state, history, _fake_runners(0))

    assert state.get_preferred_hand() == 'left'
    trials = history.all()
    assert [t['task'] for t in trials[:3]] == ['experiment_begin', 'sit_comfortably', 'tutorial_introduction']
    hand_trial = trials[-1]
    assert hand_trial['task'] == 'preferred_hand'
    assert hand_trial['response'] == 0
    assert hand_trial['preferredHand'] == 'left'
    assert hand_trial['trial_type'] == 'html-button-response'


def test_run_introduction_sets_right_hand():
    state = ExperimentState(AllSettingsType())
    history = TrialHistory()

    run_introduction(state, history, _fake_runners(1))

    assert state.get_preferred_hand() == 'right'
    assert history.last_value()['preferredHand'] == 'right'
