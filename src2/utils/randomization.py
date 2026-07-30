"""Randomization helpers.

Port of the randomization-related functions in
src/modules/experiment/utils/utils.ts. Uses Python's `random` module;
exact draws will not match the JS Math.random() stream (different PRNGs),
but distribution shape and algorithm are preserved.
"""

from __future__ import annotations

import math
import random
from typing import List, TypeVar

T = TypeVar('T')


def random_number_bm(min_value: float, max_value: float, skew: float = 1) -> float:
    """Random number with a bias towards the mean (Box-Muller transform).

    Direct port of randomNumberBm in utils.ts, including its resample-if-
    out-of-range recursion.
    """
    u = 0.0
    v = 0.0
    while u == 0:
        u = random.random()
    while v == 0:
        v = random.random()
    num = math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * v)

    num = num / 10.0 + 0.5
    if num > 1 or num < 0:
        return random_number_bm(min_value, max_value, skew)
    num **= skew
    num *= max_value - min_value
    num += min_value
    return num


def sample_delay_uniform_centered(delay_level: float, half_width: float) -> float:
    """Uniform delay sample centered on delay_level, clamped at 0."""
    lo = max(0.0, delay_level - half_width)
    hi = delay_level + half_width
    return random.random() * (hi - lo) + lo


def shuffle(array: List[T]) -> List[T]:
    """Fisher-Yates shuffle -- returns a new shuffled list, leaving the
    input untouched (mirrors the JS `arr = array.slice()` clone)."""
    arr = list(array)
    for i in range(len(arr) - 1, 0, -1):
        j = random.randint(0, i)
        arr[i], arr[j] = arr[j], arr[i]
    return arr
