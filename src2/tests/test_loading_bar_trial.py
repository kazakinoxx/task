import random

import pytest

from src2.trials.loading_bar_trial import LoadingBarState, loading_bar_increment
from src2.utils.constants import LOADING_BAR_SPEED_NO, LOADING_BAR_SPEED_YES


def test_increment_bounded_by_speed_for_acceptance():
    rng = random.Random(42)
    for _ in range(200):
        inc = loading_bar_increment(True, rng)
        assert 1 <= inc <= LOADING_BAR_SPEED_YES


def test_increment_bounded_by_speed_for_rejection():
    rng = random.Random(42)
    for _ in range(200):
        inc = loading_bar_increment(False, rng)
        assert 1 <= inc <= LOADING_BAR_SPEED_NO


def test_rejected_trials_progress_faster_on_average():
    rng_accept = random.Random(1)
    rng_reject = random.Random(1)
    accept_increments = [loading_bar_increment(True, rng_accept) for _ in range(1000)]
    reject_increments = [loading_bar_increment(False, rng_reject) for _ in range(1000)]
    assert sum(reject_increments) / len(reject_increments) > sum(accept_increments) / len(accept_increments)


def test_state_reaches_100_and_ends():
    state = LoadingBarState(acceptance=False)
    rng = random.Random(7)
    steps = 0
    while not state.ended and steps < 1000:
        state.step(rng)
        steps += 1
    assert state.ended is True
    assert state.percentage == 100


def test_percentage_never_exceeds_100():
    state = LoadingBarState(acceptance=True)
    rng = random.Random(3)
    for _ in range(200):
        state.step(rng)
        assert state.percentage <= 100
        if state.ended:
            break
