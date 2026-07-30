# validation_phase.py

import frontend.drawUtils.message as message
import frontend.drawUtils.countdown as countdown
import frontend.drawUtils.tapping as tapping
import frontend.drawUtils.release_keys as release_keys
import frontend.drawUtils.loading_bar as loading_bar
import frontend.drawUtils.success as success
import frontend.drawUtils.questionnaire as questionnaire  # if this module exists

from src2.parts.introduction import IntroductionRunners, run_introduction  # probably not needed, but keep if used
import src2.i18n.stimulus_text as stimulus_text
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
from src2.utils.constants import CONTINUE_HINT, LEFT_HAND_KEY, RIGHT_HAND_KEY
from frontend.parts.context import PhaseContext
from frontend.parts.common import hand_suffix

from src2.utils.types import ValidationPartType
from src2.utils.calculations import get_hold_keys, get_tap_key
from src2.trials.countdown_trial import CountdownParams
from src2.trials.tapping_task_trial import TappingTaskParams
from src2.trials.release_keys_trial import ReleaseKeysParams
from src2.trials.success_trial import resolve_success_screen_params_validation
from src2.trials.likert_trial import LikertSurveyParams
from src2.parts.validation import (
    ValidationRunners,
    run_validation_trial_loop,
    should_run_extra_validation,
    should_finish_early_after_extra_validation,
    ValidationFailedError,
    resolve_validation_result,
)

from typing import Tuple

class ValidationPhase:
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

        suffix = hand_suffix(state)
        header = f'<h2>{stimulus_text.validation_practice_header(translator)}</h2>'
        tutorial_text = stimulus_text.validation_video_tutorial_message(translator, state)
        
        narration.play(resolve_audio_relative_path(f'validation-instruction-{suffix}.mp3'))
        message.run_message(
            win, keyboard_monitor, tutorial_text + CONTINUE_HINT, continue_key='space',
            image_path=resolve_image_path(f'target-area-{translator.language}.png'),
            header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
            align='left', text_pos=(-0.5, 0), image_pos=(0.4, 0), image_size=0.8
        )
        narration.stop()
        history.add({'task': 'validation_video_tutorial', 'trial_type': 'html-button-response'})

        def run_countdown() -> dict:
            return countdown.run_countdown(
                win, keyboard_monitor, clock,
                CountdownParams(keys_to_hold=get_hold_keys(state), key_to_press=get_tap_key(state)),
                translator
            )

        def run_tapping(auto_increase_amount: float, key_tapped_early_flag: bool, bounds: Tuple[float, float]) -> dict:
            params = TappingTaskParams(
                keys_to_hold=get_hold_keys(state),
                key_to_press=get_tap_key(state),
                bounds=bounds,
                auto_increase_amount=auto_increase_amount,
                key_tapped_early_flag=key_tapped_early_flag,
                target_area=True,
                show_thermometer=True,
                flash_go_message=True,
            )
            return tapping.run_tapping(
                win, keyboard_monitor, clock, params,
                translator=translator
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
                resolve_success_screen_params_validation(history, show_freeze_frame=False),
                translator=translator,
                key_settings=state.get_key_settings()
            )

        def run_loading() -> None:
            loading_bar.run_loading_bar(
                win,
                acceptance=True,
                translator=translator
            )

        for level in (ValidationPartType.VALIDATION_EASY, ValidationPartType.VALIDATION_MEDIUM, ValidationPartType.VALIDATION_HARD):
            runners = ValidationRunners(run_countdown, run_tapping, run_release, run_success, run_loading)
            run_validation_trial_loop(level.value, state, history, runners)

        if should_run_extra_validation(state):
            runners = ValidationRunners(run_countdown, run_tapping, run_release, run_success, run_loading)
            run_validation_trial_loop(ValidationPartType.VALIDATION_EXTRA.value, state, history, runners)
            if should_finish_early_after_extra_validation(state):
                raise ValidationFailedError()

        # -- AMF likert after validation --
        likert_preamble = stimulus_text.to_plain_text(stimulus_text.likert_preamble_final_questions(translator))
        likert_questions = {k: stimulus_text.to_plain_text(v) for k, v in stimulus_text.likert_survey_3_questions(translator).items()}
        narration.play(resolve_audio_relative_path('likert-amf-preamble.mp3'))
        likert_result = questionnaire.run_questionnaire(
            win, keyboard_monitor, likert_questions,
            LikertSurveyParams(list(likert_questions.keys()), randomize_question_order=False),
            preamble=likert_preamble,
            continue_label=stimulus_text.continue_button_message(translator),
        )
        narration.stop()
        history.add({**likert_result, 'trial_type': 'survey-likert', 'additional': True, 'validation': True})

        # -- result screen --
        result = resolve_validation_result(state)
        result_text = stimulus_text.to_plain_text(
            stimulus_text.passed_validation_message(translator) if result['passed']
            else stimulus_text.failed_validation_message(translator)
        )
        result_audio = 'validation-completed.mp3' if result['passed'] else 'validation-failed.mp3'
        narration.play(resolve_audio_relative_path(result_audio))
        message.run_message(win, keyboard_monitor, result_text + CONTINUE_HINT, continue_key='space')
        narration.stop()
        history.add({'task': 'validation_result', 'trial_type': 'html-button-response', **result})

        if result['should_finish_early']:
            raise ValidationFailedError()