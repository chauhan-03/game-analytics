"""python src/run_analysis.py

Reads data/raw, writes:
    outputs/powerbi/*.csv   tables the Power BI dashboard is built on
    outputs/charts/*.png    the charts referenced in the README
    outputs/findings.md     every headline number, regenerated on each run
    outputs/findings.json   the same numbers, machine-readable (tests read this)
"""

import json
import os
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

import data
import metrics as m
import powerbi_project
import reviews as rv
from stats import bootstrap_arpu_diff, bootstrap_mean_diff, two_proportion_ztest

OUT = data.ROOT / "outputs"
PBI = OUT / "powerbi"
CHARTS = OUT / "charts"
DASHBOARD_TEMPLATE = data.ROOT / "dashboard" / "template.html"
DASHBOARD = data.ROOT / "docs" / "index.html"   # docs/ so GitHub Pages can serve it

# The last login in the data is part-way through 2020-09-23, so the last full day is the 22nd.
LAST_DATE = pd.Timestamp("2020-09-22")
COHORT_START = pd.Timestamp("2020-01-01")

COLORS = {"a": "#4C72B0", "b": "#DD8452", "gate_30": "#4C72B0", "gate_40": "#DD8452",
          "main": "#4C72B0", "muted": "#9AA5B1"}


def main() -> None:
    t0 = time.time()
    for d in (PBI, CHARTS):
        d.mkdir(parents=True, exist_ok=True)

    print("Loading data ...")
    regs = data.load_registrations()
    activity = data.load_activity(since=str(COHORT_START - pd.Timedelta(days=29)))
    ab = data.load_ab_test()
    cc = data.load_cookie_cats()

    cohort = regs[regs["reg_date"].between(COHORT_START, LAST_DATE)]
    days = m.player_days(cohort, activity, LAST_DATE)

    print("Retention ...")
    curve = m.retention_curve(cohort, days, LAST_DATE)
    cohorts = m.cohort_retention(cohort, days, LAST_DATE)

    print("Onboarding ...")
    profile = m.new_player_profile(cohort, days, LAST_DATE)
    onboarding = m.onboarding_summary(profile)
    first_return = m.first_return_distribution(profile)
    progress = m.early_progress(cc)
    d7_rounds = m.d7_by_rounds(cc)
    gate = {
        f"d{n}": two_proportion_ztest(
            *_successes(cc, "gate_30", f"retention_{n}"), *_successes(cc, "gate_40", f"retention_{n}"))
        for n in (1, 7)
    }

    print("Engagement ...")
    daily = m.daily_activity(activity, regs, COHORT_START, LAST_DATE)
    segments = m.segment_summary(profile)

    print("Monetization ...")
    money = m.monetization_summary(ab)
    tiers = m.tier_breakdown(ab)
    ab_tests = monetization_tests(ab)

    print("Player voice (reviews) ...")
    tagged = rv.tag_reviews(data.load_reviews())
    themes = rv.theme_summary(tagged)
    review_games = rv.by_game(tagged)

    findings = build_findings(curve, cohorts, onboarding, first_return, progress, gate,
                              daily, segments, money, ab_tests, cohort, profile)

    findings["player_voice"] = {
        "reviews": int(len(tagged)),
        "games": int(tagged["game_name"].nunique()),
        "avg_stars": float(tagged["review_score"].mean()),
        "share_negative": float((tagged["review_score"] <= 2).mean()),
        **{f"themes.{r.theme}.share_of_reviews": float(r.share_of_reviews) for r in themes.itertuples()},
        **{f"themes.{r.theme}.negative_lift": float(r.negative_lift) for r in themes.itertuples()},
    }

    print("Writing Power BI tables ...")
    export_powerbi(curve, cohorts, profile, daily, ab, cc, findings)
    themes.to_csv(PBI / "review_themes.csv", index=False)
    review_games.to_csv(PBI / "review_games.csv", index=False)

    (data.ROOT / "coach-proxy" / "src").mkdir(parents=True, exist_ok=True)
    (data.ROOT / "coach-proxy" / "src" / "facts.json").write_text(
        json.dumps({"facts": coach_facts(findings, segments, progress)}, indent=2) + "\n")

    print("Building dashboard ...")
    export_dashboard(findings, curve, cohorts, first_return, segments, progress, d7_rounds,
                     daily, money, tiers, ab)

    print("Building Power BI project ...")
    powerbi_project.build()

    print("Drawing charts ...")
    draw_charts(curve, cohorts, first_return, d7_rounds, daily, segments, ab, tiers)

    (OUT / "findings.json").write_text(json.dumps(findings, indent=2, default=_jsonable))
    draw_review_chart(themes)
    (OUT / "findings.md").write_text(findings_markdown(findings, cohorts, segments,
                                                       money, tiers, progress, d7_rounds)
                                     + review_markdown(findings, themes, review_games, tagged))
    print(f"Done in {time.time() - t0:.0f}s -> {OUT}")


