"""ADO trial selection -- port of
src/modules/experiment/ado/ado-selector.ts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, TypedDict

from src2.ado.ado_math import CANDIDATE_DELAYS, SEED_DELAYS, compute_eig, posterior_from_data, select_next_delay
from src2.utils.trial_history import TrialHistory

if TYPE_CHECKING:
    from src2.state.experiment_state import ExperimentState


class AgencyTrial(TypedDict):
    delay: float
    response: str
    responseNumeric: int


def get_agency_data(history: TrialHistory, state: 'ExperimentState') -> List[AgencyTrial]:
    """Port of getAgencyData -- previously-recorded trials (from a
    resumed session, via state.previousTrials) prepended to the current
    session's 'core' trials that carry a y/n interruption response."""
    agency_data: List[AgencyTrial] = []

    previous_trials = state.get_state().get('previousTrials')
    if previous_trials:
        agency_data.extend(previous_trials)

    for trial in history.values():
        response = trial.get('interruptionResponse')
        if trial.get('task') == 'core' and response in ('y', 'n'):
            agency_data.append(
                AgencyTrial(
                    delay=float(trial['delayOriginal']),
                    response=response,
                    responseNumeric=1 if response.lower() == 'y' else 0,
                )
            )

    return agency_data


def get_next_delay_level(history: TrialHistory, state: 'ExperimentState') -> float:
    """Port of getNextDelayLevel."""
    agency_data = get_agency_data(history, state)

    if len(agency_data) < len(SEED_DELAYS):
        return SEED_DELAYS[len(agency_data)]

    delays = [d['delay'] for d in agency_data]
    responses = [d['responseNumeric'] for d in agency_data]

    posterior = posterior_from_data(delays, responses)
    eigs = compute_eig(CANDIDATE_DELAYS, posterior)

    history_counts: Dict[float, int] = {}
    for d in delays:
        history_counts[d] = history_counts.get(d, 0) + 1

    return select_next_delay(CANDIDATE_DELAYS, eigs, history_counts)
