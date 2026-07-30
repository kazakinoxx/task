from frontend.narration import Narration


def test_disabled_narration_play_is_a_no_op_without_touching_psychopy():
    # enabled=False must short-circuit before the lazy `from psychopy
    # import sound`, so this is testable without PsychoPy installed --
    # if it tried to import psychopy here, this test would fail/error in
    # this dev environment (see the module docstrings on why PsychoPy
    # can't be installed here).
    narration = Narration(enabled=False)
    narration.play('sit-comfortably.mp3')
    assert narration._current_sound is None


def test_disabled_narration_stop_is_always_safe():
    narration = Narration(enabled=False)
    narration.stop()  # no current sound, no exception


def test_enabled_flag_is_stored_as_given():
    assert Narration(enabled=True).enabled is True
    assert Narration(enabled=False).enabled is False


def test_disabled_narration_with_device_set_never_touches_psychopy_prefs():
    # enabled=False must short-circuit in play() before
    # _apply_device_preference() runs, so this stays importable/testable
    # without psychopy even when a device override is configured.
    narration = Narration(enabled=False, device='Some Headset')
    narration.play('sit-comfortably.mp3')
    assert narration._device_pref_applied is False
