"""Checks on the real Kaggle data and on the outputs the pipeline produced from it.

The cross-checks recompute headline numbers straight from the raw CSVs in the
plainest way possible and compare against findings.json, so a bug in
metrics.py cannot hide behind the same bug in its own test.
"""

import numpy as np
import pandas as pd
import pytest

from conftest import OUT, RAW, needs_outputs, needs_raw

LAST = pd.Timestamp("2020-09-22")


@pytest.fixture(scope="module")
def raw():
    reg = pd.read_csv(RAW / "reg_data.csv", sep=";")
    auth = pd.read_csv(RAW / "auth_data.csv", sep=";")
    ab = pd.read_csv(RAW / "ab_test.csv", sep=";")
    cc = pd.read_csv(RAW / "cookie_cats.csv")
    return reg, auth, ab, cc


# --------------------------------------------------------------------------- data quality

QUALITY_CHECKS = {
    "reg has 1M players": lambda reg, auth, ab, cc: len(reg) == 1_000_000,
    "reg uid unique": lambda reg, auth, ab, cc: reg["uid"].is_unique,
    "reg no nulls": lambda reg, auth, ab, cc: reg.notna().all().all(),
    "auth no nulls": lambda reg, auth, ab, cc: auth.notna().all().all(),
    "auth no duplicate rows": lambda reg, auth, ab, cc: not auth.duplicated().any(),
    "every login belongs to a registered player":
        lambda reg, auth, ab, cc: auth["uid"].isin(reg["uid"]).all(),
    "no login before registration":
        lambda reg, auth, ab, cc: (auth.merge(reg, on="uid").eval("auth_ts >= reg_ts")).all(),
    "every player logs in at registration":
        lambda reg, auth, ab, cc: auth.merge(reg, on="uid").eval("auth_ts == reg_ts").sum() == len(reg),
    "data ends 2020-09-23": lambda reg, auth, ab, cc:
        pd.to_datetime(auth["auth_ts"].max(), unit="s").date() == pd.Timestamp("2020-09-23").date(),
    "ab user_id unique": lambda reg, auth, ab, cc: ab["user_id"].is_unique,
    "ab groups are a and b": lambda reg, auth, ab, cc: set(ab["testgroup"]) == {"a", "b"},
    "ab groups balanced within 1%": lambda reg, auth, ab, cc:
        abs(ab["testgroup"].value_counts(normalize=True)["a"] - 0.5) < 0.01,
    "ab revenue non-negative": lambda reg, auth, ab, cc: (ab["revenue"] >= 0).all(),
    "cookie userid unique": lambda reg, auth, ab, cc: cc["userid"].is_unique,
    "cookie versions": lambda reg, auth, ab, cc: set(cc["version"]) == {"gate_30", "gate_40"},
    "cookie rounds non-negative": lambda reg, auth, ab, cc: (cc["sum_gamerounds"] >= 0).all(),
    "cookie retention is boolean": lambda reg, auth, ab, cc:
        cc["retention_1"].dtype == bool and cc["retention_7"].dtype == bool,
    "cookie groups balanced within 1%": lambda reg, auth, ab, cc:
        abs(cc["version"].value_counts(normalize=True)["gate_30"] - 0.5) < 0.01,
}


@needs_raw
@pytest.mark.parametrize("name", QUALITY_CHECKS)
def test_data_quality(raw, name):
    assert QUALITY_CHECKS[name](*raw), name


# --------------------------------------------------------------------------- cross-checks

@needs_raw
@needs_outputs
@pytest.mark.parametrize("n", [1, 3, 7, 14, 30])
def test_retention_matches_naive_recount(raw, findings, n):
    reg, auth, _, _ = raw
    reg = reg.assign(reg_date=pd.to_datetime(reg["reg_ts"], unit="s").dt.normalize())
    cohort = reg[reg["reg_date"].between("2020-01-01", LAST - pd.Timedelta(days=n))]
    target = set(zip(cohort["uid"], cohort["reg_date"] + pd.Timedelta(days=n)))
    logins = auth[auth["uid"].isin(cohort["uid"])]
    login_days = set(zip(logins["uid"], pd.to_datetime(logins["auth_ts"], unit="s").dt.normalize()))
    naive = len(target & login_days) / len(cohort)
    assert findings["retention"][f"d{n}"] == pytest.approx(naive, abs=1e-12)


