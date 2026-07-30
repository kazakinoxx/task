import pytest

from src2.trials.tapping_task_trial import TappingTaskParams, TappingTaskState
from src2.utils.constants import (
    AUTO_DECREASE_AMOUNT,
    AUTO_DECREASE_RATE,
    GO_DURATION,
    NUM_TAPS_WITHOUT_DELAY,
    REHOLD_TIMEOUT,
)


def make_state(**overrides) -> TappingTaskState:
    defaults = dict(
        task='block',
        keys_to_hold=['s'],
        key_to_press='l',
        bounds=(45, 75),
        trial_duration=5000,
        auto_increase_amount=10,
    )
    defaults.update(overrides)
    return TappingTaskState(TappingTaskParams(**defaults))


def test_start_running_resets_mercury_and_tap_count():
    state = make_state()
    state.tap_count = 3
    state.mercury_height = 50
    ended = state.start_running(0.0)
    assert ended is False
    assert state.mercury_height == 0
    assert state.tap_count == 0
    assert state.is_running is True
    assert state.start_time == 0.0


def test_tap_increases_mercury_immediately_for_non_demo_block_task():
    state = make_state(task='practice')
    state.start_running(0.0)
    state.handle_key_up('l', 0.1)
    assert state.mercury_height == 10  # auto_increase_amount


def test_tap_beyond_threshold_is_delayed_for_block_task():
    # auto_decrease_amount=0 isolates the delayed-increase behavior under
    # test from the (separately tested) auto-decrease ticking.
    state = make_state(task='block', random_delay=(100, 100), auto_decrease_amount=0)
    state.start_running(0.0)
    for i in range(NUM_TAPS_WITHOUT_DELAY):
        state.handle_key_up('l', 0.01 * i)
    # exactly NUM_TAPS_WITHOUT_DELAY taps applied immediately (tapCount > threshold triggers delay)
    assert state.mercury_height == NUM_TAPS_WITHOUT_DELAY * 10

    # the next (6th) tap should be delayed by ~100ms, not applied immediately
    state.handle_key_up('l', 1.0)
    assert state.mercury_height == NUM_TAPS_WITHOUT_DELAY * 10
    assert state.tap_count == NUM_TAPS_WITHOUT_DELAY + 1

    # tick before the delay elapses -> still not applied
    state.tick(1.05)
    assert state.mercury_height == NUM_TAPS_WITHOUT_DELAY * 10

    # tick after the delay elapses -> now applied
    state.tick(1.11)
    assert state.mercury_height == (NUM_TAPS_WITHOUT_DELAY + 1) * 10


def test_auto_decrease_applies_over_ticks():
    state = make_state()
    state.start_running(0.0)
    state.mercury_height = 50
    # advance by exactly one decrease-rate interval
    state.tick(AUTO_DECREASE_RATE / 1000.0)
    assert state.mercury_height == 50 - AUTO_DECREASE_AMOUNT


def test_mercury_never_exceeds_100_or_drops_below_0():
    state = make_state(auto_increase_amount=1000)
    state.start_running(0.0)
    state.handle_key_up('l', 0.01)
    assert state.mercury_height == 100

    state.mercury_height = 1
    state.tick(state._next_decrease_time + 10)
    assert state.mercury_height == 0


def test_key_held_down_then_release_flags_after_rehold_timeout():
    state = make_state()
    state.start_running(0.0)
    state.handle_key_up('s', 0.5)  # release the hold key
    assert state.are_keys_held is False
    assert state.trial_ended is False

    # before the rehold grace period elapses, nothing happens yet
    state.tick(0.5 + REHOLD_TIMEOUT / 1000.0 - 0.05)
    assert state.trial_ended is False

    # after the grace period elapses without re-holding, trial ends in error
    events = state.tick(0.5 + REHOLD_TIMEOUT / 1000.0 + 0.01)
    assert 'stopped_due_to_release' in events
    assert state.trial_ended is True
    assert state.keys_released_flag is True
    assert state.error_occurred is True


