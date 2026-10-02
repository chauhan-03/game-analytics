"""Regression baseline: a frozen snapshot of every number the pipeline produces.

    python tests/baseline.py            # print what would change, write nothing
    python tests/baseline.py --update   # accept the current outputs as the new baseline

Only update the baseline when a change in the numbers is intended (new data, a fixed
metric definition). tests/test_regression.py fails on any other drift.
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PBI = ROOT / "outputs" / "powerbi"
BASELINE = Path(__file__).with_name("regression_baseline.json")

RAW_FILES = {"reg_data.csv": ";", "auth_data.csv": ";", "ab_test.csv": ";", "cookie_cats.csv": ",",
             "games_info.csv": ",", "games_reviews.csv": ","}

# Column totals that pin each Power BI table's contents, not just its shape.
COLUMN_SUMS = {
    "daily_activity.csv": ["dau", "wau", "mau", "new_players"],
    "cohort_retention.csv": ["cohort_size", "retained"],
    "retention_curve.csv": ["eligible", "retained"],
    "new_players.csv": ["return_days", "logins"],
    "ab_test_players.csv": ["revenue"],
    "cookie_cats_players.csv": ["sum_gamerounds"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raw_rows(name: str) -> int:
    """Rows as a CSV parser sees them (review text contains line breaks, so lines != rows)."""
    return len(pd.read_csv(RAW / name, sep=RAW_FILES[name], usecols=[0]))


def snapshot() -> dict:
    kpi = pd.read_csv(PBI / "kpi_summary.csv")
    return {
        "kpi": {f"{r.area}.{r.metric}": float(r.value) for r in kpi.itertuples()},
        "raw_sha256": {name: sha256(RAW / name) for name in RAW_FILES},
        "raw_rows": {name: raw_rows(name) for name in RAW_FILES},
        "export_rows": {p.name: int(len(pd.read_csv(p))) for p in sorted(PBI.glob("*.csv"))},
        "export_sums": {f"{file}:{col}": float(pd.read_csv(PBI / file, usecols=[col])[col].sum())
                        for file, cols in COLUMN_SUMS.items() for col in cols},
    }


def diff(old: dict, new: dict) -> list[str]:
    out = []
    for section in new:
        for key in sorted(set(old.get(section, {})) | set(new[section])):
            a, b = old.get(section, {}).get(key), new[section].get(key)
            if a != b:
                out.append(f"{section}[{key}]: {a} -> {b}")
    return out


if __name__ == "__main__":
    current = snapshot()
    previous = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    changes = diff(previous, current)
    print("\n".join(changes) if changes else "No changes from the baseline.")
    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"Baseline written: {sum(len(v) for v in current.values())} values -> {BASELINE.name}")
