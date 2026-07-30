from pathlib import Path

from src2.config.settings_schema import AllSettingsType
from src2.data.data_writer import DataWriter
from src2.data.result_schema import ExperimentResult
from src2.state.experiment_state import ExperimentState


def test_append_trial_and_finalize_writes_expected_shape(tmp_path: Path):
    settings = AllSettingsType()
    writer = DataWriter('participant1', tmp_path, settings)
    writer.append_trial({'trial_type': 'task-plugin', 'task': 'block', 'tapCount': 5})
    writer.append_trial({'trial_type': 'countdown-trial', 'task': 'countdown'})

    session_path = writer.finalize()
    assert session_path.exists()

    result = ExperimentResult.from_dict(__import__('json').loads(session_path.read_text()))
    assert len(result.rawData.trials) == 2
    assert result.rawData.trials[0]['task'] == 'block'
    assert result.settings.generalSettings.taskOrder == 'EBDMFirst'


def test_checkpoint_and_resume_roundtrip(tmp_path: Path):
    settings = AllSettingsType()
    writer = DataWriter('participant2', tmp_path, settings)
    writer.append_trial({'trial_type': 'task-plugin', 'tapCount': 3})

    state = ExperimentState(settings)
    state.set_instruction_phase('EBDM')
    state.set_preferred_hand('left')
    state.set_previous_reward(12)
    writer.checkpoint(phase='EBDM', state=state, remaining_trial_blocks=['sync', 'midasync'], block=2)

    # Simulate a fresh process resuming the same participant directory.
    resumed_writer = DataWriter('participant2', tmp_path, settings)
    reload_object = resumed_writer.load_reload_object()

    assert reload_object is not None
    assert reload_object.phase == 'EBDM'
    assert reload_object.preferredHand == 'left'
    assert reload_object.totalReward == 12
    assert reload_object.remainingTrialBlocks == ['sync', 'midasync']
    assert resumed_writer.trials == [{'trial_type': 'task-plugin', 'tapCount': 3}]


def test_checkpoint_missing_returns_none(tmp_path: Path):
    settings = AllSettingsType()
    writer = DataWriter('participant3', tmp_path, settings)
    assert writer.load_reload_object() is None
