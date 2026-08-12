"""Stimulus text builders -- port of the i18n.t()-calling helper
functions in src/modules/experiment/utils/constants.ts (everything in
that file except the plain numeric/logic constants, which were already
ported to utils/constants.py in milestone 1).

Each function mirrors its TS counterpart's name, parameters, and
interpolation variables 1:1, just calling `translator.t(...)` instead of
the module-level `i18n.t(...)`. Functions are grouped under the same
section comments used in the original file for easy cross-reference.
"""

from __future__ import annotations

import html
import re
from typing import Dict, List

from src2.i18n.translator import Translator
from src2.utils.types import ExtendedKeySettings, InstructionIDs

_BLOCK_BREAK_PATTERN = re.compile(r'<\s*(br|/p|/li|/h[1-6])\s*/?\s*>', re.IGNORECASE)
_TAG_PATTERN = re.compile(r'<[^>]+>')
_BLANK_LINES_PATTERN = re.compile(r'\n{3,}')
_INLINE_WHITESPACE_PATTERN = re.compile(r'[ \t]+')


def to_plain_text(markup: str) -> str:
    """Strips the locale JSON's inline HTML (<span>, <b>, <br>, <svg>, ...)
    down to plain text -- those strings are an unmodified copy of the
    original web app's resources (see translator.py), which assumed an
    HTML-rendering DOM. PsychoPy's TextStim only renders plain text."""
    text = _BLOCK_BREAK_PATTERN.sub('\n', markup)
    text = _TAG_PATTERN.sub('', text)
    text = html.unescape(text)
    text = _INLINE_WHITESPACE_PATTERN.sub(' ', text)
    text = _BLANK_LINES_PATTERN.sub('\n\n', text)
    return text.strip()


def to_name(key: str) -> str:
    """Port of toName."""
    lowered = key.lower()
    names = {
        ' ': 'Spacebar',
        'arrowright': 'Right Arrow',
        'arrowleft': 'Left Arrow',
        'arrowup': 'Up Arrow',
        'arrowdown': 'Down Arrow',
    }
    return names.get(lowered, key.upper())


CUSTOM_KEY_ORDER = ['leftPink', 'leftRing', 'leftMiddle', 'leftThumb', 'rightIndex', 'leftIndex']


def left_index(t: Translator) -> str:
    return t.t('LEFT_INDEX')


def right_index(t: Translator) -> str:
    return t.t('RIGHT_INDEX')


def tap_on_go_instruction(t: Translator, key_settings: ExtendedKeySettings) -> str:
    return t.t('TAP_ON_GO_INSTRUCTION', KEY_TO_PRESS=key_settings['leftIndex'])


def key_instructions(t: Translator, key_settings: ExtendedKeySettings) -> List[str]:
    preferred = key_settings['preferredHand']
    return [
        t.t(
            'HOLD_KEY_INSTRUCTION',
            KEY_REPLACE=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
            HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
        ),
        t.t(
            'TAP_ON_GO_INSTRUCTION',
            KEY_TO_PRESS=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
            TAP_FINGER=left_index(t) if preferred == 'left' else right_index(t),
        ),
    ]


def lost_connection_warning_message(t: Translator) -> str:
    return t.t('LOST_CONNECTION_WARNING')


def try_again_button(t: Translator) -> str:
    return t.t('TRY_AGAIN')


def trying_again_label(t: Translator) -> str:
    return t.t('TRYING_AGAIN_LABEL')


def warning_messages_instruction(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'WARNING_MESSAGES_INSTRUCTION',
        TAP_KEY_REPLACE=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
        HOLD_KEYS_REPLACE=f"<b>{to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex'])}</b>",
        TAP_FINGER=left_index(t) if preferred == 'left' else right_index(t),
    )


def key_instructions_list(t: Translator, key_settings: ExtendedKeySettings) -> str:
    items = ''.join(f'<li>{instr}</li>' for instr in key_instructions(t, key_settings))
    return f'<ul>{items}</ul>'


def tapping_task_instructions(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'TAPPING_TASK_INSTRUCTIONS',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
        HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
        TAP_FINGER=left_index(t) if preferred == 'left' else right_index(t),
    )


