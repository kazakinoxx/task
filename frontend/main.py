"""Entry point -- launches the experiment on real PsychoPy hardware.

This project (`frontend/`) is the only place that imports `psychopy`.
It depends on `src2` (the pure experiment logic, importable with zero
PsychoPy in the loop) the way any application depends on a library --
`src2` has no knowledge of this project at all, so a different frontend
(or none, e.g. a future signal-processing-focused runtime) could stand
in its place without touching `src2`.

`main()` only does process setup (args, settings, data, window) and then
delegates: the experiment *structure* lives in
`src2/experiment_runner.py::run_experiment`, and the per-phase PsychoPy
wiring lives in `frontend/phase_runners.py::make_phase_runners`.

Usage:
    py -3.10 -m venv .venv310
    .venv310\\Scripts\\pip install -r src2/requirements.txt
    .venv310\\Scripts\\python -m frontend.main --participant P01
    run cmd : .venv310\Scripts\python.exe -m frontend.main --participant P01_TEST 
"""

from __future__ import annotations

import argparse
from pathlib import Path

from frontend.narration import Narration
from frontend.phase_runners import CONTINUE_HINT, make_phase_runners, resolve_end_message_text
from frontend.runtime import build_clock, build_keyboard_monitor, build_window
import frontend.drawUtils.message as message

from src2.config.settings_loader import load_settings, settings_to_dict
from src2.data.data_writer import DataWriter, RecordingTrialHistory
from src2.experiment_runner import run_experiment
from src2.i18n.translator import Translator
from src2.parts.calibration import CalibrationAbortedError
from src2.parts.validation import ValidationFailedError
from src2.state.experiment_state import ExperimentState
from src2.state.reload import apply_reload_object
from src2.triggers.trigger_device import create_trigger_device
from device_connection import BLEController
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),   # prints to terminal
    ]
)

DATA_DIR = Path(__file__).parent.parent / 'src2' / 'data'
SETTINGS_PATH = Path(__file__).parent.parent / 'src2' / 'settings.json'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--participant', required=True)
    parser.add_argument('--trigger', choices=['none', 'parallel', 'serial'], default='none')
    parser.add_argument('--trigger-address', default=None)
    parser.add_argument(
        '--audio-device', default=None,
        help=(
            'Exact PsychToolbox/PortAudio device name to force narration '
            'playback through (e.g. a specific headset). List available '
            "devices with: python -c \"from frontend.narration import "
            'list_audio_devices; [print(d) for d in list_audio_devices()]"'
        ),
    )
    parser.add_argument(
        '--audio-mono', action='store_true',
        help='Force mono playback (useful for Bluetooth headsets that only expose a 1-channel Hands-Free endpoint).',
    )
    args = parser.parse_args()

    settings = load_settings(SETTINGS_PATH)
    print(settings_to_dict(settings))  # for debugging, to see what settings were loaded
    translator = Translator(settings.languageSettings.language)
    trigger_device = create_trigger_device(args.trigger, args.trigger_address)
    narration = Narration(
        enabled=settings.generalSettings.useNarration,
        device=args.audio_device,
        stereo=False if args.audio_mono else None,
    )

    data_writer = DataWriter(args.participant, DATA_DIR, settings)
    reload_object = data_writer.load_reload_object()

    state = ExperimentState(settings)
    if reload_object is not None:
        apply_reload_object(state, reload_object)

    history = RecordingTrialHistory(data_writer, trials=data_writer.trials)

    win = build_window()
    clock = build_clock()
    keyboard_monitor = build_keyboard_monitor(win, clock)

    # ble = BLEController.BLEController(
    #     python313_path=r"C:/Users/ikaze/AppData/Local/Programs/Python/Python313/python.exe",
    #     project_root=r"C:/Users/ikaze/Documents/EEGproj/versasens-gui-main",
    #     opus_lib_path=r"C:/Users/ikaze/AppData/Local/Programs/Python/Python313",
    # )
    # ble.start()  #runs throughout the whole experiment, so we start it here and pass it to the phase runners   

    try:
        runners = make_phase_runners(
            win, keyboard_monitor, clock, state, history, trigger_device, translator, args.participant, narration#, ble
        )
        try:
            run_experiment(state, reload_object, runners)
        except (CalibrationAbortedError, ValidationFailedError):
            # Port of finishExperimentEarly (jspsych/finish.ts): show the
            # same next-step-or-generic message as the normal end page,
            # then fall through to the same cleanup as a normal finish.
            history.add({'task': 'finish_experiment', 'trial_type': 'html-button-response'})
            text = resolve_end_message_text(state, translator, args.participant)
            message.run_message(win, keyboard_monitor, text + CONTINUE_HINT, continue_key='space')
    finally:
        data_writer.finalize()
        trigger_device.close()
        win.close()


if __name__ == '__main__':
    main()
