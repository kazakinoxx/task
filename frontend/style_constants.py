"""Centralized rendering style constants for the PsychoPy frontend.

Single source of truth for every visual value used across `frontend/**`
-- window setup, fonts, colors, text sizing, on-screen positions, and
stimulus geometry. Change a value here to restyle every screen that
references it; view modules should import these names rather than
hardcoding literals.

Grouped by concern so a specific knob is easy to find. All positions and
norm-unit sizes assume the window's `units='norm'` (-1..1 across the
screen); thermometer geometry is in pixels (`units='pix'`).
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------
WINDOW_FULLSCREEN = False
WINDOW_COLOR = 'white'  # CSS .jspsych-display-element background-color: #ffffff
WINDOW_UNITS = 'norm'

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
# CSS font-family: Nunito, Roboto, sans-serif. Nunito may not be installed on
# this machine -- PsychoPy warns and falls back to a default sans-serif if so.
DEFAULT_FONT = 'Nunito'      # trial screens (countdown, tapping, feedback, ...)
INSTRUCTION_FONT = 'Nunito'  # message / instruction / break screens

# --------------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------------
TEXT_COLOR = 'black'  # CSS .jspsych-content color: #000000

# inline key-reference coloring (CSS .hold-key blue / .tap-key red, both bold)
HOLD_KEY_COLOR = '#3182ce'
TAP_KEY_COLOR = '#e53e3e'

# success/failure feedback screen
SUCCESS_COLOR = 'green'  # CSS .active / .right-arrow green
FAILURE_COLOR = 'red'    # CSS .left-arrow fill: red
SKIP_COLOR = 'gray'

# per-tap "checkmark" flashed during the tapping tutorial (task == 'practice')
CHECKMARK_COLOR = '#568259'      # green
CHECKMARK_POS = (0, 0.3)         # height units (see run_tapping); above the center prompt
CHECKMARK_SIZE = 0.05            # height units -- overall glyph scale
CHECKMARK_LINE_WIDTH = 6
CHECKMARK_FLASH_DURATION = 0.25  # seconds each tap's checkmark stays visible

# post-introduction fixation-cross screen (a centered '+' shown for a few
# seconds so the participant settles and fixates before the tasks begin)
FIXATION_CROSS_COLOR = 'black'
FIXATION_CROSS_SIZE = 0.12        # height units -- arm span of the cross
FIXATION_CROSS_THICKNESS = 0.02   # height units -- stroke thickness
FIXATION_MESSAGE_POS = (0, -0.35)  # norm units, below the cross
FIXATION_DURATION = 3.0           # seconds the fixation screen stays up

# thermometer stimulus
THERMOMETER_OUTLINE_COLOR = 'black'  # CSS #thermometer border: 2px solid black
THERMOMETER_MERCURY_COLOR = 'red'    # CSS #mercury background-color: red
THERMOMETER_TARGET_AREA_COLOR = '#0000ff'
THERMOMETER_BOUND_LINE_COLOR = 'black'

# loading bar (CSS .bar silver track / .progress #568259 fill)
LOADING_BAR_TRACK_COLOR = 'silver'
LOADING_BAR_FILL_COLOR = '#568259'

# clickable buttons (CSS .jspsych-btn: black bg, white text, #222 on hover)
BUTTON_FILL_COLOR = 'black'
BUTTON_HOVER_COLOR = '#222222'
BUTTON_TEXT_COLOR = 'white'

# --------------------------------------------------------------------------
# Text sizing (norm units)
# --------------------------------------------------------------------------
TEXT_HEIGHT = 0.05           # default body / prompt text
TEXT_HEIGHT_SMALL = 0.04     # loading-bar label + caption
TEXT_HEIGHT_PREAMBLE = 0.045  # likert preamble header
FEEDBACK_TEXT_HEIGHT = 0.06  # success/failure screen
TITLE_TEXT_HEIGHT = 0.1    # break-screen title (plain TextStim, no <h2> scaling)
# Instruction-screen header (`header=` in message.run_message). Kept small
# because the header text carries an <h2> tag, which RichText scales up by
# 1.6x -- so the on-screen size is ~0.05*1.6 = 0.08, not 0.05.
HEADER_TEXT_HEIGHT = 0.05
DEFAULT_WRAP_WIDTH = 1.6     # trial screens
MESSAGE_WRAP_WIDTH = 1.2     # message / instruction / break screens

# --------------------------------------------------------------------------
# On-screen positions (norm units)
# --------------------------------------------------------------------------
TAPPING_PROMPT_POS = (0, 0)  # screen center
TAPPING_GO_HEADER_POS = (0, 0.85)  # CSS #go-message top:8-10%
TAPPING_GO_HEADER_HEIGHT = 0.12    # CSS .fs-go (large font-size)
TAPPING_GO_HEADER_COLOR = 'green'  # CSS #go-message color: green
LIKERT_PREAMBLE_POS = (0, 0.35)
LIKERT_PROMPT_POS = (0, 0.2)

# multi-question single-page likert survey (port of the jsPsych
# survey-likert plugin's one-page-per-question-set layout)
LIKERT_QUESTIONS_TOP_Y = 0.2
LIKERT_QUESTIONS_BOTTOM_Y = -0.55
LIKERT_QUESTION_PROMPT_OFFSET = 0.06  # prompt sits this far above its own slider
LIKERT_QUESTION_TEXT_HEIGHT = 0.032
LIKERT_SLIDER_WIDTH = 1.3
LIKERT_SLIDER_HEIGHT = 0.05
LIKERT_CONTINUE_BUTTON_POS = (0, -0.82)
LOADING_BAR_LABEL_POS = (0, 0.08)
LOADING_BAR_CAPTION_POS = (0, 0.16)

# message / instruction screens (text shifts left when an image is beside it)
MESSAGE_TEXT_POS_CENTERED = (0, 0)
MESSAGE_TEXT_POS_WITH_IMAGE = (0, 0.5)
MESSAGE_IMAGE_POS = (0, -0.5)
MESSAGE_IMAGE_SIZE = 0.5  # desired image *height* in norm units; width is derived from the image's aspect ratio

# timed-break screen
BREAK_TITLE_POS = (0, 0.45)   # title sits near the top, clear of the body
BREAK_BODY_POS = (0, 0.0)

# clickable buttons (norm units)
BUTTON_WIDTH = 0.45
BUTTON_HEIGHT = 0.14
BUTTON_TEXT_HEIGHT = 0.05
BUTTON_ROW_Y = -0.75      # vertical position of the button row
BUTTON_X_OFFSET = 0.3     # horizontal offset from center for a 2-button row (+/-)

# --------------------------------------------------------------------------
# Thermometer geometry (pixels)
# --------------------------------------------------------------------------
THERMOMETER_WIDTH = 75  # CSS #thermometer width: 200px
THERMOMETER_HEIGHT = 250
THERMOMETER_UNITS = 'pix'

# --------------------------------------------------------------------------
# Agency interruption "question" card (shown while a core/practice trial is
# paused mid-trial for the Y/N control question) -- norm units
# --------------------------------------------------------------------------
INTERRUPTION_BOX_COLOR = '#ffe066'        # yellow pause card
INTERRUPTION_BOX_LINE_COLOR = 'black'
INTERRUPTION_BOX_WIDTH = 1.3
INTERRUPTION_BOX_HEIGHT = 0.95
INTERRUPTION_TITLE_POS = (0, 0.30)
INTERRUPTION_QUESTION_POS = (0, 0.10)
INTERRUPTION_OPTIONS_POS = (0, -0.12)
INTERRUPTION_RELEASE_POS = (0, -0.30)
INTERRUPTION_WRAP_WIDTH = 1.1

# --------------------------------------------------------------------------
# Loading bar geometry (norm units)
# --------------------------------------------------------------------------
LOADING_BAR_WIDTH = 0.6
LOADING_BAR_HEIGHT = 0.05

# --------------------------------------------------------------------------
# Hold-key practice progress bar (norm units) -- port of
# hold-key-practice-trial.ts's startProgressIndicator() div bar
# --------------------------------------------------------------------------
HOLD_PROGRESS_BAR_POS = (0, -0.3)
HOLD_PROGRESS_BAR_WIDTH = 0.6
HOLD_PROGRESS_BAR_HEIGHT = 0.05
HOLD_PROGRESS_BAR_TRACK_COLOR = '#e0e0e0'  # CSS background-color: #e0e0e0
HOLD_PROGRESS_BAR_FILL_COLOR = '#1976D2'   # CSS background-color: #1976D2
