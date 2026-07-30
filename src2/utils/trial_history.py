"""In-memory trial history, replacing jsPsych's `jsPsych.data.get()`
DataCollection queries.

The JS codebase leans heavily on jsPsych's DataCollection API
(`.filter({...}).last(n).select('field').median()`), so this module
reproduces just that query surface against a plain list of trial dicts,
rather than translating each call site to bespoke list-comprehensions.
This keeps utils/calculations.py a near-literal port of utils.ts.
"""

from __future__ import annotations

import statistics
from typing import Any, List, Optional


class DataColumn:
    """Port of jsPsych's DataColumn (the object returned by `.select(field)`)."""

    def __init__(self, values: List[Any]):
        self._values = values

    def values(self) -> List[Any]:
        return self._values

    def median(self) -> Optional[float]:
        if not self._values:
            return None
        return statistics.median(self._values)

    def sum(self) -> float:
        return sum(self._values)

    def __len__(self) -> int:
        return len(self._values)


class TrialHistory:
    """Port of jsPsych's DataCollection query surface, backed by a plain
    list of trial dicts (each dict is one trial's recorded data, using
    the same camelCase field names as the original TrialData)."""

    def __init__(self, trials: Optional[List[dict]] = None):
        self._trials: List[dict] = list(trials) if trials else []

    def add(self, trial: dict) -> None:
        self._trials.append(trial)

    def all(self) -> List[dict]:
        return list(self._trials)

    def filter(self, **kwargs) -> 'TrialHistory':
        def matches(trial: dict) -> bool:
            return all(trial.get(k) == v for k, v in kwargs.items())

        return TrialHistory([t for t in self._trials if matches(t)])

    def last(self, n: int) -> 'TrialHistory':
        return TrialHistory(self._trials[-n:] if n > 0 else [])

    def select(self, field: str) -> DataColumn:
        return DataColumn([t[field] for t in self._trials if field in t])

    def values(self) -> List[dict]:
        return list(self._trials)

    def first_value(self) -> Optional[dict]:
        return self._trials[0] if self._trials else None

    def last_value(self) -> Optional[dict]:
        return self._trials[-1] if self._trials else None

    def __len__(self) -> int:
        return len(self._trials)


# ---------------------------------------------------------------------------
# check_* helpers -- port of the equivalent functions in utils.ts, querying
# a TrialHistory instead of jsPsych.data.
# ---------------------------------------------------------------------------


def check_flag(history: TrialHistory, trial_type: str, flag: str) -> bool:
    """Port of checkFlag. Returns True if the flag is missing (mirrors the
    JS `lastTrialData ? lastTrialData[flag] : true` fallback -- note the
    fallback to True applies only when there's no matching trial at all;
    if a trial exists but lacks that specific field, JS `undefined` is
    falsy, so this returns False, not True)."""
    last_trial = history.filter(trial_type=trial_type).last(1).last_value()
    if last_trial is None:
        return True
    return bool(last_trial.get(flag))


def check_taps(history: TrialHistory) -> int:
    """Port of checkTaps."""
    last_trial = (
        history.filter(trial_type='task-plugin').last(1).last_value()
    )
    return last_trial['tapCount'] if last_trial else 0


def check_mercury_height(history: TrialHistory) -> bool:
    """Port of checkMercuryHeight -- True if the final mercury height was
    below the lower bound."""
    last_trial = (
        history.filter(trial_type='task-plugin').last(1).last_value()
    )
    if not last_trial:
        return False
    return last_trial['mercuryHeight'] < last_trial['bounds'][0]


def check_keys(history: TrialHistory) -> bool:
    """Port of checkKeys -- True if every hold-key was still down at trial
    end."""
    last_trial = (
        history.filter(trial_type='task-plugin').last(1).last_value()
    )
    keys_state = last_trial['keysState']
    return all(keys_state.values())


def check_last_trial_success(history: TrialHistory, minimum_calibration_median: int) -> bool:
    """Port of checkLastTrialSuccess."""
    return (
        not check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
        and not (
            check_flag(history, 'task-plugin', 'keysReleasedFlag')
            or check_flag(history, 'task-plugin', 'keysReleasedFlag')
        )
        and check_taps(history) >= minimum_calibration_median
    )


def check_last_agency_trial_success(history: TrialHistory) -> bool:
    """Port of checkLastAgencyTrialSuccess.

    NOTE (preserved quirk, not a porting error): the third clause checks
    an empty-string field name (`checkFlag(TappingTask, '', jsPsych)` in
    the original). No trial ever has a '' key, so `check_flag` always
    returns False for it (once a trial exists) and `not False` is always
    True -- this clause is therefore a permanent no-op and the function
    reduces to `not keyTappedEarlyFlag and not keysReleasedFlag`. It does
    NOT check the tapping trial's actual bounds/`success` field, despite
    the name. This looks like an unintentional bug in the original app
    (likely meant to check `'success'`), but is replicated exactly here
    for line-by-line fidelity -- see parts/validation.py's
    `run_validation_trial_loop` for the resulting behavioral consequence
    on validation retries."""
    return (
        not check_flag(history, 'countdown-trial', 'keyTappedEarlyFlag')
        and not check_flag(history, 'task-plugin', 'keysReleasedFlag')
        and not check_flag(history, 'task-plugin', '')
    )


def check_last_agency_trial_question_answered(
    history: TrialHistory, task_type: str = 'core'
) -> bool:
    """Port of checkLastAgencyTrialQuestionAnswered."""
    last_trial = history.filter(task=task_type).last(1).last_value()
    if not last_trial:
        return False
    return last_trial.get('interruptionResponse') in ('y', 'n')