@needs_raw
@needs_outputs
@pytest.mark.parametrize("group", ["a", "b"])
@pytest.mark.parametrize("metric", ["conversion", "arpu", "arppu"])
def test_monetization_matches_raw(raw, findings, group, metric):
    _, _, ab, _ = raw
    rev = ab.loc[ab["testgroup"] == group, "revenue"]
    expected = {"conversion": (rev > 0).mean(), "arpu": rev.mean(), "arppu": rev[rev > 0].mean()}[metric]
    assert findings["monetization"][f"{metric}_{group}"] == pytest.approx(expected)


@needs_raw
@needs_outputs
@pytest.mark.parametrize("n", [1, 7])
def test_gate_test_rates_match_raw(raw, findings, n):
    _, _, _, cc = raw
    rates = cc.groupby("version")[f"retention_{n}"].mean()
    t = findings["onboarding"]["gate_test"][f"d{n}"]
    assert t["rate_a"] == pytest.approx(rates["gate_30"])
    assert t["rate_b"] == pytest.approx(rates["gate_40"])


@needs_raw
@needs_outputs
def test_dau_on_last_day_matches_raw(raw):
    _, auth, _, _ = raw
    dates = pd.to_datetime(auth["auth_ts"], unit="s").dt.normalize()
    expected = auth.loc[dates == LAST, "uid"].nunique()
    daily = pd.read_csv(OUT / "powerbi" / "daily_activity.csv", parse_dates=["date"])
    assert daily.set_index("date").loc[LAST, "dau"] == expected


# --------------------------------------------------------------------------- outputs

POWERBI_COLUMNS = {
    "daily_activity.csv": {"date", "dau", "wau", "mau", "new_players", "returning_players", "stickiness"},
    "cohort_retention.csv": {"cohort_week", "day_n", "cohort_size", "retained", "retention"},
    "retention_curve.csv": {"day_n", "eligible", "retained", "retention"},
    "new_players.csv": {"uid", "reg_date", "return_days", "logins", "first_return_day",
                        "active_d1", "active_d7", "active_d30", "segment"},
    "ab_test_players.csv": {"user_id", "revenue", "testgroup", "is_payer", "revenue_tier"},
    "cookie_cats_players.csv": {"userid", "version", "sum_gamerounds", "retention_1",
                                "retention_7", "rounds_bucket"},
    "kpi_summary.csv": {"area", "metric", "value"},
}


@needs_outputs
@pytest.mark.parametrize("file, columns", POWERBI_COLUMNS.items())
def test_powerbi_table_schema(file, columns):
    df = pd.read_csv(OUT / "powerbi" / file)
    assert columns <= set(df.columns)
    assert len(df) > 0


@needs_outputs
@pytest.mark.parametrize("key", ["d1", "d3", "d7", "d14", "d30", "peak_retention"])
def test_retention_findings_are_rates(findings, key):
    assert 0 < findings["retention"][key] < 1


@needs_outputs
def test_cohort_cells_are_rates():
    c = pd.read_csv(OUT / "powerbi" / "cohort_retention.csv")
    assert c["retention"].between(0, 1).all()
    assert (c["retained"] <= c["cohort_size"]).all()


@needs_outputs
def test_segment_shares_sum_to_one(findings):
    seg = findings["engagement"]["segments"]
    assert sum(s["share_of_players"] for s in seg.values()) == pytest.approx(1)
    assert sum(s["share_of_logins"] for s in seg.values()) == pytest.approx(1)


@needs_outputs
def test_kpi_summary_values_are_finite():
    k = pd.read_csv(OUT / "powerbi" / "kpi_summary.csv")
    assert np.isfinite(k["value"]).all()


@needs_outputs
@pytest.mark.parametrize("chart", ["retention_curve", "cohort_heatmap", "first_return_day",
                                   "cookie_cats_d7_by_rounds", "dau_mau_stickiness",
                                   "player_segments", "ab_payer_revenue", "ab_revenue_by_tier"])
def test_chart_written(chart):
    path = OUT / "charts" / f"{chart}.png"
    assert path.exists() and path.stat().st_size > 10_000
