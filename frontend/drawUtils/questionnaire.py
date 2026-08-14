"""PsychoPy rendering for the likert survey trials -- thin, not unit
tested. Matches the original jsPsych survey-likert plugin's layout: all
questions in the set are shown at once, each with its own
psychopy.visual.Slider (style='rating', granularity=1) stacked
vertically on one screen, with a single Continue button at the bottom
that only proceeds once every question has been answered (port of the
plugin's `required: true` on every question). See
src2/trials/likert_trial.py for the pure logic this drives.
"""

from __future__ import annotations

from typing import Dict, Optional

from frontend.style_constants import (
    DEFAULT_FONT,
    DEFAULT_WRAP_WIDTH,
    LIKERT_CONTINUE_BUTTON_POS,
    LIKERT_LABEL_TEXT_HEIGHT,
    LIKERT_LABEL_WRAP_WIDTH,
    LIKERT_PREAMBLE_POS,
    LIKERT_QUESTION_PROMPT_OFFSET,
    LIKERT_QUESTION_TEXT_HEIGHT,
    LIKERT_QUESTIONS_BOTTOM_Y,
    LIKERT_QUESTIONS_TOP_Y,
    LIKERT_SLIDER_HEIGHT,
    LIKERT_SLIDER_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT_PREAMBLE,
)
from frontend.widgets import Button
from src2.trials.likert_trial import (
    SEVEN_POINT_SCALE,
    LikertSurveyParams,
    build_likert_trial_record,
    build_question_order,
)


def run_questionnaire(
    win, keyboard_monitor, question_texts: Dict[str, str], params: LikertSurveyParams,
    preamble: str = '', continue_label: Optional[str] = None, labels=None,
) -> dict:
    """`preamble` is drawn as a persistent header above the question
    list (port of the survey-likert plugin's `preamble` field). All
    questions in `params.question_keys` are laid out on one screen at
    once, each with its own slider; `continue_label` (defaults to
    'Continue') labels the button at the bottom, which only responds to
    clicks once every slider has a rating -- port of the plugin's
    `required: true` on every question, enforced before the page can be
    submitted.

    `labels` puts the response wording under each slider tick (port of the
    survey-likert questions' `labels` arrays): pass a single 7-item list to
    use the same labels on every question (e.g. Strongly Disagree ... Strongly
    Agree), or a {question_key: [labels]} dict for per-question labels (the
    final AMF survey's endpoint-only Low/High). None keeps the sliders
    unlabelled."""
    from psychopy import event, visual

    def labels_for(key: str):
        if isinstance(labels, dict):
            return labels.get(key)
        return labels

    question_order = build_question_order(params)

    preamble_stim = visual.TextStim(
        win, text=preamble, pos=LIKERT_PREAMBLE_POS, height=TEXT_HEIGHT_PREAMBLE, color=TEXT_COLOR,
        wrapWidth=DEFAULT_WRAP_WIDTH, font=DEFAULT_FONT,
    )

    count = len(question_order)
    if count > 1:
        step = (LIKERT_QUESTIONS_TOP_Y - LIKERT_QUESTIONS_BOTTOM_Y) / (count - 1)
        ys = [LIKERT_QUESTIONS_TOP_Y - i * step for i in range(count)]
    else:
        ys = [(LIKERT_QUESTIONS_TOP_Y + LIKERT_QUESTIONS_BOTTOM_Y) / 2]

    prompts = []
    sliders = []
    for key, y in zip(question_order, ys):
        prompts.append(visual.TextStim(
            win, text=question_texts.get(key, key), pos=(0, y + LIKERT_QUESTION_PROMPT_OFFSET),
            height=LIKERT_QUESTION_TEXT_HEIGHT, color=TEXT_COLOR, font=DEFAULT_FONT, wrapWidth=DEFAULT_WRAP_WIDTH, 
        ))
        sliders.append(visual.Slider(
            win, ticks=SEVEN_POINT_SCALE, labels=labels_for(key), granularity=1, style='rating',
            pos=(0, y), size=(LIKERT_SLIDER_WIDTH, LIKERT_SLIDER_HEIGHT), lineColor='black',
            labelColor=TEXT_COLOR, labelHeight=LIKERT_LABEL_TEXT_HEIGHT, labelWrapWidth=LIKERT_LABEL_WRAP_WIDTH,
        ))

    continue_button = Button(win, continue_label or 'Continue', pos=LIKERT_CONTINUE_BUTTON_POS)
    mouse = event.Mouse(win=win, visible=True)
    prev_pressed = bool(mouse.getPressed()[0])

    while True:
        keyboard_monitor.poll()

        all_answered = all(slider.getRating() is not None for slider in sliders)
        pressed_now = bool(mouse.getPressed()[0])
        if (
            all_answered and pressed_now and not prev_pressed
            and mouse.isPressedIn(continue_button.rect, buttons=[0])
        ):
            break
        prev_pressed = pressed_now

        if preamble:
            preamble_stim.draw()
        for prompt in prompts:
            prompt.draw()
        for slider in sliders:
            slider.draw()
        if all_answered:
            continue_button.update_hover(mouse)
        continue_button.draw()
        win.flip()

    responses = {key: int(slider.getRating()) for key, slider in zip(question_order, sliders)}
    return build_likert_trial_record(question_order, responses)
