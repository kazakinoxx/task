# practice_phase.py

# --- Imports from drawUtils (trial views) ---
from frontend.drawUtils.message import run_message
from frontend.drawUtils.hold_key import run_hold_key
from frontend.drawUtils.countdown import run_countdown
from frontend.drawUtils.tapping import run_tapping
from frontend.drawUtils.success import run_success_screen
from frontend.drawUtils.loading_bar import run_loading_bar

# --- Other imports ---
from src2.parts.practice import run_hold_key_practice_block, run_tapping_practice_block
from src2.trials.hold_key_practice_trial import HoldKeyPracticeParams
from src2.trials.countdown_trial import CountdownParams
from src2.trials.success_trial import resolve_success_screen_params
from src2.trials.tapping_task_trial import TappingTaskParams
from src2.utils.calculations import get_hold_keys, get_tap_key
from src2.utils.constants import CONTINUE_HINT, HOLD_KEY_MAX_FAILURES
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
import src2.i18n.stimulus_text as stimulus_text
from frontend.parts.context import PhaseContext

class PracticePhase:
    def __init__(self, context: PhaseContext):
        self.context = context
    

    def run(self) -> None:
        state = self.context.state
        translator = self.context.translator
        narration = self.context.narration
        win = self.context.win
        keyboard_monitor = self.context.keyboard_monitor
        clock = self.context.clock
        history = self.context.history
        ble = self.context.ble
        ble.start_recording()  # Start BLE recording at the beginning of the practice phase

        suffix = 'l' if state.get_preferred_hand() == 'left' else 'r'
        hold_key_str = get_hold_keys(state)[0]

        # -- hold-key instructions --
        header = stimulus_text.tutorial_header_1(translator)
        hold_key_text = stimulus_text.phase_5_instruction(translator, state.get_key_settings())
        narration.play(resolve_audio_relative_path(f'instruction-hold-key-{suffix}.mp3'))
        run_message(
            win, keyboard_monitor, hold_key_text,
            image_path=resolve_image_path(f'hand-{suffix}-1-{translator.language}.png'),
            image_pos=(0.4, 0), image_size=0.8, text_pos=(-0.5, 0), align='left',
            header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9
        )
        narration.stop()
        history.add({'task': 'hold_key_instructions', 'trial_type': 'html-button-response'})

        def run_hold_key_practice_attempt() -> dict:
            narration.play(resolve_audio_relative_path(f'hold-key-practice-{suffix}.mp3'))
            result = run_hold_key(
                win, keyboard_monitor, clock,
                HoldKeyPracticeParams(hold_key=hold_key_str),
                translator
            )
            narration.stop()
            return result

        hold_key_result = run_hold_key_practice_block(history, run_hold_key_practice_attempt)

        # -- hold-key block complete --
        if hold_key_result['failureCount'] >= HOLD_KEY_MAX_FAILURES:
            complete_text = stimulus_text.to_plain_text(stimulus_text.hold_s_practice_continue_message(translator))
            complete_audio = 'hold-key-practice-done.mp3'
        else:
            complete_text = stimulus_text.to_plain_text(stimulus_text.hold_s_practice_complete_message(translator))
            complete_audio = 'hold-key-practice-completed.mp3'
        narration.play(resolve_audio_relative_path(complete_audio))
        run_message(win, keyboard_monitor, complete_text, align='center')
        narration.stop()
        history.add({'task': 'hold_key_practice_complete', 'trial_type': 'html-button-response'})

        # -- tapping instructions --
        header = stimulus_text.tutorial_header_2(translator)
        tapping_text = stimulus_text.tapping_instructions_pages(translator, state.get_key_settings())[0]
        narration.play(resolve_audio_relative_path(f'instruction-tapping-{suffix}.mp3'))
        run_message(
            win, keyboard_monitor, tapping_text,
            image_path=resolve_image_path(f'hand-{suffix}-3-{translator.language}.png'),
            header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
            align='left', text_pos=(-0.5, 0), image_pos=(0.4, 0), image_size=0.8
        )
        narration.stop()
        history.add({'task': 'tapping_instructions', 'trial_type': 'html-button-response'})

        def run_countdown_trial() -> dict:
            narration.play(resolve_audio_relative_path(f'tapping-practice-{suffix}.mp3'))
            result = run_countdown(
                win, keyboard_monitor, clock,
                CountdownParams(keys_to_hold=get_hold_keys(state), key_to_press=get_tap_key(state)),
                translator,
                hold_text=stimulus_text.practice_trial_message(translator, state.get_key_settings()),
                countdown_label=stimulus_text.practice_countdown_message(translator, state.get_key_settings())
            )
            narration.stop()
            return result

        def run_practice_tapping() -> dict:
            narration.play(resolve_audio_relative_path(f'tapping-tapping-practice-{suffix}.mp3'))
            params = TappingTaskParams(
                task='practice',
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state),
                show_thermometer=False,
                continue_tapping_reminder_message=stimulus_text.continue_tapping_message(translator),
                continue_tapping_reminder_delay=700,
            )
            result = run_tapping(
                win, keyboard_monitor, clock, params,
                translator=translator,
                go_text=stimulus_text.tap_prompt_message(translator, state.get_key_settings()),
                release_warning_text=stimulus_text.key_released_early_first_error_message(translator, state.get_key_settings()),
                continue_tapping_reminder_text=stimulus_text.continue_tapping_message(translator),
                trigger_fn=self.context.ble_trigger,
            )
            narration.stop()
            return result

        def run_success_after_practice() -> dict:
            return run_success_screen(
                win,
                resolve_success_screen_params(history, show_freeze_frame=False),
                translator=translator,
                key_settings=state.get_key_settings()
            )

        def run_loading() -> None:
            run_loading_bar(win, acceptance=True, translator=translator)

        run_tapping_practice_block(
            history,
            run_countdown_trial,
            run_practice_tapping,
            run_success_after_practice,
            run_loading
        )

        # -- tapping-practice block complete --
        narration.play(resolve_audio_relative_path('hold-key-practice-completed.mp3'))
        run_message(
            win, keyboard_monitor,
            stimulus_text.to_plain_text(stimulus_text.hold_s_practice_complete_message(translator)) + CONTINUE_HINT,
            continue_key='space'
        )
        narration.stop()
        history.add({'task': 'tapping_practice_complete', 'trial_type': 'html-button-response'})

        