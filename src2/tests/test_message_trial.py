from src2.trials.message_trial import resolve_break_remaining_seconds, resolve_choice_response


def test_resolve_choice_response_maps_known_key():
    assert resolve_choice_response('left', {'left': 0, 'right': 1}) == 0
    assert resolve_choice_response('right', {'left': 0, 'right': 1}) == 1


def test_resolve_choice_response_is_case_insensitive():
    assert resolve_choice_response('LEFT', {'left': 0, 'right': 1}) == 0


def test_resolve_choice_response_unknown_key_returns_none():
    assert resolve_choice_response('space', {'left': 0, 'right': 1}) is None


def test_resolve_break_remaining_seconds_counts_down():
    assert resolve_break_remaining_seconds(0, 60000) == 60.0
    assert resolve_break_remaining_seconds(30000, 60000) == 30.0


def test_resolve_break_remaining_seconds_never_negative():
    assert resolve_break_remaining_seconds(90000, 60000) == 0.0
