# Feature spec: First Week Journey

| | |
|---|---|
| **Status** | Proposed, ready for design review |
| **Goal** | More new players come back in their first week and build a habit |
| **Primary metric** | Share of new players who return at least once in days 1–7 (today **24.0%**) |
| **Teams** | Product, Game design, Engineering (client + backend), Art, Analytics, CRM / Marketing, QA, Community |
| **Evidence** | [Onboarding funnel review](01-onboarding-funnel-review.md) · [Competitive review](04-competitive-review.md) · [Player personas](05-player-personas-and-survey.md) |

## 1. Problem

76 of every 100 new players never come back after their first day. Every player who
returns does so within 7 days, so the first week is the whole opportunity. Players who
play 10+ rounds early are far more likely to stay. Competitor reviews name early
difficulty spikes, early ads and stingy rewards as top reasons for 1★ reviews.

## 2. Hypothesis

If new players (a) get an easy, rewarding first 10 rounds, (b) have a concrete reason to
return tomorrow, and (c) can see a reward waiting at the end of week one, then more of
them will return in week one and more will become Regulars, without hurting revenue.

## 3. What we're building

| Part | Player sees | Design notes |
|---|---|---|
| **A. Gentle start** | First 10 levels can't be failed (extra moves granted silently); a booster gift on level 3; no interstitial ads before level 10 | Uses the existing level-tuning tools; ad-free window is a config flag |
| **B. Tomorrow's gift** | At the end of session 1: "Your gift unlocks in 20 h" with a countdown chest on the home screen. Push when it unlocks (if opted in) | Chest contents: 2 boosters + 1 hour of unlimited lives. The opt-in prompt appears after the first win, not at launch |
| **C. 7-day calendar** | A calendar on the home screen. Each day you log in fills a stamp; day 7 is a big chest. One missed day is forgiven | Stamps count calendar days with a login (the same definition as retention). Ends on day 7 to match the window where players decide |
| **D. Week-one recap** | On day 7: "You played 42 levels and beat 3 bosses this week" with a share card | The share card becomes social content (see the campaign brief) |

**Out of scope for v1:** teams, PvP, paid offers inside the calendar (tested later, see §9).

## 4. Requirements

**Must have**
- Parts A–C, configurable per experiment arm without a client release (remote config).
- Telemetry in §6 live and verified in staging before launch.
- Works offline; calendar state stored server-side so it survives reinstall. "Lost
  progress" is a 3.0× pain theme in reviews.
- Localized into the top 5 store languages.

**Should have:** part D. Push copy variants for the message test (§9).

**Won't have (v1):** paid skips of calendar days.

## 5. Success metrics

| Metric | Today | Target | Type |
|---|---|---|---|
| Returned within 7 days | 24.0% | +2 pts (26.0%) | **Primary** |
| D1 retention | 2.0% | +1 pt | Secondary |
| Share reaching 10 rounds in the first 14 days | 62% (Cookie Cats) | +5 pts | Secondary |
| New players reaching 4+ return days in 30 | 18.3% | +1.5 pts | Secondary |
| ARPU at day 30 | baseline per arm | no drop beyond −3% | **Guardrail** |
| Ad revenue per DAU | baseline | no drop beyond −5% (ad-free window costs some) | **Guardrail** |
| Crash-free sessions | baseline | no drop | **Guardrail** |
| Push opt-out rate | baseline | no increase beyond +1 pt | **Guardrail** |

## 6. Telemetry (events)

| Event | When | Key properties |
|---|---|---|
| `onboarding_level_start` / `_complete` / `_fail` | Each of levels 1–10 | `level`, `moves_left`, `assist_applied` (bool), `arm` |
| `gift_chest_shown` | End of session 1 | `unlock_at`, `arm` |
| `gift_chest_claimed` | Player opens the chest | `hours_since_install`, `source` (push / organic) |
| `push_permission_prompt` / `_result` | After first win | `granted` (bool) |
| `push_sent` / `push_opened` | Each notification | `campaign`, `variant`, `local_hour` |
| `calendar_day_stamped` | First login of a calendar day | `day_index` (1–7), `forgiven` (bool) |
| `calendar_completed` | Day-7 chest opened | `days_logged`, `rewards` |
| `recap_shared` | Share card sent | `channel` |

