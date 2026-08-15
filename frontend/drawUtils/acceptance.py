"""PsychoPy rendering for the acceptance (accept/reject offer) trial --
thin, not unit tested. See src2/trials/acceptance_trial.py for the pure
logic this drives.

Port of the acceptance html-button-response in createTaskBlockTrials
(jspsych/trials.ts), whose stimulus is `acceptanceThermometer(bounds,
reward)` (jspsych/stimulus.ts): a thermometer whose blue band shows how
much effort the offer requires (a higher band = more effort), HIGH/LOW
effort labels beside it, and the reward below -- then the Accept/Decline
buttons. The old text-only "press the arrow keys" prompt is gone from the
web app, so it's dropped here too.
"""

from __future__ import annotations

from psychopy import visual

from frontend.style_constants import (
    BUTTON_ROW_Y,
    BUTTON_X_OFFSET,
    DEFAULT_FONT,
    TEXT_COLOR,
    THERMOMETER_HEIGHT,
    THERMOMETER_WIDTH,
)
from frontend.drawUtils.common import resolve_text
from frontend.thermometer_stim import ThermometerStim
from frontend.widgets import Button, run_button_screen
from src2.trials.acceptance_trial import AcceptanceTrialParams, build_acceptance_trial_record

# Offer thermometer: left-of-center in pixels, leaving room for the effort
# labels to its right. These are layout knobs -- tune on a real display.
_THERMO_POS = (-70, 40)
_THERMO_BG_COLOR = '#e0e0e0'
_LABEL_HEIGHT = 22
_REWARD_HEIGHT = 26


def run_acceptance(
    win, keyboard_monitor, params: AcceptanceTrialParams, accept_key: str, reject_key: str,
    translator=None, ble=None,
) -> dict:
    accept_label = resolve_text(translator, 'ACCEPT_BUTTON_MESSAGE', plain=True, fallback='Accept')
    reject_label = resolve_text(translator, 'REJECT_BUTTON_MESSAGE', plain=True, fallback='Decline')
    high_effort = resolve_text(translator, 'HIGH_EFFORT_MESSAGE', plain=True, fallback='High effort')
    low_effort = resolve_text(translator, 'LOW_EFFORT_MESSAGE', plain=True, fallback='Low effort')
    reward_prefix = resolve_text(translator, 'REWARD_TRIAL_MESSAGE', plain=True, fallback='Reward: ')
    reward_text = f'{reward_prefix}{int(round(params.reward))}'

    half_h = THERMOMETER_HEIGHT / 2.0

    # Grey backing behind the thermometer (matches the web app's #e0e0e0
    # thermometer background), drawn before the thermometer's blue band/outline.
    grey_bg = visual.Rect(
        win, width=THERMOMETER_WIDTH, height=THERMOMETER_HEIGHT, pos=_THERMO_POS,
        fillColor=_THERMO_BG_COLOR, lineColor=None, units='pix',
    )
    thermometer = ThermometerStim(win, pos=_THERMO_POS)
    thermometer.update(0, params.bounds)  # no mercury -- just the target band + bounds

    labels_x = _THERMO_POS[0] + THERMOMETER_WIDTH / 2.0 + 70
    high_label = visual.TextStim(
        win, text=high_effort, pos=(labels_x, _THERMO_POS[1] + half_h - 20), color=TEXT_COLOR,
        height=_LABEL_HEIGHT, font=DEFAULT_FONT, units='pix', anchorHoriz='left', alignText='left',
    )
    low_label = visual.TextStim(
        win, text=low_effort, pos=(labels_x, _THERMO_POS[1] - half_h + 20), color=TEXT_COLOR,
        height=_LABEL_HEIGHT, font=DEFAULT_FONT, units='pix', anchorHoriz='left', alignText='left',
    )
    reward_stim = visual.TextStim(
        win, text=reward_text, pos=(_THERMO_POS[0], _THERMO_POS[1] - half_h - 45), color=TEXT_COLOR,
        height=_REWARD_HEIGHT, bold=True, font=DEFAULT_FONT, units='pix',
    )

    # buttons[0] = Accept (right), buttons[1] = Decline (left) -- indices match
    # the key_map so a click and the corresponding key produce the same result.
    buttons = [
        Button(win, accept_label, pos=(BUTTON_X_OFFSET, BUTTON_ROW_Y)),
        Button(win, reject_label, pos=(-BUTTON_X_OFFSET, BUTTON_ROW_Y)),
    ]
    # BLE decision trigger: start when the offer is put on screen, stop the
    # moment a decision (accept/decline) is registered.
    if ble is not None:
        ble.send_start()
    response_index = run_button_screen(
        win, keyboard_monitor, buttons=buttons,
        key_map={accept_key.lower(): 0, reject_key.lower(): 1},
        extra_stims=[grey_bg, thermometer, high_label, low_label, reward_stim],
    )
    if ble is not None:
        ble.send_stop()
    return build_acceptance_trial_record(params, response_index)
