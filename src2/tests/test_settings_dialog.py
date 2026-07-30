from src2.config.settings_dialog import apply_dialog_dict, settings_to_dialog_dict
from src2.config.settings_schema import AllSettingsType


def test_settings_to_dialog_dict_reflects_current_values():
    settings = AllSettingsType()
    settings.generalSettings.taskOrder = 'AgencyFirst'
    settings.agencyTaskSettings.numberOfTrials = 20
    fields = settings_to_dialog_dict(settings)
    assert fields['Task order'] == 'AgencyFirst'
    assert fields['Agency: number of trials'] == 20


def test_apply_dialog_dict_roundtrip():
    settings = AllSettingsType()
    fields = settings_to_dialog_dict(settings)
    fields['Language'] = 'fr'
    fields['Font size'] = 'large'
    fields['Agency: number of trials'] = '15'
    fields['Validation: successes required (%)'] = '80'

    updated = apply_dialog_dict(settings, fields)
    assert updated.languageSettings.language == 'fr'
    assert updated.generalSettings.fontSize == 'large'
    assert updated.agencyTaskSettings.numberOfTrials == 15
    assert updated.validationSettings.percentageOfValidationSuccessesRequired == 80.0
    # Original settings object must be untouched.
    assert settings.languageSettings.language == 'en'
