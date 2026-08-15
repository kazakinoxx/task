# final_calibration_phase.py

import frontend.drawUtils.message as message
import frontend.drawUtils.countdown as countdown
import frontend.drawUtils.tapping as tapping
import frontend.drawUtils.release_keys as release_keys
import frontend.drawUtils.loading_bar as loading_bar
import frontend.drawUtils.success as success

import src2.i18n.stimulus_text as stimulus_text
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
from src2.utils.constants import CONTINUE_HINT
from src2.utils.calculations import get_hold_keys, get_tap_key
from src2.trials.countdown_trial import CountdownParams
from src2.trials.tapping_task_trial import TappingTaskParams
from src2.trials.release_keys_trial import ReleaseKeysParams
from src2.trials.success_trial import resolve_success_screen_params
from src2.parts.calibration import CalibrationRunners, run_calibration_loop
from frontend.parts.context import PhaseContext
from frontend.parts.common import hand_suffix

from src2.utils.types import CalibrationPartType

class FinalCalibrationPhase:
    def __init__(self, context: PhaseContext):
        self.context = context

    def run(self) -> None:
        win = self.context.win
        keyboard_monitor = self.context.keyboard_monitor
        clock = self.context.clock
        state = self.context.state
        history = self.context.history
        translator = self.context.translator
        narration = self.context.narration
        ble = self.context.ble

        suffix = hand_suffix(state)
        header = f'<h2>{stimulus_text.wrap_up_header(translator)}</h2>'
        instructions_text = stimulus_text.final_calibration_part_2_directions(translator, state.get_key_settings())
        narration.play(resolve_audio_relative_path(f'final-calibration-instruction-{suffix}.mp3'))
        message.run_message(
            win, keyboard_monitor, instructions_text + CONTINUE_HINT, continue_key='space',
            image_path=resolve_image_path('calibration.png'),
            image_pos=(0.4, 0), image_size=0.8, text_pos=(-0.5, 0), align='left',
            header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
        )
        narration.stop()
        history.add({'task': 'final_calibration_instructions', 'trial_type': 'html-button-response'})

        def run_countdown() -> dict:
            return countdown.run_countdown(
                win, keyboard_monitor, clock,
                CountdownParams(keys_to_hold=get_hold_keys(state), key_to_press=get_tap_key(state)),
                translator
            )

        def run_tapping(auto_increase_amount: float, key_tapped_early_flag: bool) -> dict:
            params = TappingTaskParams(
                task=CalibrationPartType.FINAL_CALIBRATION_PART_2.value,
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state),
                bounds=(50, 50),
                auto_increase_amount=auto_increase_amount,
                key_tapped_early_flag=key_tapped_early_flag,
                show_thermometer=True,
            )
            return tapping.run_tapping(
                win, keyboard_monitor, clock, params,
                translator=translator,
                trigger_fn=self.context.ble_trigger,
            )

        def run_release() -> dict:
            return release_keys.run_release_keys(
                win, keyboard_monitor,
                ReleaseKeysParams(valid_responses=get_hold_keys(state)),
                translator
            )

        def run_success() -> dict:
            return success.run_success_screen(
                win,
                resolve_success_screen_params(history, show_freeze_frame=False),
                translator=translator,
                key_settings=state.get_key_settings()
            )

        def run_loading() -> None:
            loading_bar.run_loading_bar(
                win,
                acceptance=True,
                translator=translator
            )

        runners = CalibrationRunners(
            run_countdown,
            run_tapping,
            run_release,
            run_success,
            run_loading
        )
        run_calibration_loop(CalibrationPartType.FINAL_CALIBRATION_PART_2.value, state, history, runners)

        
        ble.stop_recording()  # Stop BLE recording at the end of the calibration phase
        ble.disconnect()  # Disconnect BLE device at the end of the calibration phase