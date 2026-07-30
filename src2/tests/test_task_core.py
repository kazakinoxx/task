import random

import pytest

from src2.config.settings_schema import AllSettingsType
from src2.parts.task_core import (
    AcceptanceRunners,
    TaskBlockScreenRunners,
    TaskTrialRunners,
    checkpoint_last_trial,
    compute_task_trial_auto_increase_amount,
    finish_reward_display,
    generate_task_block_permutations,
    generate_trial_order,
    get_num_trials_per_block,
    resolve_actual_trial_params,
    resolve_break_allow_skip,
    resolve_random_skip,
    resolve_reward_display,
    resolve_trial_block_sequence,
    run_generate_task_trial,
    run_task_block_demo,
    run_task_block_trials,
    run_task_trial_block,
    should_show_break,
)
from src2.state.experiment_state import ExperimentState
from src2.utils.trial_history import TrialHistory
from src2.utils.types import BoundsType, DelayType, RewardType


def make_state(**task_overrides) -> ExperimentState:
    settings = AllSettingsType()
    for key, value in task_overrides.items():
        setattr(settings.taskSettings, key, value)
    return ExperimentState(settings)


# ---------------------------------------------------------------------------
# generate_trial_order
# ---------------------------------------------------------------------------


def test_generate_trial_order_has_no_triple_repeats_and_correct_length():
    state = make_state(taskBlockRepetitions=5, taskBlocksIncluded=[DelayType.SYNC.value, DelayType.SHORT_ASYNC.value])
    for _ in range(20):
        order = generate_trial_order(state)
        assert len(order) == 5 * 2
        for i in range(2, len(order)):
            assert not (order[i] == order[i - 1] == order[i - 2])


def test_generate_trial_order_contains_correct_multiset():
    state = make_state(taskBlockRepetitions=2, taskBlocksIncluded=[DelayType.SYNC.value, DelayType.MID_ASYNC.value])
    order = generate_trial_order(state)
    assert sorted(order) == sorted([DelayType.SYNC.value, DelayType.MID_ASYNC.value] * 2)


# ---------------------------------------------------------------------------
# permutations / random skip / actual params
# ---------------------------------------------------------------------------


def test_get_num_trials_per_block():
    state = make_state(
        taskPermutationRepetitions=2,
        taskBoundsIncluded=[BoundsType.EASY.value, BoundsType.HARD.value],
        taskRewardsIncluded=[RewardType.LOW.value],
    )
    assert get_num_trials_per_block(state) == 2 * 2 * 1


def test_generate_task_block_permutations_repeats_full_cross_product_per_repetition():
    state = make_state(
        taskPermutationRepetitions=3,
        taskBoundsIncluded=[BoundsType.EASY.value, BoundsType.HARD.value],
        taskRewardsIncluded=[RewardType.LOW.value, RewardType.HIGH.value],
    )
    combos = generate_task_block_permutations(state)
    assert len(combos) == 3 * 2 * 2
    # each successive chunk of 4 should be a full shuffled cross-product
    expected = {(BoundsType.EASY.value, RewardType.LOW.value), (BoundsType.EASY.value, RewardType.HIGH.value),
                (BoundsType.HARD.value, RewardType.LOW.value), (BoundsType.HARD.value, RewardType.HIGH.value)}
    for i in range(3):
        chunk = combos[i * 4:(i + 1) * 4]
        assert {(c['bounds'], c['reward']) for c in chunk} == expected


def test_resolve_random_skip_uses_chance_setting(monkeypatch):
    state = make_state(randomSkipChance=50)
    monkeypatch.setattr(random, 'random', lambda: 0.3)
    assert resolve_random_skip(state) is True
    monkeypatch.setattr(random, 'random', lambda: 0.7)
    assert resolve_random_skip(state) is False


def test_resolve_actual_trial_params_shape():
    params = resolve_actual_trial_params(BoundsType.MEDIUM.value, RewardType.HIGH.value, DelayType.SHORT_ASYNC.value)
    assert params['reward'] == 20
    assert params['delay'] == (0, 500)
    lo, hi = params['bounds']
    assert hi - lo == pytest.approx(75 - 45)


