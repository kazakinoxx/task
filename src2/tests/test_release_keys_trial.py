from src2.trials.release_keys_trial import ReleaseKeysParams, ReleaseKeysState


def test_ends_immediately_if_no_keys_held_initially():
    state = ReleaseKeysState(ReleaseKeysParams(valid_responses=[]))
    assert state.ended is True


def test_does_not_end_while_keys_still_held():
    state = ReleaseKeysState(ReleaseKeysParams(valid_responses=['s', 'l']))
    assert state.ended is False
    state.handle_key_up('s')
    assert state.ended is False


def test_ends_once_all_keys_released():
    state = ReleaseKeysState(ReleaseKeysParams(valid_responses=['s', 'l']))
    state.handle_key_up('s')
    state.handle_key_up('l')
    assert state.ended is True


def test_re_pressing_a_key_prevents_end():
    state = ReleaseKeysState(ReleaseKeysParams(valid_responses=['s', 'l']))
    state.handle_key_up('s')
    state.handle_key_down('s')
    state.handle_key_up('l')
    assert state.ended is False  # 's' is held again, so not all released


def test_enter_key_force_ends_trial():
    state = ReleaseKeysState(ReleaseKeysParams(valid_responses=['s', 'l']))
    state.handle_key_up('enter')
    assert state.ended is True


def test_build_trial_record():
    state = ReleaseKeysState(ReleaseKeysParams(valid_responses=[]))
    assert state.build_trial_record() == {'errorOccurred': False}
