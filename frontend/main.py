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
    .venv310\Scripts\python.exe -m pip install -r src2/requirements.txt
    .venv310\\Scripts\\python -m frontend.main --participant P01
    run cmd : .venv310\Scripts\python.exe -m frontend.main --participant P01_TEST 
"""

from __future__ import annotations

import argparse
import os
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

REPO_ROOT = Path(__file__).resolve().parent.parent

# All experiment output lives under a single top-level `output/` folder:
#   output/task_data/  -- per-participant session/checkpoint JSON (written here)
#   output/eeg/        -- EEG recordings from the versasens worker (config.ini)
#   output/logs/       -- versasens worker logs (versasens/src/utils/logger.py)
# The versasens paths are wired on that side; DATA_DIR wires the task data.
OUTPUT_DIR = REPO_ROOT / 'output'
DATA_DIR = OUTPUT_DIR / 'task_data'
SETTINGS_PATH = REPO_ROOT / 'src2' / 'settings.json'

# The BLE worker (`src.connect`) is the versasens stack, which targets Python
# 3.13, while the experiment runs on 3.10 -- so it is launched under a separate
# interpreter. `project_root` is the versasens folder, resolved relative to this
# repo so it isn't tied to one machine's layout. The 3.13 interpreter location
# IS machine-specific, so it's read from the PYTHON313_HOME env var (set it to
# your Python 3.13 install dir); the fallback keeps the previous default working.
VERSASENS_ROOT = REPO_ROOT / 'versasens'
PYTHON313_HOME = Path(
    os.environ.get('PYTHON313_HOME', r'C:/Users/ikaze/AppData/Local/Programs/Python/Python313')
)
# The versasens audio codec needs libopus; it ships alongside the 3.13 install.
OPUS_LIBRARY_PATH = os.environ.get('OPUS_LIBRARY_PATH', str(PYTHON313_HOME))
# Serial port the marker/trigger board enumerates as (override via BLE_MARKER_PORT).
MARKER_PORT = os.environ.get('BLE_MARKER_PORT', 'COM3')


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

    ble = BLEController.BLEController(
        python313_path=str(PYTHON313_HOME / 'python.exe'),
        project_root=str(VERSASENS_ROOT),
        opus_lib_path=OPUS_LIBRARY_PATH,
    )
    ble.start()  #runs throughout the whole experiment, so we start it here and pass it to the phase runners
    ble.open_marker_port(MARKER_PORT)  # Open the marker port for sending triggers

    try:
        runners = make_phase_runners(
            win, keyboard_monitor, clock, state, history, trigger_device, translator, args.participant, narration, ble
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
