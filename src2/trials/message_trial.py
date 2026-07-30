"""Generic message/choice/timed-break screens.

Unlike the other trials/*.py modules, this one has no single JS source
file -- it's a shared primitive extracted for the five screens that were
still `lambda: None` stubs in main.py (see main.py's TODO comments,
milestone 10): buildIntroduction's plain instruction screens
(introduction.ts), continueMessageDirection and getEndPage
(experiment.ts), deviceConnectPages's status confirmation
(triggers/serialport.ts), and endOfAgencyTaskBreak
(parts/agency-task-core.ts). All five are "show text (+ maybe a
countdown/skip/2-choice), wait for a key" screens with no HTML/DOM
markup worth porting, so this module factors out that shape once instead
of duplicating the TextStim/poll/flip loop five times.
"""

from __future__ import annotations

from typing import Dict, Optional



def resolve_choice_response(key: str, key_map: Dict[str, int]) -> Optional[int]:
    """Maps a released key to a response index, or None if the key isn't
    one of the choices. Generalizes the accept/reject key mapping already
    used ad hoc in trials/acceptance_trial.py's run_acceptance_trial."""
    return key_map.get(key.lower())


def resolve_break_remaining_seconds(elapsed_ms: float, duration_ms: float) -> float:
    """Port of the JS break screens' `remaining -= 1` countdown tick,
    expressed as a pure function of elapsed time instead of a stateful
    setInterval. Never goes negative."""
    return max(0.0, (duration_ms - elapsed_ms) / 1000.0)
