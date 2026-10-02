"""Data regression suite: every number must match tests/regression_baseline.json.

One test case per value: headline KPIs, raw-file checksums and row counts, and the row
counts and column totals of every Power BI table. A failure names the exact value that
drifted. If the change is intended, run `python tests/baseline.py --update`.
"""

import json
import math

import pandas as pd
import pytest

from baseline import BASELINE, PBI, RAW, RAW_FILES, raw_rows, sha256
from conftest import needs_outputs, needs_raw

BASE = json.loads(BASELINE.read_text())

# Deterministic pipeline (the bootstrap is seeded), so values must match to float noise.
REL = 1e-9


@pytest.fixture(scope="module")
def kpi():
    k = pd.read_csv(PBI / "kpi_summary.csv")
    return {f"{r.area}.{r.metric}": float(r.value) for r in k.itertuples()}


def test_baseline_covers_at_least_100_values():
    assert sum(len(v) for v in BASE.values()) >= 100


@needs_outputs
@pytest.mark.parametrize("name", sorted(BASE["kpi"]))
def test_kpi_unchanged(kpi, name):
    assert name in kpi, f"{name} is no longer produced"
    assert math.isclose(kpi[name], BASE["kpi"][name], rel_tol=REL, abs_tol=1e-12), \
        f"{name}: baseline {BASE['kpi'][name]}, now {kpi[name]}"


@needs_outputs
def test_no_new_untracked_kpis(kpi):
    assert set(kpi) <= set(BASE["kpi"]), f"new KPIs not in baseline: {sorted(set(kpi) - set(BASE['kpi']))}"


@needs_raw
@pytest.mark.parametrize("name", sorted(RAW_FILES))
def test_raw_file_unchanged(name):
    assert sha256(RAW / name) == BASE["raw_sha256"][name], f"{name} differs from the pinned Kaggle version"


@needs_raw
@pytest.mark.parametrize("name", sorted(RAW_FILES))
def test_raw_row_count(name):
    assert raw_rows(name) == BASE["raw_rows"][name]


@needs_outputs
@pytest.mark.parametrize("name", sorted(BASE["export_rows"]))
def test_export_row_count(name):
    assert len(pd.read_csv(PBI / name)) == BASE["export_rows"][name]


@needs_outputs
@pytest.mark.parametrize("key", sorted(BASE["export_sums"]))
def test_export_column_total(key):
    file, col = key.split(":")
    total = float(pd.read_csv(PBI / file, usecols=[col])[col].sum())
    assert math.isclose(total, BASE["export_sums"][key], rel_tol=REL), f"{key}: baseline {BASE['export_sums'][key]}, now {total}"
