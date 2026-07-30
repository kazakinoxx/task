import pytest

from src2.i18n import stimulus_text as st
from src2.i18n.translator import Translator


def test_translator_returns_plain_string():
    t = Translator('en')
    assert t.t('CONTINUE_BUTTON_MESSAGE') == 'Continue'


def test_translator_switches_language():
    t = Translator('en')
    assert t.t('BREAK_TIME') == 'Break time'
    t.set_language('fr')
    assert t.t('BREAK_TIME') == 'Pause'


def test_translator_interpolates_variables():
    t = Translator('en')
    result = t.t('BREAK_MESSAGE', BREAK_DURATION='30')
    assert '30' in result
    assert '{{BREAK_DURATION}}' not in result


def test_translator_dotted_key_lookup_nested_object():
    t = Translator('en')
    assert t.t('LIKERT_RESPONSES.STRONGLY_DISAGREE') == 'Strongly Disagree'
    t2 = Translator('fr')
    assert t2.t('LIKERT_RESPONSES.STRONGLY_DISAGREE') == 'Tout à fait en désaccord'


def test_translator_return_objects_gives_list():
    t = Translator('en')
    pages = t.t('CORE_TAPPING_INSTRUCTIONS_PAGES', return_objects=True, NUMBER_OF_BLOCKS=4,
                NUMBER_OF_DEMO_TRIALS=3, POINT_VALUE=0.01, CURRENCY='EUR',
                ACCEPT_OFFER_BUTTON='arrowright', DECLINE_OFFER_BUTTON='arrowleft',
                HOLD_KEY='S', TAP_KEY='L', HOLD_FINGER='left index finger', TAP_FINGER='right index finger')
    assert isinstance(pages, list)
    assert len(pages) == 3


def test_translator_missing_var_leaves_placeholder_untouched():
    t = Translator('en')
    result = t.t('BREAK_MESSAGE')  # BREAK_DURATION not supplied
    assert '{{BREAK_DURATION}}' in result


def test_translator_interpolates_return_objects_string_value():
    # Regression test: INSTRUCTION_PAGES is a plain string in the locale
    # data (not an array), so return_objects=True hits the non-list
    # branch -- that branch must still interpolate {{VAR}} placeholders,
    # matching i18next's actual behavior (interpolation is independent
    # of returnObjects). Previously this branch returned the raw,
    # un-interpolated string, which -- combined with callers assuming a
    # List[str] and indexing [0] -- silently produced a single '<'
    # character (the string's first char) instead of the intended page.
    t = Translator('en')
    result = t.t('BREAK_MESSAGE', return_objects=True, BREAK_DURATION='45')
    assert isinstance(result, str)
    assert '45' in result
    assert '{{BREAK_DURATION}}' not in result


def make_key_settings(preferred='right'):
    return {'leftIndex': 's', 'rightIndex': 'l', 'preferredHand': preferred}


def test_to_name_special_keys():
    assert st.to_name(' ') == 'Spacebar'
    assert st.to_name('arrowleft') == 'Left Arrow'
    assert st.to_name('s') == 'S'


def test_key_instructions_swaps_hold_and_tap_by_hand():
    t = Translator('en')
    right_hand = st.key_instructions(t, make_key_settings('right'))
    left_hand = st.key_instructions(t, make_key_settings('left'))
    assert right_hand != left_hand
    assert len(right_hand) == 2
    assert len(left_hand) == 2


def test_warning_messages_instruction_contains_tap_key():
    t = Translator('en')
    result = st.warning_messages_instruction(t, make_key_settings('right'))
    assert 'S' in result  # leftIndex 's' -> tap key when preferred hand is right


def test_likert_responses_full_seven_point_scale():
    t = Translator('en')
    responses = st.likert_responses(t)
    assert set(responses.keys()) == {
        'STRONGLY_DISAGREE', 'SOMEWHAT_DISAGREE', 'DISAGREE', 'NEUTRAL',
        'AGREE', 'SOMEWHAT_AGREE', 'STRONGLY_AGREE',
    }
    assert responses['STRONGLY_AGREE'] == 'Strongly Agree'


def test_likert_survey_2_questions_has_six_questions():
    t = Translator('en')
    questions = st.likert_survey_2_questions(t)
    assert len(questions) == 6
    assert questions['QUESTION_1']


def test_progress_bar_labels():
    t = Translator('en')
    labels = st.progress_bar(t)
    assert labels['PROGRESS_BAR_TRIAL_BLOCKS'] == 'Tapping Offers Task'


def test_resolve_reason_message_maps_codes_to_text():
    t = Translator('en')
    key_settings = make_key_settings('right')
    assert 'too early' in st.resolve_reason_message(t, 'KEY_TAPPED_EARLY', key_settings)
    assert st.resolve_reason_message(t, 'SUCCESSFUL_FIRST_TRIAL', key_settings) == st.successful_first_trial_message(t)
    assert st.resolve_reason_message(t, None, key_settings) == ''


def test_french_translations_differ_from_english():
    en = Translator('en')
    fr = Translator('fr')
    assert st.continue_button_message(en) == 'Continue'
    assert st.continue_button_message(fr) == 'Continuer'


def test_tapping_instructions_pages_always_returns_a_list_with_interpolated_vars():
    # Regression test for the '<' bug: INSTRUCTION_PAGES is a single
    # string in the locale data, not an array, so this must normalize it
    # into a one-element list (matching JS's `Array.isArray(rawPages) ?
    # rawPages[0] : rawPages` guard, centralized here instead of pushed
    # onto every caller) with {{HOLD_KEY}}/{{TAP_KEY}} interpolated.
    t = Translator('en')
    pages = st.tapping_instructions_pages(t, make_key_settings('right'))
    assert isinstance(pages, list)
    assert len(pages) == 1
    assert '{{' not in pages[0]
    assert 'S' in pages[0] or 'L' in pages[0]  # HOLD_KEY/TAP_KEY got substituted in
