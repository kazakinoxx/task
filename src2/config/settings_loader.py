"""Local JSON persistence for experiment settings.

Replaces the Graasp REST `postAppSetting`/`patchAppSetting` mutations used
by SettingsContext.tsx. Desktop app has no backend, so settings are a
plain JSON file the experimenter edits directly or through
config/settings_dialog.py (milestone 9).

Missing-key fallback mirrors ALL_SETTING_NAMES.reduce(...) in
SettingsContext.tsx: any category (or field within a category) absent
from the file falls back to the dataclass default rather than raising.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from src2.config.settings_schema import (
    ALL_SETTING_NAMES,
    SETTING_CLASS_BY_NAME,
    AllSettingsType,
)


def _merge_category(cls, data: dict | None):
    """Builds a dataclass instance from a possibly-partial dict, falling
    back to per-field defaults for anything missing (mirrors the JS
    `setting.data || default` fallback, but at field granularity)."""
    instance = cls()
    if not data:
        return instance
    for f in dataclasses.fields(cls):
        if f.name in data and data[f.name] is not None:
            setattr(instance, f.name, data[f.name])
    return instance


def settings_from_dict(data: dict) -> AllSettingsType:
    settings = AllSettingsType()
    for name in ALL_SETTING_NAMES:
        cls = SETTING_CLASS_BY_NAME[name]
        setattr(settings, name, _merge_category(cls, data.get(name)))
    return settings


def settings_to_dict(settings: AllSettingsType) -> dict:
    return dataclasses.asdict(settings)


def load_settings(path: str | Path) -> AllSettingsType:
    """Loads settings JSON from disk. Returns pure defaults if the file
    does not exist yet (first run)."""
    path = Path(path)
    if not path.exists():
        return AllSettingsType()
    with path.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    return settings_from_dict(data)


def save_settings(settings: AllSettingsType, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as fh:
        json.dump(settings_to_dict(settings), fh, indent=2)
    tmp_path.replace(path)
