import pytest

from src2.trials.agency_tapping_task_trial import (
    AgencyTappingTaskParams,
    AgencyTappingTaskState,
    compute_agency_auto_increase_amount,
)
from src2.utils.constants import (
    MIN_TAPS_FOR_INTERRUPTION,
    NUM_TAPS_AGENCY_WITHOUT_DELAY,
    PRACTICE_TRIAL_DURATION,
    PREMATURE_KEY_RELEASE_ERROR_TIME,
)


def make_state(interruption_time_offset=0.0, **overrides) -> AgencyTappingTaskState:
    defaults = dict(
        task='core',
        keys_to_hold=['s'],
        key_to_press='l',
        bounds=(30, 50),
        trial_duration=10000,  # TRIAL_DURATION_AGENCY_TASK
        auto_increase_amount=10,
    )
    defaults.update(overrides)
    params = AgencyTappingTaskParams(**defaults)
    return AgencyTappingTaskState(params, interruption_time_offset=interruption_time_offset)


def test_interruption_time_computed_from_trial_duration():
    state = make_state(interruption_time_offset=0.0, trial_duration=10000)
    assert state.interruption_time == pytest.approx(10000 * 0.667)
    assert state.second_half_duration == pytest.approx(10000 - 10000 * 0.667)


def test_start_running_resets_state():
    state = make_state()
    state.tap_count = 5
    state.mercury_height = 40
    ended = state.start(0.0)
    assert ended is False
    assert state.mercury_height == 0
    assert state.tap_count == 0
    assert state.is_running is True


def test_start_ends_immediately_on_key_tapped_early_flag():
    state = make_state(key_tapped_early_flag=True)
    ended = state.start(0.0)
    assert ended is True
    assert state.trial_ended is True
    assert state.error_occurred is True


def test_tap_beyond_threshold_is_delayed():
    state = make_state(delay_original=0)  # delay=0 -> queued but due immediately
    state.start(0.0)
    for i in range(NUM_TAPS_AGENCY_WITHOUT_DELAY + 2):
        t = 0.01 * i
        state.handle_key_up('l', t)
        state.tick(t)  # even a 0ms delay is only applied once ticked, like the real poll loop
    assert state.mercury_height == (NUM_TAPS_AGENCY_WITHOUT_DELAY + 2) * 10


def test_tap_beyond_threshold_delayed_with_nonzero_delay_level():
    state = make_state(delay_original=500, auto_decrease_amount=0)
    state.start(0.0)
    state.handle_key_up('l', 0.0)  # tap 1 (== NUM_TAPS_AGENCY_WITHOUT_DELAY) -> immediate
    assert state.mercury_height == 10
    state.handle_key_up('l', 0.1)  # tap 2 (> threshold) -> delayed
    assert state.mercury_height == 10  # not yet applied
    assert len(state._pending_increases) == 1


def test_interruption_triggers_when_enough_taps():
    state = make_state(interruption_time_offset=0.0, trial_duration=10000)
    state.start(0.0)
    for i in range(MIN_TAPS_FOR_INTERRUPTION + 1):
        state.handle_key_up('l', 0.001 * i)
    assert state.tap_count == MIN_TAPS_FOR_INTERRUPTION + 1

    state.tick(state.interruption_time / 1000.0 + 0.01)
    assert state.is_in_interruption is True
    assert state.awaiting_interruption_response is True
    assert state.is_running is False


def test_interruption_response_and_resume_flow():
    state = make_state(interruption_time_offset=0.0, trial_duration=10000)
    state.start(0.0)
    for i in range(MIN_TAPS_FOR_INTERRUPTION + 1):
        state.handle_key_up('l', 0.001 * i)
    check_time = state.interruption_time / 1000.0
    state.tick(check_time + 0.01)
    assert state.awaiting_interruption_response is True

    state.receive_interruption_response('y', check_time + 1.0)
    assert state.interruption_response == 'y'
    assert state.awaiting_hold_key_reminder is True

    state.confirm_keys_reheld(check_time + 2.0)
    assert state.awaiting_resume_countdown is True

    resume_time = check_time + 2.0 + 2.0  # COUNTDOWN_TIME = 2s
    state.tick(resume_time)
    assert state.is_running is True
    assert state.is_in_interruption is False

    # Trial should now stop after second_half_duration from resume.
    state.tick(resume_time + state.second_half_duration / 1000.0 + 0.01)
    assert state.trial_ended is True


def test_interruption_response_accepts_french_oui():
    state = make_state(interruption_time_offset=0.0)
    state.start(0.0)
    state.receive_interruption_response('o', 1.0)
    assert state.interruption_response == 'y'