def test_rehold_before_deadline_prevents_trial_end():
    state = make_state()
    state.start_running(0.0)
    state.handle_key_up('s', 0.5)  # release
    state.handle_key_down('s', 0.5 + REHOLD_TIMEOUT / 1000.0 / 2)  # re-hold in time
    assert state.are_keys_held is True

    # even after the original deadline would have fired, trial should not end
    state.tick(0.5 + REHOLD_TIMEOUT / 1000.0 + 0.01)
    assert state.trial_ended is False


def test_success_within_bounds():
    state = make_state(bounds=(45, 75))
    state.start_running(0.0)
    state.mercury_height = 60
    assert state.is_success() is True


def test_success_with_safety_margin():
    state = make_state(bounds=(45, 75))
    state.mercury_height = 44  # just below lower bound but within PATIENT_SAFETY_MARGIN=3
    assert state.is_success() is True

    state.mercury_height = 40  # outside the margin
    assert state.is_success() is False


def test_failure_on_keys_released_flag():
    state = make_state(bounds=(45, 75))
    state.mercury_height = 60
    state.keys_released_flag = True
    assert state.is_success() is False


def test_failure_on_key_tapped_early_flag():
    state = make_state(bounds=(45, 75), key_tapped_early_flag=True)
    state.mercury_height = 60
    assert state.is_success() is False


def test_random_chance_accepted_forces_success_regardless_of_mercury():
    state = make_state(bounds=(45, 75), random_chance_accepted=True)
    state.mercury_height = 0
    assert state.is_success() is True


def test_start_ends_immediately_when_key_tapped_early_flag_set():
    state = make_state(key_tapped_early_flag=True)
    ended = state.start(0.0)
    assert ended is True
    assert state.trial_ended is True
    assert state.error_occurred is True


def test_start_running_short_circuits_on_random_chance_accepted():
    state = make_state(random_chance_accepted=True)
    ended = state.start_running(0.0)
    assert ended is True
    assert state.trial_ended is True
    assert state.error_occurred is False


def test_build_trial_record_field_names_and_median_taps():
    state = make_state(trial_duration=5000, auto_decrease_rate=100, auto_decrease_amount=2, auto_increase_amount=10)
    state.start_running(0.0)
    record = state.build_trial_record()
    assert set(record.keys()) == {
        'tapCount', 'startTime', 'endTime', 'mercuryHeight', 'error', 'bounds',
        'reward', 'task', 'errorOccurred', 'keysReleasedFlag', 'success',
        'keyTappedEarlyFlag', 'keysState', 'medianTaps',
    }
    # (100 + (5000/100)*2) / 10 = (100+100)/10 = 20
    assert record['medianTaps'] == pytest.approx(20)


def test_practice_task_flashes_checkmark_on_tap():
    state = make_state(task='practice')
    state.start_running(0.0)
    ui_events = state.handle_key_up('l', 0.1)
    assert 'flash_checkmark' in ui_events


def test_freeze_frame_first_and_subsequent_tap_events():
    state = make_state(show_freeze_frame=True)
    # Trial hasn't started running yet -- freeze frame awaits the first tap
    ui_events = state.handle_key_up('l', 0.0)
    assert 'freeze_frame_first_tap' in ui_events
    assert state.freeze_frame_state == 'firstTap'

    state.start_running(0.0)
    ui_events = state.handle_key_up('l', 0.2)
    assert 'freeze_frame_subsequent_tap' in ui_events


# ---------------------------------------------------------------------------
# continue-tapping reminder -- port of the 200ms continueReminderInterval
# poller in tapping-task-trial.ts (only active when
# continue_tapping_reminder_message is set, matching practice.ts's
# tappingPracticeBlock, the only original call site that wires it on).
# ---------------------------------------------------------------------------


