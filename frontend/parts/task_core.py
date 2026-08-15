import frontend.drawUtils.message as message
import frontend.drawUtils.countdown as countdown
import frontend.drawUtils.tapping as tapping
import frontend.drawUtils.release_keys as release_keys
import frontend.drawUtils.loading_bar as loading_bar
import frontend.drawUtils.success as success
import frontend.drawUtils.questionnaire as questionnaire
import frontend.drawUtils.acceptance as acceptance       # if this module exists
       

import src2.i18n.stimulus_text as stimulus_text
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
from src2.utils.constants import CONTINUE_HINT, MAIN_TASK_BREAK_DURATION
from src2.utils.calculations import get_hold_keys, get_tap_key
from src2.trials.countdown_trial import CountdownParams
from src2.trials.tapping_task_trial import TappingTaskParams
from src2.trials.release_keys_trial import ReleaseKeysParams
from src2.trials.success_trial import resolve_success_screen_params, resolve_basic_success_screen_params
from src2.trials.likert_trial import LikertSurveyParams
from src2.trials.acceptance_trial import AcceptanceTrialParams
from src2.parts.task_core import (
    TaskTrialRunners,
    AcceptanceRunners,
    TaskBlockScreenRunners,
    resolve_trial_block_sequence,
    get_num_trials_per_block,
    run_task_trial_block,
)
from frontend.parts.context import PhaseContext
from frontend.parts.common import hand_suffix

from typing import Optional, List

