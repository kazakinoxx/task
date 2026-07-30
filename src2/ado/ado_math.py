"""ADO math -- numpy-vectorized port of
src/modules/experiment/ado/adoMath.ts.

The JS version already recomputes the full 67,600-cell posterior from
scratch on every call (uniform log-prior, no persisted Bayesian state),
so vectorizing the grid with numpy changes only performance, not
semantics -- this is a legitimate "same math, better implementation"
rewrite rather than a literal loop transliteration. See
tests/test_ado_math.py for a naive-loop reference implementation used to
verify numerical equivalence.

Exact RNG draws are not reproduced (JS Math.random() vs. Python's
random/numpy PRNGs are different streams) -- what's preserved is the
EIG ranking/selection algorithm, not bit-identical sampled outcomes.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

SEED_DELAYS = [0, 250, 500, 750, 1000]
MAXDELAY = 1000
CANDIDATE_DELAYS = np.arange(0, MAXDELAY // 50 + 1) * 50  # 0..1000 step 50 -> 21 candidates
TEMP = 0.1
DIVERSITY_WEIGHT = 0.0
ALPHA = 0.0
EPS = 1e-9


def logistic(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def normalize(arr: np.ndarray) -> np.ndarray:
    """Port of `normalize` -- if the array sums to 0, falls back to a
    uniform distribution rather than dividing by zero (matches the JS
    `sum === 0 ? arr.map(() => 1 / arr.length) : ...` branch)."""
    total = arr.sum()
    if total == 0:
        return np.full_like(arr, 1.0 / len(arr))
    return arr / total


def entropy(p: np.ndarray) -> float:
    """Shannon entropy (base 2), port of `entropy`."""
    safe_p = np.maximum(p, EPS)
    return float(-(safe_p * np.log2(safe_p)).sum())


_CACHED_GRID: Optional[Dict[str, np.ndarray]] = None


def param_grid() -> Dict[str, np.ndarray]:
    """Port of PARAM_GRID() -- lazily built and cached at module scope,
    mirroring the JS `cachedGrid` memoization. Returns a dict of four
    flat (67600,) arrays: mu, k, gamma, lambda, built in the same
    mu -> k -> gamma -> lambda nested-loop order as the original (order
    is otherwise irrelevant to the vectorized math, but keeping it
    identical makes any index-level debugging against the JS version
    straightforward)."""
    global _CACHED_GRID
    if _CACHED_GRID is not None:
        return _CACHED_GRID

    mu_values = 50 + np.arange(20) * (950 / 19)
    k_values = 0.002 + np.arange(20) * ((0.04 - 0.002) / 19)
    gamma_values = np.arange(13) * 0.025
    lambda_values = np.arange(13) * 0.025

    mu_grid, k_grid, gamma_grid, lambda_grid = np.meshgrid(
        mu_values, k_values, gamma_values, lambda_values, indexing='ij'
    )
    _CACHED_GRID = {
        'mu': mu_grid.ravel(),
        'k': k_grid.ravel(),
        'gamma': gamma_grid.ravel(),
        'lambda': lambda_grid.ravel(),
    }
    return _CACHED_GRID


def p_yes_grid(delay: float) -> np.ndarray:
    """Port of pYesGrid -- P(Yes) for every grid cell at a given delay."""
    grid = param_grid()
    p = logistic(grid['k'] * (grid['mu'] - delay))
    p_full = grid['gamma'] + (1 - grid['gamma'] - grid['lambda']) * p
    return np.clip(p_full, EPS, 1 - EPS)


def log_likelihood_array(delays: np.ndarray, responses: np.ndarray) -> np.ndarray:
    """Port of logLikelihoodArray -- vectorized over both the grid
    (67600,) and the trial history (n,) via broadcasting."""
    grid = param_grid()
    delays = np.asarray(delays, dtype=float)
    responses = np.asarray(responses, dtype=float)

    p = logistic(grid['k'][:, None] * (grid['mu'][:, None] - delays[None, :]))
    p_full = grid['gamma'][:, None] + (1 - grid['gamma'][:, None] - grid['lambda'][:, None]) * p
    p_full = np.clip(p_full, EPS, 1 - EPS)

    y = responses[None, :]
    log_l = (y * np.log(p_full) + (1 - y) * np.log(1 - p_full)).sum(axis=1)
    return log_l


def posterior_from_data(
    delays: np.ndarray, responses: np.ndarray, log_prior: Optional[np.ndarray] = None
) -> np.ndarray:
    """Port of posteriorFromData -- recomputes the full posterior from
    scratch (uniform log-prior unless overridden), exactly as the JS
    version does on every call."""
    ll = log_likelihood_array(delays, responses)
    prior = log_prior if log_prior is not None else np.full(ll.shape, np.log(1.0 / len(ll)))
    log_post = ll + prior
    max_log = log_post.max()
    post_unnorm = np.exp(log_post - max_log)
    return normalize(post_unnorm)


def compute_eig(candidate_delays: np.ndarray, posterior: np.ndarray) -> np.ndarray:
    """Port of computeEIG -- expected information gain per candidate
    delay."""
    h_prior = entropy(posterior)
    eigs = np.empty(len(candidate_delays))
    for i, d in enumerate(candidate_delays):
        p_yes = p_yes_grid(d)
        p_r1 = float((posterior * p_yes).sum())
        p_r0 = 1 - p_r1

        post_r1 = normalize(posterior * p_yes)
        post_r0 = normalize(posterior * (1 - p_yes))

        h_r1 = entropy(post_r1)
        h_r0 = entropy(post_r0)

        eigs[i] = h_prior - (p_r1 * h_r1 + p_r0 * h_r0)
    return eigs


def select_next_delay(
    candidate_delays: np.ndarray,
    eigs: np.ndarray,
    history_counts: Dict[float, int],
    temp: float = TEMP,
    diversity_weight: float = DIVERSITY_WEIGHT,
    alpha: float = ALPHA,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Port of selectNextDelay -- softmax sampling over EIG-derived
    utility (diversity term is a no-op with the default weights, same as
    the original)."""
    counts = np.array([history_counts.get(float(d), 0) for d in candidate_delays])
    diversity_factor = 1.0 / (1.0 + alpha * counts)

    utility = eigs * (1 - diversity_weight + diversity_weight * diversity_factor)

    max_u = utility.max()
    probs = normalize(np.exp((utility - max_u) / max(temp, EPS)))

    r = rng.random() if rng is not None else np.random.random()
    cum = 0.0
    for i, p in enumerate(probs):
        cum += p
        if r <= cum:
            return float(candidate_delays[i])
    return float(candidate_delays[-1])
