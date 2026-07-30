"""Acceptance (accept/reject offer) trial -- port of the html-button-response
trial defined inline in createTaskBlockTrials
(src/modules/experiment/jspsych/trials.ts). Choices are
[ACCEPT_BUTTON_MESSAGE(), REJECT_BUTTON_MESSAGE()], so response index 0
means "accepted" (`data.accepted = data.response === 0`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class AcceptanceTrialParams:
    bounds: Tuple[float, float]
    original_bounds: Tuple[float, float]
    reward: float
    delay: Tuple[float, float]


def resolve_acceptance(response_index: int) -> bool:
    """Port of `data.accepted = data.response === 0;`."""
    return response_index == 0


def build_acceptance_trial_record(params: AcceptanceTrialParams, response_index: int) -> dict:
    return {
        'task': 'accept',
        'reward': params.reward,
        'bounds': list(params.bounds),
        'originalBounds': list(params.original_bounds),
        'delay': list(params.delay),
        'response': response_index,
        'accepted': resolve_acceptance(response_index),
    }
