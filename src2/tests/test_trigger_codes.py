import pytest

from src2.triggers.photodiode import BLACK, WHITE, photodiode_flash_schedule
from src2.triggers.trigger import send_trigger
from src2.triggers.trigger_codes import build_trigger_byte
from src2.triggers.trigger_device import NullTriggerDevice
from src2.utils.types import BoundsType, RewardType


def test_build_trigger_byte_bit_flags():
    assert build_trigger_byte(outside_task=True, decision_trigger=False) == 128
    assert build_trigger_byte(outside_task=False, decision_trigger=True) == 64
    assert (
        build_trigger_byte(outside_task=False, decision_trigger=False, delayed_condition=True)
        == 32
    )
    assert build_trigger_byte(outside_task=False, decision_trigger=False, is_end=True) == 1


@pytest.mark.parametrize(
    'reward,expected',
    [
        (RewardType.LOW.value, 8),
        (RewardType.MIDDLE.value, 16),
        (RewardType.HIGH.value, 24),
        (RewardType.LOW_MIDDLE.value, 0),  # no assigned bits, same as JS default case
        (None, 0),
    ],
)
def test_build_trigger_byte_reward_bits(reward, expected):
    assert build_trigger_byte(outside_task=False, decision_trigger=False, reward=reward) == expected


@pytest.mark.parametrize(
    'bounds,expected',
    [
        (BoundsType.EASY.value, 2),
        (BoundsType.MEDIUM.value, 4),
        (BoundsType.HARD.value, 6),
        (BoundsType.EASY_MEDIUM.value, 0),
        (None, 0),
    ],
)
def test_build_trigger_byte_bounds_bits(bounds, expected):
    assert build_trigger_byte(outside_task=False, decision_trigger=False, bounds=bounds) == expected


def test_build_trigger_byte_combines_all_flags():
    # decision trigger, delayed condition, high reward, hard bounds, end -> 64+32+24+6+1
    code = build_trigger_byte(
        outside_task=False,
        decision_trigger=True,
        delayed_condition=True,
        reward=RewardType.HIGH.value,
        bounds=BoundsType.HARD.value,
        is_end=True,
    )
    assert code == 64 + 32 + 24 + 6 + 1


def test_send_trigger_sends_code_then_resets():
    device = NullTriggerDevice(verbose=False)
    waited = []
    code = send_trigger(
        device,
        outside_task=True,
        decision_trigger=False,
        is_end=True,
        wait_fn=lambda s: waited.append(s),
    )
    assert code == 128 + 1
    assert device.last_code == 0  # reset after the pulse
    assert waited == [0.1]


def test_photodiode_flash_schedule_start_only():
    schedule = photodiode_flash_schedule(is_end=False)
    assert schedule == [(0.0, WHITE), (0.1, BLACK)]


def test_photodiode_flash_schedule_with_end_double_pulse():
    schedule = photodiode_flash_schedule(is_end=True)
    assert schedule == [(0.0, WHITE), (0.1, BLACK), (0.2, WHITE), (0.3, BLACK)]
