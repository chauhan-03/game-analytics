# Player personas and survey plan

Each persona is built from two sources:
- **What players do:** the player kinds in the telemetry. Share of new players and share of visits come from Gamelytics, first 30 days.
- **What players say:** themes from 25,719 match-3 Google Play reviews.

The quotes are verbatim 1–5★ Google Play reviews, spelling kept, pulled with `rv.quotes()`. Names are illustrative.

## Personas

### 1. "Just Browsing" Bea: tried once (76% of new players, 33% of visits)
- **Behavior:** plays on install day and never returns.
- **Says:** "Played one time and wanted me to upgrade, too much time waiting to play, not much to play." / "Says no ads....There are ads!!! BORING......."
- **Needs:** fun in the first 3 minutes, no friction, a reason to come back tomorrow.
- **Wins her:** a gentle start, an ad-free first session, tomorrow's gift.
- **Watch:** D1; share of players reaching 10 rounds.

### 2. "Coffee Break" Carlos: Visitor (5.7%, 7% of visits)
- **Behavior:** comes back 1–3 days in week one, then drifts.
- **Says:** "Enjoyed playing it, got too hard, sick of seeing the green grass. Uninstalled." / "Starts out fun, but lots of ads and matching game becomes repetitive. Also takes way too long to refill lives."
- **Needs:** short sessions, visible progress, a goal that fits into a week.
- **Wins him:** a 7-day calendar with a forgiving streak; "stuck help" after 3 fails.
- **Watch:** share reaching 4+ return days.

### 3. "Daily Ritual" Dana: Regular (14.2%, 42.5% of visits)
- **Behavior:** 4–7 return days in her first month. Plays most days.
- **Says:** "Finished all levels! It was fun and challenging. Please bring out more rooms." / "I never get the daily rewards for unlimited lives"
- **Needs:** fresh goals, fair rewards, a sense of progress beyond levels.
- **Wins her:** weekly races, co-op events, generous event rewards.
- **Watch:** sessions per DAU; event participation; D30.

### 4. "Collector" Kai: Superfan (4.1%, 16.9% of visits; includes the highest spenders)
- **Behavior:** 8+ return days in 30; the group that includes high-value payers.
- **Says:** "No support for migrating to a new device. All progress lost." / "frauds they end up taking your paid booster.. all of sudden the opponent time doesn't move."
- **Needs:** status, collections, safety for what they've earned, value for money.
- **Wins him:** team features, cosmetics, account linking, clear-value bundles. The offer test
  shows that removing high-price bundles lost every 10,000+ spender.
- **Watch:** ARPPU; revenue concentration (top 1% share); 1★ "lost progress" mentions.

## Survey plan

**Goal:** confirm *why* players leave in week one, and what would bring Visitors back.
Telemetry shows *what* happens; this tells us *why*.

**Who and when:**

| Survey | Audience | Trigger | Size | Channel |
|---|---|---|---|---|
| A. Week-one pulse | Players on their 3rd return day | After a level win (positive moment) | 1,500 responses | In-game, 4 questions |
| B. Lapsed check-in | Played 1–3 days, then 7+ days inactive | Email, one send | 400 responses | Email link, 6 questions |
| C. Superfan panel | 8+ return days | Invite in community channel | 30–50 people | Survey + 5 video calls |

**Survey A, week-one pulse:**
1. How much are you enjoying the game so far? (1–5)
2. What do you enjoy most? (pick up to 2: relaxing / challenge / decorating / events / playing with others / rewards)
3. Has anything frustrated you? (pick any: levels too hard / not enough lives / ads / prices / bugs / nothing)
4. What would make you play tomorrow? (open text, optional)

**Survey B, lapsed check-in:**
1. What's the main reason you stopped playing? (single choice, same list as A3 plus "just forgot" / "found another game")
2. Which game did you move to, if any? (open text)
3. How long were your sessions usually? (under 5 min / 5–15 / 15+)
4. Would any of these bring you back? (free boosters / new levels / easier levels / play with friends / none)
5. How likely are you to recommend the game? (0–10)
6. Anything else? (open text)

**Design rules:**
- Ask after a win, never after a fail.
- One survey per player per 30 days.
- No incentive that changes the answer: a thank-you booster is sent *after* completion,
  whatever the answers.
- Store the answers with `player_id`, so they can be joined to telemetry.

**Analysis:**
- **Close-ended:** cross-tab A3 and B1 by persona and by experiment arm.
- **Open text:** tag it with the same theme rules used for app-store reviews (`src/reviews.py`),
  so survey and review themes are directly comparable.
- **Validation:** check the stated reasons against behavior. Do players who say "too hard"
  actually show more fails before they lapse?

## Other qualitative sources to fold in

| Source | What to pull | Cadence |
|---|---|---|
| App-store reviews | Theme shares, 1–2★ trend, competitor gaps (`src/reviews.py`) | Weekly |
| Customer support tickets | Top 10 contact reasons; "lost progress" and payment issues | Weekly |
| Community (Discord, Reddit, Facebook) | Event feedback threads, bug reports, feature requests | Per event |
| Social media | Sentiment on announcements; creator content performance | Per campaign |
| Playtests | Where new players hesitate in levels 1–10 | Each onboarding change |
