"""Loading bar trial -- port of
src/modules/experiment/trials/loading-bar-trial.ts.

A mandatory rest period after a tapping trial: percentage increments by
a random amount every ~100ms until reaching 100%. Accepted trials get a
slower bar (longer rest); rejected trials get a faster bar.
"""

from __future__ import annotations

import math
import random
from typing import Optional

from src2.utils.constants import LOADING_BAR_SPEED_NO, LOADING_BAR_SPEED_YES

TICK_INTERVAL_SECONDS = 0.1  # matches the JS `setTimeout(..., 100)` cadence


def loading_bar_increment(acceptance: bool, rng: Optional[random.Random] = None) -> int:
    """Port of the increment calculation in loadingBarTrial's on_load."""
    rng = rng or random
    speed = LOADING_BAR_SPEED_YES if acceptance else LOADING_BAR_SPEED_NO
    return math.ceil(rng.random() * speed)


class LoadingBarState:
    """Pure port of the updatePercentage recursion's state."""

    def __init__(self, acceptance: bool):
        self.acceptance = acceptance
        self.percentage = 0
        self.ended = False

    def step(self, rng: Optional[random.Random] = None) -> int:
        increment = loading_bar_increment(self.acceptance, rng)
        self.percentage = min(self.percentage + increment, 100)
        if self.percentage >= 100:
            self.ended = True
        return self.percentage