def test_compute_task_trial_auto_increase_amount_uses_calibration_part2_median():
    state = ExperimentState()
    amount = compute_task_trial_auto_increase_amount(state, (0, 500))
    assert amount > 0


# ---------------------------------------------------------------------------
# run_generate_task_trial
# ---------------------------------------------------------------------------


def make_task_runners(tapping_record, countdown_record=None):
    calls = {'countdown': 0, 'release_keys': 0, 'freeze_frame': 0, 'skip_screen': 0, 'loading_bar': []}

    def countdown():
        calls['countdown'] += 1
        return countdown_record or {'task': 'countdown', 'keyTappedEarlyFlag': False}

    def tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label):
        return dict(tapping_record)

    def release_keys():
        calls['release_keys'] += 1
        return {'errorOccurred': False}

    def freeze_frame_failure_screen():
        calls['freeze_frame'] += 1
        return {'task': 'success', 'success': False}

    def skip_screen():
        calls['skip_screen'] += 1
        return {'task': 'success', 'success': True, 'skip': True}

    def loading_bar(acceptance):
        calls['loading_bar'].append(acceptance)

    return TaskTrialRunners(countdown, tapping, release_keys, freeze_frame_failure_screen, skip_screen, loading_bar), calls


def test_run_generate_task_trial_clean_success_shows_no_feedback_screen():
    state = ExperimentState()
    history = TrialHistory()
    tapping_record = {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True}}
    runners, calls = make_task_runners(tapping_record)

    run_generate_task_trial(state, history, runners, (45, 75), 10, (0, 0), 'sync', demo=False, random_skip=False)

    assert calls['countdown'] == 1
    assert calls['freeze_frame'] == 0
    assert calls['skip_screen'] == 0
    assert calls['loading_bar'] == [True]  # not random_skip -> True


def test_run_generate_task_trial_procedural_error_shows_freeze_frame_screen():
    state = ExperimentState()
    history = TrialHistory()
    tapping_record = {'tapCount': 30, 'keysReleasedFlag': True, 'keyTappedEarlyFlag': False, 'success': False, 'keysState': {'s': True}}
    runners, calls = make_task_runners(tapping_record)

    run_generate_task_trial(state, history, runners, (45, 75), 10, (0, 0), 'sync', demo=False, random_skip=False)

    assert calls['freeze_frame'] == 1
    assert calls['skip_screen'] == 0


def test_run_generate_task_trial_random_skip_skips_countdown_and_shows_skip_screen():
    state = ExperimentState()
    history = TrialHistory()
    tapping_record = {'tapCount': 0, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'keysState': {}}
    runners, calls = make_task_runners(tapping_record)

    run_generate_task_trial(state, history, runners, (45, 75), 10, (0, 0), 'sync', demo=False, random_skip=True)

    assert calls['countdown'] == 0
    assert calls['skip_screen'] == 1
    assert calls['freeze_frame'] == 0
    assert calls['loading_bar'] == [False]  # random_skip -> fast bar


def test_run_generate_task_trial_demo_always_uses_slow_loading_bar():
    state = ExperimentState()
    history = TrialHistory()
    tapping_record = {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True}}
    runners, calls = make_task_runners(tapping_record)

    run_generate_task_trial(state, history, runners, (45, 75), 0, (0, 0), 'sync', demo=True, random_skip=False)

    assert calls['loading_bar'] == [True]


