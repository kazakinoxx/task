"""Keyboard hold/tap event bookkeeping.

`KeyEdgeBuffer` is the pure (key, 'down'|'up', time) event queue, kept
independent of any hardware source so it's unit-testable in isolation.
The PsychoPy/pyglet adapter that feeds it (`PygletKeyHoldMonitor`) lives
in src2/frontend/keyboard_monitor.py -- see that module's docstring for
why a pyglet window's native callbacks (not psychopy.hardware.keyboard)
are the right desktop analogue of the JS trials' keydown/keyup listeners.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Tuple


class KeyEdgeBuffer:
    """Pure event queue: accumulates (key, 'down'|'up', time) events as
    they're pushed (e.g. from a hardware callback), and hands them out in
    order via `drain()`. Kept separate from any hardware source so it's
    unit-testable in isolation."""

    def __init__(self):
        self._queue: Deque[Tuple[str, str, float]] = deque()

    def push(self, key: str, event_type: str, time: float) -> None:
        self._queue.append((key.lower(), event_type, time))

    def drain(self) -> List[Tuple[str, str, float]]:
        events = list(self._queue)
        self._queue.clear()
        return events

    def __len__(self) -> int:
        return len(self._queue)