# --------------------------------
# Introduction part
# --------------------------------


def experiment_setup_header(t: Translator) -> str:
    return t.t('EXPERIMENT_SETUP_HEADER')


def sit_comfortably_message(t: Translator) -> str:
    return t.t('SIT_COMFORTABLY_MESSAGE')


def introduction_header(t: Translator) -> str:
    return t.t('INTRODUCTION_HEADER')


def click_button_to_proceed_message(t: Translator) -> str:
    return t.t('CLICK_BUTTON_TO_PROCEED_MESSAGE')


def continue_message_title(t: Translator) -> str:
    return t.t('CONTINUE_MESSAGE_TITLE')


def continue_button_message(t: Translator) -> str:
    return t.t('CONTINUE_BUTTON_MESSAGE')


def start_button_message(t: Translator) -> str:
    return t.t('START_BUTTON_MESSAGE')


def finish_button_message(t: Translator) -> str:
    return t.t('FINISH_BUTTON_MESSAGE')


def dominant_hand_message(t: Translator) -> str:
    return t.t('DOMINANT_HAND_MESSAGE')


def left_hand_button(t: Translator) -> str:
    return t.t('LEFT_HAND_BUTTON')


def right_hand_button(t: Translator) -> str:
    return t.t('RIGHT_HAND_BUTTON')


# --------------------------------
# Practice part
# --------------------------------


def tutorial_header_1(t: Translator) -> str:
    return t.t('TUTORIAL_HEADER_1')


def tutorial_header_2(t: Translator) -> str:
    return t.t('TUTORIAL_HEADER_2')


def fixation_message(t: Translator) -> str:
    return t.t('FIXATION_MESSAGE')


def tutorial_introduction_message(t: Translator) -> str:
    return t.t('TUTORIAL_INTRODUCTION_MESSAGE')


def continue_tapping_message(t: Translator) -> str:
    return t.t('CONTINUE_TAPPING_MESSAGE')


def tap_prompt_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = (key_settings.get('preferredHand') or '').lower()
    return t.t(
        'TAP_PROMPT_MESSAGE',
        TAP_KEY=to_name(key_settings['rightIndex'] if preferred == 'right' else key_settings['leftIndex']),
    )


def phase_5_instruction(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'PHASE_5_INSTRUCTION',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
    )


def hold_s_prompt_message(t: Translator, hold_key: str) -> str:
    return t.t('HOLD_S_PROMPT_MESSAGE', HOLD_KEY=to_name(hold_key))


def hold_s_release_prompt(t: Translator, hold_key: str) -> str:
    return t.t('HOLD_S_RELEASE_PROMPT', HOLD_KEY=to_name(hold_key))


def hold_s_success_message(t: Translator) -> str:
    return t.t('HOLD_S_SUCCESS_MESSAGE')


def hold_s_retry_message(t: Translator, hold_key: str) -> str:
    return t.t('HOLD_S_RETRY_MESSAGE', HOLD_KEY=to_name(hold_key))


def hold_s_practice_complete_message(t: Translator) -> str:
    return t.t('HOLD_S_PRACTICE_COMPLETE_MESSAGE')


def hold_s_practice_continue_message(t: Translator) -> str:
    return t.t('HOLD_S_PRACTICE_CONTINUE_MESSAGE')


def tapping_instructions_pages(t: Translator, key_settings: ExtendedKeySettings) -> List[str]:
    """INSTRUCTION_PAGES is actually a single string in the locale data,
    not a true array (confirmed: locale JSON has one string under this
    key), unlike this function's `-> List[str]` return type suggests.
    JS's tappingInstructionPagesStimulus (stimulus.ts) has to defensively
    check `Array.isArray(rawPages) ? rawPages[0] : rawPages` at every
    call site for exactly this reason; normalizing here once means every
    Python caller can rely on the promised List[str] shape instead of
    needing the same defensive check (a caller that instead assumed the
    list shape and indexed [0] directly would silently get the string's
    first *character* instead of its first *page*)."""
    preferred = key_settings['preferredHand']
    result = t.t(
        'INSTRUCTION_PAGES',
        return_objects=True,
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
        TAP_FINGER=left_index(t) if preferred == 'left' else right_index(t),
        HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
    )
    return result if isinstance(result, list) else [result]


