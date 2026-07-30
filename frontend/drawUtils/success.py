"""PsychoPy rendering for the success/failure feedback screen -- thin,
not unit tested. See src2/trials/success_trial.py for the pure logic
this drives.
"""

from __future__ import annotations

from frontend.rich_text import RichText
from frontend.style_constants import (
    DEFAULT_FONT,
    DEFAULT_WRAP_WIDTH,
    FAILURE_COLOR,
    FEEDBACK_TEXT_HEIGHT,
    SKIP_COLOR,
    SUCCESS_COLOR,
    TEXT_COLOR,
)
from frontend.drawUtils.common import resolve_text
from src2.trials.success_trial import build_success_trial_record, success_screen_variant


def run_success_screen(win, screen_params: dict, reason_text: str = '', translator=None, key_settings=None) -> dict:
    from psychopy import core, visual

    reason_markup = reason_text
    if not reason_markup and translator is not None and screen_params.get('reason_code'):
        from src2.i18n.stimulus_text import resolve_reason_message

        reason_markup = resolve_reason_message(translator, screen_params['reason_code'], key_settings or {})

    variant = success_screen_variant(
        screen_params['success'],
        screen_params.get('show_freeze_frame', False),
        bool(reason_markup),
        screen_params.get('skip', False),
    )

    if 'freeze_frame' in variant:
        # Reason paragraph: black base text with the hold-key/tap-key words
        # colored inline (rich), matching the web app's spans.
        stim = RichText(
            win, reason_markup, height=FEEDBACK_TEXT_HEIGHT, color=TEXT_COLOR, font=DEFAULT_FONT,
            wrap_width=DEFAULT_WRAP_WIDTH, align='left',
        )
    else:
        color = SUCCESS_COLOR if variant in ('basic_success', 'freeze_frame_success') else FAILURE_COLOR
        if variant == 'skip':
            color = SKIP_COLOR
        succeeded = screen_params['success']
        text = resolve_text(
            translator, 'TRIAL_SUCCEEDED' if succeeded else 'TRIAL_FAILED',
            plain=True, fallback='SUCCESS' if succeeded else 'FAILED',
        )
        stim = visual.TextStim(
            win, text=text, color=color, height=FEEDBACK_TEXT_HEIGHT, wrapWidth=DEFAULT_WRAP_WIDTH, font=DEFAULT_FONT,
        )

    stim.draw()
    win.flip()
    core.wait(screen_params['trial_duration'])

    return build_success_trial_record(screen_params['success'])
