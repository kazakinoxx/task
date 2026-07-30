"""PsychoPy rendering for the tapping task trial -- thin, not unit
tested. Verify manually with a real window/keyboard. See the src2
project's trials/tapping_task_trial.py for the pure state machine this
drives.
"""

from __future__ import annotations

from typing import Callable, Optional

from frontend.rich_text import RichText
from frontend.style_constants import (
    DEFAULT_FONT,
    DEFAULT_WRAP_WIDTH,
    TAPPING_GO_HEADER_COLOR,
    TAPPING_GO_HEADER_HEIGHT,
    TAPPING_GO_HEADER_POS,
    TAPPING_PROMPT_POS,
    TEXT_COLOR,
    TEXT_HEIGHT,
)
from frontend.thermometer_stim import ThermometerStim
from frontend.drawUtils.common import MarkupStim, resolve_text
from src2.trials.tapping_task_trial import TappingTaskParams, TappingTaskState


def run_tapping(
    win,
    keyboard_monitor,
    clock,
    params: TappingTaskParams,
    trigger_fn: Optional[Callable[[bool], None]] = None,
    translator=None,
    go_text: Optional[str] = None,
    release_warning_text: Optional[str] = None,
    continue_tapping_reminder_text: Optional[str] = None,
    height: float = TEXT_HEIGHT, color: str = TEXT_COLOR, font: str = DEFAULT_FONT,
    pos=TAPPING_PROMPT_POS, wrap_width: Optional[float] = DEFAULT_WRAP_WIDTH, align: str = 'center',
) -> dict:
    """Drives one tapping-task trial against a real PsychoPy window and
    keyboard monitor. `trigger_fn(is_end)` is called at trial start/end
    if provided (wiring to triggers/trigger.py's send_trigger).

    `go_text` overrides the "GO!" cue markup -- defaults to the
    translated GO_MESSAGE if omitted (or no text at all with no
    translator). How it's shown depends on `params.flash_go_message`:
    when True (validation only), it's a green header flashed at the top
    of the screen for GO_DURATION ms right as the trial starts running,
    then hidden (port of the `#go-message` visibility toggle in
    `startRunning()`/`stopRunning()`); when False (default -- practice,
    calibration, demo), it stays in the center at `pos` continuously
    while tapping. `release_warning_text` overrides the
    markup shown at `pos` while a hold key is released mid-trial --
    defaults to the translated PREMATURE_KEY_RELEASE_ERROR_MESSAGE if
    omitted. `continue_tapping_reminder_text` overrides the markup shown
    at `pos` (in bold) once `params.showing_continue_reminder` goes True
    -- i.e. only shown at all when `params.continue_tapping_reminder_message`
    was set on the TappingTaskParams in the first place (matches
    tapping-task-trial.ts's `if (trial.continueTappingReminderMessage)`
    opt-in guard; port of `showContinueReminder()`). Defaults to the
    translated CONTINUE_TAPPING_MESSAGE if omitted. All three may contain
    the i18n HTML spans (hold-key/tap-key words render colored, see
    rich_text). `height`/`color`/`font`/`pos`/`wrap_width`/`align`
    control the `pos`-anchored text's styling and layout; the go-message
    header always uses TAPPING_GO_HEADER_* styling, same meaning as
    elsewhere in frontend/rich_text.py."""

    # ------------------------------------------------------------
    # 1. PREPARE STATIC TEXT OBJECTS (CACHED)
    # ------------------------------------------------------------
    # Resolve the three text variants (may contain HTML).
    resolved_go_text = resolve_text(translator, 'GO_MESSAGE', override=go_text)
    resolved_release_text = resolve_text(
        translator, 'PREMATURE_KEY_RELEASE_ERROR_MESSAGE', override=release_warning_text
    )
    resolved_reminder_text = resolve_text(
        translator, 'CONTINUE_TAPPING_MESSAGE', override=continue_tapping_reminder_text
    )

    # Pre‑create RichText objects for each possible center text state.
    # We'll store them in a dict keyed by the final markup string to
    # avoid re‑parsing HTML on every frame.
    _rich_cache = {}

    def get_rich(markup: str) -> Optional[RichText]:
        if markup is None:
            return None
        if markup not in _rich_cache:
            _rich_cache[markup] = RichText(
                win, markup, height=height, color=color,
                font=font, pos=pos, wrap_width=wrap_width, align=align
            )
        return _rich_cache[markup]

    # Build the three variants:
    go_markup = resolved_go_text if resolved_go_text else ''
    release_markup = resolved_release_text if resolved_release_text else ''
    # Reminder markup: if we have a go text and we are NOT flashing it as a header,
    # then combine go + bold reminder; else just bold reminder.
    if resolved_go_text and not params.flash_go_message:
        reminder_markup = f'{resolved_go_text}<br><br><b>{resolved_reminder_text}</b>'
    else:
        reminder_markup = f'<b>{resolved_reminder_text}</b>' if resolved_reminder_text else ''

    # Cache them:
    go_rich = get_rich(go_markup) if go_markup else None
    release_rich = get_rich(release_markup) if release_markup else None
    reminder_rich = get_rich(reminder_markup) if reminder_markup else None

    # For the flashing GO header (only used when params.flash_go_message is True)
    go_header = None
    if resolved_go_text and params.flash_go_message:
        go_header = RichText(
            win, resolved_go_text, height=TAPPING_GO_HEADER_HEIGHT,
            color=TAPPING_GO_HEADER_COLOR, font=font,
            pos=TAPPING_GO_HEADER_POS, wrap_width=wrap_width, align='center'
        )

    # ------------------------------------------------------------
    # 2. STATE INITIALISATION
    # ------------------------------------------------------------
    state = TappingTaskState(params)
    thermometer = ThermometerStim(win) if params.show_thermometer else None

    now = clock.getTime()
    if state.start(now):
        return state.build_trial_record()

    if trigger_fn:
        trigger_fn(False)

    deadline: Optional[float] = None
    if not params.show_freeze_frame:
        if state.start_running(now):
            if trigger_fn:
                trigger_fn(True)
            return state.build_trial_record()
        deadline = now + params.trial_duration / 1000.0

    # ------------------------------------------------------------
    # 3. MAIN LOOP (optimised for FPS)
    # ------------------------------------------------------------
    while not state.trial_ended:
        now = clock.getTime()

        # Keyboard events
        for key, event_type, event_time in keyboard_monitor.poll():
            if event_type == 'down':
                state.handle_key_down(key, event_time)
            else:
                ui_events = state.handle_key_up(key, event_time)
                if params.show_freeze_frame and 'freeze_frame_first_tap' in ui_events:
                    if state.start_running(event_time):
                        deadline = None
                    else:
                        deadline = event_time + params.trial_duration / 1000.0

        state.tick(now)

        # Thermometer update & draw
        if thermometer is not None:
            thermometer.update(state.mercury_height, params.bounds)
            thermometer.draw()

        # Decide which pre‑cached text to draw (no parsing, no new objects)
        if not state.are_keys_held and release_rich is not None:
            current_rich = release_rich
        elif state.showing_continue_reminder and reminder_rich is not None:
            current_rich = reminder_rich
        elif params.flash_go_message:
            # Center text is hidden; only the header may be shown.
            current_rich = None
        else:
            current_rich = go_rich

        if current_rich is not None:
            current_rich.draw()

        # Draw the flashing GO header (if active)
        if go_header is not None and state.showing_go_message:
            go_header.draw()

        # Flip the window – once per frame
        win.flip()

        # Check trial deadline
        if deadline is not None and now >= deadline:
            state.stop_running(now, error_flag=False)

    # ------------------------------------------------------------
    # 4. CLEANUP
    # ------------------------------------------------------------
    if trigger_fn:
        trigger_fn(True)

    return state.build_trial_record()