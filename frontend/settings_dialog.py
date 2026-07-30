"""Pre-experiment settings dialog -- thin psychopy.gui wrapper, not unit
tested (requires a real display). See src2/config/settings_dialog.py for
the pure dict round-trip (`settings_to_dialog_dict`/`apply_dialog_dict`)
this drives.
"""

from __future__ import annotations

from typing import Optional

from src2.config.settings_dialog import apply_dialog_dict, settings_to_dialog_dict
from src2.config.settings_schema import AllSettingsType


def run_settings_dialog(settings: AllSettingsType) -> Optional[AllSettingsType]:
    """Shows the dialog and returns updated settings, or None if the
    participant/technician cancelled."""
    from psychopy import gui

    fields = settings_to_dialog_dict(settings)
    dlg = gui.DlgFromDict(
        dictionary=fields,
        title='Experiment Settings',
        order=list(fields.keys()),
    )
    if not dlg.OK:
        return None
    return apply_dialog_dict(settings, fields)