class TaskCorePhase:
    def __init__(self, context: PhaseContext):
        self.context = context

    def run(self, remaining_trial_blocks: Optional[List[str]] = None) -> None:
        win = self.context.win
        keyboard_monitor = self.context.keyboard_monitor
        clock = self.context.clock
        state = self.context.state
        history = self.context.history
        translator = self.context.translator
        narration = self.context.narration
        ble = self.context.ble

        trial_block, start_index = resolve_trial_block_sequence(state, remaining_trial_blocks)
        suffix = hand_suffix(state)

        # -- one-time task instructions (3 pages) --
        pages = stimulus_text.core_tapping_instructions_pages(translator, state)
        page_images = [
            resolve_image_path(f'hand-{suffix}-3-{translator.language}.png'),
            resolve_image_path(f'two-offer-view-{translator.language}.png'),
            resolve_image_path(f'accept-refuse-{translator.language}.png'),
        ]
        header = f'<h2>{stimulus_text.core_tapping_header(translator)}</h2>\n{stimulus_text.instructions_sub_header(translator)}'
        narration.play(resolve_audio_relative_path(f'task-instructions-{suffix}.mp3'))
        for page_index, page_text in enumerate(pages):
            message.run_message(
                win, keyboard_monitor, page_text + CONTINUE_HINT,
                continue_key='space',
                image_path=page_images[page_index] if page_index < len(page_images) else None,
                image_pos=(0.4, 0), image_size=0.8, text_pos=(-0.5, 0), align='left',
                header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9
            )
        narration.stop()
        history.add({'task': 'task_core_instructions', 'trial_type': 'html-button-response'})

        def run_countdown() -> dict:
            return countdown.run_countdown(
                win, keyboard_monitor, clock,
                CountdownParams(keys_to_hold=get_hold_keys(state), key_to_press=get_tap_key(state)),
                translator
            )

        def run_tapping(auto_increase_amount, key_tapped_early_flag, delay, bounds, reward, random_chance_accepted, task_label) -> dict:
            params = TappingTaskParams(
                task=task_label,
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state),
                bounds=bounds,
                reward=reward,
                random_delay=delay,
                auto_increase_amount=auto_increase_amount,
                key_tapped_early_flag=key_tapped_early_flag,
                random_chance_accepted=random_chance_accepted,
                show_thermometer=True,
                flash_go_message=True,
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

        def run_freeze_frame_screen() -> dict:
            return success.run_success_screen(
                win,
                resolve_success_screen_params(history, show_freeze_frame=True, main_task=True),
                translator=translator,
                key_settings=state.get_key_settings()
            )

        def run_skip_screen() -> dict:
            return success.run_success_screen(
                win,
                resolve_basic_success_screen_params(history, skip=True),
                translator=translator,
                key_settings=state.get_key_settings()
            )

        def run_loading(acceptance: bool) -> None:
            loading_bar.run_loading_bar(
                win,
                acceptance=acceptance,
                translator=translator
            )

        def run_acceptance(bounds, original_bounds, reward, delay) -> dict:
            params = AcceptanceTrialParams(
                bounds=bounds,
                original_bounds=original_bounds,
                reward=reward,
                delay=delay
            )
            return acceptance.run_acceptance(   # adjust if module/function name differs
                win, keyboard_monitor, params,
                accept_key='right',
                reject_key='left',
                translator=translator,
                ble=self.context.ble,
            )

        task_runners = TaskTrialRunners(
            run_countdown,
            run_tapping,
            run_release,
            run_freeze_frame_screen,
            run_skip_screen,
            run_loading
        )
        acceptance_runners = AcceptanceRunners(run_acceptance, run_loading)

        def make_screen_runners() -> TaskBlockScreenRunners:
            def demo_intro() -> dict:
                num_bounds = len(state.get_task_settings().taskBoundsIncluded)
                num_demo = 2 if num_bounds > 2 else num_bounds
                num_trials = get_num_trials_per_block(state)
                text = stimulus_text.demo_trial_message(translator, num_demo, num_trials, state.get_key_settings())
                narration.play(resolve_audio_relative_path('task-demo-introduction.mp3'))
                message.run_message(win, keyboard_monitor, text + CONTINUE_HINT, continue_key='space')
                narration.stop()
                return {'task': 'demo_intro'}

            def likert_1() -> dict:
                preamble = stimulus_text.to_plain_text(stimulus_text.likert_preamble_demo(translator))
                questions = {k: stimulus_text.to_plain_text(v) for k, v in stimulus_text.likert_survey_1_questions(translator).items()}
                narration.play(resolve_audio_relative_path('likert-demo-preamble.mp3'))
                result = questionnaire.run_questionnaire(
                    win, keyboard_monitor, questions,
                    LikertSurveyParams(list(questions.keys()), randomize_question_order=True),
                    preamble=preamble,
                    continue_label=stimulus_text.continue_button_message(translator),
                    labels=list(stimulus_text.likert_responses(translator).values()),
                )
                narration.stop()
                return result

            def reminder() -> dict:
                header = f'<h2>{stimulus_text.remember_page_title(translator)}</h2>'
                text = stimulus_text.remember_page_directions(translator, state)
                narration.play(resolve_audio_relative_path('task-reminder.mp3'))
                message.run_message(
                    win, keyboard_monitor, text + CONTINUE_HINT, continue_key='space',
                    image_path=resolve_image_path(f'two-offer-view-{translator.language}.png'),
                    image_pos=(0.4, 0), image_size=0.8, text_pos=(-0.5, 0), align='left',
                    header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
                )
                narration.stop()
                return {'task': 'remember_direction'}

            def likert_intro_screen() -> dict:
                text = stimulus_text.to_plain_text(stimulus_text.likert_intro(translator))
                narration.play(resolve_audio_relative_path('likert-intro.mp3'))
                message.run_message(win, keyboard_monitor, text + CONTINUE_HINT, continue_key='space')
                narration.stop()
                return {'task': 'likert_intro'}

            def likert_2() -> dict:
                preamble = stimulus_text.to_plain_text(stimulus_text.likert_preamble_block(translator))
                questions = {k: stimulus_text.to_plain_text(v) for k, v in stimulus_text.likert_survey_2_questions(translator).items()}
                narration.play(resolve_audio_relative_path('likert-state-preamble.mp3'))
                result = questionnaire.run_questionnaire(
                    win, keyboard_monitor, questions,
                    LikertSurveyParams(list(questions.keys()), randomize_question_order=True),
                    preamble=preamble,
                    continue_label=stimulus_text.continue_button_message(translator),
                    labels=list(stimulus_text.likert_responses(translator).values()),
                )
                narration.stop()
                return result

            def likert_final() -> dict:
                preamble = stimulus_text.to_plain_text(stimulus_text.likert_preamble_final_questions(translator))
                questions = {k: stimulus_text.to_plain_text(v) for k, v in stimulus_text.likert_survey_3_questions(translator).items()}
                narration.play(resolve_audio_relative_path('likert-amf-preamble.mp3'))
                result = questionnaire.run_questionnaire(
                    win, keyboard_monitor, questions,
                    LikertSurveyParams(list(questions.keys()), randomize_question_order=False),
                    preamble=preamble,
                    continue_label=stimulus_text.continue_button_message(translator),
                    labels=stimulus_text.likert_final_question_labels(translator),
                )
                narration.stop()
                return {**result, 'additional': True, 'validation': True}

            def break_screen(allow_skip: bool) -> None:
                def message_fn(remaining: float) -> str:
                    text = stimulus_text.to_plain_text(stimulus_text.break_message(translator, f'{remaining:.0f}'))
                    if allow_skip:
                        text += f'\n\n{stimulus_text.to_plain_text(stimulus_text.skip_message(translator))}'
                    return text

                message.run_break(   # adjust if module/function name differs
                    win, keyboard_monitor, clock,
                    stimulus_text.to_plain_text(stimulus_text.break_time(translator)),
                    message_fn,
                    duration_ms=MAIN_TASK_BREAK_DURATION,
                    skip_key='space' if allow_skip else None,
                )

            return TaskBlockScreenRunners(
                demo_intro,
                likert_1,
                reminder,
                likert_intro_screen,
                likert_2,
                likert_final,
                break_screen
            )

        for i, delay in enumerate(trial_block):
            index = start_index + i
            run_task_trial_block(
                state,
                history,
                delay,
                index,
                task_runners,
                acceptance_runners,
                make_screen_runners()
            )