def test_pending_increase_dropped_during_interruption():
    # auto_decrease_amount=0 isolates the pending-increase-drop behavior
    # under test from the (separately tested) auto-decrease ticking.
    state = make_state(interruption_time_offset=0.0, delay_original=0, trial_duration=10000, auto_decrease_amount=0)
    state.start(0.0)
    # Enough taps to qualify for interruption (delay_original=0 so each
    # resolves immediately on tick, isolating the one pending increase
    # under test below).
    for i in range(MIN_TAPS_FOR_INTERRUPTION + 1):
        t = 0.001 * i
        state.handle_key_up('l', t)
        state.tick(t)
    height_before = state.mercury_height

    check_time = state.interruption_time / 1000.0
    # Directly inject a pending increase whose fire_time is *after* the
    # interruption's check_time -- mirrors a tap whose randomized per-tap
    # delay happens to land past the interruption boundary. Chronological
    # ordering inside tick() must resolve the (earlier) interruption_check
    # first and then drop this increase rather than apply it.
    state._pending_increases.append((check_time + 0.05, state.params.auto_increase_amount))

    state.tick(check_time + 1.0)
    assert state.is_in_interruption is True
    assert state.mercury_height == height_before  # dropped, not applied
    assert state._pending_increases == []  # consumed (dropped), not left dangling


def test_not_enough_taps_schedules_double_interruption_time_before_stopping():
    # Quirk 2: with too few taps, the trial stops at roughly
    # 2 * interruption_time, not at interruption_time or trial_duration.
    state = make_state(interruption_time_offset=0.0, trial_duration=10000)
    state.start(0.0)
    # Fewer taps than MIN_TAPS_FOR_INTERRUPTION.
    state.handle_key_up('l', 0.001)

    check_time = state.interruption_time / 1000.0
    state.tick(check_time + 0.01)
    assert state.is_in_interruption is False
    assert state.trial_ended is False

    # Should not have ended at just interruption_time.
    state.tick(check_time + state.interruption_time / 1000.0 - 0.05)
    assert state.trial_ended is False

    # Should end once the second interruption_time delay elapses.
    state.tick(check_time + state.interruption_time / 1000.0 + 0.05)
    assert state.trial_ended is True


def test_no_interruption_for_target_task_uses_practice_trial_duration():
    state = make_state(task='target', interruption_time_offset=0.0)
    state.start(0.0)
    assert state.no_interruption is True

    state.tick(PRACTICE_TRIAL_DURATION / 1000.0 - 0.05)
    assert state.trial_ended is False
    state.tick(PRACTICE_TRIAL_DURATION / 1000.0 + 0.05)
    assert state.trial_ended is True


def test_premature_release_immediately_flags_no_grace_period():
    state = make_state()
    state.start(0.0)
    state.handle_key_up('s', 1.0)  # release hold key
    assert state.keys_released_flag is True
    assert state.error_occurred is True
    assert state.trial_ended is False  # not yet -- fixed delay before stop

    state.tick(1.0 + PREMATURE_KEY_RELEASE_ERROR_TIME / 1000.0 - 0.05)
    assert state.trial_ended is False

    state.tick(1.0 + PREMATURE_KEY_RELEASE_ERROR_TIME / 1000.0 + 0.01)
    assert state.trial_ended is True


def test_premature_release_ignored_during_interruption():
    state = make_state(interruption_time_offset=0.0, trial_duration=10000)
    state.start(0.0)
    for i in range(MIN_TAPS_FOR_INTERRUPTION + 1):
        state.handle_key_up('l', 0.001 * i)
    check_time = state.interruption_time / 1000.0
    state.tick(check_time + 0.01)
    assert state.is_in_interruption is True

    state.handle_key_up('s', check_time + 0.1)  # release during interruption -- should not flag
    assert state.keys_released_flag is False
    assert state.error_occurred is False


def test_is_success_requires_no_margin_unlike_base_tapping_task():
    state = make_state(bounds=(30, 50))
    state.mercury_height = 29  # just outside, no PATIENT_SAFETY_MARGIN allowance here
    state.interruption_response = 'y'
    assert state.is_success() is False

    state.mercury_height = 30
    assert state.is_success() is True


def test_is_success_requires_interruption_answered_unless_no_interruption():
    state = make_state(bounds=(30, 50), task='core')
    state.mercury_height = 40
    assert state.is_success() is False  # interruption_response still None
    state.interruption_response = 'n'
    assert state.is_success() is True


def test_is_success_target_task_does_not_require_interruption_response():
    state = make_state(bounds=(30, 50), task='target')
    state.mercury_height = 40
    assert state.is_success() is True


def test_build_trial_record_field_names():
    state = make_state(bounds=(30, 50), delay_original=250, required_time_in_bounds=2000)
    state.start(0.0)
    record = state.build_trial_record()
    assert set(record.keys()) == {
        'tapCount', 'delayOriginal', 'startTime', 'endTime', 'mercuryHeight', 'error',
        'bounds', 'task', 'errorOccurred', 'keysReleasedFlag', 'success',
        'keyTappedEarlyFlag', 'keysState', 'requiredTimeInBounds', 'interruptionResponse',
    }
    assert record['requiredTimeInBounds'] == 2000
    assert record['delayOriginal'] == 250


def test_compute_agency_auto_increase_amount_uses_hardcoded_median_of_10():
    amount_sync = compute_agency_auto_increase_amount(0)
    amount_delayed = compute_agency_auto_increase_amount(500)
    assert amount_sync > 0
    assert amount_delayed > amount_sync  # larger symmetric delay range -> fewer effective presses -> bigger increment
