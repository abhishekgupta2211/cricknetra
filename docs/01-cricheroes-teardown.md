# CricHeroes Teardown — Module-by-Module Analysis

> Reference spec for building **CricNetra**. This maps every module CricHeroes
> ships, what data each needs, and how hard it is to build. Use it to decide
> what to clone, what to skip, and where CricNetra should be *better*.

Legend for **Build effort**: 🟢 easy · 🟡 medium · 🔴 hard (core IP / lots of edge cases)

---

## 0. The big picture

CricHeroes is **mobile-first** (Android leads, iOS follows) with a **public web**
layer for sharing scorecards/tournaments. It is free for scorers; it monetizes
through PRO subscriptions, white-label (Your App / Your Web), sponsorships, a
store, and official association deals.

The whole product is really **four engines wearing a social-network coat**:

1. **Scoring engine** — turns taps into a ball-by-ball match record. *(the crown jewels)*
2. **Stats/aggregation engine** — rolls balls up into player/team/tournament numbers.
3. **Tournament engine** — fixtures, points tables, NRR, knockouts.
4. **Graph/social engine** — profiles, follows, search, "looking for", DMs, feed.

Everything else (streaming, store, leaderboards, insights) is built **on top of
the data those four engines produce**. If CricNetra nails #1 and #2 correctly,
the rest is "just" product work.

---

## 1. Identity & Accounts  🟡

| Feature | Notes for CricNetra |
|---|---|
| Mobile-number identity (unique player key) | Phone = primary key for a human. Critical: a player exists *before* they register (added by a team), then "claims" the account. |
| OTP login + PIN fallback | PIN lets you resume scoring on another phone with no signal. |
| Verified vs **unverified** players | Huge concept. Unverified = a stub created by someone else. Can't claim records, be MoM, score, or be admin until they verify via OTP. |
| Cross-device resume | Match state must live server-side (or sync) so a match started on phone A resumes on phone B. |
| Multi-language | i18n from day one is cheaper than retrofitting. |
| No account deletion (stats integrity) | Because stats are shared across matches, deleting a user would corrupt others' scorecards. Design soft-delete only. |

**Data:** `users`, `phone_index`, `verification_status`, `auth_sessions`, `pins`.

---

## 2. Player Profile & Stats  🔴

| Feature | Notes |
|---|---|
| "International-grade" career profile | Batting/bowling/fielding aggregates across every match ever. |
| Career stats | Matches, innings, runs, balls, SR, avg, 50s/100s, HS, wickets, economy, best bowling, catches, stumpings, run-outs. |
| Per-format / per-ball-type splits | Leather vs tennis, T20 vs T10, etc. CricHeroes segments these. |
| Skill tags & batting/bowling style | Right/left hand, pace/spin, role. |
| Featured profile, badges, challenges | Gamification layer. |

**Why 🔴:** stats are *derived* from balls but must be **incrementally
maintained** (you can't re-aggregate every player's whole career on each ball).
And **edits to a finished scorecard must ripple** into every affected aggregate.
This is the #1 place clones get wrong.

**Data:** `player_career_stats` (materialized), `player_format_stats`, `badges`, `skills`.

---

## 3. Teams  🟢

| Feature | Notes |
|---|---|
| Create team (name, location, logo) | Owner + admin roles. |
| Add players by phone/contacts | Creates unverified stubs if the number is new. |
| Captain designation, member removal | Owner/admin only. |
| Team-level stats & history | Aggregated like player stats. |

**Data:** `teams`, `team_members(role)`, `team_stats`.

---

## 4. Scoring Engine  🔴🔴  *(the core — get this right first)*

This is the heart. Everything downstream is worthless if the ball log is wrong.

### Match setup flow
1. Pick two teams → Playing XI for each.
2. Toss (real or **virtual coin**) → winner elects bat/bowl.
3. Match config / rules (see Module 5).
4. Choose striker, non-striker, opening bowler.

### Per-ball inputs the engine must capture
- **Runs:** 0,1,2,3,4,6 (and odd values for gully variants like "1-run declare").
- **Extras:** wide, no-ball (+ free hit), bye, leg-bye — each with its own
  run-accounting and whether it consumes a legal ball.
- **Wicket:** bowled, caught, caught-behind, caught & bowled, LBW, run-out,
  stumped, hit-wicket, retired hurt, retired out, obstructing the field,
  hit ball twice, timed out. Each attributes credit differently
  (bowler vs fielder vs nobody) and some don't count a ball faced as "out".
