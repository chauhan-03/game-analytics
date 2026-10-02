"""Review theme rules, checked on hand-written examples, plus sanity checks on the real reviews."""

import pandas as pd
import pytest

import reviews as rv
from conftest import RAW

needs_reviews = pytest.mark.skipif(not (RAW / "games_reviews.csv").exists(),
                                   reason="reviews missing: python src/download_data.py")


@pytest.mark.parametrize("text, theme", [
    ("Way too many ads after every level", "Ads"),
    ("an advert pops up all the time", "Ads"),
    ("I'm stuck on level 245 for a week", "Too hard / stuck"),
    ("this level is impossible without boosters", "Too hard / stuck"),
    ("no lives left, have to wait 30 minutes", "Lives & waiting"),
    ("everything costs coins, pure pay to win", "Prices & pay-to-win"),
    ("way too expensive to keep playing", "Prices & pay-to-win"),
    ("keeps crashing after the update", "Bugs & crashes"),
    ("the game freezes on the loading screen", "Bugs & crashes"),
    ("I lost all my progress when I changed phones", "Lost progress"),
    ("love the daily rewards and boosters", "Rewards & boosters"),
    ("the new event is great", "Events & new content"),
    ("I play with my friends in a team", "Friends & teams"),
    ("so relaxing and fun", "Fun & relaxing"),
])
def test_theme_detected(text, theme):
    assert theme in rv.tag(text)


@pytest.mark.parametrize("text, theme", [
    ("The game is stuck on the loading screen", "Too hard / stuck"),   # a bug, not difficulty
    ("I downloaded it yesterday", "Ads"),                                # 'downloaded' is not 'ad'
    ("my wife likes it", "Lives & waiting"),                             # 'wife' is not 'life'
    ("great graphics", "Fun & relaxing"),
])
def test_theme_not_detected(text, theme):
    assert theme not in rv.tag(text)


def test_theme_summary_verdicts():
    df = pd.DataFrame({"review_text": ["too many ads"] * 4 + ["fun game"] * 4,
                       "review_score": [1, 1, 2, 5, 5, 5, 4, 1]})
    s = rv.theme_summary(rv.tag_reviews(df)).set_index("theme")
    assert s.loc["Ads", "verdict"] == "Pain point"
    assert s.loc["Fun & relaxing", "verdict"] == "Delight"
    assert s.loc["Ads", "reviews"] == 4


@needs_reviews
def test_real_reviews_loaded():
    r = rv.tag_reviews(__import__("data").load_reviews())
    assert r["game_name"].nunique() >= 5
    assert r["review_score"].between(1, 5).all()
    assert len(r) > 10_000
