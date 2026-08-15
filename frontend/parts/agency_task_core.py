# agency_task_core_phase.py

import frontend.drawUtils.message as message
import frontend.drawUtils.countdown as countdown
import frontend.drawUtils.release_keys as release_keys
import frontend.drawUtils.loading_bar as loading_bar
import frontend.drawUtils.agency_tapping as agency_tapping

import src2.i18n.stimulus_text as stimulus_text
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
from src2.utils.constants import CONTINUE_HINT
from src2.utils.calculations import get_hold_keys, get_tap_key
from src2.trials.countdown_trial import CountdownParams
from src2.trials.release_keys_trial import ReleaseKeysParams
from src2.trials.agency_tapping_task_trial import AgencyTappingTaskParams
from src2.parts.agency_task_core import (
    AgencyPracticeRunners,
    AgencyCoreRunners,
    AgencyBreakRunners,
    run_agency_practice_trials,
    run_agency_core_block,
)
from frontend.parts.context import PhaseContext
from frontend.parts.common import hand_suffix

class AgencyTaskCorePhase:
    def __init__(self, context: PhaseContext):
        self.context = context

    def run(self) -> None:
        win = self.context.win
        keyboard_monitor = self.context.keyboard_monitor
        clock = self.context.clock
        state = self.context.state
        history = self.context.history
        translator = self.context.translator
        narration = self.context.narration   # not used in original, but kept

        suffix = hand_suffix(state)

        # -- agency intro (before practice); JS has no narration here --
        intro_header = f'<h2>{stimulus_text.agency_tapping_header(translator)}</h2>'
        intro_text = stimulus_text.agency_task_intro_page(translator, state.get_key_settings())
        message.run_message(
            win, keyboard_monitor, intro_text + CONTINUE_HINT, continue_key='space',
            image_path=resolve_image_path(f'agency-task-{translator.language}.png'),
            image_pos=(0.4, 0), image_size=0.8, text_pos=(-0.5, 0), align='left',
            header=intro_header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
        )
        history.add({'task': 'agency_task_intro', 'trial_type': 'html-button-response'})

        def run_countdown() -> dict:
            return countdown.run_countdown(
                win, keyboard_monitor, clock,
                CountdownParams(keys_to_hold=get_hold_keys(state), key_to_press=get_tap_key(state)),
                translator
            )

        def run_release() -> dict:
            return release_keys.run_release_keys(
                win, keyboard_monitor,
                ReleaseKeysParams(valid_responses=get_hold_keys(state)),
                translator
            )

        def run_loading() -> None:
            loading_bar.run_loading_bar(
                win,
                acceptance=True,
                translator=translator
            )

        def run_practice_tapping() -> dict:
            params = AgencyTappingTaskParams(
                task='practice',
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state)
            )
            return agency_tapping.run_agency_tapping(
                win, keyboard_monitor, clock, params, translator, ble=self.context.ble
            )

        practice_runners = AgencyPracticeRunners(
            run_countdown,
            run_practice_tapping,
            run_release,
            run_loading
        )
        run_agency_practice_trials(state, history, practice_runners)

        # -- core-block instructions (after practice, before the main loop) --
        core_instructions_text = (
            f'<h2>{stimulus_text.agency_tapping_header(translator)}</h2>\n\n'
            f'{stimulus_text.agency_tapping_core_block_instructions_message(translator, state.get_agency_task_settings().breakFrequency)}'
        )
        message.run_message(win, keyboard_monitor, core_instructions_text + CONTINUE_HINT, continue_key='space')
        history.add({'task': 'agency_core_block_instructions', 'trial_type': 'html-button-response'})

        def run_core_tapping(selected_delay: float) -> dict:
            params = AgencyTappingTaskParams(
                task='core',
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state),
                delay_original=selected_delay,
            )
            return agency_tapping.run_agency_tapping(
                win, keyboard_monitor, clock, params, translator, ble=self.context.ble
            )

        core_runners = AgencyCoreRunners(
            run_countdown,
            run_core_tapping,
            run_release,
            run_loading
        )

        def run_break(break_number: int, allow_skip: bool) -> None:
            from psychopy import core as psychopy_core
            psychopy_core.wait(state.get_agency_task_settings().breakDuration / 1000.0)

        break_runners = AgencyBreakRunners(run_break)
        run_agency_core_block(state, history, core_runners, break_runners)