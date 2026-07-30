"""PsychoPy rendering for the loading bar trial -- thin, not unit
tested. See src2/trials/loading_bar_trial.py for the pure state machine
this drives.
"""

from __future__ import annotations

from frontend.style_constants import (
    DEFAULT_FONT,
    LOADING_BAR_CAPTION_POS,
    LOADING_BAR_FILL_COLOR,
    LOADING_BAR_HEIGHT,
    LOADING_BAR_LABEL_POS,
    LOADING_BAR_TRACK_COLOR,
    LOADING_BAR_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT_SMALL,
)
from frontend.drawUtils.common import resolve_text
from src2.trials.loading_bar_trial import TICK_INTERVAL_SECONDS, LoadingBarState


def run_loading_bar(win, acceptance: bool, wait_fn=None, translator=None) -> dict:
    from psychopy import core, visual

    if wait_fn is None:
        wait_fn = core.wait

    caption = resolve_text(translator, 'LOADING_BAR_MESSAGE', plain=True, fallback='Loading...')

    state = LoadingBarState(acceptance)
    bar_outline = visual.Rect(
        win, width=LOADING_BAR_WIDTH, height=LOADING_BAR_HEIGHT, lineColor=None, fillColor=LOADING_BAR_TRACK_COLOR,
    )
    bar_fill = visual.Rect(
        win, width=0.0, height=LOADING_BAR_HEIGHT, fillColor=LOADING_BAR_FILL_COLOR, lineColor=None,
    )
    label = visual.TextStim(
        win, text='0%', pos=LOADING_BAR_LABEL_POS, height=TEXT_HEIGHT_SMALL, color=TEXT_COLOR, font=DEFAULT_FONT,
    )
    caption_stim = visual.TextStim(
        win, text=caption, pos=LOADING_BAR_CAPTION_POS, height=TEXT_HEIGHT_SMALL, color=TEXT_COLOR, font=DEFAULT_FONT,
    )

    while not state.ended:
        state.step()
        bar_fill.width = LOADING_BAR_WIDTH * (state.percentage / 100.0)
        label.text = f'{state.percentage}%'
        bar_outline.draw()
        bar_fill.draw()
        label.draw()
        caption_stim.draw()
        win.flip()
        wait_fn(TICK_INTERVAL_SECONDS)

    return {}
