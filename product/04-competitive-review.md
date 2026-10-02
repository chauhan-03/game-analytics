# Competitive review: progression and social systems in match-3

**Question:** How do the leading puzzle games keep players progressing and playing
together? Where are competitors weak, and what should we build?
**Method:**
- **Desk research** on live games, sources linked.
- **Review mining** of 25,719 Google Play reviews across 9 match-3 games, using
  `src/reviews.py`. Each game's weakest spot is the theme that dominates its 1–2★ reviews.

## 1. Market context

- **Mature category.** Match-3 and puzzle form a large but flat category. Growth comes from
  taking share and from live ops, not from new players arriving
  ([AppMagic Casual Report 2025](https://appmagic.rocks/research/casual-report-2025)).
  Royal Match has challenged Candy Crush since 2024
  ([Raviosoft 2026](https://www.raviosoft.com/post/best-match-3-games-of-2026-the-games-kpis-and-marketing-strategies-dominating-the-market)).
- **Retention is getting harder.** Match-3 D1 retention slipped from 25% to 24% in 2024, while
  time spent by retained players rose
  ([Adjust](https://www.adjust.com/blog/puzzle-games-trends-strategies/)).
- **Live ops is converging on templates and personalization.** Proven event formats get reused
  across games and tuned to each player
  ([PocketGamer.biz, 2026 live ops trends](https://www.pocketgamer.biz/2026-live-ops-trends-templatisation-personalisation-and-ai/)).
- **Genre-blending events spread fast.** One example is Klondike-style "Expedition" events,
  popularized by Playrix
  ([Naavik](https://naavik.co/digest/what-leading-match-3-and-merge-games-do-differently/)).

## 2. Progression systems

| Game | Core progression | Event layer on top | What it does well |
|---|---|---|---|
| **Royal Match** | Level campaign, 12,400+ levels, new levels every 2 weeks; earn stars to renovate the castle | **King's Cup:** 50 players race for cups, Mon–Fri. **Lava Quest:** 100 players, 7 levels in a row in 24 h | Short, clear, time-boxed goals stacked on an endless campaign ([Wikipedia](https://en.wikipedia.org/wiki/Royal_Match), [Royal Match wiki](https://royalmatch.fandom.com/wiki/%F0%9F%8F%86_King's_Cup), [This Week in LiveOps](https://thisweekinliveops.substack.com/p/this-week-in-liveops-royal-matchs)) |
| **Candy Crush Saga** | Map of episodes; lives gate play | Daily rewards, season pass, leaderboards among friends | Huge content library; habit loops ([Business of Apps](https://www.businessofapps.com/data/puzzle-games-market/)) |
| **Match Masters** | Trophy road through PvP duels | Tournaments in a play-off format | **Boosters work as both energy and wallet.** You pick one before every duel and lose it if you lose ([Naavik deconstruction](https://naavik.co/deep-dives/match-masters-deconstruction/)) |
| **Cookie Cats** (our test data) | Linear levels with **gates** (wait or ask friends) | — | The A/B test shows the gate's position matters: level 40 cost 0.8 pts of D7 vs level 30 |

## 3. Social systems

| Game | Social system | Evidence it works |
|---|---|---|
| **Royal Match** | **Teams:** progress as a team; **Team Battle** pits 20 teams against each other | Core retention layer for engaged players ([Wikipedia](https://en.wikipedia.org/wiki/Royal_Match)) |
| **Monopoly GO** | **Partners:** co-op events, 4 players build attractions together; rent and stickers trade between friends | A Partners event drove a ~55% revenue spike; Royal Match and Squad Busters copied the co-op format ([AppMagic](https://appmagic.rocks/research/monopoly-go-revenue-spike/?hl=en), [PocketGamer.biz](https://www.pocketgamer.biz/decoding-the-live-ops-strategy-of-monopoly-go/)) |
| **Match Masters** | Real-time PvP duels | Distinct positioning, but its reviews show the cost (below) |
| **Candy Crush** | Friends leaderboard on the map; ask friends for lives | Low-effort social proof |

## 4. Where competitors are weak (review mining)

| Game | Reviews | Avg ★ | 1–2★ share | #1 theme in its 1–2★ reviews |
|---|---|---|---|---|
| Goods Puzzle: Sort Challenge | 5,000 | 3.00 | 40% | **Prices & pay-to-win** (48% of negatives) |
| Match Masters | 5,000 | 3.00 | 40% | **Rewards & boosters** (55%) |
| Triple Tile | 4,507 | 3.06 | 39% | **Ads** (63%) |
| Tile Explorer | 1,319 | 4.32 | 14% | **Ads** (56%) |
| Open House | 2,457 | 3.40 | 33% | Events & new content (12%) |
| Simon's Cat Match! | 317 | 4.71 | 5% | Too hard / stuck (24%) |

What this tells us:
- **Ads are the #1 complaint in tile-match.** Triple Tile and Tile Explorer both lose most of
  their 1★ reviews to ads. An ad-light early game is a real point of difference.
- **Booster-gated PvP angers players.** Match Masters' booster economy is its money engine and
  also its #1 complaint. Copy the competition, not the gating.
- **"Events & new content" complaints are mostly broken updates.** Reviews like "Game won't
  load since last update" or "after the update it's not working properly" suggest release QA
  matters more than event design. Ship events behind remote config, and stage rollouts.
- **High ratings come from the craft.** Simon's Cat Match! (4.71★) is criticized only for
  difficulty, which suggests a cozy brand plus a fair economy wins sentiment.

## 5. Proposals for the game leads

| # | Feature | Borrowed from | Why us | First test |
|---|---|---|---|---|
| 1 | **First Week Journey** (gentle start, tomorrow's gift, 7-day calendar) | Daily-reward and calendar patterns | Our biggest loss is day 1 to day 7 | [Spec ready](02-feature-spec-first-week-journey.md) |
| 2 | **Co-op "Duo Builds"**: 2–4 players fill a shared meter in a 3-day event; rewards for everyone | Monopoly GO Partners | Co-op lifts revenue without PvP's frustration; "Friends & teams" shows up 1.65× in negative reviews, so it must feel fair, not forced | Event A/B on Regulars: participation, D30, ARPU |
| 3 | **Weekly 50-player race** (cups per level, Mon–Fri) | Royal Match King's Cup | A short goal for Regulars and Superfans, who are 18% of players and 59% of visits | Template event with tuned difficulty; measure sessions per DAU |
| 4 | **Ad-light promise**: no interstitials before level 10; rewarded ads only after | Gap in tile-match competitors | Ads are the top 1★ theme for 3 of 9 competitors | Guardrail: ad revenue per DAU |
| 5 | **"Stuck help"**: after 3 fails, a hint and a free booster, once per level | Answer to the #1 pain theme | "Too hard / stuck" is 4.1× more common in 1★ reviews | A/B: level completion, review theme share |

**Not recommended now:** PvP duels with entry boosters. They're a strong monetization model,
but the review evidence says it costs goodwill, and our audience comes for "fun & relaxing".