**Every event carries:** `player_id`, `install_date`, `session_id`, `platform`, `country`, `experiment_arm`.

**Data checks before launch:** event volume within 5% of the session count in staging; no
null `experiment_arm`; tests like the ones in `tests/` for every new metric definition.

## 7. Experiment design

- **Unit:** new players, randomized at first launch. Players already in the game are untouched.
- **Arms:**
  - A: control.
  - B: Gentle start only (part A).
  - C: Full journey (A+B+C).
  - Arm B separates the effect of easier levels from the return-reason features.
- **Size:** the baseline is 24.0% and the target lift is 2 points, at α = 0.05 and 80% power.
  That needs **7,349 players per arm** (`src/experiment.py`). With 3 arms and about 1,330 new
  players a day, that's about **17 days** at 100% of installs. Plan for 3 weeks, plus 7 days
  for the last cohort to finish its first week.
- **Smaller effects cost more time.** A +1-point lift needs 29,001 per arm, about 65 days for
  3 arms. If the effect is that small, the decision should rest on the guardrails and the
  secondary metrics.
- **Analysis:** two-proportion z-test on the primary metric, with Holm correction for the
  two comparisons against control. Bootstrap CIs for ARPU (revenue is heavily skewed, see
  Level 4 of the dashboard). Check sample-ratio mismatch on day 1 of the test.
- **Stop rules:** stop early only on a guardrail breach (crash rate, ARPU −10%). No peeking
  at the primary metric before the planned end.

## 8. Rollout

| Phase | Audience | Duration | Gate to continue |
|---|---|---|---|
| 1. Internal + QA | Staff builds | 1 week | Telemetry verified, crash-free ≥ baseline |
| 2. Experiment | 100% of new installs, 3 arms | ~3 weeks + 1 week to mature | Primary metric significant; no guardrail breach |
| 3. Ship winner | All new installs | — | Holdout of 5% kept for 4 weeks to confirm |
| 4. Iterate | Paid calendar offer test, copy tests | Ongoing | See §9 |

**Delivery plan:**
- Sprint 1 (2 weeks): telemetry, parts A and B, remote config.
- Sprint 2: part C, server-side state, localization.
- Sprint 3: part D, QA, push copy.
- Design review before sprint 1. Playtest of parts A–C at the end of sprint 2, with 8–10
  external players new to the game: watch where they hesitate in levels 1–10.

## 9. Follow-up experiments

1. **Push copy** (3 variants × 2 send times). See the [campaign brief](03-campaign-brief-welcome-week.md).
2. **Calendar length:** 5 vs 7 days.
3. **Day-7 chest contents:** boosters vs a cosmetic.
4. **A paid "catch-up" for a missed day:** only after the free version proves itself, with ARPU and review sentiment as guardrails.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Easier early levels lower the challenge players expect | Assist is invisible and capped at level 10; measure D30 as well as D7 |
| Push fatigue drives opt-outs | One push per day at most in week one; opt-out rate is a guardrail |
| Gift economy inflation | Gift contents come from the existing new-player budget; economy designer signs off |
| Gamelytics baseline may not match the live game | Re-baseline from live telemetry in the week before launch |

## 11. Feature retrospective (after the test)

- Did we hit the primary metric? Effect size and CI per arm.
- What surprised us in the data, in playtests, or in reviews and community posts?
- What would we change in the design or the experiment?
- Utilization: share of eligible players who saw, claimed and completed each part (from the §6 events).
- Decision: ship, iterate, or roll back. Record it in the [feature tracker](feature_tracker.csv).
