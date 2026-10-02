"""Experiment sizing: how many players an A/B test needs before it can detect a change."""

import math

from scipy import stats


def sample_size_two_proportions(p_control: float, p_variant: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Players per arm for a two-sided two-proportion z-test."""
    if p_control == p_variant:
        raise ValueError("the two rates must differ")
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    p_bar = (p_control + p_variant) / 2
    num = (z_a * math.sqrt(2 * p_bar * (1 - p_bar))
           + z_b * math.sqrt(p_control * (1 - p_control) + p_variant * (1 - p_variant))) ** 2
    return math.ceil(num / (p_variant - p_control) ** 2)


def days_to_run(n_per_arm: int, daily_new_players: float, arms: int = 2, share_in_test: float = 1.0) -> int:
    """Calendar days of new-player traffic needed to fill every arm."""
    return math.ceil(n_per_arm * arms / (daily_new_players * share_in_test))


if __name__ == "__main__":
    import json
    from pathlib import Path

    f = json.loads((Path(__file__).resolve().parents[1] / "outputs" / "findings.json").read_text())
    base = f["onboarding"]["returned_within_7d"]
    daily = f["window"]["new_players"] / 266
    print(f"Baseline 'returned within 7 days': {base:.2%}, ~{daily:,.0f} new players/day")
    for lift in (0.005, 0.01, 0.02, 0.03):
        n = sample_size_two_proportions(base, base + lift)
        print(f"  detect +{lift * 100:.1f} pts: {n:,} players per arm, {days_to_run(n, daily)} days at 100% of new players")
