"""Trial data record shapes and builder.

Port of the TaskTrialData/PassedTaskData interfaces in
src/modules/experiment/utils/types.ts, plus the auto-added jsPsych
metadata fields (trial_type, trial_index, plugin_version, time_elapsed)
that used to come from jsPsych's DataCollection.

Field names are kept in camelCase to match the existing JSON output
exactly -- see result_schema.py for why this matters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class TaskTrialData(TypedDict, total=False):
    tapCount: int
    startTime: float
    endTime: float
    mercuryHeight: float
    error: str
    bounds: List[float]
    reward: float
    task: str
    errorOccurred: bool
    keysReleasedFlag: bool
    success: bool
    keyTappedEarlyFlag: bool
    accepted: Optional[bool]
    response: Optional[str]
    minimumTapsReached: Optional[bool]
    keysState: Dict[str, bool]
    medianTaps: Optional[float]
    # Agency-task-only fields
    interruptionResponse: Optional[str]
    delayOriginal: Optional[float]


class PassedTaskData(TypedDict, total=False):
    bounds: List[float]
    originalBounds: List[float]
    reward: float
    accepted: Optional[bool]
    randomDelay: List[float]
    randomChanceAccepted: Optional[bool]


_trial_index_counter = {'value': 0}


def reset_trial_index_counter() -> None:
    """Call at the start of a new session/participant run."""
    _trial_index_counter['value'] = 0


def build_trial_record(
    trial_type: str,
    time_elapsed_ms: float,
    data: Dict[str, Any],
    plugin_version: Optional[str] = None,
) -> dict:
    """Builds one trial dict combining jsPsych-style auto metadata with
    the trial's custom data fields, auto-incrementing trial_index the
    same way jsPsych.data does per trial recorded."""
    record: Dict[str, Any] = {
        'trial_type': trial_type,
        'trial_index': _trial_index_counter['value'],
        'plugin_version': plugin_version,
        'time_elapsed': time_elapsed_ms,
    }
    record.update(data)
    _trial_index_counter['value'] += 1
    return record
