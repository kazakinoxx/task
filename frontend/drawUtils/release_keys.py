"""PsychoPy rendering for the release-keys trial -- thin, not unit
tested. See src2/trials/release_keys_trial.py for the pure state machine
this drives.
"""

from __future__ import annotations

from frontend.style_constants import DEFAULT_FONT, DEFAULT_WRAP_WIDTH, TEXT_COLOR, TEXT_HEIGHT
from frontend.drawUtils.common import resolve_text
from src2.trials.release_keys_trial import ReleaseKeysParams, ReleaseKeysState


def run_release_keys(win, keyboard_monitor, params: ReleaseKeysParams, translator=None) -> dict:
    from psychopy import visual

    state = ReleaseKeysState(params)
    if state.ended:
        return state.build_trial_record()

    message = resolve_text(translator, 'RELEASE_KEYS_MESSAGE', plain=True, fallback='Release all keys')
    text_stim = visual.TextStim(
        win, text=message, height=TEXT_HEIGHT, color=TEXT_COLOR, wrapWidth=DEFAULT_WRAP_WIDTH, font=DEFAULT_FONT,
    )
    while not state.ended:
        for key, event_type, _ in keyboard_monitor.poll():
            if event_type == 'up':
                state.handle_key_up(key)
            else:
                state.handle_key_down(key)
        text_stim.draw()
        win.flip()

    return state.build_trial_record()
