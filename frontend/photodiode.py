"""PhotoDiode flasher -- thin PsychoPy execution of a flash schedule,
not unit tested (manually verified). See the src2 project's
triggers/photodiode.py for the pure `photodiode_flash_schedule` this
drives.
"""

from __future__ import annotations

from typing import Callable, Optional

from src2.triggers.photodiode import photodiode_flash_schedule


class PhotoDiodeFlasher:
    """Executes a photodiode_flash_schedule against a PsychoPy Rect
    stimulus pinned to a screen corner."""

    def __init__(self, rect_stim, win, wait_fn: Optional[Callable[[float], None]] = None):
        self.rect_stim = rect_stim
        self.win = win
        if wait_fn is None:
            from psychopy import core

            wait_fn = core.wait
        self._wait_fn = wait_fn

    def flash(self, is_end: bool = False) -> None:
        schedule = photodiode_flash_schedule(is_end)
        last_time = 0.0
        for delay, color in schedule:
            wait_time = delay - last_time
            if wait_time > 0:
                self._wait_fn(wait_time)
            self.rect_stim.color = color
            self.rect_stim.draw()
            self.win.flip()
            last_time = delay
