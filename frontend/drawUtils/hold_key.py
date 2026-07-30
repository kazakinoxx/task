"""PsychoPy rendering for the hold-key practice trial -- thin, not unit
tested. See src2/trials/hold_key_practice_trial.py for the pure state
machine this drives.
"""

from __future__ import annotations

from frontend.style_constants import (
    DEFAULT_FONT,
    HOLD_PROGRESS_BAR_FILL_COLOR,
    HOLD_PROGRESS_BAR_HEIGHT,
    HOLD_PROGRESS_BAR_POS,
    HOLD_PROGRESS_BAR_TRACK_COLOR,
    HOLD_PROGRESS_BAR_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT,
)
from frontend.drawUtils.common import MarkupStim
from src2.i18n.stimulus_text import to_name
from src2.trials.hold_key_practice_trial import HoldKeyPracticeParams, HoldKeyPracticeState


def _hold_key_practice_phase_markup(state: HoldKeyPracticeState, translator, hold_key: str) -> str:
    """Raw i18n markup (with hold-key spans / <b>) per phase, so the rich
    text renderer can color the key. Falls back to the bare phase name
    when there's no translator."""
    if translator is None:
        return state.phase
    if state.phase == 'idle':
        return translator.t('HOLD_S_PROMPT_MESSAGE', HOLD_KEY=to_name(hold_key))
    if state.phase == 'holding':
        return translator.t('HOLD_S_RETRY_MESSAGE', HOLD_KEY=to_name(hold_key))
    if state.phase == 'release_prompt':
        return translator.t('HOLD_S_RELEASE_PROMPT', HOLD_KEY=to_name(hold_key))
    if state.phase == 'feedback':
        if state.success:
            return translator.t('HOLD_S_SUCCESS_MESSAGE')
        return translator.t('KEY_RELEASED_EARLY_FIRST_ERROR_MESSAGE', HOLD_KEY=to_name(hold_key))
    return ''


def run_hold_key(win, keyboard_monitor, clock, params: HoldKeyPracticeParams, translator=None) -> dict:
    from psychopy import visual

    state = HoldKeyPracticeState(params)
    text = MarkupStim(win, height=TEXT_HEIGHT, color=TEXT_COLOR, font=DEFAULT_FONT)

    bar_left = HOLD_PROGRESS_BAR_POS[0] - HOLD_PROGRESS_BAR_WIDTH / 2
    bar_track = visual.Rect(
        win, width=HOLD_PROGRESS_BAR_WIDTH, height=HOLD_PROGRESS_BAR_HEIGHT,
        pos=HOLD_PROGRESS_BAR_POS, lineColor=None, fillColor=HOLD_PROGRESS_BAR_TRACK_COLOR,
    )
    bar_fill = visual.Rect(
        win, width=0.0, height=HOLD_PROGRESS_BAR_HEIGHT,
        pos=HOLD_PROGRESS_BAR_POS, lineColor=None, fillColor=HOLD_PROGRESS_BAR_FILL_COLOR,
    )

    while not state.ended:
        now = clock.getTime()
        for key, event_type, event_time in keyboard_monitor.poll():
            if event_type == 'down':
                state.handle_key_down(key, event_time)
            else:
                state.handle_key_up(key, event_time)

        state.tick(now)

        markup = _hold_key_practice_phase_markup(state, translator, params.hold_key)
        text.draw(markup)

        progress = state.hold_progress(now)
        if progress is not None:
            fill_width = HOLD_PROGRESS_BAR_WIDTH * progress
            bar_fill.width = fill_width
            bar_fill.pos = (bar_left + fill_width / 2, HOLD_PROGRESS_BAR_POS[1])
            bar_track.draw()
            bar_fill.draw()

        win.flip()

    return state.build_trial_record()
