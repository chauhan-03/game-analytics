# Go-to-market plan: a new cozy match-3 game

**Brief:** we're launching a new match-3 puzzle game into a mature, flat category. The
working title is *Tea Garden Match*: match tiles to restore a garden café. This plan covers
positioning, soft launch, launch and the first 90 days. Numbers reuse this project's
findings and the sources in the [competitive review](04-competitive-review.md).

## 1. Where we can win

| Insight | Source | So we... |
|---|---|---|
| "Fun & relaxing" is the clearest delight in match-3 reviews (0.47×) | Review mining, 25,719 reviews | Position as **the calm puzzle game** |
| Ads are the #1 1★ theme for 3 of 9 tile-match competitors | Review mining | Promise **no forced ads in the first 10 levels**, then rewarded ads only |
| Booster-gated PvP drives Match Masters' #1 complaint | Review mining + [Naavik](https://naavik.co/deep-dives/match-masters-deconstruction/) | Lead with **co-op** events, not PvP |
| Co-op events lifted Monopoly GO revenue ~55% | [AppMagic](https://appmagic.rocks/research/monopoly-go-revenue-spike/?hl=en) | Ship a co-op "Duo Builds" event by launch + 60 days |
| The category is flat; growth comes from share | [AppMagic 2025](https://appmagic.rocks/research/casual-report-2025) | Win on retention and word of mouth, not UA volume alone |

**Positioning:** *"The puzzle game that lets you breathe. Cozy levels, a garden to grow,
friends to build with, and no ad ambush."*

**Primary audience:** adults 25–54 who play casual puzzles in short breaks. They match the
"Coffee Break Carlos" and "Daily Ritual Dana" [personas](05-player-personas-and-survey.md).
**Secondary:** lapsed players of big match-3 titles who left over ads or difficulty.

## 2. Launch phases and gates

| Phase | Markets | Length | Must hit to move on |
|---|---|---|---|
| **Closed alpha** | Staff + 200 community testers | 4 weeks | Crash-free sessions ≥ 99.5%; first-10-level funnel without a hard drop; playtest notes closed |
| **Soft launch 1: retention** | 2–3 English-speaking test markets (e.g. Philippines, Canada) | 6–8 weeks | D1 ≥ 32%, D7 ≥ 12%, D30 ≥ 5% (puzzle-genre averages in [Business of Apps](https://www.businessofapps.com/data/mobile-game-retention-rates/)); stretch D1 35%; 1–2★ share ≤ 15% |
| **Soft launch 2: monetization** | Add 1–2 Tier-1 markets | 6 weeks | Payer conversion and ARPDAU trending to an LTV above the CPI target; revenue not concentrated in the top 1% of payers |
| **Global launch** | Worldwide | — | All gates green; live ops calendar planned 12 weeks ahead |

Each gate is reviewed with Product, Design, Engineering, Analytics, UA and Community leads.
A missed gate means another iteration, not a delayed decision.

## 3. Launch beats

| When | Beat | Channels |
|---|---|---|
| L−8 weeks | Pre-registration opens; store page live | Google Play pre-registration, App Store pre-order, landing page |
| L−6 | Creator seeding (cozy and puzzle creators) | TikTok, YouTube Shorts, Instagram |
| L−4 | Community opens: "Founding Gardeners" Discord with weekly dev notes | Discord, Reddit |
| L−2 | Store featuring pitch: cozy game + ad-light promise | Google Play / Apple editorial teams |
| **L** | Launch: "Welcome Week" journey live ([campaign brief](03-campaign-brief-welcome-week.md)) | In-game, push, email, social, creators, paid UA |
| L+2 weeks | First live event: Garden Race (50-player weekly race) | In-game, push, social |
| L+60 days | Co-op Duo Builds event | In-game, community, creators |
| L+90 days | Season 1 content update + store refresh | All |

## 4. Acquisition and creative

- **UA creative tests in soft launch:** gameplay "satisfying clear" vs. cozy story vs. "fail"
  bait. Judge each by install rate *and* D1/D7 of the players it brings, since bait ads
  inflate installs and hurt retention.
- **App store:**
  - Two screenshot sets: "Relaxing" vs. "Challenge", tested with Google Play store-listing experiments.
  - Keyword focus: match-3, tile, cozy, garden, puzzle.
  - Reply to every 1–2★ review in the first 4 weeks.
- **Creators:** pay for performance where possible. Measure installs and D7 per creator, not views.

## 5. Measurement plan

| Question | Metric | Where |
|---|---|---|
| Do players come back? | D1 / D7 / D30, returned within 7 days | Dashboard Levels 1–2 |
| Do they build a habit? | Stickiness (DAU/MAU), share with 4+ return days | Level 3 |
| Do they pay fairly? | Conversion, ARPU, ARPPU, revenue share of top 1% | Level 4 |
| Do they like it? | Avg ★, 1–2★ share, review themes vs competitors | Player voice (`src/reviews.py`) |
| Which channel works? | CPI, D7 and ROAS by source and creative | UA dashboard (add `install_source` to telemetry) |

**Weekly launch review:**
- KPIs vs gates.
- Top 3 review themes.
- Top 3 support contact reasons.
- Decisions taken and owners.

## 6. Risks

| Risk | Plan |
|---|---|
| Cozy positioning reads as "too easy" for experienced players | Optional hard levels marked with a pepper icon; separate leaderboards |
| Ad-light promise hurts early revenue | Rewarded ads and a starter bundle; track ad revenue per DAU against the plan |
| Soft-launch markets don't predict Tier-1 behavior | Second soft-launch phase adds a Tier-1 market before global |
| Launch-day crashes | Staged rollout (10% → 50% → 100% over 72 h); crash-free gate |
