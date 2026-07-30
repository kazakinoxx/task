from src2.trials.likert_trial import (
    LIKERT_SURVEY_1_QUESTION_KEYS,
    LIKERT_SURVEY_2_QUESTION_KEYS,
    LikertSurveyParams,
    build_likert_trial_record,
    build_question_order,
)


def test_build_question_order_randomizes_by_default():
    params = LikertSurveyParams(question_keys=LIKERT_SURVEY_2_QUESTION_KEYS)
    order = build_question_order(params)
    assert sorted(order) == sorted(LIKERT_SURVEY_2_QUESTION_KEYS)


def test_build_question_order_preserves_order_when_disabled():
    params = LikertSurveyParams(question_keys=LIKERT_SURVEY_1_QUESTION_KEYS, randomize_question_order=False)
    order = build_question_order(params)
    assert order == LIKERT_SURVEY_1_QUESTION_KEYS


def test_build_likert_trial_record_keys_by_question_name():
    responses = {'QUESTION_1': 5, 'QUESTION_2': 3}
    record = build_likert_trial_record(['QUESTION_2', 'QUESTION_1'], responses)
    assert record == {'response': {'QUESTION_2': 3, 'QUESTION_1': 5}}
