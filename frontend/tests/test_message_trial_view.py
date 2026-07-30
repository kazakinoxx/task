"""TextStyle / StimConfig live in the frontend view now (styling is a
frontend concern). to_kwargs() just builds a plain dict, so these are
pure and need no PsychoPy. Defaults are asserted against
frontend/style_constants.py so the two stay in sync. Also regression
coverage for the `style` UnboundLocalError that once made
run_message_trial crash on every call.
"""

from frontend.style_constants import (
    INSTRUCTION_FONT,
    MESSAGE_WRAP_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TITLE_TEXT_HEIGHT,
)
from frontend.trials.message_trial_view import CONFIG, StimConfig, TextStyle


def test_text_style_default_to_kwargs_shape():
    kwargs = TextStyle().to_kwargs()
    assert kwargs == {
        'font': INSTRUCTION_FONT, 'color': TEXT_COLOR, 'height': TEXT_HEIGHT,
        'wrapWidth': MESSAGE_WRAP_WIDTH, 'bold': False, 'italic': False,
    }


def test_text_style_overrides_are_reflected_in_kwargs():
    kwargs = TextStyle(color='red', bold=True, height=0.08).to_kwargs()
    assert kwargs['color'] == 'red'
    assert kwargs['bold'] is True
    assert kwargs['height'] == 0.08


def test_stim_config_title_defaults_larger_and_bold():
    assert StimConfig().title.height == TITLE_TEXT_HEIGHT
    assert StimConfig().title.height > StimConfig().text.height
    assert StimConfig().title.bold is True


def test_config_singleton_is_a_stim_config():
    assert isinstance(CONFIG, StimConfig)