def _successes(cc: pd.DataFrame, version: str, col: str) -> tuple[int, int]:
    g = cc[cc["version"] == version][col]
    return int(g.sum()), int(g.size)


def monetization_tests(ab: pd.DataFrame) -> dict:
    a, b = ab[ab["testgroup"] == "a"]["revenue"], ab[ab["testgroup"] == "b"]["revenue"]
    pa, pb = a[a > 0].to_numpy(), b[b > 0].to_numpy()
    tests = {
        "conversion": two_proportion_ztest(pa.size, a.size, pb.size, b.size),
        "arpu": bootstrap_arpu_diff(pa, a.size, pb, b.size),
        "arppu": bootstrap_mean_diff(pa, pb),
    }
    # Sensitivity: how much of A's revenue story is the handful of 10,000+ payers?
    whales = pa >= 10_000
    tests["arpu_without_10k_payers"] = bootstrap_arpu_diff(pa[~whales], a.size - whales.sum(),
                                                           pb, b.size)
    tests["group_a_10k_payers"] = int(whales.sum())
    tests["group_a_10k_revenue_share"] = float(pa[whales].sum() / pa.sum())
    return tests


# --------------------------------------------------------------------------- findings

def build_findings(curve, cohorts, onboarding, first_return, progress, gate, daily, segments,
                   money, ab_tests, cohort, profile) -> dict:
    ret = curve.set_index("day_n")["retention"]
    first_complete = cohorts.dropna().groupby("day_n")
    jan = daily[daily["date"].dt.month == 1]
    last30 = daily.tail(30)
    seg = segments.set_index("segment")
    mon = money.set_index("testgroup")
    gp = progress.set_index("version")
    return {
        "window": {"cohort_start": COHORT_START.date(), "last_full_day": LAST_DATE.date(),
                   "new_players": len(cohort), "players_with_30_days": len(profile)},
        "retention": {
            **{f"d{n}": float(ret[n]) for n in m.RETENTION_DAYS},
            "peak_day": int(ret.idxmax()),
            "peak_retention": float(ret.max()),
            "best_cohort_d7": float(first_complete.get_group(7)["retention"].max()),
            "worst_cohort_d7": float(first_complete.get_group(7)["retention"].min()),
        },
        "onboarding": {
            **onboarding,
            "first_return_on_d1_share_of_all": float(
                first_return.loc[first_return["first_return_day"] == 1, "share"].sum()),
            "cookie_cats_never_played": float((progress["never_played"] * progress["players"]).sum()
                                              / progress["players"].sum()),
            "cookie_cats_under_10_rounds": float((progress["under_10_rounds"] * progress["players"]).sum()
                                                 / progress["players"].sum()),
            "gate_test": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in gate.items()},
            "gate_30_reached_30_rounds": float(gp.loc["gate_30", "reached_30_rounds"]),
        },
        "engagement": {
            "dau_jan_avg": float(jan["dau"].mean()),
            "dau_last30_avg": float(last30["dau"].mean()),
            "mau_last_day": int(daily["mau"].iloc[-1]),
            "stickiness_last30_avg": float(last30["stickiness"].mean()),
            "returning_share_of_dau_last30": float(last30["returning_players"].sum() / last30["dau"].sum()),
            "segments": {s: {"share_of_players": float(seg.loc[s, "share_of_players"]),
                             "share_of_logins": float(seg.loc[s, "share_of_logins"])}
                         for s in m.SEGMENTS},
        },
        "monetization": {
            **{f"{col}_{g}": float(mon.loc[g, col]) for g in ("a", "b")
               for col in ("players", "payers", "conversion", "revenue", "arpu", "arppu",
                           "median_payer_revenue", "top_1pct_payer_revenue_share")},
            "tests": {k: ({kk: float(vv) for kk, vv in v.items()} if isinstance(v, dict) else v)
                      for k, v in ab_tests.items()},
        },
    }


