"""Metric definitions checked against small inputs whose answers are worked out by hand."""

import numpy as np
import pandas as pd
import pytest

import metrics as m
from conftest import LAST


# --------------------------------------------------------------------------- retention

@pytest.mark.parametrize("day_n, eligible, retained", [
    (1, 5, 3),    # everyone registered by Jan 30; back on day 1: uids 1, 2, 5
    (2, 4, 1),    # uid 5 not eligible yet; back on day 2: uid 2
    (7, 4, 2),    # back on day 7: uids 1, 4
    (11, 4, 0),   # uid 4 reached day 11 on Jan 31 exactly, still eligible
    (12, 3, 0),   # uid 4's day-12 login is after LAST and must not count
    (30, 3, 1),   # only the Jan 1 players have had 30 days; uid 1 came back
])
def test_retention_curve_hand_counted(toy, day_n, eligible, retained):
    regs, activity = toy
    days = m.player_days(regs, activity, LAST)
    row = m.retention_curve(regs, days, LAST).set_index("day_n").loc[day_n]
    assert row["eligible"] == eligible
    assert row["retained"] == retained
    assert row["retention"] == pytest.approx(retained / eligible)


def test_player_days_drops_activity_after_last_date(toy):
    regs, activity = toy
    days = m.player_days(regs, activity, LAST)
    assert days["date"].max() <= LAST
    assert len(days) == len(activity) - 2


def test_retention_curve_never_exceeds_one(toy):
    regs, activity = toy
    curve = m.retention_curve(regs, m.player_days(regs, activity, LAST), LAST)
    assert curve["retention"].between(0, 1).all()


@pytest.mark.parametrize("week, day_n, expected", [
    ("2019-12-30", 1, 2 / 3),   # uids 1-3 registered Wed Jan 1; uids 1, 2 back on day 1
    ("2019-12-30", 7, 1 / 3),
    ("2019-12-30", 30, 1 / 3),  # Jan 1 + 30 = Jan 31 = LAST, so the cell is complete
    ("2020-01-20", 7, 1.0),
    ("2020-01-20", 14, None),   # Jan 20 + 14 is after LAST: incomplete, must be empty
    ("2020-01-27", 1, 1.0),
    ("2020-01-27", 3, None),
])
def test_cohort_retention_cells(toy, week, day_n, expected):
    regs, activity = toy
    cells = m.cohort_retention(regs, m.player_days(regs, activity, LAST), LAST)
    cell = cells.set_index(["cohort_week", "day_n"]).loc[(pd.Timestamp(week), day_n), "retention"]
    if expected is None:
        assert np.isnan(cell)
    else:
        assert cell == pytest.approx(expected)


# --------------------------------------------------------------------------- onboarding

@pytest.mark.parametrize("uid, return_days, first_return, d1, d7, d30, segment", [
    (1, 3, 1, True, True, True, "Tried it"),
    (2, 2, 1, True, False, False, "Tried it"),
    (3, 0, None, False, False, False, "One-and-done"),
])
def test_new_player_profile(toy, uid, return_days, first_return, d1, d7, d30, segment):
    regs, activity = toy
    profile = m.new_player_profile(regs, m.player_days(regs, activity, LAST), LAST).set_index("uid")
    row = profile.loc[uid]
    assert row["return_days"] == return_days
    assert (np.isnan(row["first_return_day"]) if first_return is None
            else row["first_return_day"] == first_return)
    assert (row["active_d1"], row["active_d7"], row["active_d30"]) == (d1, d7, d30)
    assert row["segment"] == segment


def test_profile_only_includes_players_with_full_window(toy):
    regs, activity = toy
    profile = m.new_player_profile(regs, m.player_days(regs, activity, LAST), LAST)
    assert set(profile["uid"]) == {1, 2, 3}


def test_onboarding_summary(toy):
    regs, activity = toy
    profile = m.new_player_profile(regs, m.player_days(regs, activity, LAST), LAST)
    s = m.onboarding_summary(profile)
    assert s["never_returned_30d"] == pytest.approx(1 / 3)
    assert s["returned_within_7d"] == pytest.approx(2 / 3)
    assert s["returners_back_on_d1"] == 1.0


def test_first_return_distribution_shares_sum_to_one(toy):
    regs, activity = toy
    profile = m.new_player_profile(regs, m.player_days(regs, activity, LAST), LAST)
    dist = m.first_return_distribution(profile)
    assert dist["share"].sum() == pytest.approx(1.0)
    assert dist.loc[dist["label"] == "Never", "players"].item() == 1


