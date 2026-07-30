"""Introduction phase -- port of
src/modules/experiment/parts/introduction.ts.

Mostly a linear sequence of instruction screens (fullscreen prompt, "sit
comfortably", tutorial summary, hand-dominance question); the only real
logic is the hand-dominance response mapping and the screen sequencing +
state/history side effects, both covered by `run_introduction` below.

Like parts/practice.py, the actual screens are injected callables
(`IntroductionRunners`) so this module's sequencing/state logic is fully
unit-testable without PsychoPy; main.py wires the real
trials/message_trial.py-backed screens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src2.utils.trial_history import TrialHistory


def resolve_preferred_hand(response_index: int) -> str:
    """Port of `state.setPreferredHand(data.response === 0 ? 'left' : 'right')`.
    Choices are [LEFT_HAND_BUTTON(), RIGHT_HAND_BUTTON()], so index 0 = left."""
    return 'left' if response_index == 0 else 'right'


@dataclass
class IntroductionRunners:
    show_begin: Callable[[], dict]
    show_sit_comfortably: Callable[[], dict]
    show_tutorial_intro: Callable[[], dict]
    ask_preferred_hand: Callable[[], dict]  # returns {'response': 0|1}


def run_introduction(state, history: TrialHistory, runners: IntroductionRunners) -> None:
    """Port of buildIntroduction -- runs the four screens in order,
    resolves the hand-preference response into `state`, and records each
    step to `history` (mirroring how every jsPsych trial in the original
    ends up in `jsPsych.data`, including `data.preferredHand =
    state.getPreferredHand()` set on the hand-preference trial)."""
    history.add({**runners.show_begin(), 'trial_type': 'fullscreen'})
    history.add({**runners.show_sit_comfortably(), 'trial_type': 'html-button-response'})
    history.add({**runners.show_tutorial_intro(), 'trial_type': 'html-button-response'})

    hand_response = runners.ask_preferred_hand()
    response_index = hand_response['response']
    preferred_hand = resolve_preferred_hand(response_index)
    state.set_preferred_hand(preferred_hand)
    history.add(
        {
            'task': 'preferred_hand',
            'response': response_index,
            'preferredHand': preferred_hand,
            'trial_type': 'html-button-response',
        }
    )
