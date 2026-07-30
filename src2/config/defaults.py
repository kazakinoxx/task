"""Default settings values and sort orders.

Port of defaultSettingsValues (SettingsContext.tsx) and
boundsSortOrder/rewardSortOrder/delaySortOrder (src/modules/config/appSettings.ts).
"""

from __future__ import annotations

from src2.config.settings_schema import AllSettingsType
from src2.utils.types import BoundsType, DelayType, RewardType


def default_settings() -> AllSettingsType:
    """Returns a fresh AllSettingsType with the same defaults as
    defaultSettingsValues in SettingsContext.tsx. A fresh instance is
    returned each call so callers can freely mutate it."""
    return AllSettingsType()


BOUNDS_SORT_ORDER = {
    BoundsType.EASY.value: 0,
    BoundsType.EASY_MEDIUM.value: 1,
    BoundsType.MEDIUM.value: 2,
    BoundsType.HARD.value: 3,
}

REWARD_SORT_ORDER = {
    RewardType.LOW.value: 0,
    RewardType.LOW_MIDDLE.value: 1,
    RewardType.MIDDLE.value: 2,
    RewardType.HIGH.value: 3,
}

DELAY_SORT_ORDER = {
    DelayType.SYNC.value: 0,
    DelayType.SHORT_ASYNC.value: 1,
    DelayType.MID_ASYNC.value: 2,
    DelayType.LONG_ASYNC.value: 3,
}
