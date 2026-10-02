"""KPI definitions. Every number in the findings and the Power BI exports comes from here.

Conventions
- A player is "active" on a calendar day if they logged in at least once that day.
- day_n is whole calendar days since registration; registration day is day 0.
- Day-N retention is the share of players active on exactly day N. A player only
  counts toward Day-N once N full days have passed since they registered, so
  recent cohorts never drag a rate down just because they have not had time.
"""

import numpy as np
import pandas as pd

RETENTION_DAYS = (1, 3, 7, 14, 30)
SEGMENTS = ["One-and-done", "Tried it", "Regular", "Core"]


# --------------------------------------------------------------------------- retention

def player_days(cohort: pd.DataFrame, activity: pd.DataFrame, last_date: pd.Timestamp) -> pd.DataFrame:
    """Activity of `cohort` players up to last_date, with day_n since registration."""
    days = activity[activity["date"] <= last_date].merge(cohort[["uid", "reg_date"]], on="uid")
    days["day_n"] = (days["date"] - days["reg_date"]).dt.days
    return days


def retention_curve(cohort: pd.DataFrame, days: pd.DataFrame, last_date: pd.Timestamp,
                    max_day: int = 30) -> pd.DataFrame:
    """Day-N retention for N = 1..max_day across the whole cohort."""
    active_on = days[days["day_n"].between(1, max_day)].groupby("day_n").size()
    rows = []
    for n in range(1, max_day + 1):
        eligible = int((cohort["reg_date"] <= last_date - pd.Timedelta(days=n)).sum())
        # (uid, date) is unique and days stop at last_date, so every row on day n
        # belongs to a distinct eligible player.
        retained = int(active_on.get(n, 0))
        rows.append({"day_n": n, "eligible": eligible, "retained": retained,
                     "retention": retained / eligible if eligible else np.nan})
    return pd.DataFrame(rows)


def cohort_retention(cohort: pd.DataFrame, days: pd.DataFrame, last_date: pd.Timestamp,
                     day_list=RETENTION_DAYS) -> pd.DataFrame:
    """Weekly registration cohorts x Day-N retention, long format.

    A cell is left empty (NaN) until every player in the cohort has reached day N.
    """
    weeks = cohort.assign(cohort_week=cohort["reg_date"].dt.to_period("W-SUN").dt.start_time)
    size = weeks.groupby("cohort_week").size()
    last_reg = weeks.groupby("cohort_week")["reg_date"].max()
    hits = (days[days["day_n"].isin(day_list)]
            .merge(weeks[["uid", "cohort_week"]], on="uid")
            .groupby(["cohort_week", "day_n"]).size())

    rows = []
    for week, n_players in size.items():
        for n in day_list:
            complete = last_reg[week] + pd.Timedelta(days=n) <= last_date
            retained = int(hits.get((week, n), 0))
            rows.append({"cohort_week": week, "day_n": n, "cohort_size": int(n_players),
                         "retained": retained if complete else np.nan,
                         "retention": retained / n_players if complete else np.nan})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- onboarding

def new_player_profile(cohort: pd.DataFrame, days: pd.DataFrame, last_date: pd.Timestamp,
                       window: int = 30) -> pd.DataFrame:
    """One row per player who has had a full `window` days since registering."""
    mature = cohort[cohort["reg_date"] <= last_date - pd.Timedelta(days=window)]
    early = days[days["uid"].isin(mature["uid"]) & days["day_n"].between(0, window)]
    returns = early[early["day_n"] >= 1]

    profile = mature.set_index("uid")[["reg_date"]].copy()
    profile["return_days"] = returns.groupby("uid").size()
    profile["logins"] = early.groupby("uid")["logins"].sum()
    profile["first_return_day"] = returns.groupby("uid")["day_n"].min()
    for n in (1, 7, 30):
        profile[f"active_d{n}"] = profile.index.isin(returns.loc[returns["day_n"] == n, "uid"])
    profile = profile.fillna({"return_days": 0, "logins": 0})
    profile[["return_days", "logins"]] = profile[["return_days", "logins"]].astype(int)
    profile["segment"] = segment(profile["return_days"])
    return profile.reset_index()


def segment(return_days: pd.Series) -> pd.Series:
    """Bucket players by how many of their first 30 days they came back on.

    Cut-offs follow this data: no player returns on more than 13 of 30 days,
    so 8+ return days is the top ~4% and the natural "core".
    """
    return pd.cut(return_days, bins=[-1, 0, 3, 7, 30], labels=SEGMENTS).astype(str)


def onboarding_summary(profile: pd.DataFrame) -> dict:
    returned = profile["first_return_day"].notna()
    return {
        "players": len(profile),
        "never_returned_30d": 1 - returned.mean(),
        "returned_within_7d": (profile["first_return_day"] <= 7).mean(),
        "returners_back_on_d1": (profile.loc[returned, "first_return_day"] == 1).mean(),
        "median_first_return_day": profile.loc[returned, "first_return_day"].median(),
    }


def first_return_distribution(profile: pd.DataFrame) -> pd.DataFrame:
    """When do players come back for the first time? Day 1..30 and 'never'."""
    s = profile["first_return_day"].fillna(-1).astype(int)
    out = s.value_counts().sort_index().rename("players").reset_index()
    out.columns = ["first_return_day", "players"]
    out["share"] = out["players"] / len(profile)
    out["cumulative_share"] = out["share"].where(out["first_return_day"] > 0, 0).cumsum()
    out["label"] = out["first_return_day"].map(lambda d: "Never" if d < 0 else f"Day {d}")
    return out


# --------------------------------------------------------------------------- engagement

