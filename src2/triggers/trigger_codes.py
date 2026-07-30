"""8-bit trigger byte encoding.

Pure port of the bit-packing logic in sendSerialTrigger
(src/modules/experiment/triggers/trigger.ts). Pin assignment:

    bit 7 (128): outside task (1) vs. task block (0)
    bit 6 (64):  decision trigger (1) vs. task (0)
    bit 5 (32):  delayed condition (1) vs. sync (0)
    bits 4-3:    reward -- low=01(8), middle=10(16), high=11(24)
    bits 2-1:    bounds/effort -- easy=01(2), medium=10(4), hard=11(6)
    bit 0 (1):   end (1) vs. start (0)
"""

from __future__ import annotations

from typing import Optional

from src2.utils.types import BoundsType, RewardType

_REWARD_BITS = {
    RewardType.LOW.value: 8,
    RewardType.MIDDLE.value: 16,
    RewardType.HIGH.value: 24,
}

_BOUNDS_BITS = {
    BoundsType.EASY.value: 2,
    BoundsType.MEDIUM.value: 4,
    BoundsType.HARD.value: 6,
}


def build_trigger_byte(
    outside_task: bool,
    decision_trigger: bool,
    delayed_condition: bool = False,
    reward: Optional[str] = None,
    bounds: Optional[str] = None,
    is_end: bool = False,
) -> int:
    """Builds the 8-bit trigger code. `reward`/`bounds` should be the
    string values of RewardType/BoundsType (e.g. 'low', 'medium'); any
    other value (including None, and BoundsType.EASY_MEDIUM/RewardType
    .LOW_MIDDLE which have no assigned bits, same as the original JS
    switch's default case) contributes 0 bits.
    """
    message = 0
    if outside_task:
        message += 128
    if decision_trigger:
        message += 64
    if delayed_condition:
        message += 32
    message += _REWARD_BITS.get(reward, 0)
    message += _BOUNDS_BITS.get(bounds, 0)
    if is_end:
        message += 1
    return message