- **Fielding detail:** which fielder caught/ran-out, dropped catch, runs saved/missed.
- **Penalty/bonus runs.**
- **Strike rotation** (auto on odd runs / end of over, but manually overridable).
- **UNDO** — must perfectly reverse the last event, including derived state.

### Engine responsibilities (state machine)
- Track: over.ball, legal-ball count, striker/non-striker, bowler, current
  partnership, innings score/wickets, extras breakdown, fall-of-wickets,
  this-over sequence, free-hit flag, powerplay state.
- Enforce: over completion (6 *legal* balls), innings end (overs done / all out /
  declaration / target chased / DLS), bowler can't bowl consecutive overs.
- Emit: an **append-only event log** (the source of truth) + a **derived
  scorecard** (projection). Wagon-wheel needs an (x,y) shot coordinate per
  scoring ball; Manhattan/worm need per-over and cumulative series.

### Live editing
- Edit a delivery mid-match (re-mark wide→dot, change bowler with stat
  adjustment, change batter, manual strike, adjust total overs in 1st innings).
- Edit/delete a **completed** scorecard → must re-derive stats.

**Architecture recommendation for CricNetra:** model the match as **event
sourcing**. Store an immutable `ball_events` log; the scorecard, stats, wagon
wheel, and charts are all **projections** you can rebuild. UNDO = pop last event
+ replay. Edits = insert/replace event + replay from that point. This single
decision makes UNDO, live-edit, and stat-rippling tractable instead of nightmarish.

**Data:** `matches`, `innings`, `ball_events` (append-only), `match_state`
(current projection), `partnerships`, `fall_of_wickets`.

---

## 5. Rules / Match-Config Engine  🔴  *(CricNetra's headline differentiator)*

CricHeroes already supports a lot of customization; this is where you said you
want to go further ("make their custom rule"). Treat the rulebook as **data, not
code** so users can compose formats.

Configurable dimensions CricHeroes exposes (and you should generalize):
- Overs per innings; players per side (not always 11 → box/gully).
- **Ball type:** leather / tennis / other (affects stat segmentation).
- **Powerplay overs** (fielding-restriction ranges).
- **No-ball** → run penalty + **free hit** on/off; what counts as no-ball.
- **Wide** rules (line strictness varies in tennis-ball cricket).
- **Last Man Stands** (indoor: last batter bats on alone).
- **DLS / VJD** rain methods.
- **Super over** for ties.
- Byes/leg-byes allowed or not; declaration allowed; follow-on.
- Format presets: Test, ODI(50), T20, T10, The Hundred, box/indoor, gully.

