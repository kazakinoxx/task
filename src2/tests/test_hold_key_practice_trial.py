import pytest

from src2.trials.hold_key_practice_trial import (
    FAILURE_FEEDBACK_DURATION,
    SUCCESS_FEEDBACK_DURATION,
    TWITCH_GRACE_SECONDS,
    HoldKeyPracticeParams,
    HoldKeyPracticeState,
)


def make_state(**overrides) -> HoldKeyPracticeState:
    defaults = dict(hold_key='s', hold_duration=5.0)
    defaults.update(overrides)
    return HoldKeyPracticeState(HoldKeyPracticeParams(**defaults))


def test_idle_to_holding_on_keydown():
    state = make_state()
    state.handle_key_down('s', 0.0)
    assert state.phase == 'holding'


def test_holding_to_release_prompt_after_hold_duration():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.tick(4.9)
    assert state.phase == 'holding'
    state.tick(5.0)
    assert state.phase == 'release_prompt'


def test_release_prompt_to_success_feedback_on_keyup():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.tick(5.0)
    assert state.phase == 'release_prompt'
    state.handle_key_up('s', 5.1)
    assert state.phase == 'feedback'
    assert state.success is True

    state.tick(5.1 + SUCCESS_FEEDBACK_DURATION - 0.01)
    assert state.ended is False
    state.tick(5.1 + SUCCESS_FEEDBACK_DURATION + 0.01)
    assert state.ended is True


def test_twitch_within_grace_window_does_not_fail_and_keeps_original_deadline():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.handle_key_up('s', 2.0)  # brief release (twitch)
    state.handle_key_down('s', 2.0 + TWITCH_GRACE_SECONDS / 2)  # recovered in time
    assert state.phase == 'holding'

    # Original hold_deadline (5.0) should be unaffected by the twitch.
    state.tick(4.9)
    assert state.phase == 'holding'
    state.tick(5.0)
    assert state.phase == 'release_prompt'


def test_twitch_grace_expiry_causes_failure():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.handle_key_up('s', 2.0)  # release, grace deadline = 2.0 + 0.3

    state.tick(2.0 + TWITCH_GRACE_SECONDS - 0.05)
    assert state.phase == 'holding'

    state.tick(2.0 + TWITCH_GRACE_SECONDS + 0.01)
    assert state.phase == 'feedback'
    assert state.success is False

    state.tick(2.0 + TWITCH_GRACE_SECONDS + FAILURE_FEEDBACK_DURATION + 0.02)
    assert state.ended is True


def test_hold_elapsing_during_pending_twitch_grace_shows_release_prompt():
    # Key released right as hold_duration is about to elapse; hold_deadline
    # fires before the twitch grace deadline -> release_prompt wins, and
    # the dangling twitch grace timer becomes a no-op (matches the JS
    # `if (currentPhase === 'holding')` guard inside the twitch callback).
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.handle_key_up('s', 4.95)  # twitch grace deadline = 5.25

    state.tick(5.0)  # hold_deadline (5.0) fires before twitch deadline (5.25)
    assert state.phase == 'release_prompt'

    # Advancing further must not retroactively fail the trial.
    state.tick(5.3)
    assert state.phase == 'release_prompt'
    assert state.ended is False


def test_key_events_for_other_keys_are_ignored():
    state = make_state(hold_key='s')
    state.handle_key_down('l', 0.0)
    assert state.phase == 'idle'


def test_build_trial_record():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.tick(5.0)
    state.handle_key_up('s', 5.1)
    assert state.build_trial_record() == {'task': 'hold-key-practice', 'success': True}


def test_hold_progress_is_none_before_holding():
    state = make_state(hold_duration=5.0)
    assert state.hold_progress(0.0) is None


def test_hold_progress_grows_linearly_while_holding():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    assert state.hold_progress(0.0) == 0.0
    assert state.hold_progress(2.5) == pytest.approx(0.5)
    assert state.hold_progress(4.0) == pytest.approx(0.8)


def test_hold_progress_clamped_to_one_when_overdue():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    assert state.hold_progress(6.0) == 1.0


def test_hold_progress_is_none_after_release_prompt():
    state = make_state(hold_duration=5.0)
    state.handle_key_down('s', 0.0)
    state.tick(5.0)
    assert state.phase == 'release_prompt'
    assert state.hold_progress(5.0) is None