def daily_activity(activity: pd.DataFrame, regs: pd.DataFrame,
                   start: pd.Timestamp, last_date: pd.Timestamp) -> pd.DataFrame:
    """DAU, WAU, MAU, stickiness and new registrations per day from start to last_date.

    WAU/MAU are trailing 7/30-day unique players, so activity must reach back
    29 days before start.
    """
    act = activity[activity["date"] <= last_date].sort_values("date")
    dates = act["date"].to_numpy()
    uids = act["uid"].to_numpy()
    installs = regs.groupby("reg_date").size()
    per_day = act.groupby("date").agg(dau=("uid", "size"))

    rows = []
    for day in pd.date_range(start, last_date, freq="D"):
        def unique_since(days_back: int) -> int:
            lo = np.searchsorted(dates, np.datetime64(day - pd.Timedelta(days=days_back - 1)))
            hi = np.searchsorted(dates, np.datetime64(day), side="right")
            return np.unique(uids[lo:hi]).size

        rows.append({"date": day,
                     "dau": int(per_day["dau"].get(day, 0)),
                     "wau": unique_since(7), "mau": unique_since(30),
                     "new_players": int(installs.get(day, 0))})
    out = pd.DataFrame(rows)
    out["returning_players"] = out["dau"] - out["new_players"]
    out["stickiness"] = out["dau"] / out["mau"]
    return out


def segment_summary(profile: pd.DataFrame) -> pd.DataFrame:
    g = profile.groupby("segment").agg(players=("uid", "size"),
                                       avg_return_days=("return_days", "mean"),
                                       avg_logins=("logins", "mean"),
                                       total_logins=("logins", "sum"))
    g = g.reindex(SEGMENTS)
    g["share_of_players"] = g["players"] / g["players"].sum()
    g["share_of_logins"] = g["total_logins"] / g["total_logins"].sum()
    return g.reset_index()


# --------------------------------------------------------------------------- monetization

REVENUE_TIERS = [0, 1, 500, 2000, 10_000, np.inf]
REVENUE_TIER_LABELS = ["Non-payer", "1-499", "500-1,999", "2,000-9,999", "10,000+"]


def revenue_tier(revenue: pd.Series) -> pd.Series:
    return pd.cut(revenue, bins=REVENUE_TIERS, labels=REVENUE_TIER_LABELS, right=False).astype(str)


def monetization_summary(ab: pd.DataFrame) -> pd.DataFrame:
    def per_group(g: pd.DataFrame) -> pd.Series:
        rev = g["revenue"]
        payers = rev[rev > 0].sort_values(ascending=False)
        top_1pct = payers.head(max(1, len(payers) // 100)).sum()
        return pd.Series({
            "players": len(g),
            "payers": len(payers),
            "conversion": len(payers) / len(g),
            "revenue": rev.sum(),
            "arpu": rev.mean(),
            "arppu": payers.mean(),
            "median_payer_revenue": payers.median(),
            "top_1pct_payer_revenue_share": top_1pct / payers.sum(),
        })
    return ab.groupby("testgroup")[["revenue"]].apply(per_group).reset_index()


def tier_breakdown(ab: pd.DataFrame) -> pd.DataFrame:
    t = ab.assign(tier=revenue_tier(ab["revenue"]))
    g = t.groupby(["testgroup", "tier"]).agg(players=("revenue", "size"), revenue=("revenue", "sum"))
    g["share_of_group_revenue"] = g["revenue"] / g.groupby(level=0)["revenue"].transform("sum")
    g = g.reset_index()
    g["tier"] = pd.Categorical(g["tier"], REVENUE_TIER_LABELS, ordered=True)
    return g.sort_values(["testgroup", "tier"]).reset_index(drop=True)


# --------------------------------------------------------------------------- Cookie Cats

ROUND_BUCKETS = [0, 1, 10, 30, 40, 100, np.inf]
ROUND_BUCKET_LABELS = ["0", "1-9", "10-29", "30-39", "40-99", "100+"]


def rounds_bucket(rounds: pd.Series) -> pd.Series:
    return pd.cut(rounds, bins=ROUND_BUCKETS, labels=ROUND_BUCKET_LABELS, right=False).astype(str)


def early_progress(cc: pd.DataFrame) -> pd.DataFrame:
    """Per gate variant: retention plus how far players got in their first 14 days."""
    g = cc.groupby("version").agg(
        players=("userid", "size"),
        d1_retention=("retention_1", "mean"),
        d7_retention=("retention_7", "mean"),
        median_rounds=("sum_gamerounds", "median"),
        never_played=("sum_gamerounds", lambda s: (s == 0).mean()),
        under_10_rounds=("sum_gamerounds", lambda s: (s < 10).mean()),
        reached_30_rounds=("sum_gamerounds", lambda s: (s >= 30).mean()),
        reached_40_rounds=("sum_gamerounds", lambda s: (s >= 40).mean()),
    )
    return g.reset_index()


def d7_by_rounds(cc: pd.DataFrame) -> pd.DataFrame:
    """How Day-7 return rate climbs with first-two-weeks rounds played."""
    t = cc.assign(rounds_bucket=rounds_bucket(cc["sum_gamerounds"]))
    g = t.groupby(["rounds_bucket", "version"]).agg(players=("userid", "size"),
                                                    d1_retention=("retention_1", "mean"),
                                                    d7_retention=("retention_7", "mean"))
    g = g.reset_index()
    g["rounds_bucket"] = pd.Categorical(g["rounds_bucket"], ROUND_BUCKET_LABELS, ordered=True)
    return g.sort_values(["rounds_bucket", "version"]).reset_index(drop=True)
