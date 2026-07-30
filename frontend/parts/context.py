from dataclasses import dataclass
from typing import Any, Optional
from frontend.narration import Narration
from src2.state.experiment_state import ExperimentState
from src2.data.data_writer import RecordingTrialHistory
from src2.i18n.translator import Translator
from src2.triggers.trigger_device import TriggerDevice
# Import the BLEController (or use a forward reference if needed)
from device_connection import BLEController

@dataclass
class PhaseContext:
    win: Any
    keyboard_monitor: Any
    clock: Any
    state: ExperimentState
    history: RecordingTrialHistory
    trigger_device: TriggerDevice
    translator: Translator
    participant_name: str
    narration: Narration
    ble: Optional[BLEController] = None