@pytest.mark.parametrize("return_days, expected", [
    (0, "One-and-done"),
    *[(d, "Tried it") for d in range(1, 4)],
    *[(d, "Regular") for d in range(4, 8)],
    *[(d, "Core") for d in range(8, 31)],
])
def test_segment_boundaries(return_days, expected):
    assert m.segment(pd.Series([return_days])).item() == expected


# --------------------------------------------------------------------------- engagement

@pytest.mark.parametrize("date, column, expected", [
    ("2020-01-01", "dau", 3),
    ("2020-01-01", "new_players", 3),
    ("2020-01-02", "wau", 3),
    ("2020-01-08", "dau", 1),
    ("2020-01-08", "wau", 2),   # Jan 2-8: uids 1 and 2
    ("2020-01-31", "mau", 4),   # Jan 2-31: everyone except uid 3
    ("2020-01-31", "dau", 2),   # uids 1 and 5
    ("2020-01-31", "returning_players", 2),
])
def test_daily_activity(toy, date, column, expected):
    regs, activity = toy
    daily = m.daily_activity(activity, regs, pd.Timestamp("2020-01-01"), LAST).set_index("date")
    assert daily.loc[pd.Timestamp(date), column] == expected


def test_daily_activity_stickiness_bounded(toy):
    regs, activity = toy
    daily = m.daily_activity(activity, regs, pd.Timestamp("2020-01-01"), LAST)
    assert (daily["dau"] <= daily["wau"]).all() and (daily["wau"] <= daily["mau"]).all()
    assert daily["stickiness"].between(0, 1).all()


# --------------------------------------------------------------------------- monetization

@pytest.fixture
def toy_ab():
    return pd.DataFrame({"user_id": range(10),
                         "revenue": [0, 0, 0, 100, 300, 0, 0, 0, 0, 1000],
                         "testgroup": list("aaaaa") + list("bbbbb")})


@pytest.mark.parametrize("group, metric, expected", [
    ("a", "players", 5), ("a", "payers", 2), ("a", "conversion", 0.4),
    ("a", "arpu", 80), ("a", "arppu", 200), ("a", "median_payer_revenue", 200),
    ("b", "players", 5), ("b", "payers", 1), ("b", "conversion", 0.2),
    ("b", "arpu", 200), ("b", "arppu", 1000),
])
def test_monetization_summary(toy_ab, group, metric, expected):
    s = m.monetization_summary(toy_ab).set_index("testgroup")
    assert s.loc[group, metric] == pytest.approx(expected)


def test_tier_shares_sum_to_one_per_group(toy_ab):
    t = m.tier_breakdown(toy_ab)
    assert t.groupby("testgroup")["share_of_group_revenue"].sum().tolist() == pytest.approx([1, 1])


@pytest.mark.parametrize("revenue, tier", [
    (0, "Non-payer"), (1, "1-499"), (499, "1-499"), (500, "500-1,999"), (1999, "500-1,999"),
    (2000, "2,000-9,999"), (9999, "2,000-9,999"), (10_000, "10,000+"), (37_433, "10,000+"),
])
def test_revenue_tier_boundaries(revenue, tier):
    assert m.revenue_tier(pd.Series([revenue])).item() == tier


# --------------------------------------------------------------------------- Cookie Cats

@pytest.mark.parametrize("rounds, bucket", [
    (0, "0"), (1, "1-9"), (9, "1-9"), (10, "10-29"), (29, "10-29"), (30, "30-39"),
    (39, "30-39"), (40, "40-99"), (99, "40-99"), (100, "100+"), (49_854, "100+"),
])
def test_rounds_bucket_boundaries(rounds, bucket):
    assert m.rounds_bucket(pd.Series([rounds])).item() == bucket


def test_early_progress():
    cc = pd.DataFrame({"userid": range(4), "version": ["gate_30"] * 2 + ["gate_40"] * 2,
                       "sum_gamerounds": [0, 50, 5, 35],
                       "retention_1": [False, True, True, True],
                       "retention_7": [False, True, False, False]})
    p = m.early_progress(cc).set_index("version")
    assert p.loc["gate_30", "never_played"] == 0.5
    assert p.loc["gate_30", "d7_retention"] == 0.5
    assert p.loc["gate_40", "reached_30_rounds"] == 0.5
    assert p.loc["gate_40", "reached_40_rounds"] == 0.0
