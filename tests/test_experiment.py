import pytest

from experiment import days_to_run, sample_size_two_proportions


@pytest.mark.parametrize("p1, p2, expected", [
    (0.10, 0.12, 3841),    # standard textbook/calculator value for these inputs
    (0.50, 0.55, 1565),
    (0.20, 0.25, 1094),
])
def test_sample_size_matches_reference(p1, p2, expected):
    assert sample_size_two_proportions(p1, p2) == pytest.approx(expected, abs=3)


def test_smaller_effects_need_more_players():
    assert sample_size_two_proportions(0.24, 0.245) > sample_size_two_proportions(0.24, 0.25)


def test_more_power_needs_more_players():
    assert sample_size_two_proportions(0.24, 0.25, power=0.9) > sample_size_two_proportions(0.24, 0.25, power=0.8)


def test_days_to_run():
    assert days_to_run(10_000, 1_000) == 20
    assert days_to_run(10_000, 1_000, share_in_test=0.5) == 40


def test_equal_rates_rejected():
    with pytest.raises(ValueError):
        sample_size_two_proportions(0.2, 0.2)
