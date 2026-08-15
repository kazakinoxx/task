from dataclasses import dataclass
from typing import Any, Optional
from frontend.narration import Narration
from src2.state.experiment_state import ExperimentState
from src2.data.data_writer import RecordingTrialHistory
from src2.i18n.translator import Translator
from src2.triggers.trigger_device import TriggerDevice
# Import the BLEController (or use a forward reference if needed)
from device_connection.BLEController import BLEController

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

    def ble_trigger(self, is_end: bool) -> None:
        """Send a BLE start (is_end=False) or stop (is_end=True) trigger, if a
        BLE controller is wired (no-op otherwise). Shaped to plug straight
        into run_tapping's `trigger_fn(is_end)` hook: it fires False at GO and
        True when the trial ends (deadline reached or early key release)."""
        if self.ble is not None:
            (self.ble.send_stop if is_end else self.ble.send_start)()