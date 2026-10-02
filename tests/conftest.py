import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"

needs_raw = pytest.mark.skipif(not (RAW / "auth_data.csv").exists(),
                               reason="raw data missing: python src/download_data.py")
needs_outputs = pytest.mark.skipif(not (OUT / "findings.json").exists(),
                                   reason="outputs missing: python src/run_analysis.py")

LAST = pd.Timestamp("2020-01-31")


@pytest.fixture
def toy():
    """Five players whose correct metrics are worked out by hand in the tests.

    uid 1  reg Jan 01  active days 0, 1, 7, 30, and day 35 (after LAST, must be ignored)
    uid 2  reg Jan 01  active days 0, 1, 2
    uid 3  reg Jan 01  active day 0 only
    uid 4  reg Jan 20  active days 0, 7, and day 12 (after LAST)
    uid 5  reg Jan 30  active days 0, 1
    """
    regs = pd.DataFrame({
        "uid": [1, 2, 3, 4, 5],
        "reg_date": pd.to_datetime(["2020-01-01"] * 3 + ["2020-01-20", "2020-01-30"]),
    })
    active = {1: [0, 1, 7, 30, 35], 2: [0, 1, 2], 3: [0], 4: [0, 7, 12], 5: [0, 1]}
    rows = [{"uid": u, "date": regs.set_index("uid").loc[u, "reg_date"] + pd.Timedelta(days=d),
             "logins": 1} for u, ds in active.items() for d in ds]
    return regs, pd.DataFrame(rows)


@pytest.fixture(scope="session")
def findings():
    return json.loads((OUT / "findings.json").read_text())
