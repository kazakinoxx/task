"""Pre-experiment settings dialog field mapping -- replaces the React
SettingsView.tsx/*SettingsView.tsx screens with a lightweight PsychoPy
GUI dialog for the fields a technician commonly needs to tweak.

Power-user fields (custom task sequences, photodiode pixel geometry)
are intentionally left out of the dialog and must be edited directly in
the settings JSON file (see config/settings_loader.py) -- the dialog
covers the common case, not full parity with every settings screen.

This module holds the pure dict round-trip between dialog fields and
AllSettingsType; the actual psychopy.gui.DlgFromDict call
(`run_settings_dialog`) lives in src2/frontend/settings_dialog.py.
"""

from __future__ import annotations

from src2.config.settings_schema import AllSettingsType


def settings_to_dialog_dict(settings: AllSettingsType) -> dict:
    """Flattens the subset of settings the dialog edits into a single
    ordered dict suitable for psychopy.gui.DlgFromDict."""
    return {
        'Participant ID': '',
        'Language': settings.languageSettings.language,
        'Font size': settings.generalSettings.fontSize,
        'Task order': settings.generalSettings.taskOrder,
        'Use external device': settings.generalSettings.useDevice,
        'Use narration': settings.generalSettings.useNarration,
        'Skip EBDM task': settings.generalSettings.skipEBDMTask,
        'Skip agency task': settings.generalSettings.skipAgencyTask,
        'Agency: number of trials': settings.agencyTaskSettings.numberOfTrials,
        'Agency: break frequency': settings.agencyTaskSettings.breakFrequency,
        'Validation: successes required (%)': settings.validationSettings.percentageOfValidationSuccessesRequired,
    }


def apply_dialog_dict(settings: AllSettingsType, dialog_result: dict) -> AllSettingsType:
    """Writes dialog field values back onto a copy of settings."""
    import dataclasses

    updated = dataclasses.replace(settings)
    updated.languageSettings = dataclasses.replace(settings.languageSettings, language=dialog_result['Language'])
    updated.generalSettings = dataclasses.replace(
        settings.generalSettings,
        fontSize=dialog_result['Font size'],
        taskOrder=dialog_result['Task order'],
        useDevice=dialog_result['Use external device'],
        useNarration=dialog_result['Use narration'],
        skipEBDMTask=dialog_result['Skip EBDM task'],
        skipAgencyTask=dialog_result['Skip agency task'],
    )
    updated.agencyTaskSettings = dataclasses.replace(
        settings.agencyTaskSettings,
        numberOfTrials=int(dialog_result['Agency: number of trials']),
        breakFrequency=int(dialog_result['Agency: break frequency']),
    )
    updated.validationSettings = dataclasses.replace(
        settings.validationSettings,
        percentageOfValidationSuccessesRequired=float(dialog_result['Validation: successes required (%)']),
    )
    return updated
