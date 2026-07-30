from src2.trials.countdown_trial import CountdownParams, CountdownState, format_countdown_time
from src2.utils.constants import REHOLD_TIMEOUT


def make_state(**overrides) -> CountdownState:
    defaults = dict(keys_to_hold=['s'], key_to_press='l', wait_time=2.0)
    defaults.update(overrides)
    return CountdownState(CountdownParams(**defaults))


def test_format_countdown_time():
    assert format_countdown_time(125000) == '2:05'
    assert format_countdown_time(59000) == '0:59'
    assert format_countdown_time(0) == '0:00'


def test_countdown_starts_when_all_keys_held():
    state = make_state()
    assert state.countdown_active is False
    state.handle_key_down('s', 0.0)
    assert state.countdown_active is True


def test_countdown_ends_after_wait_time():
    state = make_state(wait_time=2.0)
    state.handle_key_down('s', 0.0)
    state.tick(1.9)
    assert state.ended is False
    state.tick(2.0)
    assert state.ended is True


def test_freeze_frame_shown_before_countdown_when_enabled():
    state = make_state(show_freeze_frame=True)
    state.handle_key_down('s', 0.0)
    assert state.freeze_frame_active is True
    assert state.countdown_active is False

    state.tick(2.9)  # before 3s freeze frame elapses
    assert state.freeze_frame_active is True

    state.tick(3.0)
    assert state.freeze_frame_active is False
    assert state.countdown_active is True


def test_early_tap_flag_set_during_countdown():
    state = make_state()
    state.handle_key_down('s', 0.0)  # starts countdown
    state.handle_key_down('l', 0.5)
    assert state.key_tapped_early_flag is True


def test_early_tap_before_countdown_starts_does_not_flag():
    state = make_state()
    # keyToPress pressed before hold keys are down -- countdown/freeze
    # frame not active yet, so no flag.
    state.handle_key_down('l', 0.0)
    assert state.key_tapped_early_flag is False


def test_releasing_hold_key_resets_countdown_and_clears_early_flag_after_grace():
    state = make_state()
    state.handle_key_down('s', 0.0)
    state.handle_key_down('l', 0.5)  # early tap
    assert state.key_tapped_early_flag is True

    state.handle_key_up('s', 1.0)  # release hold key
    assert state.countdown_active is True  # still active until grace elapses

    # before grace period elapses, still active
    state.tick(1.0 + REHOLD_TIMEOUT / 1000.0 - 0.05)
    assert state.countdown_active is True

    # after grace period elapses without re-holding, countdown resets
    state.tick(1.0 + REHOLD_TIMEOUT / 1000.0 + 0.01)
    assert state.countdown_active is False
    assert state.key_tapped_early_flag is False  # cleared on reset


def test_rehold_before_grace_elapses_keeps_countdown_running():
    state = make_state()
    state.handle_key_down('s', 0.0)
    state.handle_key_up('s', 1.0)
    state.handle_key_down('s', 1.0 + REHOLD_TIMEOUT / 1000.0 / 2)
    state.tick(1.0 + REHOLD_TIMEOUT / 1000.0 + 0.01)
    assert state.countdown_active is True
    assert state.ended is False


def test_build_trial_record():
    state = make_state()
    state.handle_key_down('s', 0.0)
    state.handle_key_down('l', 0.5)
    record = state.build_trial_record()
    assert record == {'task': 'countdown', 'keyTappedEarlyFlag': True}
