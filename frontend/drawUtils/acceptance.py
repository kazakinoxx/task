"""PsychoPy rendering for the acceptance (accept/reject offer) trial --
thin, not unit tested. See src2/trials/acceptance_trial.py for the pure
logic this drives.
"""

from __future__ import annotations

from frontend.style_constants import (
    BUTTON_ROW_Y,
    BUTTON_X_OFFSET,
    DEFAULT_FONT,
    DEFAULT_WRAP_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT,
)
from frontend.drawUtils.common import resolve_text
from frontend.widgets import Button, run_button_screen
from src2.trials.acceptance_trial import AcceptanceTrialParams, build_acceptance_trial_record
from psychopy import visual

def run_acceptance(
    win, keyboard_monitor, params: AcceptanceTrialParams, accept_key: str, reject_key: str, translator=None
) -> dict:
    

    body = resolve_text(translator, 'ACCEPTANCE_TRIAL_MESSAGE', plain=True, fallback='Accept or Reject?')
    # The reward prefix is only shown alongside the translated body.
    message = f'Reward: {params.reward}\n\n{body}' if translator is not None else body
    accept_label = resolve_text(translator, 'ACCEPT_BUTTON_MESSAGE', plain=True, fallback='Accept')
    reject_label = resolve_text(translator, 'REJECT_BUTTON_MESSAGE', plain=True, fallback='Decline')
    text_stim = visual.TextStim(
        win, text=message, height=TEXT_HEIGHT, color=TEXT_COLOR, wrapWidth=DEFAULT_WRAP_WIDTH, font=DEFAULT_FONT,
    )

    # buttons[0] = Accept (right), buttons[1] = Decline (left) -- indices match
    # the key_map so a click and the corresponding key produce the same result.
    buttons = [
        Button(win, accept_label, pos=(BUTTON_X_OFFSET, BUTTON_ROW_Y)),
        Button(win, reject_label, pos=(-BUTTON_X_OFFSET, BUTTON_ROW_Y)),
    ]
    response_index = run_button_screen(
        win, keyboard_monitor, buttons=buttons,
        key_map={accept_key.lower(): 0, reject_key.lower(): 1}, extra_stims=[text_stim],
    )
    return build_acceptance_trial_record(params, response_index)
