"""ExperimentResult -- port of the `ExperimentResult` shape used
throughout src/modules/{answers,context,main} (`{ settings, rawData:
{ trials: [] } }`).

Kept as a thin dict-shaped wrapper (not a strict dataclass with nested
dataclasses per trial) since trial dicts are heterogeneous (different
trial types carry different fields) -- matching the original TS
`TrialData[]` which is likewise a loosely-typed array of trial objects
with type-specific optional fields.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src2.config.settings_schema import AllSettingsType


@dataclass
class RawData:
    trials: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExperimentResult:
    settings: AllSettingsType
    rawData: RawData = field(default_factory=RawData)

    def to_dict(self) -> dict:
        return {
            'settings': dataclasses.asdict(self.settings),
            'rawData': {'trials': list(self.rawData.trials)},
        }

    @staticmethod
    def from_dict(data: dict) -> 'ExperimentResult':
        from src2.config.settings_loader import settings_from_dict

        settings = settings_from_dict(data.get('settings', {}))
        raw_data = RawData(trials=data.get('rawData', {}).get('trials', []))
        return ExperimentResult(settings=settings, rawData=raw_data)