def practice_trial_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'PRACTICE_TRIAL_MESSAGE',
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
        TAPPING_TASK_INSTRUCTIONS=tapping_task_instructions(t, key_settings),
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
    )


def practice_countdown_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'PRACTICE_COUNTDOWN_MESSAGE',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
    )


def successful_hold_key_message(t: Translator, key_to_hold: str) -> str:
    return t.t('SUCCESSFUL_HOLD_KEY_MESSAGE', HOLD_KEY=to_name(key_to_hold))


def start_first_tap_instruction(t: Translator, key_to_tap: str) -> str:
    return t.t('START_FIRST_TAP_INSTRUCTION', TAP_KEY=to_name(key_to_tap))


def successful_first_tap_message(t: Translator, key_to_tap: str) -> str:
    return t.t('SUCCESSFUL_FIRST_TAP_MESSAGE', TAP_KEY=to_name(key_to_tap))


def successful_first_trial_message(t: Translator) -> str:
    return t.t('SUCCESSFUL_FIRST_TRIAL_MESSAGE')


def practice_ending_title(t: Translator) -> str:
    return t.t('PRACTICE_ENDING_TITLE')


def practice_ending_message_retry(t: Translator) -> str:
    return t.t('PRACTICE_ENDING_MESSAGE_RETRY')


def practice_ending_message_no_retry(t: Translator) -> str:
    return t.t('PRACTICE_ENDING_MESSAGE_NO_RETRY')


def repeat_practice_button(t: Translator) -> str:
    return t.t('REPEAT_PRACTICE_BUTTON')


# --------------------------------
# Calibration part
# --------------------------------


def calibration_header(t: Translator) -> str:
    return t.t('CALIBRATION_HEADER')


def calibration_part(t: Translator) -> str:
    return t.t('CALIBRATION_PART')


def validation_practice_header(t: Translator) -> str:
    return t.t('VALIDATION_PRACTICE_HEADER')


