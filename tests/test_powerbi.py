"""measures.dax must only reference columns and KPI rows the pipeline actually exports."""

import re

import pandas as pd
import pytest

from conftest import OUT, ROOT, needs_outputs

DAX = (ROOT / "powerbi" / "measures.dax").read_text()
COLUMN_REFS = sorted(set(re.findall(r"\b([a-z_]+)\[([a-z_0-9]+)\]", DAX)))
KPI_REFS = sorted(set(re.findall(r'kpi_summary\[metric\] = "([^"]+)"', DAX)))


def test_dax_has_references():
    assert len(COLUMN_REFS) > 10 and KPI_REFS


@needs_outputs
@pytest.mark.parametrize("table, column", COLUMN_REFS)
def test_dax_column_exists(table, column):
    header = pd.read_csv(OUT / "powerbi" / f"{table}.csv", nrows=0)
    assert column in header.columns


@needs_outputs
@pytest.mark.parametrize("metric", KPI_REFS)
def test_dax_kpi_row_exists(metric):
    k = pd.read_csv(OUT / "powerbi" / "kpi_summary.csv")
    assert metric in set(k["metric"])
