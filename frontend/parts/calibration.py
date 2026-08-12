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

class CalibrationPhase:
    def __init__(self, context: PhaseContext):
        self.context = context

    def run(self) -> None:
        from src2.utils.types import CalibrationPartType

        win = self.context.win
        keyboard_monitor = self.context.keyboard_monitor
        clock = self.context.clock
        state = self.context.state
        history = self.context.history
        translator = self.context.translator
        narration = self.context.narration
        ble = self.context.ble

        suffix = hand_suffix(state)
        header = f'<h2>{stimulus_text.calibration_header(translator)}</h2>'
        instructions_text = stimulus_text.calibration_part_2_directions(translator, state.get_key_settings())

        narration.play(resolve_audio_relative_path(f'calibration-instruction-{suffix}.mp3'))
        message.run_message(   # <-- prefix with 'message.'
            win, keyboard_monitor, instructions_text + CONTINUE_HINT,
            image_path=resolve_image_path('calibration.png'),
            header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
            align='left', text_pos=(-0.5, 0), image_pos=(0.4, 0), image_size=0.8
        )
        narration.stop()
        history.add({'task': 'calibration_instructions', 'trial_type': 'html-button-response'})

        def run_countdown() -> dict:
            return countdown.run_countdown(  # <-- prefix with 'countdown.'
                win, keyboard_monitor, clock,
                CountdownParams(keys_to_hold=get_hold_keys(state), key_to_press=get_tap_key(state)),
                translator
            )

        def run_tapping(auto_increase_amount: float, key_tapped_early_flag: bool) -> dict:
            params = TappingTaskParams(
                task=CalibrationPartType.CALIBRATION_PART_2.value,
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state),
                bounds=(50, 50),
                auto_increase_amount=auto_increase_amount,
                key_tapped_early_flag=key_tapped_early_flag,
                show_thermometer=True,
                flash_go_message=True,
            )
            return tapping.run_tapping(  # <-- prefix with 'tapping.'
                win, keyboard_monitor, clock, params,
                translator=translator
            )

        def run_release() -> dict:
            return release_keys.run_release_keys(  # <-- prefix with 'release_keys.'
                win, keyboard_monitor,
                ReleaseKeysParams(valid_responses=get_hold_keys(state)),
                translator
            )

        def run_success() -> dict:
            return success.run_success_screen(  # <-- prefix with 'success.'
                win,
                resolve_success_screen_params(history, show_freeze_frame=False),
                translator=translator,
                key_settings=state.get_key_settings()
            )

        def run_loading() -> None:
            loading_bar.run_loading_bar(  # <-- prefix with 'loading_bar.'
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
        run_calibration_loop(CalibrationPartType.CALIBRATION_PART_2.value, state, history, runners)
