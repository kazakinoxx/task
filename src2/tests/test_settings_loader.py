import json
from pathlib import Path

from src2.config.settings_loader import load_settings, save_settings, settings_to_dict
from src2.config.settings_schema import AllSettingsType


def test_load_settings_missing_file_returns_defaults(tmp_path: Path):
    settings = load_settings(tmp_path / 'does_not_exist.json')
    assert settings.generalSettings.taskOrder == 'EBDMFirst'
    assert settings.taskSettings.taskBoundsIncluded == ['easy', 'hard']


def test_save_then_load_roundtrip(tmp_path: Path):
    settings = AllSettingsType()
    settings.generalSettings.taskOrder = 'AgencyFirst'
    settings.agencyTaskSettings.numberOfTrials = 99
    path = tmp_path / 'settings.json'
    save_settings(settings, path)

    loaded = load_settings(path)
    assert loaded.generalSettings.taskOrder == 'AgencyFirst'
    assert loaded.agencyTaskSettings.numberOfTrials == 99
    # Untouched categories still carry their defaults
    assert loaded.validationSettings.percentageOfValidationSuccessesRequired == 75


def test_load_settings_falls_back_for_partial_file(tmp_path: Path):
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'generalSettings': {'taskOrder': 'AgencyFirst'}}), encoding='utf-8')
    settings = load_settings(path)
    assert settings.generalSettings.taskOrder == 'AgencyFirst'
    # fontSize was absent from the file -> falls back to default
    assert settings.generalSettings.fontSize == 'normal'