**CricNetra opportunity:** a **Rule Template Builder** — a JSON schema where an
organizer toggles/edits rules, saves a named template ("Society Night Box
Cricket — 6 players, 5 overs, last-man-stands, no LBW, one-tip-one-hand catch"),
and reuses it. Validate rules at match-create time; feed them into the scoring
state machine as parameters. This is a genuine wedge against CricHeroes.

**Data:** `rule_templates(json schema)`, `match_rules` (snapshot per match).

---

## 6. Tournaments & Leagues  🔴

| Feature | Notes |
|---|---|
| Create tournament (details, teams, scorers, officials) | Multi-role admin. |
| **Auto-schedule generator** | Generate fixtures for league / groups / knockout in seconds. |
| Formats | Round-robin, multi-group, knockout, league+playoffs. |
| **Points table** | W/L/T/NR points, bonus points (configurable). |
| **NRR calculation** | Auto net-run-rate; "what do we need to qualify" helper. |
| Boundary tracker, leaderboards, MoM, media, sponsors | Tournament microsite. |
| Public tournament page (web) | Shareable URL with live scores. |

**Why 🔴:** fixture generation (esp. balanced round-robins and bracket
progression) and **correct NRR** are fiddly. Knockout brackets must auto-advance
winners.

**Data:** `tournaments`, `tournament_teams`, `groups`, `rounds`, `fixtures`,
`standings`, `points_rules`.

---

## 7. Leaderboards & Rankings  🟡

City/state/national leaderboards, table-toppers, scorer leaderboard, top
performers with **daily/weekly/monthly** windows. These are heavy read
aggregations → precompute with scheduled jobs into ranking tables; don't compute
on request.

**Data:** `leaderboard_snapshots(scope, window, metric)`.

---

## 8. CricInsights (Analytics)  🟡 *(PRO)*

Strengths/weaknesses, current form, preferred batting position, bowling
analysis, head-to-head player comparison, opponent scouting. All derivable from
the ball-event log — this is where rich data pays off. Gate behind PRO.

---

## 9. Live Streaming & Highlights  🔴 *(hard / can defer)*

| Feature | Notes |
|---|---|
| Go Live with **phone** | In-app camera → stream. |
| Go Live with **camera** (OBS/vMix) | Pro broadcast software + score-ticker overlay. |
| **Score overlay / auto-animations** | Real-time graphics for 4/6/wicket/milestones, driven by the live score feed. |
| **AI-generated highlights** | Clip the video at scoring-event timestamps from the ball log. |

**Why 🔴:** real media infrastructure (RTMP ingest, transcoding, CDN, overlay
compositing). Recommend **deferring** — integrate a third-party (Mux/Cloudflare
Stream/Agora) later. The *overlay* and *highlight-timestamping* are the clever
bits and only need your ball-event timestamps.

---

## 10. Community, Networking & Discovery  🟡

Profiles you can follow, **CricHeroes DM**, **"Looking For"** (players,
opponents, umpires, scorers), smart search (players/teams/tournaments/grounds/
academies) with voice search. This is a classic social graph + search-index
problem (Postgres FTS or Elastic/Meilisearch).

**Data:** `follows`, `dm_threads`, `messages`, `looking_for_posts`, `search_index`.

---

## 11. Content Feed  🟢🟡

Cricket Stories (trivia, news, polls, quizzes), top performers, tips. A CMS +
feed-ranking surface. Low priority for a scoring MVP.

---

## 12. Commerce & Money  🟡

- **Store** — branded apparel/gear (full e-commerce or print-on-demand).
- **CricPay** — split/track team expenses (ground fees, registration, kit).
- **Sponsors / Super Sponsor** — sponsor slots on tournament pages.

All deferrable past MVP, but **CricPay** is a sticky, easy-to-love feature.

---

## 13. Notifications & Device Integrations  🟡

Push notifications, **Apple Watch** live scores, **iOS Live Activity** (lock-screen
scores), social sharing to WhatsApp/FB. Live Activity/Watch are platform-specific
polish; do them after the web/core works.

---

## 14. Monetization Surfaces  🟡

- **PRO** subscription (insights, PRO Club community, premium overlays).
- **Your App / Your Web** — white-label for associations/academies.
- **Official** matches from ICC associations & BCCI state bodies (B2B deals,
  verified data, not something you build — you earn).

---

## 15. Trust, Integrity & Admin  🟡

- Auto MoM/Best Batter/Best Bowler algorithm (manual override only in tournaments).
- Anti-favoritism rules (no manual MoM in individual matches).
- Auto-cleanup of demo/test matches.
- Stats can't be reset (integrity), photos must be cricket-related (moderation).
- Scorer access transfer / role management.

---

## What makes this genuinely hard (so we plan for it)

1. **Event-sourced scoring** — the only sane way to get UNDO, live-edit, and
   editable history without corrupting stats. **Build this foundation first.**
2. **Incremental, reversible stat aggregation** — edits must ripple correctly.
3. **NRR + fixture/bracket generation** — small but bug-prone; needs tests.
4. **The "unverified stub player"** identity model — affects everything.
5. **Offline-first scoring** — scorers often have no signal on the ground;
   the app must score offline and sync. (CricHeroes does this via PIN resume.)

---

## Suggested build order (de-risked)

1. **Scoring engine + rules engine** (Modules 4 & 5) with a thin UI — prove the
   ball-event log, projections, UNDO, and a Test/T20/box-cricket template.
2. **Identity + Teams + Players** (1, 3) and the verified/unverified model.
3. **Stats aggregation** (2) as projections off the event log.
4. **Tournaments** (6): fixtures, points table, NRR, knockouts.
5. **Public web** scorecard + tournament pages (shareable, SEO).
6. **Leaderboards & Insights** (7, 8) as precomputed reads.
7. Social/discovery (10), content (11), commerce (12).
8. Streaming/highlights (9) via a third party.

> Rule of thumb: if Modules 4–6 are correct and tested, CricNetra is already a
> real product. Everything after is growth.
