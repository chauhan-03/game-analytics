"""The three statistical tests the A/B comparisons need, kept small and explicit."""

import numpy as np
from scipy import stats


def two_proportion_ztest(success_a: int, n_a: int, success_b: int, n_b: int) -> dict:
    """Is rate B different from rate A? Pooled two-sided z-test."""
    p_a, p_b = success_a / n_a, success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    se = np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se
    se_diff = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    return {
        "rate_a": p_a,
        "rate_b": p_b,
        "diff": p_b - p_a,
        "ci_low": p_b - p_a - 1.96 * se_diff,
        "ci_high": p_b - p_a + 1.96 * se_diff,
        "z": z,
        "p_value": 2 * stats.norm.sf(abs(z)),
    }


def bootstrap_mean_diff(a: np.ndarray, b: np.ndarray, n_boot: int = 5000, seed: int = 7) -> dict:
    """95% bootstrap CI for mean(b) - mean(a). Use for ARPPU and other small arrays."""
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = rng.choice(b, b.size).mean() - rng.choice(a, a.size).mean()
    return _summarise(b.mean() - a.mean(), diffs)


def bootstrap_arpu_diff(
    payer_rev_a: np.ndarray, n_a: int, payer_rev_b: np.ndarray, n_b: int,
    n_boot: int = 5000, seed: int = 7,
) -> dict:
    """95% bootstrap CI for ARPU(b) - ARPU(a) without materialising 200k-row samples.

    Resampling n users with replacement draws Binomial(n, payers/n) payers, then
    that many payer revenues with replacement; non-payers add zero. Same
    distribution as the naive bootstrap, a thousand times cheaper.
    """
    rng = np.random.default_rng(seed)

    def arpu_draws(rev: np.ndarray, n: int) -> np.ndarray:
        k = rng.binomial(n, rev.size / n, n_boot)
        return np.array([rng.choice(rev, ki).sum() for ki in k]) / n

    diffs = arpu_draws(payer_rev_b, n_b) - arpu_draws(payer_rev_a, n_a)
    observed = payer_rev_b.sum() / n_b - payer_rev_a.sum() / n_a
    return _summarise(observed, diffs)


def _summarise(observed: float, diffs: np.ndarray) -> dict:
    low, high = np.percentile(diffs, [2.5, 97.5])
    # Two-sided bootstrap p: how often the resampled difference lands across zero.
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"diff": observed, "ci_low": low, "ci_high": high, "p_value": min(p, 1.0)}
