"""The SQL in sql/ must give the same answers as the Python pipeline."""

import pandas as pd
import pytest

import sql_kpis
from conftest import needs_outputs, needs_raw


@pytest.fixture(scope="module")
def db():
    if not sql_kpis.DB.exists():
        sql_kpis.build()
    return sql_kpis.DB


@needs_raw
@needs_outputs
@pytest.mark.parametrize("n", [1, 3, 7, 14, 30])
def test_sql_retention_equals_python(db, findings, n):
    r = sql_kpis.run("01_retention_day_n", db).set_index("day_n")
    assert r.loc[n, "retention"] == pytest.approx(findings["retention"][f"d{n}"], abs=1e-6)


@needs_raw
@needs_outputs
@pytest.mark.parametrize("col", ["never_returned_30d", "returned_within_7d", "players"])
def test_sql_onboarding_equals_python(db, findings, col):
    r = sql_kpis.run("02_onboarding_never_returned", db).iloc[0]
    assert r[col] == pytest.approx(findings["onboarding"][col], abs=1e-6)


@needs_raw
@needs_outputs
def test_sql_dau_equals_python(db):
    sql = sql_kpis.run("03_daily_active_players", db)
    py = pd.read_csv(sql_kpis.data.ROOT / "outputs" / "powerbi" / "daily_activity.csv")
    merged = sql.merge(py, on="date", suffixes=("_sql", "_py"))
    assert len(merged) == len(py)
    assert (merged["dau_sql"] == merged["dau_py"]).all()
    assert (merged["new_players_sql"] == merged["new_players_py"]).all()


@needs_raw
@needs_outputs
@pytest.mark.parametrize("group", ["a", "b"])
@pytest.mark.parametrize("metric", ["players", "payers", "conversion", "revenue", "arpu", "arppu"])
def test_sql_offer_test_equals_python(db, findings, group, metric):
    r = sql_kpis.run("04_offer_test_summary", db).set_index("testgroup")
    assert r.loc[group, metric] == pytest.approx(findings["monetization"][f"{metric}_{group}"], rel=1e-6, abs=1e-6)


@needs_raw
@needs_outputs
@pytest.mark.parametrize("n", [1, 7])
def test_sql_gate_test_equals_python(db, findings, n):
    r = sql_kpis.run("05_gate_test_retention", db).set_index("version")
    t = findings["onboarding"]["gate_test"][f"d{n}"]
    assert r.loc["gate_30", f"d{n}_retention"] == pytest.approx(t["rate_a"], abs=1e-6)
    assert r.loc["gate_40", f"d{n}_retention"] == pytest.approx(t["rate_b"], abs=1e-6)


@needs_raw
def test_sql_churn_falls_with_early_rounds(db):
    r = sql_kpis.run("06_churn_by_early_rounds", db)
    assert r["churned_by_day7"].is_monotonic_decreasing
