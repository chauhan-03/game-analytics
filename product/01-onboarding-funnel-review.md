# Onboarding funnel review: where new players drop, and why

**Question:** Of every 100 players who install, how many become regular players? Where
do we lose the rest?
**Sources:**
- **Gamelytics logins:** 305,832 players registered in 2020 who have had 30 days to play.
- **Cookie Cats:** first-14-day telemetry, 90,189 players.
- **Google Play reviews:** 25,719 reviews of 9 match-3 games.
- **SQL:** `sql/02_onboarding_never_returned.sql` and `sql/06_churn_by_early_rounds.sql`.

**Status:** findings final. Recommendations go into the
[First Week Journey spec](02-feature-spec-first-week-journey.md).

## 1. The funnel

| Step | Players | Out of 100 | Lost at this step |
|---|---|---|---|
| Registered (day 0) | 305,832 | 100 | |
| Came back at least once in days 1–7 | 73,264 | 24.0 | **76.0** |
| Came back on 4+ different days in 30 ("Regular" or better) | 55,913 | 18.3 | 5.7 |
| Came back on 8+ days in 30 ("Superfan") | 12,589 | 4.1 | 14.2 |

Three facts shape everything else:

1. **Day 1 is the bottleneck.** 76 of 100 players never return. D1 retention is 2.0%, the
   lowest day of the first week. Industry roundups put puzzle-game D1 around 24–32%
   ([Adjust](https://www.adjust.com/blog/puzzle-games-trends-strategies/),
   [Business of Apps](https://www.businessofapps.com/data/mobile-game-retention-rates/)).
   The Gamelytics data looks simulated, so that comparison is directional. The shape of the
   drop is the useful part.
2. **There's no second chance after day 7.** Every player who ever returns does so within
   7 days, and the median first return is day 4. A win-back sent after week one is talking
   to people who have already left.
3. **The small group that stays carries the game.** "Regulars" and "Superfans" are 18% of
   new players but make 59% of all visits.

## 2. Why players drop: early play predicts staying

Cookie Cats records how many rounds each player played in their first 14 days:

| Rounds in first 14 days | Share of players | Back on day 7 |
|---|---|---|
| 0 | 4% | 0.7% |
| 1–9 | 34% | 1.8% |
| 10–29 | 25% | ~7.7% |
| 30–39 | 7% | 15.7% |
| 40–99 | 16% | ~31% |
| 100+ | 14% | 71% |

**Churn within a segment.** The analysis looks at day-1 returners, players who did come back
the next day, which is the group onboarding already "won". Among them:
- **Under 10 rounds:** 96% were gone by day 7.
- **100+ rounds:** 29% were gone by day 7.

So coming back once isn't enough. The players who stay are the ones who get into the
game's rhythm early.

**Caveat:** this is correlation. Players who love the game play more and return more. The
experiment in the spec tests whether *helping* players through early rounds causes more
of them to stay.

## 3. What gets in the way: friction points

The Cookie Cats A/B test shows that friction early in the game costs players:
- **The test:** moving the first progress gate from level 30 to 40 lowered D7 retention
  from 19.0% to 18.2%. That's -0.8 points, p = 0.002.
- **Gate reach:** only 37% of players get past 30 rounds. Gate placement matters, but it
  reaches a minority.

Player reviews of 9 competing match-3 games name the friction directly. These themes appear
far more often in 1–2 star reviews than in 4–5 star ones:

| Pain | In 1–2★ vs 4–5★ reviews | What it means for onboarding |
|---|---|---|
| Too hard / stuck on a level | 4.1× | Early difficulty spikes push players out |
| Bugs & crashes | 3.3× | A crash in session one ends the relationship |
| Lost progress | 3.0× | Account and save must be safe from day one |
| Rewards & boosters feel stingy | 2.2× | Early rewards set the tone for fairness |
| Prices / pay-to-win | 2.1× | Hard paywalls feel worse before trust exists |
| Ads | 1.8× | Ads in the first session read as greed |

"Fun & relaxing" is the clearest delight (0.47×). It's what players come for.

## 4. Recommendations

| # | Change | Expected effect | How we'll know |
|---|---|---|---|
| 1 | **Day-1 reason to return:** a gift that unlocks 20–24 h after install, plus a push when it's ready | More players return on day 1, the weakest day | D1 and "returned within 7 days" in an A/B test |
| 2 | **Gentle first 10 rounds:** no fail states before round 10, guaranteed early wins, no ads before round 10 | More players reach 10+ rounds; fewer 1–2★ "too hard" and "ads" reviews | Share reaching 10 rounds; D7; review theme share |
| 3 | **Keep the first gate at level 30** | Protects D7 | Already tested (p = 0.002) |
| 4 | **First-week journey for players who come back:** a 7-day login calendar that ends on a big reward | Converts "Visitors" (1–3 days) into "Regulars" (4+) | Share of new players reaching 4+ return days |
| 5 | **Crash and save hardening** before any UA push | Cuts the two pains most tied to 1★ reviews | Crash-free sessions; "bugs" and "lost progress" review share |

Recommendations 1, 2 and 4 together become the
**[First Week Journey](02-feature-spec-first-week-journey.md)** feature.
