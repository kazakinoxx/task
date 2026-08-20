"""Settings dataclasses.

Port of AllSettingsType and its 10 sub-types from
src/modules/context/SettingsContext.tsx. Field names are kept in the
original camelCase (not snake_case) on purpose: these objects are
serialized verbatim into the `settings` block of the exported
ExperimentResult JSON, and keeping identical field names means
dataclasses.asdict() produces byte-for-byte-comparable JSON keys to the
old JS output with no translation layer to get wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from src2.utils.types import BoundsType, CalibrationPartType, DelayType, RewardType

TaskOrder = Literal['EBDMFirst', 'AgencyFirst']
AllowedLanguages = Literal['en', 'fr']
TaskSequencingMode = Literal['pseudorandom', 'custom']
PhotoDiodePosition = Literal['top-left', 'top-right', 'customize', 'off']


@dataclass
class GeneralSettingsType:
    fontSize: Literal['small', 'normal', 'large', 'extra-large'] = 'normal'
    useDevice: bool = True
    skipAgencyTask: bool = False
    skipEBDMTask: bool = False
    useNarration: bool = True
    taskOrder: TaskOrder = 'EBDMFirst'
    # Duration (seconds) of the resting-state fixation cross shown after the
    # introduction. Default 300 = 5 minutes.
    fixationDurationSeconds: float = 300


@dataclass
class LanguageSettingsType:
    language: AllowedLanguages = 'en'


@dataclass
class PracticeSettingsType:
    numberOfPracticeLoops: int = 0


@dataclass
class CalibrationSettingsType:
    requiredTrialsCalibration: dict = field(
        default_factory=lambda: {
            CalibrationPartType.CALIBRATION_PART_1.value: 1,
            CalibrationPartType.CALIBRATION_PART_2.value: 3,
            CalibrationPartType.FINAL_CALIBRATION_PART_1.value: 1,
            CalibrationPartType.FINAL_CALIBRATION_PART_2.value: 3,
        }
    )
    minimumCalibrationMedianTaps: int = 10


@dataclass
class AgencyTaskSettingsType:
    numberOfPracticeTrials: int = 1
    breakFrequency: int = 10
    numberOfTrials: int = 40
    allowBreakSkip: bool = True
    breakDuration: int = 30000


@dataclass
class ValidationSettingsType:
    numberOfValidationsPerType: int = 1
    percentageOfValidationSuccessesRequired: float = 75
    percentageOfExtraValidationSuccessesRequired: float = 50


@dataclass
class TaskSettingsType:
    taskBlockRepetitions: int = 1
    taskPermutationRepetitions: int = 1
    taskBlocksIncluded: List[str] = field(
        default_factory=lambda: [
            DelayType.SYNC.value,
            DelayType.SHORT_ASYNC.value,
            DelayType.MID_ASYNC.value,
            DelayType.LONG_ASYNC.value,
        ]
    )
    taskBoundsIncluded: List[str] = field(
        default_factory=lambda: [BoundsType.EASY.value, BoundsType.HARD.value]
    )
    taskRewardsIncluded: List[str] = field(
        default_factory=lambda: [RewardType.LOW.value, RewardType.HIGH.value]
    )
    randomSkipChance: float = 0
    taskSequencingMode: TaskSequencingMode = 'pseudorandom'
    taskCustomSequence: List[str] = field(default_factory=list)


@dataclass
class PhotoDiodeSettings:
    usePhotoDiode: PhotoDiodePosition = 'off'
    photoDiodeLeft: Optional[str] = None
    photoDiodeTop: Optional[str] = None
    photoDiodeHeight: Optional[str] = None
    photoDiodeWidth: Optional[str] = None
    testPhotoDiode: Optional[bool] = None


@dataclass
class KeySettings:
    leftIndex: str = 's'
    rightIndex: str = 'l'
    leftPink: Optional[str] = None
    leftRing: Optional[str] = None
    leftMiddle: Optional[str] = None
    leftThumb: Optional[str] = None


@dataclass
class NextStepSettings:
    linkToNextPage: bool = False
    title: str = ''
    description: str = ''
    link: str = ''
    linkText: str = ''


@dataclass
class AllSettingsType:
    generalSettings: GeneralSettingsType = field(default_factory=GeneralSettingsType)
    languageSettings: LanguageSettingsType = field(default_factory=LanguageSettingsType)
    practiceSettings: PracticeSettingsType = field(default_factory=PracticeSettingsType)
    calibrationSettings: CalibrationSettingsType = field(
        default_factory=CalibrationSettingsType
    )
    agencyTaskSettings: AgencyTaskSettingsType = field(
        default_factory=AgencyTaskSettingsType
    )
    validationSettings: ValidationSettingsType = field(
        default_factory=ValidationSettingsType
    )
    taskSettings: TaskSettingsType = field(default_factory=TaskSettingsType)
    photoDiodeSettings: PhotoDiodeSettings = field(default_factory=PhotoDiodeSettings)
    keySettings: KeySettings = field(default_factory=KeySettings)
    nextStepSettings: NextStepSettings = field(default_factory=NextStepSettings)


# Ordered list of setting category names -- mirrors ALL_SETTING_NAMES in
# SettingsContext.tsx; used by settings_loader for missing-key fallback.
ALL_SETTING_NAMES = [
    'generalSettings',
    'languageSettings',
    'practiceSettings',
    'calibrationSettings',
    'agencyTaskSettings',
    'validationSettings',
    'taskSettings',
    'photoDiodeSettings',
    'keySettings',
    'nextStepSettings',
]

SETTING_CLASS_BY_NAME = {
    'generalSettings': GeneralSettingsType,
    'languageSettings': LanguageSettingsType,
    'practiceSettings': PracticeSettingsType,
    'calibrationSettings': CalibrationSettingsType,
    'agencyTaskSettings': AgencyTaskSettingsType,
    'validationSettings': ValidationSettingsType,
    'taskSettings': TaskSettingsType,
    'photoDiodeSettings': PhotoDiodeSettings,
    'keySettings': KeySettings,
    'nextStepSettings': NextStepSettings,
}
