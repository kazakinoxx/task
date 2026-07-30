from src2.trials.acceptance_trial import AcceptanceTrialParams, build_acceptance_trial_record, resolve_acceptance


def test_response_index_0_is_accepted():
    assert resolve_acceptance(0) is True


def test_response_index_1_is_rejected():
    assert resolve_acceptance(1) is False


def test_build_acceptance_trial_record_shape():
    params = AcceptanceTrialParams(bounds=(42, 72), original_bounds=(45, 75), reward=10.5, delay=(0, 500))
    record = build_acceptance_trial_record(params, response_index=0)
    assert record == {
        'task': 'accept',
        'reward': 10.5,
        'bounds': [42, 72],
        'originalBounds': [45, 75],
        'delay': [0, 500],
        'response': 0,
        'accepted': True,
    }


def test_build_acceptance_trial_record_rejected():
    params = AcceptanceTrialParams(bounds=(5, 35), original_bounds=(5, 35), reward=1, delay=(0, 0))
    record = build_acceptance_trial_record(params, response_index=1)
    assert record['accepted'] is False
