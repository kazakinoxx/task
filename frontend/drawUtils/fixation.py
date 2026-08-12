"""Fixation-cross screen -- draws a centered '+' (plus an optional
instruction below it) and holds it for a fixed duration. Thin, not unit
tested; verify manually on a real window.
"""

from __future__ import annotations

from typing import Optional

from frontend.rich_text import RichText
from frontend.style_constants import (
    DEFAULT_FONT,
    FIXATION_CROSS_COLOR,
    FIXATION_CROSS_SIZE,
    FIXATION_CROSS_THICKNESS,
    FIXATION_DURATION,
    FIXATION_MESSAGE_POS,
    MESSAGE_WRAP_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT,
)


def run_fixation(win, clock, duration: float = FIXATION_DURATION, text: Optional[str] = None) -> None:
    """Show a centered fixation cross for `duration` seconds. The cross is
    two thin rectangles in 'height' units so it stays square regardless of
    the window's aspect ratio; `text` (if given) is drawn below it."""
    from psychopy import core, visual

    horizontal = visual.Rect(
        win, width=FIXATION_CROSS_SIZE, height=FIXATION_CROSS_THICKNESS,
        fillColor=FIXATION_CROSS_COLOR, lineColor=None, units='height',
    )
    vertical = visual.Rect(
        win, width=FIXATION_CROSS_THICKNESS, height=FIXATION_CROSS_SIZE,
        fillColor=FIXATION_CROSS_COLOR, lineColor=None, units='height',
    )
    message = None
    if text:
        message = RichText(
            win, text, height=TEXT_HEIGHT, color=TEXT_COLOR, font=DEFAULT_FONT,
            pos=FIXATION_MESSAGE_POS, wrap_width=MESSAGE_WRAP_WIDTH, align='center',
        )

    horizontal.draw()
    vertical.draw()
    if message is not None:
        message.draw()
    win.flip()
    core.wait(duration)
