import frontend.drawUtils.message as message
from src2.parts.introduction import IntroductionRunners, run_introduction
import src2.i18n.stimulus_text as stimulus_text
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
from src2.utils.constants import CONTINUE_HINT, LEFT_HAND_KEY, RIGHT_HAND_KEY
from frontend.parts.context import PhaseContext

class IntroductionPhase:
    def __init__(self, context: PhaseContext):
        self.context = context

    def run(self) -> None:
        win = self.context.win
        kb = self.context.keyboard_monitor
        state = self.context.state
        history = self.context.history
        translator = self.context.translator
        narration = self.context.narration
        ble = self.context.ble

        def show_begin() -> dict:
            text = stimulus_text.experiment_begin_message(translator)
            message.run_message(win, kb, text, button_label='Start', align='center')
            return {'task': 'experiment_begin'}

        def show_sit_comfortably() -> dict:
            text = f'<h2>{stimulus_text.introduction_header(translator)}</h2>\n\n{stimulus_text.sit_comfortably_message(translator)}'
            narration.play(resolve_audio_relative_path('sit-comfortably.mp3'))
            message.run_message(
                win, kb, text + CONTINUE_HINT,
                image_path=resolve_image_path('tip.png'),
                image_pos=(0, -0.2),
                image_size=0.8
            )
            narration.stop()
            return {'task': 'sit_comfortably'}

        def show_tutorial_intro() -> dict:
            text = f'<h2>{stimulus_text.experiment_setup_header(translator)}</h2>\n\n{stimulus_text.tutorial_introduction_message(translator)}'
            narration.play(resolve_audio_relative_path('tutorial-introduction.mp3'))
            message.run_message(win, kb, text + CONTINUE_HINT)
            narration.stop()
            return {'task': 'tutorial_introduction'}

        def ask_preferred_hand() -> dict:
            text = stimulus_text.dominant_hand_message(translator)
            narration.play(resolve_audio_relative_path('dominant-hand.mp3'))
            result = message.run_choice(
                win, kb, text, {LEFT_HAND_KEY: 0, RIGHT_HAND_KEY: 1},
                button_labels=[
                    stimulus_text.to_plain_text(stimulus_text.left_hand_button(translator)),
                    stimulus_text.to_plain_text(stimulus_text.right_hand_button(translator))
                ],
            )
            narration.stop()
            return result

        runners = IntroductionRunners(
            show_begin,
            show_sit_comfortably,
            show_tutorial_intro,
            ask_preferred_hand
        )
        run_introduction(state, history, runners)