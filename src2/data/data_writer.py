"""DataWriter -- local-disk replacement for the Graasp REST
`usePostAppData`/`usePatchAppData` persistence used by
ExperimentContext.tsx / ExperimentLoader.tsx.

File layout per participant:

    data/<participant_id>/
        session_<timestamp>.json   # final ExperimentResult, written by finalize()
        checkpoint.json            # rolling checkpoint, overwritten after every trial

Checkpointing after every trial (not just at phase boundaries, as the JS
version does) is a deliberate improvement: there's no network-request
cost to batch against anymore, and it makes a crashed/closed session
resumable from the exact trial it stopped at.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src2.config.settings_schema import AllSettingsType
from src2.data.result_schema import ExperimentResult, RawData
from src2.utils.trial_history import TrialHistory
from src2.state.experiment_state import ExperimentState
from src2.state.reload import ReloadObject, reload_object_from_dict


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)
    tmp_path.replace(path)


class DataWriter:
    def __init__(self, participant_id: str, base_dir: str | Path, settings: AllSettingsType):
        self.participant_id = participant_id
        self.base_dir = Path(base_dir)
        self.participant_dir = self.base_dir / participant_id
        self.settings = settings
        self.trials: List[Dict[str, Any]] = []

    @property
    def checkpoint_path(self) -> Path:
        return self.participant_dir / 'checkpoint.json'

    def append_trial(self, trial: Dict[str, Any]) -> None:
        self.trials.append(trial)
        self._write_checkpoint_file(phase=None, state=None)

    def checkpoint(
        self,
        phase: str,
        state: ExperimentState,
        remaining_trial_blocks: Optional[List[str]] = None,
        block: Optional[int] = None,
        previous_trials: Optional[List[dict]] = None,
    ) -> None:
        """Explicit phase-boundary checkpoint carrying the full
        ReloadObject shape (phase, medianTaps, totalReward, preferredHand,
        block, remainingTrialBlocks, previousTrials for ADO)."""
        self._write_checkpoint_file(
            phase=phase,
            state=state,
            remaining_trial_blocks=remaining_trial_blocks,
            block=block,
            previous_trials=previous_trials,
        )

    def _write_checkpoint_file(
        self,
        phase: Optional[str],
        state: Optional[ExperimentState],
        remaining_trial_blocks: Optional[List[str]] = None,
        block: Optional[int] = None,
        previous_trials: Optional[List[dict]] = None,
    ) -> None:
        existing = self._read_checkpoint_raw() or {}
        if state is not None:
            existing.update(
                {
                    'phase': phase if phase is not None else state.get_state()['phase'],
                    'medianTaps': state.get_state()['medianTaps'],
                    'totalReward': state.get_state()['previousReward'],
                    'preferredHand': state.get_preferred_hand(),
                    'block': block,
                    'remainingTrialBlocks': remaining_trial_blocks,
                    'previousTrials': previous_trials if previous_trials is not None else state.get_state().get('previousTrials'),
                }
            )
        existing['trials'] = self.trials
        _atomic_write_json(self.checkpoint_path, existing)

    def _read_checkpoint_raw(self) -> Optional[dict]:
        if not self.checkpoint_path.exists():
            return None
        with self.checkpoint_path.open('r', encoding='utf-8') as fh:
            return json.load(fh)

    def load_reload_object(self) -> Optional[ReloadObject]:
        """Reads checkpoint.json (if present) and reconstructs both the
        ReloadObject and the previously-recorded trials, so a resumed
        session picks up its trial history too."""
        raw = self._read_checkpoint_raw()
        if not raw or 'phase' not in raw:
            return None
        self.trials = raw.get('trials', [])
        return reload_object_from_dict(raw)

    def finalize(self) -> Path:
        result = ExperimentResult(settings=self.settings, rawData=RawData(trials=self.trials))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_path = self.participant_dir / f'session_{timestamp}.json'
        _atomic_write_json(session_path, result.to_dict())
        return session_path


class RecordingTrialHistory(TrialHistory):
    """A TrialHistory that also persists every added trial through a
    DataWriter. The parts/*.py orchestration functions (calibration,
    validation, task_core, agency_task_core) only know about the
    TrialHistory query interface (filter/last/select, used by the
    check_* helpers) -- this subclass lets a single `.add()` call from
    that code satisfy both the in-memory querying needs and on-disk
    persistence/checkpointing, without those modules needing to know
    about DataWriter at all."""

    def __init__(self, data_writer: DataWriter, trials: Optional[List[dict]] = None):
        super().__init__(trials)
        self.data_writer = data_writer

    def add(self, trial: dict) -> None:
        super().add(trial)
        self.data_writer.append_trial(trial)
