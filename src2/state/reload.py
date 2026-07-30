"""ReloadObject -- port of the `ReloadObject` type in
src/modules/experiment/utils/types.ts, plus the logic to rehydrate an
ExperimentState from a checkpoint (replacing the JS
`input.reloadObject` resume path in experiment.ts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src2.state.experiment_state import ExperimentState


@dataclass
class ReloadObject:
    phase: str
    medianTaps: dict
    totalReward: float
    preferredHand: str
    block: Optional[int] = None
    remainingTrialBlocks: Optional[List[str]] = None
    previousTrials: Optional[List[dict]] = field(default_factory=list)


def apply_reload_object(state: ExperimentState, reload_object: ReloadObject) -> None:
    """Rehydrates an ExperimentState in-place from a ReloadObject.

    Port of the `if (input.reloadObject) { ... }` block at the top of
    experiment.ts's `run()`. NOTE: that block does NOT set `state.phase`
    -- `reload_object.phase` is only read directly (by
    ExperimentRunner's should-show-EBDM/Agency predicates) to decide
    which phases to skip; `state.phase` itself is only written fresh
    when each block's on_timeline_start actually fires. Setting it here
    too would be harmless in practice (it gets overwritten before
    anything reads it) but is intentionally omitted to match the
    original control flow exactly.

    Each field is applied only if truthy, mirroring the original's
    `if (input.reloadObject.medianTaps)` / etc. guards (in JS, objects
    are always truthy, so this is effectively a None-check for
    medianTaps/preferredHand; totalReward==0 is falsy in JS too, so a
    zero reward is skipped here exactly as it would be there -- harmless
    since ExperimentState already defaults previousReward to 0).
    """
    if reload_object.medianTaps:
        state.set_median_taps(reload_object.medianTaps)
    if reload_object.preferredHand:
        state.set_preferred_hand(reload_object.preferredHand)
    if reload_object.totalReward:
        state.set_previous_reward(reload_object.totalReward)
    # previousTrials isn't part of the original reload block (which lives
    # in experiment.ts, outside this port's scope) -- ADO history
    # restoration on resume is this port's own necessary addition, since
    # the desktop app has no separate loader layer to do it elsewhere.
    if reload_object.previousTrials:
        state.set_previous_trials(reload_object.previousTrials)


def reload_object_from_dict(data: dict) -> ReloadObject:
    return ReloadObject(
        phase=data['phase'],
        medianTaps=data['medianTaps'],
        totalReward=data['totalReward'],
        preferredHand=data['preferredHand'],
        block=data.get('block'),
        remainingTrialBlocks=data.get('remainingTrialBlocks'),
        previousTrials=data.get('previousTrials', []),
    )