def _jsonable(o):
    if hasattr(o, "isoformat"):
        return o.isoformat()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    raise TypeError(type(o))


def _md_table(df: pd.DataFrame, fmt: dict) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append("" if pd.isna(v) else fmt.get(c, "{}").format(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def findings_markdown(f, cohorts, segments, money, tiers, progress, d7_rounds) -> str:
    pct, num = "{:.1%}", "{:,.0f}"
    r, o, e, mo = f["retention"], f["onboarding"], f["engagement"], f["monetization"]
    t = mo["tests"]
    g1, g7 = o["gate_test"]["d1"], o["gate_test"]["d7"]

    def ci(x, f_=pct):
        p = "p < 0.001" if x["p_value"] < 0.001 else f"p = {x['p_value']:.3f}"
        return f"{f_.format(x['diff'])} (95% CI {f_.format(x['ci_low'])} to {f_.format(x['ci_high'])}, {p})"

    heat = (cohorts.dropna().pivot(index="cohort_week", columns="day_n", values="retention")
            .reset_index())
    heat["cohort_week"] = heat["cohort_week"].dt.strftime("%Y-%m-%d")
    heat.columns = ["cohort_week"] + [f"D{c}" for c in heat.columns[1:]]

    return f"""# Findings

Generated by `src/run_analysis.py`. Do not edit by hand; rerun the script.

Window: players who registered {f['window']['cohort_start']} to {f['window']['last_full_day']}
({f['window']['new_players']:,} players; {f['window']['players_with_30_days']:,} have had a full 30 days).

## Retention (Gamelytics)

| Day | D1 | D3 | D7 | D14 | D30 |
|---|---|---|---|---|---|
| Retention | {pct.format(r['d1'])} | {pct.format(r['d3'])} | {pct.format(r['d7'])} | {pct.format(r['d14'])} | {pct.format(r['d30'])} |

- Retention climbs from D1 to a peak of {pct.format(r['peak_retention'])} on day {r['peak_day']}, then decays. Cohorts from 2018 show the same
  shape, so it is a property of the dataset, not of 2020 (see README, Data caveats).
- Weekly cohorts' D7 ranged from {pct.format(r['worst_cohort_d7'])} to {pct.format(r['best_cohort_d7'])}: retention is flat across 2020, not trending.

Weekly cohorts (complete cells only):

{_md_table(heat, {c: pct for c in heat.columns[1:]})}

## Onboarding

Gamelytics, players with a full 30 days:
- {pct.format(o['never_returned_30d'])} never came back after registration day.
- {pct.format(o['returned_within_7d'])} came back at least once within 7 days.
- Of players who ever came back, {pct.format(o['returners_back_on_d1'])} did so on day 1; median first return is day {o['median_first_return_day']:.0f}.

Cookie Cats, first 14 days:
- {pct.format(o['cookie_cats_never_played'])} installed and never played a round; {pct.format(o['cookie_cats_under_10_rounds'])} played fewer than 10.
- Only {pct.format(o['gate_30_reached_30_rounds'])} of gate_30 players played 30+ rounds, so most players never meet the first gate wherever it sits.
- Moving the gate from level 30 to 40 changed D1 by {ci(g1)} and D7 by {ci(g7)}.

{_md_table(progress, {'players': num, 'd1_retention': pct, 'd7_retention': pct, 'median_rounds': '{:.0f}', 'never_played': pct, 'under_10_rounds': pct, 'reached_30_rounds': pct, 'reached_40_rounds': pct})}

D7 return rate by rounds played in the first 14 days:

{_md_table(d7_rounds, {'players': num, 'd1_retention': pct, 'd7_retention': pct})}

## Engagement

- Average DAU: {num.format(e['dau_jan_avg'])} in January 2020, {num.format(e['dau_last30_avg'])} over the last 30 days.
- MAU on {f['window']['last_full_day']}: {num.format(e['mau_last_day'])}. DAU/MAU stickiness over the last 30 days: {pct.format(e['stickiness_last30_avg'])}.
- Returning players are {pct.format(e['returning_share_of_dau_last30'])} of DAU; the rest are that day's new registrations.

New-player segments by return days in the first 30 days:

{_md_table(segments, {'players': num, 'avg_return_days': '{:.1f}', 'avg_logins': '{:.1f}', 'total_logins': num, 'share_of_players': pct, 'share_of_logins': pct})}

## Monetization (offer-set A/B test)

{_md_table(money, {'players': num, 'payers': num, 'conversion': '{:.2%}', 'revenue': num, 'arpu': '{:.2f}', 'arppu': num, 'median_payer_revenue': num, 'top_1pct_payer_revenue_share': pct})}

- Conversion B - A: {ci(t['conversion'], '{:.3%}')}.
- ARPU B - A: {ci(t['arpu'], '{:.2f}')}.
- ARPPU B - A: {ci(t['arppu'], '{:,.0f}')}.
- Group A has {t['group_a_10k_payers']} payers at 10,000+, who bring in {pct.format(t['group_a_10k_revenue_share'])} of A's revenue.
  Leaving them out, ARPU B - A becomes {ci(t['arpu_without_10k_payers'], '{:.2f}')}.

{_md_table(tiers, {'players': num, 'revenue': num, 'share_of_group_revenue': pct})}
"""


# --------------------------------------------------------------------------- Power BI

def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records: dates as ISO strings, NaN as null."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        elif isinstance(out[c].dtype, pd.CategoricalDtype):
            out[c] = out[c].astype(str)
    return out.astype(object).where(out.notna(), None).to_dict("records")


def export_dashboard(findings, curve, cohorts, first_return, segments, progress, d7_rounds,
                     daily, money, tiers, ab) -> None:
    """Inject the aggregates into dashboard/template.html -> docs/index.html."""
    payers = ab[ab["revenue"] > 0]
    edges = np.logspace(0, np.log10(ab["revenue"].max() + 1), 31)
    payload = {
        "findings": findings,
        "window_days": int((LAST_DATE - COHORT_START).days) + 1,
        "daily": _records(daily[["date", "dau", "wau", "mau", "new_players", "returning_players"]]),
        "curve": _records(curve),
        "cohorts": _records(cohorts.pivot(index="cohort_week", columns="day_n", values="retention")
                            .rename(columns=lambda n: f"d{n}")
                            .join(cohorts.groupby("cohort_week")["cohort_size"].first())
                            .reset_index()),
        "first_return": _records(first_return[["first_return_day", "players", "share"]]),
        "segments": _records(segments),
        "progress": _records(progress),
        "d7_rounds": _records(d7_rounds),
        "money": _records(money),
        "tiers": _records(tiers),
        "payer_hist": {"edges": edges.tolist(),
                       **{g: np.histogram(payers.loc[payers["testgroup"] == g, "revenue"], edges)[0].tolist()
                          for g in ("a", "b")}},
    }
    blob = json.dumps(payload, default=_jsonable, allow_nan=False)
    html = DASHBOARD_TEMPLATE.read_text().replace(
        '/*__COACH_API__*/""', json.dumps(os.environ.get("COACH_API_URL", "")))
    assert "/*__DATA__*/null" in html, "dashboard template lost its data placeholder"
    DASHBOARD.parent.mkdir(exist_ok=True)
    # The template is a page body; give the published copy a full document shell.
    DASHBOARD.write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "</head>\n<body>\n" + html.replace("/*__DATA__*/null", blob) + "\n</body>\n</html>\n")


def coach_facts(f: dict, segments: pd.DataFrame, progress: pd.DataFrame) -> str:
    """Plain-English facts the Coach proxy is allowed to use. Bundled into coach-proxy at deploy."""
    r, o, e, m = f["retention"], f["onboarding"], f["engagement"], f["monetization"]
    t, g = m["tests"], o["gate_test"]
    seg = segments.set_index("segment")
    pct = lambda v: f"{v * 100:.1f}%"
    return "\n".join([
        "Games: levels 2-4 use the Gamelytics dataset (Kaggle): an unnamed mobile game, 1 million registrations "
        "1998-2020, 9.6 million logins, and a 404,770-player shop (offer set) A/B test. The data looks simulated, "
        "so treat it as practice data. Level 1's gate experiment uses Cookie Cats (Kaggle), a real match-3 puzzle "
        "game by Tactile Entertainment, 90,189 new players.",
        f"Window: players who registered {f['window']['cohort_start']} to {f['window']['last_full_day']}: "
        f"{f['window']['new_players']:,} new players.",
        f"Onboarding: {pct(o['never_returned_30d'])} never come back after day one; {pct(o['returned_within_7d'])} "
        f"come back within 7 days, and nobody returns for the first time after day 7. Median first return: day "
        f"{o['median_first_return_day']:.0f}. Cookie Cats: {pct(o['cookie_cats_under_10_rounds'])} play fewer than 10 rounds "
        f"in 14 days; {pct(o['cookie_cats_never_played'])} never play a round. Players with 100+ rounds return on day 7 "
        f"about 71% of the time vs about 2% for 1-9 rounds.",
        f"Gate test (Cookie Cats): moving the first gate from level 30 to 40 changed day-1 retention by "
        f"{g['d1']['diff'] * 100:+.1f} points (p={g['d1']['p_value']:.3f}, could be luck) and day-7 retention by "
        f"{g['d7']['diff'] * 100:+.1f} points (p={g['d7']['p_value']:.3f}, a real difference). Recommendation: keep it at 30.",
        f"Retention: day 1 {pct(r['d1'])}, day 3 {pct(r['d3'])}, day 7 {pct(r['d7'])}, day 14 {pct(r['d14'])}, "
        f"day 30 {pct(r['d30'])}. Peak is day {r['peak_day']} at {pct(r['peak_retention'])}. Weekly cohorts are flat.",
        f"Engagement: about {e['dau_last30_avg']:,.0f} players a day recently (vs {e['dau_jan_avg']:,.0f} in January); "
        f"{e['mau_last_day']:,} monthly players; stickiness (DAU/MAU) {pct(e['stickiness_last30_avg'])}.",
        "Player kinds (first 30 days): " + "; ".join(
            f"{name} ({rng}): {pct(seg.loc[key, 'share_of_players'])} of players, {pct(seg.loc[key, 'share_of_logins'])} of visits"
            for key, name, rng in [("One-and-done", "Tried once", "0 days back"), ("Tried it", "Visitors", "1-3 days"),
                                   ("Regular", "Regulars", "4-7 days"), ("Core", "Superfans", "8+ days")]) + ".",
        f"Shop test: shop A (old) vs shop B (new). Buy rate {pct(m['conversion_a'])} vs {pct(m['conversion_b'])} "
        f"(p={t['conversion']['p_value']:.3f}, real difference, B lower). Money per player {m['arpu_a']:.2f} vs "
        f"{m['arpu_b']:.2f} (p={t['arpu']['p_value']:.2f}, could be luck). Money per buyer {m['arppu_a']:,.0f} vs "
        f"{m['arppu_b']:,.0f}. Typical buyer spends {m['median_payer_revenue_a']:,.0f} (A) vs {m['median_payer_revenue_b']:,.0f} (B). "
        f"Shop A has {t['group_a_10k_payers']} huge spenders (10,000+) bringing {pct(t['group_a_10k_revenue_share'])} of its "
        f"money; shop B has none. Without them B wins by {t['arpu_without_10k_payers']['diff']:.2f} per player.",
        "Player reviews: 25,719 Google Play reviews of 9 match-3 games, average 3.24 stars, 35% are 1-2 stars. "
        "Themes far more common in 1-2 star than 4-5 star reviews: too hard/stuck 4.1x, bugs & crashes 3.3x, lost progress 3.0x, "
        "rewards & boosters 2.2x, prices/pay-to-win 2.1x, ads 1.8x. 'Fun & relaxing' is the top delight. Ads are the #1 "
        "complaint for 3 of 9 competitors; Match Masters' #1 complaint is boosters.",
        "Recommendations: fix the first session and add a day-1 reason to return; get players through their first 10 rounds; "
        "keep the gate at level 30; don't ship shop B as-is, add a high-value bundle and re-test; audit the 123 huge spenders; "
        "a streak reward to turn Regulars into Superfans; track revenue concentration next to ARPU.",
        "Dashboard tabs: Home, Level 1 Starting, Level 2 Coming back, Level 3 Playing, Level 4 Spending, Power-up lab "
        "(what-if planner), and the Neon Dash mini-game. Made by Jatin Chauhan.",
    ])


def export_powerbi(curve, cohorts, profile, daily, ab, cc, findings) -> None:
    curve.to_csv(PBI / "retention_curve.csv", index=False)
    cohorts.dropna().to_csv(PBI / "cohort_retention.csv", index=False, date_format="%Y-%m-%d")
    daily.to_csv(PBI / "daily_activity.csv", index=False, date_format="%Y-%m-%d")
    profile.to_csv(PBI / "new_players.csv", index=False, date_format="%Y-%m-%d")
    ab.assign(is_payer=ab["revenue"] > 0, revenue_tier=m.revenue_tier(ab["revenue"])) \
      .to_csv(PBI / "ab_test_players.csv", index=False)
    cc.assign(rounds_bucket=m.rounds_bucket(cc["sum_gamerounds"])) \
      .to_csv(PBI / "cookie_cats_players.csv", index=False)

    def flatten(block, prefix=""):
        for k, v in block.items():
            if isinstance(v, dict):
                yield from flatten(v, f"{prefix}{k}.")
            elif isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
                yield f"{prefix}{k}", v

    rows = [{"area": area, "metric": k, "value": v}
            for area, block in findings.items() for k, v in flatten(block)]
    pd.DataFrame(rows).to_csv(PBI / "kpi_summary.csv", index=False)


# --------------------------------------------------------------------------- charts

def _style(ax, title, ylabel=None, pct_axis=False):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    if ylabel:
        ax.set_ylabel(ylabel)
    if pct_axis:
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(CHARTS / name, dpi=140)
    plt.close(fig)


def draw_charts(curve, cohorts, first_return, d7_rounds, daily, segments, ab, tiers):
    # 1. Retention curve
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(curve["day_n"], curve["retention"], color=COLORS["main"], marker="o", ms=3)
    for n in m.RETENTION_DAYS:
        v = curve.loc[curve["day_n"] == n, "retention"].iloc[0]
        ax.annotate(f"D{n} {v:.1%}", (n, v), textcoords="offset points", xytext=(4, 6), fontsize=8)
    ax.set_xlabel("Days since registration")
    _style(ax, "Day-N retention, players registered in 2020", "Active that day", pct_axis=True)
    _save(fig, "retention_curve.png")

    # 2. Cohort heatmap
    heat = cohorts.dropna().pivot(index="cohort_week", columns="day_n", values="retention")
    fig, ax = plt.subplots(figsize=(7, 9))
    im = ax.imshow(heat.to_numpy(), aspect="auto", cmap="Blues")
    ax.set_xticks(range(heat.shape[1]), [f"D{c}" for c in heat.columns])
    ax.set_yticks(range(heat.shape[0]), heat.index.strftime("%b %d"), fontsize=7)
    for (i, j), v in np.ndenumerate(heat.to_numpy()):
        if not np.isnan(v):
            ax.text(j, i, f"{v:.1%}", ha="center", va="center", fontsize=6,
                    color="white" if v > np.nanmax(heat.to_numpy()) * 0.6 else "black")
    ax.set_title("Weekly registration cohorts: Day-N retention", loc="left", fontweight="bold")
    fig.colorbar(im, ax=ax, format=mtick.PercentFormatter(1.0, decimals=0), shrink=0.6)
    _save(fig, "cohort_heatmap.png")

    # 3. Onboarding: when do players first come back?
    fr = first_return.copy()
    shown = fr[(fr["first_return_day"] > 0) & (fr["first_return_day"] <= 14)]
    never = fr.loc[fr["first_return_day"] < 0, "share"].sum()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(shown["first_return_day"].astype(str), shown["share"], color=COLORS["main"])
    ax.set_xlabel("Day of first return (days 15-30 omitted)")
    _style(ax, f"First return after registering. {never:.0%} never come back in 30 days",
           "Share of new players", pct_axis=True)
    _save(fig, "first_return_day.png")

    # 4. Cookie Cats: D7 by rounds played, per gate variant
    fig, ax = plt.subplots(figsize=(8, 4))
    buckets = m.ROUND_BUCKET_LABELS
    x = np.arange(len(buckets))
    for i, v in enumerate(["gate_30", "gate_40"]):
        s = d7_rounds[d7_rounds["version"] == v].set_index("rounds_bucket").reindex(buckets)
        ax.bar(x + (i - 0.5) * 0.38, s["d7_retention"], 0.38, label=v, color=COLORS[v])
    share = d7_rounds.groupby("rounds_bucket", observed=True)["players"].sum().reindex(buckets)
    ax.set_xticks(x, [f"{b}\n{s / share.sum():.0%} of players" for b, s in zip(buckets, share)])
    ax.set_xlabel("Rounds played in first 14 days")
    ax.legend(frameon=False)
    _style(ax, "Cookie Cats: Day-7 return rate climbs with early rounds played",
           "D7 retention", pct_axis=True)
    _save(fig, "cookie_cats_d7_by_rounds.png")

    # 5. Engagement: DAU, MAU, stickiness
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(daily["date"], daily["mau"], label="MAU", color=COLORS["muted"])
    ax1.plot(daily["date"], daily["wau"], label="WAU", color=COLORS["b"])
    ax1.plot(daily["date"], daily["dau"], label="DAU", color=COLORS["main"])
    ax1.plot(daily["date"], daily["new_players"], label="New players", color="#55A868", ls="--")
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    ax1.legend(frameon=False, ncol=4, fontsize=8)
    _style(ax1, "Active players, 2020", "Players")
    ax2.plot(daily["date"], daily["stickiness"], color=COLORS["main"])
    _style(ax2, "Stickiness (DAU / MAU)")
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=1))
    _save(fig, "dau_mau_stickiness.png")

    # 6. Segments: share of players vs share of logins
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(segments))
    ax.bar(x - 0.2, segments["share_of_players"], 0.4, label="Share of players", color=COLORS["muted"])
    ax.bar(x + 0.2, segments["share_of_logins"], 0.4, label="Share of logins", color=COLORS["main"])
    ax.set_xticks(x, [f"{s}\n({lab})" for s, lab in
                      zip(segments["segment"], ["0 return days", "1-3", "4-7", "8+"])])
    ax.legend(frameon=False)
    _style(ax, "New players, first 30 days: a small core does most of the playing",
           pct_axis=True)
    _save(fig, "player_segments.png")

    # 7. Monetization: payer revenue distribution per group
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = np.logspace(0, np.log10(ab["revenue"].max() + 1), 50)
    for g in ("a", "b"):
        rev = ab[(ab["testgroup"] == g) & (ab["revenue"] > 0)]["revenue"]
        ax.hist(rev, bins=bins, alpha=0.7, label=f"Group {g.upper()} ({len(rev):,} payers)",
                color=COLORS[g])
    ax.set_xscale("log")
    ax.set_xlabel("Revenue per payer (log scale)")
    ax.legend(frameon=False)
    _style(ax, "Offer-set test: the two groups' payers spend in different ranges", "Payers")
    _save(fig, "ab_payer_revenue.png")

    # 8. Monetization: revenue by tier
    piv = tiers.pivot(index="tier", columns="testgroup", values="revenue").reindex(m.REVENUE_TIER_LABELS[1:])
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(piv))
    for i, g in enumerate(("a", "b")):
        ax.bar(x + (i - 0.5) * 0.4, piv[g].fillna(0), 0.4, label=f"Group {g.upper()}", color=COLORS[g])
    ax.set_xticks(x, piv.index)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v / 1e6:.1f}M"))
    ax.set_xlabel("Payer spend tier")
    ax.legend(frameon=False)
    _style(ax, "Where each group's revenue comes from", "Revenue")
    _save(fig, "ab_revenue_by_tier.png")


