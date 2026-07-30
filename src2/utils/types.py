"""Enums and shared type aliases.

Port of src/modules/experiment/utils/types.ts. String values are kept
identical to the TS enum values since they appear as data in exported
trial/settings JSON (task labels, setting choices, etc).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, TypedDict


class TrialTypes(str, Enum):
    TAPPING_TASK = 'task-plugin'
    COUNTDOWN_TASK = 'countdown-trial'
    ACCEPT_TASK = 'html-button-response'


class DelayType(str, Enum):
    SYNC = 'sync'
    SHORT_ASYNC = 'shortasync'
    MID_ASYNC = 'midasync'
    LONG_ASYNC = 'longasync'


class BoundsType(str, Enum):
    EASY = 'easy'
    EASY_MEDIUM = 'easymedium'
    MEDIUM = 'medium'
    HARD = 'hard'


class RewardType(str, Enum):
    LOW = 'low'
    LOW_MIDDLE = 'lowmiddle'
    MIDDLE = 'middle'
    HIGH = 'high'


class NoRewardType(str, Enum):
    NO = 'no'


class InstructionIDs(str, Enum):
    TAPPING = 'tapping'
    EBDM = 'ebdm'
    AGENCY = 'agency'


class CalibrationPartType(str, Enum):
    CALIBRATION_PART_1 = 'calibrationPart1'
    CALIBRATION_PART_2 = 'calibrationPart2'
    FINAL_CALIBRATION_PART_1 = 'finalCalibrationPart1'
    FINAL_CALIBRATION_PART_2 = 'finalCalibrationPart2'


class ValidationPartType(str, Enum):
    VALIDATION_EASY = 'validationEasy'
    VALIDATION_MEDIUM = 'validationMedium'
    VALIDATION_HARD = 'validationHard'
    VALIDATION_EXTRA = 'validationExtra'


class OtherTaskStagesType(str, Enum):
    PRACTICE = 'practice'
    COUNTDOWN = 'countdown'
    DEMO = 'demo'
    SUCCESS = 'success'
    ACCEPT = 'accept'
    BLOCK = 'block'


Phase = Literal[
    'introduction',
    'practice',
    'calibration',
    'validation',
    'EBDM',
    'agency',
    'final-calibration',
    'end-screen',
]


class ExtendedKeySettings(TypedDict, total=False):
    preferredHand: str
    rightIndex: str
    leftIndex: str
    leftPink: Optional[str]
    leftRing: Optional[str]
    leftMiddle: Optional[str]
    leftThumb: Optional[str]


class ReloadObject(TypedDict, total=False):
    phase: Phase
    medianTaps: dict
    totalReward: float
    preferredHand: Literal['left', 'right']
    block: Optional[int]
    remainingTrialBlocks: Optional[list]
