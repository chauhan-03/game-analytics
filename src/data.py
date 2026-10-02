"""Download and load the two Kaggle datasets this project uses.

Gamelytics (debs2x/gamelytics-mobile-analytics-challenge)
    reg_data.csv   one row per player: registration timestamp
    auth_data.csv  one row per login: login timestamp
    ab_test.csv    one row per player in an offer-set A/B test: revenue, group

Cookie Cats (mursideyarkin/mobile-games-ab-testing-cookie-cats)
    cookie_cats.csv  one row per new player: which level the first progress gate
                     sits at (30 or 40), rounds played in 14 days, D1/D7 return

Play Market 2025 (dmytrobuhai/play-market-2025-1m-reviews-500-titles)
    games_info.csv     one row per game: name, Play Store categories, rating
    games_reviews.csv  one row per Google Play review: text, 1-5 stars, date

Versions are pinned so a rerun downloads exactly the data the findings came from.
"""

import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

DATASETS = {
    "debs2x/gamelytics-mobile-analytics-challenge/versions/2": [
        "reg_data.csv",
        "auth_data.csv",
        "ab_test.csv",
    ],
    "mursideyarkin/mobile-games-ab-testing-cookie-cats/versions/1": [
        "cookie_cats.csv",
    ],
    "dmytrobuhai/play-market-2025-1m-reviews-500-titles/versions/1": [
        "games_info.csv",
        "games_reviews.csv",
    ],
}


def download() -> None:
    """Fetch every dataset into data/raw. Public datasets need no Kaggle login."""
    import kagglehub

    RAW.mkdir(parents=True, exist_ok=True)
    for handle, files in DATASETS.items():
        source = Path(kagglehub.dataset_download(handle))
        for name in files:
            shutil.copy(source / name, RAW / name)
            print(f"  {name:<18} <- {handle}")


def _require(name: str) -> Path:
    path = RAW / name
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing. Run: python src/download_data.py")
    return path


def load_registrations() -> pd.DataFrame:
    """uid, reg_date (calendar day, UTC)."""
    df = pd.read_csv(_require("reg_data.csv"), sep=";")
    df["reg_date"] = pd.to_datetime(df["reg_ts"], unit="s").dt.normalize()
    return df[["uid", "reg_date"]]


def load_activity(since: str) -> pd.DataFrame:
    """One row per (uid, date) the player logged in, from `since` onward.

    Logins are collapsed to days: retention and DAU count days, not sessions.
    `logins` keeps the number of logins that day for engagement depth.
    """
    df = pd.read_csv(_require("auth_data.csv"), sep=";")
    df = df[df["auth_ts"] >= pd.Timestamp(since).timestamp()]
    df["date"] = pd.to_datetime(df["auth_ts"], unit="s").dt.normalize()
    return df.groupby(["uid", "date"]).size().rename("logins").reset_index()


def load_ab_test() -> pd.DataFrame:
    """user_id, revenue, testgroup ('a' = control offer set, 'b' = new offer set)."""
    return pd.read_csv(_require("ab_test.csv"), sep=";")


def load_cookie_cats() -> pd.DataFrame:
    """userid, version, sum_gamerounds, retention_1, retention_7."""
    return pd.read_csv(_require("cookie_cats.csv"))


def load_reviews(genre: str = "Match 3") -> pd.DataFrame:
    """Google Play reviews for games whose Play Store categories include `genre`."""
    info = pd.read_csv(_require("games_info.csv"))
    games = info[info["categories"].str.contains(genre, na=False)][["game_id", "game_name"]]
    reviews = pd.read_csv(_require("games_reviews.csv"), parse_dates=["review_date"])
    return reviews.merge(games, on="game_id")
