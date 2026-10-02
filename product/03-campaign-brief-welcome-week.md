# Campaign brief: Welcome Week

| | |
|---|---|
| **What** | Player communication for the [First Week Journey](02-feature-spec-first-week-journey.md) launch, plus a win-back flow for players who stall |
| **When** | Starts with the feature experiment; stays always-on for new players once the winner ships |
| **Owner** | Product (brief) with CRM, Community, Social, UA creative, App Store / ASO |
| **Budget** | Owned channels plus creator seeding (see §6) |

## 1. Audience

New players in their first 7 days, split by what they've done. The segments come from the
dashboard's player kinds:

| Segment | Definition | Size today | What they need |
|---|---|---|---|
| **Day-1 at risk** | Installed, hasn't returned by hour 20 | 76% of new players never return | A reason to come back *tomorrow* |
| **Visitors** | 1–3 return days in week one | 5.7% | A habit: something to finish this week |
| **Regulars** | 4–7 return days | 14.2% | Recognition, then social hooks |
| **Superfans** | 8+ return days in 30 | 4.1% | Community and creator content; first look at events |

## 2. Player insight

> "I liked it, but I got stuck, ran out of lives and forgot about it."

This is what players tell us across 25,719 match-3 reviews:
- **Too hard / stuck:** 4.1× more common in 1★ reviews than in 5★.
- **Fun & relaxing:** the word players use when they love the game (0.47×, the clearest delight).
- **Timing:** every returning player in our data comes back within 7 days. After that they're gone.

**What players need:** a short, friendly nudge while the game is still fresh, promising fun
and progress, not pressure.

## 3. Message

**Core message:** *"Your week of puzzles is just getting started. A gift is waiting for you."*

**Supporting points, by day:**
1. Day 1: "Your free gift is ready."
2. Day 3: "You're 3 stamps from the big chest."
3. Day 7: "Look what you did this week."

**Tone:** warm, playful, short. Never guilt ("We miss you!!!"), never scarcity spam.

## 4. Player journey by channel

| Day | Trigger | In-game | Push | Email (if known) | Social / community |
|---|---|---|---|---|---|
| 0 | First session ends | Gift chest + countdown | — | Welcome: "how to play" GIF | Invite to the Discord / Facebook group on the end screen |
| 1 | Gift unlocks (20 h) | Chest glow on home screen | **"Your gift is ready 🎁"** | — | — |
| 2 | No login by local 6 pm | — | "Two boosters are waiting in your chest" | — | — |
| 3 | Stamp 3 earned | "Halfway to the big chest" banner | — | — | — |
| 4–6 | Missed a day | Forgiven-day badge | "No worries, your streak is safe" (once) | Tips: "3 tricks for tricky levels" | Creator tips video in feed |
| 7 | Calendar complete | Week-one recap + share card | "Your week in puzzles 🏆" | Recap with stats | Share card to Instagram / WhatsApp |
| 8–10 | No login since day 7 (win-back) | Return gift on next open | One message only, on day 9 | "New levels added this week" | Retarget ad with the newest event (UA team) |

**Frequency cap:** at most 1 push a day and 4 in week one. Quiet hours 22:00–09:00 local.

## 5. A/B tests

| Test | Variants | Audience | Metric | Size note |
|---|---|---|---|---|
| Day-1 push copy | Gift ("Your gift is ready") · Progress ("Level 6 is waiting") · Social ("1,200 players beat level 6 today") | Arm C installs with push on | Push open rate, then D1 | Open rate moves fast: 1,500–1,800 per variant detects +3 pts from an 8–10% baseline |
| Push send time | Hour 20 after install · 7 pm local | Same | D1 return | Run after the copy test |
| Return gift in win-back | 2 boosters · 1 h unlimited lives | Day-8 lapsed | Return by day 14 | Small audience: run 4+ weeks |
| Store creative | "Relaxing" screenshot set · "Challenge" set | Play Store experiment | Install conversion | Built into Play Console |
| UA creative concept | Satisfying-clear gameplay · "Fail" bait ad | UA test budget | IPI, D1 of acquired users | Watch D1: bait ads raise installs but can hurt retention |

## 6. Social, creators and community

- **Creator partnerships:** seed 10–15 cozy and puzzle creators (TikTok, YouTube Shorts) with
  early access to the week-one calendar. The brief: "show your favorite satisfying clear".
  Measure installs per tracked link and D7 of those installs, not views.
- **Social content:** weekly "Puzzle of the week" posts using real level layouts. Repost
  player recap cards with permission.
- **Community activation:** a Discord / Facebook "Week One Club" channel, plus a pinned
  "stuck on a level?" help thread run by community managers. It answers the top pain theme
  directly.
- **App store:**
  - Update the first two screenshots to show the gift chest and calendar.
  - Promotional content on Google Play: "Welcome Week".
  - Reply to 1–2★ reviews that mention being stuck with a tip and the help-thread link.

## 7. Success metrics

| Metric | Target | Read at |
|---|---|---|
| D1 retention (new players) | +1 pt vs control | Day 2 of each cohort |
| Returned within 7 days | +2 pts | Day 8 |
| Push open rate (day-1 push) | ≥ 8% | Daily |
| Push opt-out in week one | ≤ baseline + 1 pt | Weekly |
| Share-card shares per 100 completions | ≥ 3 | Weekly |
| Creator installs → D7 retention | ≥ organic D7 | Per creator |
| 1–2★ reviews mentioning "stuck" or "ads" | −20% within 6 weeks | Weekly, from the review pipeline (`src/reviews.py`) |

## 8. Timeline

| Week | Milestones |
|---|---|
| −2 | Brief approved; copy and art requests to Art and CRM |
| −1 | Push copy localized; creators briefed; store creative uploaded |
| 0 | Experiment starts with the feature; copy test on arm C |
| 3 | Read results; ship the winning journey + copy |
| 4 | Retrospective; update the [feature tracker](feature_tracker.csv) |
