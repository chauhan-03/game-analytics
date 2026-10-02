"""python src/sql_kpis.py

Loads the raw data into a SQLite database (data/game.db) and runs every query in sql/,
writing each result to outputs/sql/<query>.csv. The queries are plain SQL, so they
port to BigQuery, Postgres or Snowflake with only the date helpers changed.
tests/test_sql.py checks that the SQL answers equal the Python pipeline's.
"""

import sqlite3
import time

import pandas as pd

import data

DB = data.ROOT / "data" / "game.db"
SQL = data.ROOT / "sql"
OUT = data.ROOT / "outputs" / "sql"
LOGINS_SINCE = "2019-12-01"   # enough history for 2020 cohorts and trailing windows


def build(path=DB) -> None:
    """(Re)create the database from data/raw."""
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as con:
        pd.read_csv(data.RAW / "reg_data.csv", sep=";").to_sql("registrations", con, index=False)
        auth = pd.read_csv(data.RAW / "auth_data.csv", sep=";")
        auth[auth["auth_ts"] >= pd.Timestamp(LOGINS_SINCE).timestamp()].to_sql("logins", con, index=False, chunksize=200_000)
        data.load_ab_test().to_sql("ab_test", con, index=False)
        data.load_cookie_cats().to_sql("cookie_cats", con, index=False)
        con.executescript("""
            CREATE INDEX idx_reg_uid ON registrations(uid);
            CREATE INDEX idx_log_uid ON logins(uid);
            CREATE INDEX idx_log_ts ON logins(auth_ts);
        """)


def run(name: str, path=DB) -> pd.DataFrame:
    """Run sql/<name>.sql and return the result."""
    with sqlite3.connect(path) as con:
        return pd.read_sql_query((SQL / f"{name}.sql").read_text(), con)


def queries() -> list[str]:
    return sorted(p.stem for p in SQL.glob("*.sql"))


if __name__ == "__main__":
    t0 = time.time()
    if not DB.exists():
        print("Building data/game.db ...")
        build()
    OUT.mkdir(parents=True, exist_ok=True)
    for q in queries():
        df = run(q)
        df.to_csv(OUT / f"{q}.csv", index=False)
        print(f"\n-- {q}\n{df.head(8).to_string(index=False)}")
    print(f"\nDone in {time.time() - t0:.0f}s -> {OUT}")
