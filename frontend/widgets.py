"""Reusable PsychoPy interaction widgets -- thin, not unit tested.

`Button` is a mouse-clickable button (a filled Rect + a bold label,
styled after the web app's black `.jspsych-btn`). `run_button_screen`
runs the draw/poll loop for a screen whose only job is to wait for the
participant to either click one of several buttons or press an
equivalent key, returning the chosen index.

Keyboard input is kept alongside the mouse so the existing keys (and the
Escape-to-quit handled inside `keyboard_monitor.poll()`) keep working;
the buttons are an added affordance, not a replacement.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from frontend.style_constants import (
    BUTTON_FILL_COLOR,
    BUTTON_HEIGHT,
    BUTTON_HOVER_COLOR,
    BUTTON_TEXT_COLOR,
    BUTTON_TEXT_HEIGHT,
    BUTTON_WIDTH,
    DEFAULT_FONT,
)


class Button:
    """A filled rounded-ish rect with a centered bold label. Hit-testing
    and hover are driven externally by `run_button_screen` via a mouse."""

    def __init__(self, win, label: str, pos, width: float = BUTTON_WIDTH, height: float = BUTTON_HEIGHT):
        from psychopy import visual

        self._rect = visual.Rect(win, width=width, height=height, pos=pos, fillColor=BUTTON_FILL_COLOR, lineColor=None)
        self._label = visual.TextStim(
            win, text=label, pos=pos, height=BUTTON_TEXT_HEIGHT, color=BUTTON_TEXT_COLOR, font=DEFAULT_FONT, bold=True,
        )

    @property
    def rect(self):
        return self._rect

    def update_hover(self, mouse) -> None:
        self._rect.fillColor = BUTTON_HOVER_COLOR if self._rect.contains(mouse.getPos()) else BUTTON_FILL_COLOR

    def draw(self) -> None:
        self._rect.draw()
        self._label.draw()


def run_button_screen(
    win,
    keyboard_monitor,
    buttons: Sequence[Button],
    key_map: Optional[Dict[str, int]] = None,
    extra_stims: Sequence = (),
) -> int:
    """Draws `extra_stims` (static text/images) + `buttons` each frame and
    returns the index of the button clicked, or the index mapped to a key
    released (`key_map`: lowercased key -> index). A click is taken on the
    press edge so holding the mouse down doesn't fire repeatedly."""
    from psychopy import event

    key_map = {k.lower(): v for k, v in (key_map or {}).items()}
    mouse = event.Mouse(win=win, visible=True)
    prev_pressed = bool(mouse.getPressed()[0])

    while True:
        for key, event_type, _ in keyboard_monitor.poll():
            if event_type == 'up' and key.lower() in key_map:
                return key_map[key.lower()]

        pressed_now = bool(mouse.getPressed()[0])
        if pressed_now and not prev_pressed:
            for index, button in enumerate(buttons):
                if mouse.isPressedIn(button.rect, buttons=[0]):
                    return index
        prev_pressed = pressed_now

        for stim in extra_stims:
            stim.draw()
        for button in buttons:
            button.update_hover(mouse)
            button.draw()
        win.flip()


def two_button_row(win, labels: List[str]) -> List[Button]:
    """Convenience: two buttons side by side on the button row."""
    from frontend.style_constants import BUTTON_ROW_Y, BUTTON_X_OFFSET

    return [
        Button(win, labels[0], pos=(-BUTTON_X_OFFSET, BUTTON_ROW_Y)),
        Button(win, labels[1], pos=(BUTTON_X_OFFSET, BUTTON_ROW_Y)),
    ]


def single_button(win, label: str) -> Button:
    """Convenience: one centered button on the button row."""
    from frontend.style_constants import BUTTON_ROW_Y

    return Button(win, label, pos=(0, BUTTON_ROW_Y))