def test_run_generate_task_trial_skips_release_keys_when_not_held():
    state = ExperimentState()
    history = TrialHistory()
    tapping_record = {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': False}}
    runners, calls = make_task_runners(tapping_record)

    run_generate_task_trial(state, history, runners, (45, 75), 10, (0, 0), 'sync', demo=False, random_skip=False)
    assert calls['release_keys'] == 0


# ---------------------------------------------------------------------------
# run_task_block_demo
# ---------------------------------------------------------------------------


def test_run_task_block_demo_retries_on_procedural_error():
    state = ExperimentState()
    history = TrialHistory()

    # first demo bounds level: fails once (early tap) then succeeds
    countdown_outcomes = iter([
        {'task': 'countdown', 'keyTappedEarlyFlag': True},
        {'task': 'countdown', 'keyTappedEarlyFlag': False},
        {'task': 'countdown', 'keyTappedEarlyFlag': False},  # second bounds level, clean first try
    ])
    calls = {'countdown': 0, 'release_keys': 0, 'freeze_frame': 0, 'skip_screen': 0, 'loading_bar': []}

    def countdown():
        calls['countdown'] += 1
        return next(countdown_outcomes)

    def tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label):
        return {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': key_tapped_early_flag, 'success': not key_tapped_early_flag, 'keysState': {'s': True}}

    def release_keys():
        calls['release_keys'] += 1
        return {'errorOccurred': False}

    def freeze_frame_failure_screen():
        calls['freeze_frame'] += 1
        return {'task': 'success', 'success': False}

    def skip_screen():
        calls['skip_screen'] += 1
        return {'task': 'success', 'success': True}

    def loading_bar(acceptance):
        calls['loading_bar'].append(acceptance)

    runners = TaskTrialRunners(countdown, tapping, release_keys, freeze_frame_failure_screen, skip_screen, loading_bar)

    run_task_block_demo(state, history, runners, DelayType.SYNC.value)

    # DEMO_TRIAL_SET has 2 bounds levels; first needed 2 attempts, second 1.
    assert calls['countdown'] == 3


# ---------------------------------------------------------------------------
# run_task_block_trials
# ---------------------------------------------------------------------------


def test_run_task_block_trials_rejects_skip_the_task_trial():
    state = make_state(
        taskPermutationRepetitions=1,
        taskBoundsIncluded=[BoundsType.EASY.value],
        taskRewardsIncluded=[RewardType.LOW.value],
    )
    history = TrialHistory()

    def acceptance(bounds, original_bounds, reward, delay):
        return {'task': 'accept', 'accepted': False, 'response': 1}

    calls = {'loading_bar': []}

    def loading_bar(acceptance_flag):
        calls['loading_bar'].append(acceptance_flag)

    acceptance_runners = AcceptanceRunners(acceptance, loading_bar)

    def tapping(*args, **kwargs):
        raise AssertionError('tapping should not run when the offer is rejected')

    task_runners = TaskTrialRunners(
        countdown=lambda: (_ for _ in ()).throw(AssertionError('should not run')),
        tapping=tapping,
        release_keys=lambda: {},
        freeze_frame_failure_screen=lambda: {},
        skip_screen=lambda: {},
        loading_bar=lambda a: None,
    )

    run_task_block_trials(state, history, DelayType.SYNC.value, acceptance_runners, task_runners)

    assert calls['loading_bar'] == [False]


def test_run_task_block_trials_accepted_runs_full_task_trial():
    state = make_state(
        taskPermutationRepetitions=1,
        taskBoundsIncluded=[BoundsType.EASY.value],
        taskRewardsIncluded=[RewardType.LOW.value],
    )
    history = TrialHistory()

    def acceptance(bounds, original_bounds, reward, delay):
        return {'task': 'accept', 'accepted': True, 'response': 0}

    acceptance_runners = AcceptanceRunners(acceptance, lambda a: None)

    task_calls = {'tapping': 0}

    def tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label):
        task_calls['tapping'] += 1
        return {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True}}

    task_runners = TaskTrialRunners(
        countdown=lambda: {'task': 'countdown', 'keyTappedEarlyFlag': False},
        tapping=tapping,
        release_keys=lambda: {'errorOccurred': False},
        freeze_frame_failure_screen=lambda: {'task': 'success', 'success': False},
        skip_screen=lambda: {'task': 'success', 'success': True},
        loading_bar=lambda a: None,
    )

    run_task_block_trials(state, history, DelayType.SYNC.value, acceptance_runners, task_runners)

    assert task_calls['tapping'] == 1