def calibration_introduction_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'CALIBRATION_INTRODUCTION_MESSAGE',
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def calibration_part_1_directions(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'CALIBRATION_PART_1_DIRECTIONS',
        KEY_INSTRUCTIONS_TEXT=key_instructions_list(t, key_settings),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def calibration_part_1_ending_message(t: Translator) -> str:
    return t.t('CALIBRATION_PART_1_ENDING_MESSAGE')


def calibration_part_2_directions(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'CALIBRATION_PART_2_DIRECTIONS',
        KEY_INSTRUCTIONS_TEXT=key_instructions_list(t, key_settings),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
    )


def wrap_up_header(t: Translator) -> str:
    return t.t('WRAP_UP_HEADER')


def final_calibration_part_1_directions(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'FINAL_CALIBRATION_PART_1_DIRECTIONS',
        KEY_INSTRUCTIONS_TEXT=key_instructions_list(t, key_settings),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def final_calibration_part_2_directions(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'FINAL_CALIBRATION_PART_2_DIRECTIONS',
        KEY_INSTRUCTIONS_TEXT=key_instructions_list(t, key_settings),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def calibration_part_2_ending_message(t: Translator) -> str:
    return t.t('CALIBRATION_PART_2_ENDING_MESSAGE')


def calibration_finished_directions(t: Translator) -> str:
    return t.t('CALIBRATION_FINISHED_DIRECTIONS')


def final_calibration_section_directions_part_1(t: Translator, key_settings: ExtendedKeySettings) -> str:
    return t.t(
        'FINAL_CALIBRATION_SECTION_DIRECTIONS_PART_1',
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
    )


def final_calibration_section_directions_part_2(t: Translator) -> str:
    return t.t('FINAL_CALIBRATION_SECTION_DIRECTIONS_PART_2')


# --------------------------------
# Agency tapping task part
# --------------------------------


def agency_tapping_header(t: Translator) -> str:
    return t.t('AGENCY_TAPPING_HEADER')


def task_paused(t: Translator) -> str:
    return t.t('TASK_PAUSED')


def question(t: Translator) -> str:
    return t.t('QUESTION')


def interruption_release_keys_message(t: Translator) -> str:
    return t.t('INTERRUPTION_RELEASE_KEYS_MESSAGE')


def hold_keys_message_agency(t: Translator, hold_keys_str: str) -> str:
    return t.t('HOLD_KEYS_MESSAGE_AGENCY', HOLD_KEYS_REPLACE=hold_keys_str)


def agency_task_intro_page(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'AGENCY_TASK_INTRO_PAGE',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
    )


def agency_tapping_instructions_pages(t: Translator, key_settings: ExtendedKeySettings) -> List[str]:
    return t.t(
        'AGENCY_TAPPING_INSTRUCTION_PAGES',
        return_objects=True,
        YES_KEY='Y',
        NO_KEY='N',
        KEY_INSTRUCTIONS_TEXT=key_instructions_list(t, key_settings),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
    )


def bar_message(t: Translator) -> str:
    return t.t('BAR_MESSAGE')


def target_area_message(t: Translator) -> str:
    return t.t('TARGET_AREA_MESSAGE')


def start_first_agency_tap_instructions(t: Translator, key_to_tap: str) -> str:
    return t.t('START_FIRST_AGENCY_TAP_INSTRUCTIONS', TAP_KEY=key_to_tap)


def keep_in_target_agency_freeze_frame_instructions(t: Translator) -> str:
    return t.t('KEEP_IN_TARGET_AGENCY_FREEZE_FRAME_INSTRUCTIONS')


def get_back_in_target_message(t: Translator) -> str:
    return t.t('GET_BACK_IN_TARGET_MESSAGE')


def stay_in_target_message(t: Translator) -> str:
    return t.t('STAY_IN_TARGET_MESSAGE')


def agency_task_control_question(t: Translator) -> str:
    return t.t('AGENCY_TASK_CONTROL_QUESTION')


def answer_options_instruction(t: Translator) -> str:
    return t.t('ANSWER_OPTIONS_INSTRUCTION')


def agency_tapping_core_block_instructions_message(t: Translator, break_frequency: int) -> str:
    return t.t('AGENCY_TAPPING_CORE_BLOCK_INSTRUCTIONS_MESSAGE', BREAK_FREQUENCY=break_frequency)


def break_time(t: Translator) -> str:
    return t.t('BREAK_TIME')


def break_message(t: Translator, break_duration: str) -> str:
    return t.t('BREAK_MESSAGE', BREAK_DURATION=break_duration)


def skip_message(t: Translator) -> str:
    return t.t('SKIP_MESSAGE')


def skip_button(t: Translator) -> str:
    return t.t('SKIP_BUTTON')


def agency_task_completion_title(t: Translator) -> str:
    return t.t('AGENCY_TASK_COMPLETION_TITLE')


def agency_task_completion_message(t: Translator) -> str:
    return t.t('AGENCY_TASK_COMPLETION_MESSAGE')


def task_completion_break_message(t: Translator, break_duration: str) -> str:
    return t.t('TASK_COMPLETION_BREAK_MESSAGE', BREAK_DURATION=break_duration)


# --------------------------------
# Validation part
# --------------------------------


def passed_validation_message(t: Translator) -> str:
    return t.t('PASSED_VALIDATION_MESSAGE')


def failed_validation_message(t: Translator) -> str:
    return t.t('FAILED_VALIDATION_MESSAGE')


def additional_calibration_part_1_directions(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'ADDITIONAL_CALIBRATION_PART_1_DIRECTIONS',
        KEY_INSTRUCTIONS_TEXT=key_instructions_list(t, key_settings),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def trial_not_successful_message(t: Translator) -> str:
    return t.t('TRIAL_NOT_SUCCESSFUL_MESSAGE')


# --------------------------------
# Countdown and tapping trial
# --------------------------------


def key_tapped_early_first_error_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'KEY_TAPPED_EARLY_FIRST_ERROR_MESSAGE',
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def key_released_early_first_error_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'KEY_RELEASED_EARLY_FIRST_ERROR_MESSAGE',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
    )


def not_enough_taps_first_error_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'NOT_ENOUGH_TAPS_FIRST_ERROR_MESSAGE',
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def hold_keys_message(t: Translator, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    replace = (
        f"<b>{to_name(key_settings['rightIndex'])}</b>"
        if preferred == 'left'
        else f"<b>{to_name(key_settings['leftIndex'])}</b>"
    )
    return t.t('HOLD_KEYS_MESSAGE', HOLD_KEYS_REPLACE=replace)


# --------------------------------
# Core experiment
# --------------------------------


def core_tapping_header(t: Translator) -> str:
    return t.t('CORE_TAPPING_HEADER')


def instructions_sub_header(t: Translator) -> str:
    return t.t('INSTRUCTIONS_SUB_HEADER')


def core_tapping_instructions_pages(t: Translator, state) -> List[str]:
    from src2.utils.constants import ACCEPT_OFFER_BUTTON, CURRENCY, DECLINE_OFFER_BUTTON, NUMBER_OF_DEMO_TRIALS, POINT_VALUE

    key_settings = state.get_key_settings()
    preferred = key_settings['preferredHand']
    task_settings = state.get_task_settings()
    return t.t(
        'CORE_TAPPING_INSTRUCTIONS_PAGES',
        return_objects=True,
        NUMBER_OF_BLOCKS=task_settings.taskBlockRepetitions * len(task_settings.taskBlocksIncluded),
        NUMBER_OF_DEMO_TRIALS=NUMBER_OF_DEMO_TRIALS,
        POINT_VALUE=POINT_VALUE,
        CURRENCY=CURRENCY,
        ACCEPT_OFFER_BUTTON=ACCEPT_OFFER_BUTTON,
        DECLINE_OFFER_BUTTON=DECLINE_OFFER_BUTTON,
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
        HOLD_FINGER=right_index(t) if preferred == 'left' else left_index(t),
        TAP_FINGER=left_index(t) if preferred == 'left' else right_index(t),
    )


def remember_page_title(t: Translator) -> str:
    return t.t('REMEMBER_PAGE_TITLE')


def remember_page_directions(t: Translator, state) -> str:
    key_settings = state.get_key_settings()
    preferred = key_settings['preferredHand']
    return t.t(
        'REMEMBER_PAGE_DIRECTIONS',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def continue_message_direction(t: Translator) -> str:
    return t.t('CONTINUE_MESSAGE_DIRECTION')


def validation_directions(t: Translator) -> str:
    return t.t('VALIDATION_DIRECTIONS')


def premature_key_release_error_message(t: Translator) -> str:
    return t.t('PREMATURE_KEY_RELEASE_ERROR_MESSAGE')


def failed_minimum_demo_taps_message(t: Translator) -> str:
    return t.t('FAILED_MINIMUM_DEMO_TAPS_MESSAGE')


def trial_failed(t: Translator) -> str:
    return t.t('TRIAL_FAILED')


def trial_succeeded(t: Translator) -> str:
    return t.t('TRIAL_SUCCEEDED')


def free_trial(t: Translator) -> str:
    return t.t('FREE_TRIAL')


def go_message(t: Translator) -> str:
    return t.t('GO_MESSAGE')


def loading_bar_message(t: Translator) -> str:
    return t.t('LOADING_BAR_MESSAGE')


def countdown_timer_message(t: Translator) -> str:
    return t.t('COUNTDOWN_TIMER_MESSAGE')


def key_tapped_early_message(t: Translator) -> str:
    return t.t('KEY_TAPPED_EARLY_MESSAGE')


def practice_message(t: Translator, key_to_tap: str, keys_to_hold: List[str]) -> str:
    return t.t(
        'PRACTICE_MESSAGE',
        TAP_KEY=to_name(key_to_tap),
        HOLD_KEY=' and '.join(to_name(k) for k in keys_to_hold),
    )


def release_keys_message(t: Translator) -> str:
    return t.t('RELEASE_KEYS_MESSAGE')


def reward_total_message(t: Translator, total_successful_reward: str, monetary_equivalent: str, currency: str) -> str:
    return t.t(
        'REWARD_TOTAL_MESSAGE',
        totalSuccessfulReward=total_successful_reward,
        monetaryEquivalent=monetary_equivalent,
        currency=currency,
    )


def experiment_begin_message(t: Translator) -> str:
    return t.t('EXPERIMENT_BEGIN_MESSAGE')


def validation_video_tutorial_message(t: Translator, state) -> str:
    key_settings = state.get_key_settings()
    preferred = key_settings['preferredHand']
    return t.t(
        'VALIDATION_VIDEO_TUTORIAL_MESSAGE',
        HOLD_KEY=to_name(key_settings['rightIndex'] if preferred == 'left' else key_settings['leftIndex']),
        TAP_KEY=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
    )


def demo_trial_message(t: Translator, num_demo: int, num_trials: int, key_settings: ExtendedKeySettings) -> str:
    preferred = key_settings['preferredHand']
    return t.t(
        'DEMO_TRIAL_MESSAGE',
        NUM_DEMO_TRIALS=num_demo,
        NUM_TRIALS=num_trials,
        KEY_TO_PRESS=to_name(key_settings['leftIndex'] if preferred == 'left' else key_settings['rightIndex']),
        WARNING_MESSAGES_INSTRUCTION=warning_messages_instruction(t, key_settings),
    )


def reward_trial_message(t: Translator, reward: str) -> str:
    return t.t('REWARD_TRIAL_MESSAGE', reward=reward)


def accept_button_message(t: Translator) -> str:
    return t.t('ACCEPT_BUTTON_MESSAGE')


def reject_button_message(t: Translator) -> str:
    return t.t('REJECT_BUTTON_MESSAGE')


def low_effort_message(t: Translator) -> str:
    return t.t('LOW_EFFORT_MESSAGE')


def high_effort_message(t: Translator) -> str:
    return t.t('HIGH_EFFORT_MESSAGE')


def acceptance_trial_message(t: Translator) -> str:
    return t.t('ACCEPTANCE_TRIAL_MESSAGE')


# --------------------------------
# Likert surveys
# --------------------------------


def likert_preamble_block(t: Translator) -> str:
    return t.t('LIKERT_PREAMBLE_BLOCK')


def likert_preamble_demo(t: Translator) -> str:
    return t.t('LIKERT_PREAMBLE_DEMO')


def likert_preamble_final_questions(t: Translator) -> str:
    return t.t('LIKERT_PREAMBLE_FINAL_QUESTIONS')


def likert_intro(t: Translator) -> str:
    return t.t('LIKERT_INTRO')


def likert_intro_demo(t: Translator) -> str:
    return t.t('LIKERT_INTRO_DEMO')


def likert_responses(t: Translator) -> Dict[str, str]:
    keys = [
        'STRONGLY_DISAGREE', 'SOMEWHAT_DISAGREE', 'DISAGREE', 'NEUTRAL',
        'AGREE', 'SOMEWHAT_AGREE', 'STRONGLY_AGREE',
    ]
    return {k: t.t(f'LIKERT_RESPONSES.{k}') for k in keys}


def likert_responses_attention(t: Translator) -> Dict[str, str]:
    return {'LOW': t.t('LIKERT_RESPONSES.LOW_ATTENTION'), 'HIGH': t.t('LIKERT_RESPONSES.HIGH_ATTENTION')}


def likert_responses_motivation(t: Translator) -> Dict[str, str]:
    return {'LOW': t.t('LIKERT_RESPONSES.LOW_MOTIVATION'), 'HIGH': t.t('LIKERT_RESPONSES.HIGH_MOTIVATION')}


def likert_responses_fatigue(t: Translator) -> Dict[str, str]:
    return {'LOW': t.t('LIKERT_RESPONSES.LOW_FATIGUE'), 'HIGH': t.t('LIKERT_RESPONSES.HIGH_FATIGUE')}


def likert_responses_tiredness(t: Translator) -> Dict[str, str]:
    return {'LOW': t.t('LIKERT_RESPONSES.LOW_TIREDNESS'), 'HIGH': t.t('LIKERT_RESPONSES.HIGH_TIREDNESS')}


def likert_responses_frustration(t: Translator) -> Dict[str, str]:
    return {'LOW': t.t('LIKERT_RESPONSES.LOW_FRUSTRATION'), 'HIGH': t.t('LIKERT_RESPONSES.HIGH_FRUSTRATION')}


def likert_survey_1_questions(t: Translator) -> Dict[str, str]:
    return {
        'QUESTION_1': t.t('LIKERT_SURVEY_1_QUESTIONS.QUESTION_1'),
        'QUESTION_2': t.t('LIKERT_SURVEY_1_QUESTIONS.QUESTION_2'),
    }


def likert_survey_2_questions(t: Translator) -> Dict[str, str]:
    return {f'QUESTION_{i}': t.t(f'LIKERT_SURVEY_2_QUESTIONS.QUESTION_{i}') for i in range(1, 7)}


def likert_survey_3_questions(t: Translator) -> Dict[str, str]:
    return {f'QUESTION_{i}': t.t(f'LIKERT_SURVEY_3_QUESTIONS.QUESTION_{i}') for i in range(1, 6)}


# --------------------------------
# Progress bar
# --------------------------------


def progress_bar(t: Translator) -> Dict[str, str]:
    keys = [
        'PROGRESS_BAR_INTRODUCTION', 'PROGRESS_BAR_PRACTICE', 'PROGRESS_BAR_CALIBRATION',
        'PROGRESS_BAR_VALIDATION', 'PROGRESS_BAR_TRIAL_BLOCKS', 'PROGRESS_BAR_AGENCY_BLOCKS',
        'PROGRESS_BAR_FINAL_CALIBRATION', 'PROGRESS_BAR_END_SCREEN',
    ]
    return {k: t.t(f'PROGRESS_BAR.{k}') for k in keys}


def font_size_title(t: Translator) -> str:
    return t.t('FONT_SIZE_TITLE')


def font_size_small(t: Translator) -> str:
    return t.t('FONT_SIZE_SMALL')


def font_size_normal(t: Translator) -> str:
    return t.t('FONT_SIZE_NORMAL')


def font_size_large(t: Translator) -> str:
    return t.t('FONT_SIZE_LARGE')


def font_size_extra_large(t: Translator) -> str:
    return t.t('FONT_SIZE_EXTRA_LARGE')


def full_screen_text(t: Translator) -> str:
    return t.t('FULL_SCREEN_TEXT')


# --------------------------------
# Ending part
# --------------------------------


def experiment_has_ended_message(t: Translator) -> str:
    return t.t('EXPERIMENT_HAS_ENDED_MESSAGE')


def end_experiment_message(t: Translator) -> str:
    return t.t('END_EXPERIMENT_MESSAGE')


# --------------------------------
# Instruction pages
# --------------------------------


def instruction_label(t: Translator) -> Dict[str, str]:
    return {
        InstructionIDs.TAPPING.value: t.t('INSTRUCTION_LABEL_TAPPING'),
        InstructionIDs.EBDM.value: t.t('INSTRUCTION_LABEL_EBDM'),
        InstructionIDs.AGENCY.value: t.t('INSTRUCTION_LABEL_AGENCY'),
    }


def select_instruction_topic(t: Translator) -> str:
    return t.t('SELECT_INSTRUCTION_TOPIC')


# --------------------------------
# Reason-code -> display text (for success_trial.py's reason codes)
# --------------------------------


def resolve_reason_message(t: Translator, reason_code: str, key_settings: ExtendedKeySettings) -> str:
    """Maps the reason codes produced by trials/success_trial.py's
    resolve_*_screen_params functions to their display text."""
    if reason_code == 'KEY_TAPPED_EARLY':
        return key_tapped_early_first_error_message(t, key_settings)
    if reason_code == 'KEY_RELEASED_EARLY':
        return key_released_early_first_error_message(t, key_settings)
    if reason_code == 'NOT_ENOUGH_TAPS':
        return not_enough_taps_first_error_message(t, key_settings)
    if reason_code == 'SUCCESSFUL_FIRST_TRIAL':
        return successful_first_trial_message(t)
    if reason_code == 'TRIAL_NOT_SUCCESSFUL':
        return trial_not_successful_message(t)
    return ''
