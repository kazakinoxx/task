"""PsychoPy runtime builders -- window, clock, keyboard monitor. The
only place a real psychopy.visual.Window gets constructed.
"""

from __future__ import annotations


def build_window():
    from psychopy import visual

    from frontend.style_constants import WINDOW_COLOR, WINDOW_FULLSCREEN, WINDOW_UNITS

    return visual.Window(fullscr=WINDOW_FULLSCREEN, color=WINDOW_COLOR, units=WINDOW_UNITS,useFBO=True)


def build_clock():
    from psychopy import core

    return core.Clock()


def build_keyboard_monitor(win, clock):
    from frontend.keyboard_monitor import PygletKeyHoldMonitor

    return PygletKeyHoldMonitor(win, clock)
