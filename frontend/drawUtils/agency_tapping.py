"""PsychoPy rendering for the agency tapping task trial -- thin, not
unit tested. Verify manually with a real window/keyboard. See the
src2 project's trials/agency_tapping_task_trial.py for the pure state
machine this drives.
"""

from __future__ import annotations

import math

import src2.i18n.stimulus_text as stimulus_text
from frontend.rich_text import RichText
from frontend.drawUtils.common import resolve_text
from frontend.style_constants import (
    DEFAULT_FONT,
    DEFAULT_WRAP_WIDTH,
    INTERRUPTION_BOX_COLOR,
    INTERRUPTION_BOX_HEIGHT,
    INTERRUPTION_BOX_LINE_COLOR,
    INTERRUPTION_BOX_WIDTH,
    INTERRUPTION_OPTIONS_POS,
    INTERRUPTION_QUESTION_POS,
    INTERRUPTION_RELEASE_POS,
    INTERRUPTION_TITLE_POS,
    INTERRUPTION_WRAP_WIDTH,
    TAPPING_PROMPT_POS,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TITLE_TEXT_HEIGHT,
)
from frontend.thermometer_stim import ThermometerStim
from src2.trials.agency_tapping_task_trial import AgencyTappingTaskParams, AgencyTappingTaskState


class _InterruptionOverlay:
    """The yellow "pause" card shown while a core/practice trial is
    interrupted for the Y/N agency question. Built once per trial (only
    for trials that can actually interrupt) and drawn per frame based on
    which sub-step of the interruption sequence the state machine is in.
    Without this, the interruption states drew nothing -- the screen just
    froze on a blank frame with no visible question."""

    def __init__(self, win, translator, keys_to_hold) -> None:
        from psychopy import visual

        self._box = visual.Rect(
            win,
            width=INTERRUPTION_BOX_WIDTH,
            height=INTERRUPTION_BOX_HEIGHT,
            fillColor=INTERRUPTION_BOX_COLOR,
            lineColor=INTERRUPTION_BOX_LINE_COLOR,
            units='norm',
        )
        self._title = RichText(
            win, stimulus_text.question(translator), height=TITLE_TEXT_HEIGHT,
            color=TEXT_COLOR, pos=INTERRUPTION_TITLE_POS, wrap_width=INTERRUPTION_WRAP_WIDTH, align='center',
        )
        self._question = RichText(
            win, stimulus_text.agency_task_control_question(translator), height=TEXT_HEIGHT,
            color=TEXT_COLOR, pos=INTERRUPTION_QUESTION_POS, wrap_width=INTERRUPTION_WRAP_WIDTH, align='center',
        )
        self._options = RichText(
            win, stimulus_text.answer_options_instruction(translator), height=TEXT_HEIGHT,
            color=TEXT_COLOR, pos=INTERRUPTION_OPTIONS_POS, wrap_width=INTERRUPTION_WRAP_WIDTH, align='center',
        )
        self._release = RichText(
            win, stimulus_text.interruption_release_keys_message(translator), height=TEXT_HEIGHT,
            color=TEXT_COLOR, pos=INTERRUPTION_RELEASE_POS, wrap_width=INTERRUPTION_WRAP_WIDTH, align='center',
        )
        hold_label = ', '.join(k.upper() for k in keys_to_hold)
        self._reminder = RichText(
            win, stimulus_text.hold_keys_message_agency(translator, hold_label), height=TEXT_HEIGHT,
            color=TEXT_COLOR, pos=(0, 0), wrap_width=INTERRUPTION_WRAP_WIDTH, align='center',
        )
        # Resume countdown number -- a plain TextStim so its .text can be
        # cheaply updated each frame without re-parsing markup.
        self._countdown = visual.TextStim(
            win, text='', color=TEXT_COLOR, height=TITLE_TEXT_HEIGHT, font=DEFAULT_FONT, pos=(0, 0), units='norm',
        )
        self._keys_to_hold = list(keys_to_hold)

    def draw(self, state, now: float) -> None:
        self._box.draw()
        if state.awaiting_interruption_response:
            self._title.draw()
            self._question.draw()
            self._options.draw()
            # Prompt to free a hand only while the hold keys are still down.
            if all(state.keys_state[k] for k in self._keys_to_hold):
                self._release.draw()
        elif state.awaiting_resume_countdown:
            deadline = state._resume_countdown_deadline
            remaining = 0.0 if deadline is None else max(0.0, deadline - now)
            self._countdown.text = str(int(math.ceil(remaining)))
            self._countdown.draw()
        elif state.awaiting_hold_key_reminder:
            self._reminder.draw()
        else:
            # Interruption triggered but momentarily between sub-steps --
            # keep the question card up rather than flashing to blank.
            self._question.draw()


