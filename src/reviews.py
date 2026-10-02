"""Player voice: what match-3 players say in Google Play reviews.

Each review is tagged with zero or more themes by keyword rules (transparent and
testable, no model needed). For each theme we report how often it comes up, the
average star rating of reviews that mention it, and whether it is mostly a
complaint (shows up in 1-2 star reviews) or a delight (shows up in 4-5 star reviews).
"""

import re

import numpy as np
import pandas as pd

# Theme -> regex. Order is the order themes are listed in outputs.
THEMES = {
    "Ads": r"\bads?\b|advert|commercials?\b",
    "Too hard / stuck": r"too hard|too difficult|impossible|stuck (?:on|at|in) (?:a |this |that |the |one )?(?:level|board|stage)|can'?t (?:pass|beat|win|get past)|unfair|rigged",
    "Lives & waiting": r"\blives\b|\blife\b|\benergy\b|\bwait(?:ing)?\b|\bhearts?\b|\btimer\b",
    "Prices & pay-to-win": r"pay to win|\bp2w\b|expensive|\bprices?\b|money|\bcoins?\b|\bgems?\b|\bpurchases?\b|\bspend",
    "Bugs & crashes": r"\bbugs?\b|\bbuggy\b|crash|glitch|freez|\blag(?:gy|s)?\b|won'?t load|not loading|\berror\b",
    "Lost progress": r"lost (?:my|all)|progress (?:is |was )?(?:gone|lost|reset)|\breset\b|start(?:ed)? over",
    "Rewards & boosters": r"\brewards?\b|\bboosters?\b|\bbonus\b|\bprizes?\b|\bgifts?\b|\bdaily\b",
    "Events & new content": r"\bevents?\b|\bupdates?\b|new levels?|\bcontent\b|\bseason|\btournaments?\b",
    "Friends & teams": r"\bfriends?\b|\bteams?\b|multiplayer|\bopponents?\b|\bpvp\b|\bclubs?\b|\bchat\b",
    "Fun & relaxing": r"\bfun\b|\brelax|addict|\blove\b|\benjoy|beautiful|\bcute\b|satisf",
}
_COMPILED = {t: re.compile(p, re.I) for t, p in THEMES.items()}


def tag(text: str) -> list[str]:
    """Themes mentioned in one review."""
    text = text if isinstance(text, str) else ""
    return [t for t, rx in _COMPILED.items() if rx.search(text)]


def tag_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """Add one boolean column per theme."""
    out = reviews.copy()
    text = out["review_text"].fillna("")
    for t, rx in _COMPILED.items():
        out[t] = text.str.contains(rx)
    out["sentiment"] = pd.cut(out["review_score"], [0, 2, 3, 5], labels=["Negative (1-2)", "Mixed (3)", "Positive (4-5)"])
    return out


def theme_summary(tagged: pd.DataFrame) -> pd.DataFrame:
    """Per theme: share of reviews, avg stars, share of negative vs positive reviews, and a verdict."""
    neg = tagged["review_score"] <= 2
    pos = tagged["review_score"] >= 4
    rows = []
    for t in THEMES:
        hit = tagged[t]
        neg_share, pos_share = hit[neg].mean(), hit[pos].mean()
        lift = neg_share / pos_share if pos_share else np.inf
        rows.append({
            "theme": t,
            "reviews": int(hit.sum()),
            "share_of_reviews": hit.mean(),
            "avg_stars": tagged.loc[hit, "review_score"].mean(),
            "share_of_negative": neg_share,
            "share_of_positive": pos_share,
            "negative_lift": lift,
            "verdict": "Pain point" if lift >= 1.5 else "Delight" if lift <= 0.67 else "Mixed",
        })
    return pd.DataFrame(rows).sort_values("negative_lift", ascending=False).reset_index(drop=True)


def by_game(tagged: pd.DataFrame) -> pd.DataFrame:
    """Avg stars and the top pain point per game: where a competitor is weak."""
    pains = [t for t in THEMES if t != "Fun & relaxing"]
    neg = tagged[tagged["review_score"] <= 2]
    g = tagged.groupby("game_name").agg(reviews=("review_score", "size"), avg_stars=("review_score", "mean"))
    g["share_negative"] = tagged.groupby("game_name")["review_score"].apply(lambda s: (s <= 2).mean())
    top = neg.groupby("game_name")[pains].mean()
    g["top_pain"] = top.idxmax(axis=1)
    g["top_pain_share_of_negative"] = top.max(axis=1)
    return g.sort_values("reviews", ascending=False).reset_index()


def quotes(tagged: pd.DataFrame, theme: str, n: int = 3, max_len: int = 160) -> list[str]:
    """Short, most-helpful real quotes for a theme (negative ones for pains, positive for delights)."""
    rows = tagged[tagged[theme]]
    rows = rows[rows["review_score"] >= 4] if theme == "Fun & relaxing" else rows[rows["review_score"] <= 2]
    rows = rows[rows["review_text"].str.len().between(40, max_len)]
    return rows.sort_values(["helpful_count", "review_date"], ascending=False)["review_text"].head(n).tolist()