# ---------------------------------------------------------------------------
# reward display / break / checkpoint / trial-block-sequence
# ---------------------------------------------------------------------------


def test_resolve_reward_display_computes_money_proportion():
    state = make_state(
        taskBlockRepetitions=1,
        taskBlocksIncluded=[DelayType.SYNC.value],
        taskBoundsIncluded=[BoundsType.EASY.value],
        taskRewardsIncluded=[RewardType.HIGH.value],
        taskPermutationRepetitions=1,
    )
    history = TrialHistory()
    history.add({'task': 'block', 'success': True, 'reward': 20})
    result = resolve_reward_display(history, state)
    assert result['totalReward'] == 20
    assert result['totalPoints'] == 20  # 1 trial * avg reward 20
    assert result['currentRewardMoney'] == pytest.approx(6.0)  # full points earned -> full money


def test_finish_reward_display_increments_completed_blocks():
    state = ExperimentState()
    before = state.get_state()['completedBlockCount']
    finish_reward_display(state)
    assert state.get_state()['completedBlockCount'] == before + 1


def test_break_skip_parity_quirk_never_coincide():
    # Documents/locks in the preserved quirk: whenever a break is actually
    # shown (odd index, not last block), allowSkip is always False.
    state = make_state(taskBlockRepetitions=1, taskBlocksIncluded=[DelayType.SYNC.value] * 6)
    for index in range(6):
        if should_show_break(state, index):
            assert resolve_break_allow_skip(index) is False


def test_checkpoint_last_trial_mutates_last_history_entry():
    history = TrialHistory()
    history.add({'task': 'display_reward'})
    checkpoint_last_trial(history, 'EBDM', 3)
    assert history.last_value()['checkpoint'] == 'EBDM'
    assert history.last_value()['checkpointBlock'] == 3


def test_resolve_trial_block_sequence_fresh_pseudorandom():
    state = make_state(taskBlockRepetitions=2, taskBlocksIncluded=[DelayType.SYNC.value, DelayType.MID_ASYNC.value])
    trial_block, start = resolve_trial_block_sequence(state)
    assert start == 0
    assert len(trial_block) == 4


def test_resolve_trial_block_sequence_resumed():
    state = make_state(taskBlockRepetitions=2, taskBlocksIncluded=[DelayType.SYNC.value, DelayType.MID_ASYNC.value])
    remaining = [DelayType.MID_ASYNC.value]
    trial_block, start = resolve_trial_block_sequence(state, remaining_trial_blocks=remaining)
    assert trial_block == remaining
    assert start == 4 - 1  # totalBlocks(4) - remaining(1)


def test_resolve_trial_block_sequence_custom():
    custom_sequence = [DelayType.SYNC.value, DelayType.LONG_ASYNC.value]
    state = make_state(taskSequencingMode='custom', taskCustomSequence=custom_sequence)
    trial_block, start = resolve_trial_block_sequence(state)
    assert trial_block == custom_sequence
    assert start == 0


# ---------------------------------------------------------------------------
# run_task_trial_block -- full per-delay-block sequence (demo intro -> demo
# trials -> likert 1 -> reminder -> real trials -> likert intro -> likert 2
# -> likert final -> reward display -> break)
# ---------------------------------------------------------------------------


def make_clean_task_runners(order_log):
    def countdown():
        order_log.append('countdown')
        return {'task': 'countdown', 'keyTappedEarlyFlag': False}

    def tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label):
        order_log.append('tapping')
        return {'tapCount': 30, 'keysReleasedFlag': False, 'keyTappedEarlyFlag': False, 'success': True, 'keysState': {'s': True}}

    def release_keys():
        return {'errorOccurred': False}

    def freeze_frame_failure_screen():
        return {'task': 'success', 'success': False}

    def skip_screen():
        return {'task': 'success', 'success': True}

    def loading_bar(acceptance):
        pass

    return TaskTrialRunners(countdown, tapping, release_keys, freeze_frame_failure_screen, skip_screen, loading_bar)


