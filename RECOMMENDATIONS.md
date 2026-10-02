# Product recommendations

Each recommendation names the finding behind it, the change to make, and the metric
that would show it worked. Numbers come from [outputs/findings.md](outputs/findings.md).
Where a finding is a correlation, the recommendation is a test rather than a rollout.

## Summary

| # | Area | Recommendation | Evidence strength |
|---|---|---|---|
| 1 | Onboarding | Fix the first session and give players a reason to return on day 1 | Strong (76% never return) |
| 2 | Onboarding | Get new players through their first 10 rounds | Correlational; test it |
| 3 | Onboarding | Keep the first gate at level 30 | Strong (A/B test, p = 0.002) |
| 4 | Monetization | Don't ship offer set B as is. Keep its mid-price offers and add a high-value bundle back, then re-test | A/B test, with a data-quality caveat |
| 5 | Monetization | Audit the 123 group-A players who paid 10,000+ before deciding anything | Data-quality |
| 6 | Engagement | Move "Regular" players to "Core" with a return-streak mechanic | Descriptive; test it |
| 7 | Measurement | Track revenue concentration next to ARPU on the dashboard | Process |

---

## 1. Fix the first session and the day-1 return

**Finding.** 76.0% of players who registered in 2020 never came back in their first 30
days. D1 retention is 2.0%, the lowest of the first week. Players who do return take a
median of 4 days to come back, and only 8.4% of them return on day 1.

**Recommendation.** The biggest lever in the game is getting a player back once. Two
changes to test together:
- Shorten the first session so it reaches a moment of success fast (first win, first
  reward) rather than ending in a tutorial.
- Add a day-1 hook: a reward that unlocks 20–24 hours after registration, with a
  push notification when it is ready.

**Success metric.** D1 retention and "returned within 7 days" (24.0% today), in an A/B test
against the current flow. At 2020 registration volumes (about 486,000 a year), each
1-point gain in "returned within 7 days" is about 4,900 more players coming back.

## 2. Get new players through their first 10 rounds

**Finding (Cookie Cats).** 38.0% of new players play fewer than 10 rounds in their first two
weeks. D7 return rate rises steeply with rounds played: 1.8% for 1–9 rounds, 7–8% for
10–29, about 16% for 30–39, and 71% for 100+.

**Recommendation.** Treat the first 10 rounds as the onboarding funnel: make them easy to
win, short, and rewarding. This is a correlation. Players who would have stayed anyway also
play more. So run it as an experiment (an easier early-level curve vs the current one), not
a rollout.

**Success metric.** Share of players reaching 10 rounds, then D7 retention.

## 3. Keep the first gate at level 30

**Finding (Cookie Cats A/B test, 90,189 players).** Moving the first progress gate from
level 30 to level 40 lowered D7 retention from 19.0% to 18.2%. That's -0.8 points (95% CI
-1.3 to -0.3, p = 0.002). D1 moved by -0.6 points, which isn't significant (p = 0.074).

**Recommendation.** Keep the gate at level 30. An early pause seems to help players come
back. Also, only 37% of players reach 30 rounds, so the gate affects a minority. Item 2
reaches far more players.

## 4. Offer set B: keep its mid-price offers, add a high-value bundle back, and re-test

**Finding (404,770 players).**

| | A (control) | B (new offers) | B - A |
|---|---|---|---|
| Conversion | 0.954% | 0.891% | -0.063 pts, p = 0.035 |
| ARPU | 25.41 | 26.75 | +1.34 (CI -2.86 to +5.51), not significant |
| ARPPU | 2,664 | 3,004 | +340 (CI -60 to +746), not significant |
| Median payer spend | 311 | 3,022 | |

The averages hide two different revenue shapes:
- **A:** 1,805 payers spend under 500, and 123 payers spend 10,000+. Those 123 bring in 89% of A's revenue.
- **B:** every payer spends 1,000–4,000. Nobody pays 10,000+.

So B converts slightly fewer players, gets about ten times more from a typical payer, and
loses the very top spenders.

**Recommendation.** Don't ship B as is, and don't kill it. Its higher-priced mid-range
offers clearly work on ordinary payers. Missing high-value bundles are the likely reason B
has no 10,000+ spenders. Build B' = B's offers plus a high-value bundle, and test B' against A.

**Success metric.** ARPU (primary), with conversion and the share of revenue from 10,000+
payers as guardrails.

## 5. Audit the 10,000+ payers before deciding

**Finding.** In both groups exactly 1,805 payers are outside the 10,000+ tier, and every
10,000+ payer is in group A. A randomized split rarely produces an exact match like that.

**Recommendation.** Before acting on item 4, check:
1. **Assignment:** were these 123 players randomized like everyone else?
2. **Refunds and fraud:** did any of the payments get refunded or charged back?
3. **Test accounts:** are any of them internal or test accounts?

If the 123 shouldn't be there, B wins on ARPU by +24.05 (CI +22.81 to +25.32), and the
decision becomes "ship B".

## 6. Turn "Regular" players into "Core"

**Finding.** Among new players with a full 30 days:
- **Regular and Core** (4+ return days) are 18.3% of players but make 59.4% of all logins.
- **Core** (8+ return days) alone is 4.1% of players and 16.9% of logins.
- **Nobody** returns on more than 13 of their first 30 days.

DAU/MAU stickiness is flat at about 15.5% all year.

**Recommendation.** Players who come back 4–7 times already have the habit. Add a
return-streak reward (escalating rewards for consecutive return days, with one missed day
forgiven) aimed at them.

**Success metric.** Share of new players reaching 8+ return days in 30 days (4.1% today),
and stickiness.

## 7. Track revenue concentration on the dashboard

**Finding.** ARPU said "no difference" in a test where the two groups earn money in
completely different ways.

**Recommendation.** Put the share of revenue from the top 1% of payers (13.8% in A, 1.3% in B)
and median payer spend next to ARPU on the monetization page. Any test summary should show
the payer spend distribution, not just the averages.

---

## Open question for the game team

Retention on this game peaks on day 6 (6.9%), then drops sharply on day 7. Cohorts from 2018
show the same shape. In a live game this pattern usually comes from a feature on a 7-day
cycle, such as a welcome event or a first-week login calendar that ends on day 6. If one
exists, extending it or following it with a second-week reward is the obvious next test. If
none exists, the shape is probably a property of how this dataset was built (see README,
Data caveats).
