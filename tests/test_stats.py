"""The statistical tests, checked against scipy and against a naive bootstrap."""

import numpy as np
import pytest
from scipy.stats import chi2_contingency

from stats import bootstrap_arpu_diff, bootstrap_mean_diff, two_proportion_ztest


@pytest.mark.parametrize("sa, na, sb, nb", [
    (20034, 44700, 20119, 45489),   # Cookie Cats D1
    (8502, 44700, 8279, 45489),     # Cookie Cats D7
    (1928, 202103, 1805, 202667),   # offer-test conversion
    (50, 1000, 70, 1000),
    (5, 100, 5, 100),
    (900, 1000, 850, 1000),
])
def test_ztest_matches_chi_square(sa, na, sb, nb):
    """A pooled two-proportion z-test is the uncorrected 2x2 chi-square: z^2 == chi2."""
    r = two_proportion_ztest(sa, na, sb, nb)
    chi2, p, _, _ = chi2_contingency([[sa, na - sa], [sb, nb - sb]], correction=False)
    assert r["z"] ** 2 == pytest.approx(chi2, rel=1e-9)
    assert r["p_value"] == pytest.approx(p, rel=1e-6)
    assert r["ci_low"] <= r["diff"] <= r["ci_high"]


def test_ztest_identical_rates():
    r = two_proportion_ztest(10, 100, 10, 100)
    assert r["z"] == 0 and r["p_value"] == pytest.approx(1.0)


@pytest.mark.parametrize("shift", [0.0, 5.0, -3.0])
def test_bootstrap_mean_diff_recovers_shift(shift):
    a = np.random.default_rng(1).exponential(10, 3000)
    r = bootstrap_mean_diff(a, a + shift, n_boot=2000)
    assert r["diff"] == pytest.approx(shift)
    assert r["ci_low"] <= shift <= r["ci_high"]


def test_bootstrap_detects_large_difference():
    rng = np.random.default_rng(2)
    r = bootstrap_mean_diff(rng.normal(0, 1, 2000), rng.normal(1, 1, 2000), n_boot=2000)
    assert r["p_value"] < 0.001 and r["ci_low"] > 0


@pytest.mark.parametrize("seed", [11, 12])
def test_fast_arpu_bootstrap_matches_naive(seed):
    """The binomial shortcut must give the same interval as resampling every user."""
    rng = np.random.default_rng(seed)
    n_a, n_b = 3000, 3000
    users_a = np.where(rng.random(n_a) < 0.05, rng.exponential(100, n_a), 0.0)
    users_b = np.where(rng.random(n_b) < 0.04, rng.exponential(140, n_b), 0.0)

    fast = bootstrap_arpu_diff(users_a[users_a > 0], n_a, users_b[users_b > 0], n_b,
                               n_boot=4000, seed=seed)
    naive_rng = np.random.default_rng(seed + 100)
    naive = np.array([naive_rng.choice(users_b, n_b).mean() - naive_rng.choice(users_a, n_a).mean()
                      for _ in range(4000)])
    lo, hi = np.percentile(naive, [2.5, 97.5])
    width = hi - lo
    assert fast["diff"] == pytest.approx(users_b.mean() - users_a.mean())
    assert abs(fast["ci_low"] - lo) < 0.1 * width
    assert abs(fast["ci_high"] - hi) < 0.1 * width


def test_bootstrap_p_value_bounded():
    a = np.random.default_rng(3).normal(0, 1, 500)
    r = bootstrap_mean_diff(a, a.copy(), n_boot=500)
    assert 0 <= r["p_value"] <= 1
