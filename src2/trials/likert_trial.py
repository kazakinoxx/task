"""Likert survey trials -- port of
src/modules/experiment/trials/likert-trial.ts.

Question text lives in the i18n layer (milestone 9); this module owns
the question-set identifiers, randomization, and response-record shape,
which is where the actual (translation-independent) logic lives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from src2.utils.randomization import shuffle

LIKERT_SURVEY_1_QUESTION_KEYS = ['QUESTION_1', 'QUESTION_2']
LIKERT_SURVEY_2_QUESTION_KEYS = [
    'QUESTION_1', 'QUESTION_2', 'QUESTION_3', 'QUESTION_4', 'QUESTION_5', 'QUESTION_6',
]
LIKERT_SURVEY_3_QUESTION_KEYS = ['QUESTION_1', 'QUESTION_2', 'QUESTION_3', 'QUESTION_4', 'QUESTION_5']

SEVEN_POINT_SCALE = list(range(1, 8))  # Strongly Disagree(1) .. Strongly Agree(7)
TWO_LABEL_SEVEN_POINT_SCALE = list(range(1, 8))  # numeric 1-7, only endpoints labeled Low/High


@dataclass
class LikertSurveyParams:
    question_keys: List[str]
    randomize_question_order: bool = True


def build_question_order(params: LikertSurveyParams) -> List[str]:
    """Port of `randomize_question_order: true` (survey-likert plugin) /
    `likertQuestions2Randomized`'s sampleWithoutReplacement(6) full-shuffle."""
    if params.randomize_question_order:
        return shuffle(params.question_keys)
    return list(params.question_keys)


def build_likert_trial_record(question_keys: List[str], responses: Dict[str, int]) -> dict:
    """Port of the survey-likert plugin's recorded `response` dict --
    keyed by question name, matching jsPsych's own output shape."""
    return {'response': {key: responses[key] for key in question_keys}}
