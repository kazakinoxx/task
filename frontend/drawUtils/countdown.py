"""PsychoPy rendering for the countdown trial -- thin, not unit tested.
See src2/trials/countdown_trial.py for the pure state machine this drives.
"""

from __future__ import annotations

from typing import Optional

from frontend.style_constants import DEFAULT_FONT, TEXT_COLOR, TEXT_HEIGHT
from frontend.drawUtils.common import MarkupStim, resolve_text
from src2.i18n.stimulus_text import to_name
from src2.trials.countdown_trial import CountdownParams, CountdownState, format_countdown_time


def run_countdown(
    win, keyboard_monitor, clock, params: CountdownParams, translator=None,
    hold_text: Optional[str] = None, countdown_label: Optional[str] = None,
    height: float = TEXT_HEIGHT, color: str = TEXT_COLOR, font: str = DEFAULT_FONT,
    pos=(0, 0), wrap_width: Optional[float] = None, align: str = 'center',
) -> dict:
    """`hold_text` overrides the markup shown before the countdown starts
    (while waiting for the hold keys) -- defaults to the translated
    HOLD_KEYS_MESSAGE if omitted (or '' with no translator). `countdown_label`
    overrides the text shown before the ticking mm:ss time -- defaults to
    the translated COUNTDOWN_TIMER_MESSAGE if omitted (or no prefix at all
    with no translator). Both may contain the i18n HTML spans (hold-key/
    tap-key words render colored, see rich_text). `height`/`color`/`font`/
    `pos`/`wrap_width`/`align` control the text's styling and layout, same
    meaning as elsewhere in frontend/rich_text.py."""
    state = CountdownState(params)

    hold_markup = resolve_text(
        translator, 'HOLD_KEYS_MESSAGE', override=hold_text,
        HOLD_KEYS_REPLACE=' and '.join(to_name(k) for k in params.keys_to_hold),
    )
    countdown_label = resolve_text(translator, 'COUNTDOWN_TIMER_MESSAGE', override=countdown_label)

    text = MarkupStim(win, height=height, color=color, font=font, pos=pos, wrap_width=wrap_width, align=align)

    while not state.ended:
        now = clock.getTime()
        for key, event_type, event_time in keyboard_monitor.poll():
            if event_type == 'down':
                state.handle_key_down(key, event_time)
            else:
                state.handle_key_up(key, event_time)

        state.tick(now)

        if state.countdown_active and state._countdown_deadline is not None:
            remaining_ms = max(0.0, (state._countdown_deadline - now) * 1000)
            time_text = format_countdown_time(remaining_ms)
            markup = f'{countdown_label} {time_text}' if countdown_label else time_text
        else:
            markup = hold_markup

        text.draw(markup)
        win.flip()

    return state.build_trial_record()