def test_reminder_never_fires_when_message_not_configured():
    state = make_state(continue_tapping_reminder_message=None, continue_tapping_reminder_delay=700)
    state.start_running(0.0)
    state.handle_key_up('l', 0.0)
    state.tick(10.0)  # way past any reasonable delay
    assert state.showing_continue_reminder is False


def test_reminder_never_fires_before_the_first_tap():
    # JS guard: `tapCount === 0` returns early -- no reminder before any tap.
    state = make_state(continue_tapping_reminder_message='Keep tapping', continue_tapping_reminder_delay=700)
    state.start_running(0.0)
    state.tick(10.0)
    assert state.showing_continue_reminder is False


def test_reminder_fires_after_inactivity_delay_following_a_tap():
    state = make_state(continue_tapping_reminder_message='Keep tapping', continue_tapping_reminder_delay=700)
    state.start_running(0.0)
    state.handle_key_up('l', 1.0)
    assert state.showing_continue_reminder is False  # not yet -- delay hasn't elapsed

    state.tick(1.0 + 0.7 - 0.05)  # just before the 700ms delay
    assert state.showing_continue_reminder is False

    state.tick(1.0 + 0.7 + 0.01)  # just after the 700ms delay
    assert state.showing_continue_reminder is True


def test_tapping_again_clears_the_reminder():
    state = make_state(continue_tapping_reminder_message='Keep tapping', continue_tapping_reminder_delay=700)
    state.start_running(0.0)
    state.handle_key_up('l', 1.0)
    state.tick(1.0 + 0.7 + 0.01)
    assert state.showing_continue_reminder is True

    state.handle_key_up('l', 2.0)  # tap again
    assert state.showing_continue_reminder is False


def test_reminder_resets_on_start_running():
    state = make_state(continue_tapping_reminder_message='Keep tapping', continue_tapping_reminder_delay=700)
    state.start_running(0.0)
    state.handle_key_up('l', 1.0)
    state.tick(1.0 + 0.7 + 0.01)
    assert state.showing_continue_reminder is True

    state.start_running(5.0)  # a fresh trial run
    assert state.showing_continue_reminder is False


# ---------------------------------------------------------------------------
# go-message flash -- port of the #go-message visibility toggle in
# startRunning()/stopRunning() (visible for GO_DURATION ms at trial start).
# Opt-in via flash_go_message (on only for validation); off elsewhere so the
# go text stays in the center continuously instead.
# ---------------------------------------------------------------------------


def test_go_message_shows_immediately_on_start_running():
    state = make_state(flash_go_message=True)
    state.start_running(0.0)
    assert state.showing_go_message is True


def test_go_message_hides_after_go_duration_elapses():
    state = make_state(flash_go_message=True)
    state.start_running(0.0)
    state.tick(GO_DURATION / 1000.0 - 0.01)
    assert state.showing_go_message is True

    state.tick(GO_DURATION / 1000.0 + 0.01)
    assert state.showing_go_message is False


def test_go_message_hidden_immediately_when_trial_stops_early():
    # "REMOVE GO IN CASE IT IS SHOWING FOR SOME REASON BEFORE TRIAL ENDS"
    state = make_state(flash_go_message=True)
    state.start_running(0.0)
    assert state.showing_go_message is True
    state.stop_running(0.05, error_flag=True)
    assert state.showing_go_message is False


def test_go_message_never_shows_on_random_chance_short_circuit():
    state = make_state(flash_go_message=True, random_chance_accepted=True)
    state.start_running(0.0)
    assert state.showing_go_message is False


def test_go_message_never_shows_when_flash_disabled():
    # Default (practice/calibration/demo): go text stays centered, no flash.
    state = make_state()  # flash_go_message defaults to False
    state.start_running(0.0)
    assert state.showing_go_message is False
    state.tick(GO_DURATION / 1000.0 + 0.01)
    assert state.showing_go_message is False