def make_screen_runners(order_log):
    def demo_intro():
        order_log.append('demo_intro')
        return {'task': 'demo_intro'}

    def likert_1():
        order_log.append('likert_1')
        return {'response': {}}

    def reminder():
        order_log.append('reminder')
        return {'task': 'remember_direction'}

    def likert_intro():
        order_log.append('likert_intro')
        return {'task': 'likert_intro'}

    def likert_2():
        order_log.append('likert_2')
        return {'response': {}}

    def likert_final():
        order_log.append('likert_final')
        return {'response': {}}

    def break_screen(allow_skip):
        order_log.append(f'break_screen(allow_skip={allow_skip})')

    return TaskBlockScreenRunners(demo_intro, likert_1, reminder, likert_intro, likert_2, likert_final, break_screen)


def _make_accepting_acceptance_runners():
    def acceptance(bounds, original_bounds, reward, delay):
        return {'task': 'accept', 'accepted': True, 'response': 0}

    return AcceptanceRunners(acceptance, lambda a: None)


def test_run_task_trial_block_full_sequence_order():
    # 3 blocks so index=1 is odd and not the last block -> should_show_break is True.
    state = make_state(
        taskBlockRepetitions=1,
        taskBlocksIncluded=[DelayType.SYNC.value] * 3,
        taskBoundsIncluded=[BoundsType.EASY.value],
        taskRewardsIncluded=[RewardType.LOW.value],
        taskPermutationRepetitions=1,
    )
    history = TrialHistory()
    order_log = []
    task_runners = make_clean_task_runners(order_log)
    acceptance_runners = _make_accepting_acceptance_runners()
    screen_runners = make_screen_runners(order_log)

    run_task_trial_block(state, history, DelayType.SYNC.value, 1, task_runners, acceptance_runners, screen_runners)

    assert order_log[0] == 'demo_intro'
    assert order_log.index('likert_1') > order_log.index('demo_intro')
    assert order_log.index('reminder') > order_log.index('likert_1')
    assert order_log.index('likert_intro') > order_log.index('reminder')
    assert order_log.index('likert_2') > order_log.index('likert_intro')
    assert order_log.index('likert_final') > order_log.index('likert_2')
    assert order_log[-1] == 'break_screen(allow_skip=False)'  # resolve_break_allow_skip(1) is False


def test_run_task_trial_block_skips_break_screen_when_not_shown():
    state = make_state(
        taskBlockRepetitions=1,
        taskBlocksIncluded=[DelayType.SYNC.value],  # single block -> should_show_break is always False
        taskBoundsIncluded=[BoundsType.EASY.value],
        taskRewardsIncluded=[RewardType.LOW.value],
        taskPermutationRepetitions=1,
    )
    history = TrialHistory()
    order_log = []
    task_runners = make_clean_task_runners(order_log)
    acceptance_runners = _make_accepting_acceptance_runners()
    screen_runners = make_screen_runners(order_log)

    run_task_trial_block(state, history, DelayType.SYNC.value, 0, task_runners, acceptance_runners, screen_runners)

    assert not any(entry.startswith('break_screen') for entry in order_log)


def test_run_task_trial_block_records_reward_display_and_increments_completed_blocks():
    state = make_state(
        taskBlockRepetitions=1,
        taskBlocksIncluded=[DelayType.SYNC.value],
        taskBoundsIncluded=[BoundsType.EASY.value],
        taskRewardsIncluded=[RewardType.HIGH.value],
        taskPermutationRepetitions=1,
    )
    history = TrialHistory()
    before = state.get_state()['completedBlockCount']
    order_log = []
    task_runners = make_clean_task_runners(order_log)
    acceptance_runners = _make_accepting_acceptance_runners()
    screen_runners = make_screen_runners(order_log)

    run_task_trial_block(state, history, DelayType.SYNC.value, 0, task_runners, acceptance_runners, screen_runners)

    assert state.get_state()['completedBlockCount'] == before + 1
    assert any(t.get('task') == 'display_reward' for t in history.all())
