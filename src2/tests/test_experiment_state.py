from src2.config.settings_schema import AllSettingsType
from src2.state.experiment_state import ExperimentState
from src2.utils.types import BoundsType, CalibrationPartType, DelayType, RewardType


def test_default_state_and_settings():
    state = ExperimentState()
    assert state.get_state()['phase'] == 'introduction'
    assert state.get_state()['tappingHand'] == 'right'
    assert state.get_general_settings().taskOrder == 'EBDMFirst'
    assert state.get_settings() is not None


def test_calibration_part2_seed_progression():
    state = ExperimentState()
    # No trials yet -> default seed
    assert state.get_calibration_part2_seed() == 20

    state.push_calibration_part2_tap_count(12)
    assert state.get_calibration_part2_seed() == 12

    state.push_calibration_part2_tap_count(15)
    assert state.get_calibration_part2_seed() == 15  # max(12, 15)

    state.push_calibration_part2_tap_count(9)
    assert state.get_calibration_part2_seed() == 15  # max(15, 9)

    # medianTaps should track the seed after each push
    assert state.get_state()['medianTaps'][CalibrationPartType.CALIBRATION_PART_2.value] == 15

    # Final MTS = max(T2, T3) = max(15, 9) = 15
    assert state.get_calibration_part2_final_mts() == 15


def test_final_calibration_part2_seed_uses_regular_final_mts_first():
    state = ExperimentState()
    state.push_calibration_part2_tap_count(10)
    state.push_calibration_part2_tap_count(20)
    state.push_calibration_part2_tap_count(5)
    regular_final_mts = state.get_calibration_part2_final_mts()  # max(20,5)=20

    # Before any final-calibration trials, seed should equal the regular
    # calibration's final MTS (option B in the original comment).
    assert state.get_final_calibration_part2_seed() == regular_final_mts == 20

    state.push_final_calibration_part2_tap_count(8)
    assert state.get_final_calibration_part2_seed() == 8


def test_get_task_settings_dedupes_and_sorts():
    settings = AllSettingsType()
    settings.taskSettings.taskBoundsIncluded = [
        BoundsType.HARD.value,
        BoundsType.EASY.value,
        BoundsType.EASY.value,
        BoundsType.MEDIUM.value,
    ]
    state = ExperimentState(settings)
    task_settings = state.get_task_settings()
    assert task_settings.taskBoundsIncluded == [
        BoundsType.EASY.value,
        BoundsType.MEDIUM.value,
        BoundsType.HARD.value,
    ]


def test_get_key_settings_includes_preferred_hand():
    state = ExperimentState()
    state.set_preferred_hand('left')
    key_settings = state.get_key_settings()
    assert key_settings['preferredHand'] == 'left'
    assert key_settings['leftIndex'] == 's'
    assert key_settings['rightIndex'] == 'l'


def test_reset_state_replicates_original_median_taps_quirk():
    state = ExperimentState()
    state.push_calibration_part2_tap_count(12)
    state.reset_state()
    # Replicates the (likely accidental) TS behavior where resetState()
    # zeroes medianTaps instead of resetting to the 10-default.
    assert all(v == 0 for v in state.get_state()['medianTaps'].values())
    assert state.get_state()['numberOfPracticeLoopsCompleted'] == 1
