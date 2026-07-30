import math

import numpy as np
import pytest

from src2.ado import ado_math
from src2.ado.ado_math import (
    CANDIDATE_DELAYS,
    EPS,
    SEED_DELAYS,
    compute_eig,
    entropy,
    log_likelihood_array,
    logistic,
    normalize,
    param_grid,
    posterior_from_data,
    select_next_delay,
)
from src2.ado.ado_selector import get_agency_data, get_next_delay_level
from src2.state.experiment_state import ExperimentState
from src2.utils.trial_history import TrialHistory


def _naive_param_grid():
    """Pure-Python re-implementation of PARAM_GRID(), built with the exact
    same nested-loop order as adoMath.ts, used to cross-check the numpy
    vectorization independently."""
    mu_values = [50 + i * (950 / 19) for i in range(20)]
    k_values = [0.002 + i * (0.04 - 0.002) / 19 for i in range(20)]
    gamma_values = [i * 0.025 for i in range(13)]
    lambda_values = [i * 0.025 for i in range(13)]
    grid = []
    for mu in mu_values:
        for k in k_values:
            for gamma in gamma_values:
                for lam in lambda_values:
                    grid.append((mu, k, gamma, lam))
    return grid


def _naive_logistic(x):
    return 1 / (1 + math.exp(-x))


def _naive_log_likelihood_array(delays, responses):
    grid = _naive_param_grid()
    out = []
    for mu, k, gamma, lam in grid:
        log_l = 0.0
        for d, y in zip(delays, responses):
            p = min(max(gamma + (1 - gamma - lam) * _naive_logistic(k * (mu - d)), EPS), 1 - EPS)
            log_l += y * math.log(p) + (1 - y) * math.log(1 - p)
        out.append(log_l)
    return out


def test_param_grid_shape_and_bounds():
    grid = param_grid()
    assert grid['mu'].shape == (67600,)
    assert grid['k'].shape == (67600,)
    assert pytest.approx(grid['mu'].min(), abs=1e-9) == 50
    assert pytest.approx(grid['mu'].max(), abs=1e-9) == 1000
    assert pytest.approx(grid['k'].min(), abs=1e-9) == 0.002
    assert pytest.approx(grid['k'].max(), abs=1e-9) == 0.04
    assert grid['gamma'].min() == 0
    assert pytest.approx(grid['gamma'].max(), abs=1e-9) == 0.3
    assert grid['lambda'].min() == 0
    assert pytest.approx(grid['lambda'].max(), abs=1e-9) == 0.3


def test_logistic_basic_properties():
    assert logistic(0) == pytest.approx(0.5)
    assert logistic(100) == pytest.approx(1.0, abs=1e-9)
    assert logistic(-100) == pytest.approx(0.0, abs=1e-9)


def test_normalize_handles_zero_sum():
    arr = np.array([0.0, 0.0, 0.0, 0.0])
    result = normalize(arr)
    assert np.allclose(result, [0.25, 0.25, 0.25, 0.25])


def test_normalize_normal_case_sums_to_one():
    arr = np.array([1.0, 2.0, 3.0])
    result = normalize(arr)
    assert result.sum() == pytest.approx(1.0)


def test_entropy_of_uniform_distribution():
    p = np.full(4, 0.25)
    assert entropy(p) == pytest.approx(2.0)  # log2(4) = 2


def test_entropy_of_certain_distribution_is_near_zero():
    p = np.array([1.0, 0.0, 0.0, 0.0])
    assert entropy(p) == pytest.approx(0.0, abs=1e-6)


def test_log_likelihood_array_matches_naive_reference():
    delays = [0, 250, 500, 750, 1000, 300]
    responses = [1, 1, 0, 0, 0, 1]

    vectorized = log_likelihood_array(np.array(delays), np.array(responses))
    naive = _naive_log_likelihood_array(delays, responses)

    assert np.allclose(vectorized, naive, rtol=1e-8, atol=1e-8)


def test_posterior_from_data_sums_to_one_and_correct_length():
    delays = [0, 500, 1000]
    responses = [1, 0, 0]
    posterior = posterior_from_data(np.array(delays), np.array(responses))
    assert posterior.shape == (67600,)
    assert posterior.sum() == pytest.approx(1.0)
    assert (posterior >= 0).all()


def test_posterior_favors_low_mu_when_all_responses_are_no():
    # If the participant always says "No" (didn't cause the movement),
    # posterior mass should shift toward lower mu (agency breaks down
    # sooner), which we can check via the posterior-weighted mean of mu.
    grid = param_grid()
    delays = [0, 100, 200, 300, 400, 500]
    responses = [0, 0, 0, 0, 0, 0]
    posterior = posterior_from_data(np.array(delays), np.array(responses))
    weighted_mu = float((posterior * grid['mu']).sum())
    assert weighted_mu < grid['mu'].mean()


def test_compute_eig_returns_finite_values_for_all_candidates():
    posterior = np.full(67600, 1.0 / 67600)
    eigs = compute_eig(CANDIDATE_DELAYS, posterior)
    assert eigs.shape == (len(CANDIDATE_DELAYS),)
    assert np.isfinite(eigs).all()


def test_select_next_delay_returns_a_candidate_value():
    posterior = np.full(67600, 1.0 / 67600)
    eigs = compute_eig(CANDIDATE_DELAYS, posterior)
    chosen = select_next_delay(CANDIDATE_DELAYS, eigs, history_counts={})
    assert chosen in [float(d) for d in CANDIDATE_DELAYS]


def test_select_next_delay_is_deterministic_with_seeded_rng():
    posterior = np.full(67600, 1.0 / 67600)
    eigs = compute_eig(CANDIDATE_DELAYS, posterior)
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    d1 = select_next_delay(CANDIDATE_DELAYS, eigs, history_counts={}, rng=rng1)
    d2 = select_next_delay(CANDIDATE_DELAYS, eigs, history_counts={}, rng=rng2)
    assert d1 == d2


def test_get_next_delay_level_uses_seed_delays_first():
    history = TrialHistory()
    state = ExperimentState()
    for expected_seed in SEED_DELAYS:
        next_delay = get_next_delay_level(history, state)
        assert next_delay == expected_seed
        history.add(
            {
                'task': 'core',
                'delayOriginal': next_delay,
                'interruptionResponse': 'y',
            }
        )


def test_get_next_delay_level_falls_back_to_ado_after_seeding():
    history = TrialHistory()
    state = ExperimentState()
    for i, seed in enumerate(SEED_DELAYS):
        history.add({'task': 'core', 'delayOriginal': seed, 'interruptionResponse': 'y' if i % 2 == 0 else 'n'})
    next_delay = get_next_delay_level(history, state)
    assert next_delay in [float(d) for d in CANDIDATE_DELAYS]


def test_get_agency_data_prepends_previous_trials_for_resumed_session():
    history = TrialHistory()
    history.add({'task': 'core', 'delayOriginal': 300, 'interruptionResponse': 'n'})
    state = ExperimentState()
    state.set_previous_trials([{'delay': 100, 'response': 'y', 'responseNumeric': 1}])

    agency_data = get_agency_data(history, state)
    assert len(agency_data) == 2
    assert agency_data[0]['delay'] == 100
    assert agency_data[1]['delay'] == 300
    assert agency_data[1]['responseNumeric'] == 0