def review_markdown(f, themes, games, tagged) -> str:
    v, pct = f["player_voice"], "{:.1%}"
    lines = [f"""
## Player voice (Google Play reviews)

{v['reviews']:,} reviews of {v['games']} match-3 / tile-match games (Play Market 2025 dataset).
Average {v['avg_stars']:.2f} stars; {pct.format(v['share_negative'])} are 1-2 stars.
"Negative lift" = how much more often a theme appears in 1-2 star reviews than in 4-5 star reviews.

{_md_table(themes, {'reviews': '{:,}', 'share_of_reviews': pct, 'avg_stars': '{:.2f}', 'share_of_negative': pct, 'share_of_positive': pct, 'negative_lift': '{:.2f}x'})}

Where each game is weakest (top theme in its 1-2 star reviews):

{_md_table(games, {'reviews': '{:,}', 'avg_stars': '{:.2f}', 'share_negative': pct, 'top_pain_share_of_negative': pct})}

What players say, in their own words (most helpful reviews):
"""]
    for t in themes["theme"].head(4).tolist() + ["Fun & relaxing"]:
        lines.append(f"**{t}**")
        lines += [f"> {q.strip()}" for q in rv.quotes(tagged, t, 2)]
        lines.append("")
    return "\n".join(lines)


def draw_review_chart(themes) -> None:
    t = themes.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    y = np.arange(len(t))
    ax.barh(y + 0.2, t["share_of_negative"], 0.4, label="In 1-2 star reviews", color=COLORS["b"])
    ax.barh(y - 0.2, t["share_of_positive"], 0.4, label="In 4-5 star reviews", color=COLORS["main"])
    ax.set_yticks(y, t["theme"])
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    ax.set_title("What match-3 players talk about in reviews", loc="left", fontsize=12, fontweight="bold")
    _save(fig, "review_themes.png")


if __name__ == "__main__":
    main()