def run_agency_tapping(win, keyboard_monitor, clock, params: AgencyTappingTaskParams, translator=None, ble=None) -> dict:
    state = AgencyTappingTaskState(params)
    thermometer = ThermometerStim(win) if params.show_thermometer else None

    # Only non-'target' trials interrupt, so only they need the card. Skip
    # building it (and its per-trial TextStim/RichText cost) otherwise, and
    # degrade gracefully to the old no-overlay behavior if no translator was
    # supplied.
    interruption_overlay = None
    if translator is not None and not state.no_interruption:
        interruption_overlay = _InterruptionOverlay(win, translator, params.keys_to_hold)

    # "You released your keys" warning, shown (in place of the thermometer)
    # while a hold key is up mid-trial -- same message and behavior as the
    # base tapping task. Only built when a translator is available.
    release_rich = None
    if translator is not None:
        release_rich = RichText(
            win, resolve_text(translator, 'PREMATURE_KEY_RELEASE_ERROR_MESSAGE'),
            height=TEXT_HEIGHT, color=TEXT_COLOR, font=DEFAULT_FONT,
            pos=TAPPING_PROMPT_POS, wrap_width=DEFAULT_WRAP_WIDTH, align='center',
        )

    now = clock.getTime()
    if state.start(now):
        return state.build_trial_record()

    # BLE triggers for the control task's three phases. Phase 1 (tapping up to
    # the interruption) starts now, at GO; the transitions inside the loop
    # stop it and bracket the control decision (the Y/N interruption) and the
    # resumed second tapping phase. If no interruption fires (too few taps),
    # phase 1 simply runs to the trial end and the single stop below closes it.
    if ble is not None:
        ble.send_start()
    prev_awaiting_response = False
    prev_in_interruption = False

    while not state.trial_ended:
        now = clock.getTime()
        # Poll the keyboard exactly once per frame. poll() drains the event
        # buffer, so a second poll() in the same iteration sees an (almost)
        # empty queue -- that's why the interruption answer previously only
        # registered if the y/n/o keyup happened to land in the gap between
        # the two polls (hence "tap twice"). Route each event to the
        # hold/tap handlers and, while awaiting the agency question, to the
        # interruption-response handler as well.
        for key, event_type, event_time in keyboard_monitor.poll():
            if event_type == 'down':
                state.handle_key_down(key, event_time)
            else:
                state.handle_key_up(key, event_time)
            if (
                state.awaiting_interruption_response
                and event_type == 'up'
                and key.lower() in ('y', 'n', 'o')
            ):
                state.receive_interruption_response(key, event_time)

        if state.awaiting_interruption_response:
            pass  # still waiting for the y/n/o answer (handled in the poll above)
        elif state.awaiting_hold_key_reminder:
            if all(state.keys_state[k] for k in params.keys_to_hold):
                state.confirm_keys_reheld(now)
        else:
            state.tick(now)

        # -- BLE control-task phase transitions --
        if ble is not None:
            if state.awaiting_interruption_response and not prev_awaiting_response:
                # Interruption fired: end phase-1 tapping, begin control decision.
                ble.send_stop()
                ble.send_start()
            elif prev_awaiting_response and not state.awaiting_interruption_response:
                # Y/N answered: end the control decision.
                ble.send_stop()
            if prev_in_interruption and not state.is_in_interruption:
                # Resume countdown elapsed: begin the second tapping phase.
                ble.send_start()
        prev_awaiting_response = state.awaiting_interruption_response
        prev_in_interruption = state.is_in_interruption

        # Draw + flip exactly once per frame so the loop stays throttled to
        # the monitor refresh (waitBlanking). Previously the flip lived inside
        # the thermometer guard, so during the interruption Q&A the loop spun
        # with no vsync, pinning a CPU core and starving the following frames.
        # During an interruption the thermometer is hidden and the yellow
        # question card is shown in its place. Otherwise, if a hold key is
        # released mid-trial the thermometer is hidden and the release warning
        # is shown alone (matching the base tapping task, so the two don't
        # overlap); when keys are held, the thermometer is advanced and drawn.
        if state.is_in_interruption:
            if interruption_overlay is not None:
                interruption_overlay.draw(state, now)
            # else: no translator -> nothing to draw, but still flip below.
        elif not state.are_keys_held and release_rich is not None:
            release_rich.draw()
        elif thermometer is not None:
            thermometer.update(state.mercury_height, params.bounds)
            thermometer.draw()
        win.flip()

    # Close whichever phase was active when the trial ended (phase 1 if there
    # was no interruption, otherwise the resumed second tapping phase).
    if ble is not None:
        ble.send_stop()
    return state.build_trial_record()
