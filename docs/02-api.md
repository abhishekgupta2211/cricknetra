# CricNetra API Reference (`/api/v1`)

Base URL (dev): `http://127.0.0.1:8023` (Docker: `http://localhost:8000`)
Interactive docs (Swagger UI): `GET /docs` · OpenAPI JSON: `GET /openapi.json`

All bodies are JSON. This file documents the most-used shapes (auth + scoring) in
detail and indexes the rest; `/docs` is the exhaustive, always-current source.

---

## Conventions

- **Auth.** Most reads are public. Mutations and contact-bearing reads need a
  bearer token: `Authorization: Bearer <access_token>` (see [Auth](#auth)).
- **Errors** share one envelope: `{"detail": ..., "request_id": "..."}`.
  - `400` invalid setup · `401` missing/invalid token · `403` role/ownership not
    allowed · `404` not found · `409` illegal scoring action · `422` body
    validation · `429` rate-limited. Every response also carries an
    `X-Request-ID` header for log correlation.
- **Capabilities & ownership.** What a role may *create* is capability-gated
  (`organizer`/`admin` create matches & tournaments, etc.); you can always
  edit/score/delete resources *you* own. Admin bypasses both.
- **Scoring responses.** Every mutating match call returns the **full
  `MatchState`** (both innings) so a client renders from one response. Strike and
  overs are server-derived — the client only sends the raw delivery.

---

## Auth

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | create an account (`role` ∈ player, general_user, or an elevated role pending admin approval) |
| POST | `/auth/login` | `{identifier, password}` → `{access_token, token_type, refresh_token}` |
| POST | `/auth/refresh` | `{refresh_token}` → new token pair (refresh is **rotated**) |
| POST | `/auth/logout` | `{refresh_token}` → revokes it |
| GET | `/auth/me` | current user (role, `capabilities[]`, records, `role_pending`) |
| POST | `/auth/verify/request` · `/auth/verify/confirm` | mobile OTP verification |
| POST | `/auth/password/forgot` · `/auth/password/reset` | password reset by code |
| GET/POST/PATCH | `/auth/profile` | extended profile (address/city/…); POST/PATCH gated to self |
| POST/DELETE | `/auth/profile/photo` | upload / remove the profile picture |

Access tokens are short-lived (30 min); the refresh token (30 days) is rotated on
every use and revoked on logout. With `CRICNETRA_AUTH_DEV_DELIVERY=true` the OTP /
reset code is returned in the response (`dev_code`/`dev_token`) for testing.

```jsonc
// POST /auth/login
{ "identifier": "9876543210", "password": "secret" }
// → 200
{ "access_token": "eyJ…", "token_type": "bearer", "refresh_token": "…" }
```

---

## Matches (scoring)

### `POST /matches` → `201` `MatchState`  *(needs match.create or admin)*
Create from a preset **or** a full custom rulebook. Sender becomes the owner.
```jsonc
{
  "team_a": "Lions", "team_b": "Tigers",
  "format_id": "t20",            // used when `rules` is omitted
  "bat_first": "a",              // "a" | "b"
  "squad_a": ["L1","L2","…"],    // optional; auto-generated if omitted
  "squad_b": null,
  "rules": null,                 // optional full MatchRules; overrides format_id
  "squad_a_ids": null, "squad_b_ids": null,   // link real players (career stats)
  "team_a_id": null, "team_b_id": null
}
```

### `GET /matches` → `MatchSummary[]`  ·  `GET /matches/{id}` → `MatchState` (`404`)

### `POST /matches/{id}/bowler` → `MatchState`  *(scorer)*
`{ "bowler": "Tigers 1" }` — required at the start of each over.

### `POST /matches/{id}/balls` → `MatchState`  ·  `409`  *(scorer)*
Record one delivery. `value` is interpreted per `action`:

| action | `value` means | other fields |
|---|---|---|
| `runs` | runs off the bat | `wagon_x`, `wagon_y` (−1..1) optional — wagon wheel |
| `wide` | extra runs run (penalty auto-added) | |
| `no_ball` | runs off the bat (penalty auto-added) | |
| `bye` / `leg_bye` | byes / leg-byes run | |
| `wicket` | runs off bat on the ball (usually 0) | `dismissal` (required), `batter_out` (`striker`/`non_striker`), `fielder` |

`dismissal` ∈ `bowled, caught, caught_behind, caught_and_bowled, lbw, run_out,
stumped, hit_wicket, retired_hurt, retired_out, obstructing_field, hit_ball_twice,
timed_out, boundary_out`. Dismissals disallowed by the format are ignored.

### Other scoring actions *(scorer)*
| Method | Path | Purpose |
|---|---|---|
| POST | `/matches/{id}/undo` | pop the last delivery and replay |
| POST | `/matches/{id}/second-innings` | start the chase (1st must be complete) |
| POST | `/matches/{id}/revised-target` | `{target, overs?}` — DLS rain revision |
| POST | `/matches/{id}/super-over` | start a super over / its reply on a tie |
| DELETE | `/matches/{id}` | delete a match (**admin only**) |

### Live & feeds *(public reads)*
| Method | Path | Purpose |
|---|---|---|
| GET | `/matches/{id}/stream` | **SSE**: pushes `{runs,wickets,overs,done}` on every score change |
| GET | `/matches/{id}/ball-feed` | auto-generated ball-by-ball commentary (projection) |
| GET/POST | `/matches/{id}/commentary` | manual commentary notes (POST needs match.commentate) |
| POST | `/matches/{id}/commentate` | record that you're commentating (member activity) |

### Match officials (per-match umpire approval)
| Method | Path | Purpose |
|---|---|---|
| GET | `/matches/{id}/officials` | officials + your status + `can_score` |
| POST | `/matches/{id}/officials/request` | an umpire requests to officiate |
| POST | `/matches/{id}/officials/{umpire_id}/approve` | owner/admin approves |
| DELETE | `/matches/{id}/officials/{umpire_id}` | decline / remove |

---

## `MatchState` (response shape)

```jsonc
{
  "id": "1",
  "team_a": "Lions", "team_b": "Tigers", "bat_first": "Lions",
  "format_id": "t20", "rules_name": "T20",
  "rules": { /* full MatchRules — the client adapts the scoring pad */ },
  "current_innings": 1,
  "awaiting_bowler": true,            // POST /bowler before /balls
  "available_bowlers": ["Tigers 1","…"],
  "can_start_second_innings": false,
  "needs_super_over": false, "awaiting_super_second": false,
  "result": null,                     // e.g. "Tigers won by 6 run(s)"
  "innings": [ Innings, Innings? ]    // + super-over innings appended
}
```

### `Innings`
```jsonc
{
  "batting_team":"Lions","bowling_team":"Tigers",
  "runs":48,"wickets":2,"legal_balls":36,"overs_str":"6.0",
  "max_overs":20,"max_wickets":10,
  "extras":{"wides":3,"no_balls":1,"byes":0,"leg_byes":2,"penalty":0,"total":6},
  "run_rate":8.0,
  "batters":[{"name":"L1","order":1,"runs":30,"balls":20,"fours":4,"sixes":1,
              "out":true,"how_out":"bowled","dismissal_text":"b Tigers 1",
              "on_strike":false,"has_batted":true,"strike_rate":150.0}],
  "bowlers":[{"name":"Tigers 1","order":1,"overs":"3.0","maidens":0,"runs":22,
              "wickets":1,"economy":7.33,"wides":1,"no_balls":0}],
  "fall_of_wickets":[{"wicket":1,"score":30,"batter_out":"L1","over":"3.2"}],
  "this_over":["1","4","Wd","6","•","W"],
  "manhattan":[8,12,6,9,7,6],         // runs per over
  "worm":[8,20,26,35,42,48],          // cumulative
  "wagon":[{"x":0.5,"y":0.7,"runs":4,"batter":"L1","over":"3.1"}],  // marked shots
  "striker":"L3","non_striker":"L2","bowler":"Tigers 1",
  "free_hit":false,"is_complete":false,
  "target":null,"required_runs":null,"balls_remaining":null,
  "required_run_rate":null,"result_note":null,
  "current_over":7,"in_powerplay":false,"powerplay_label":null,
  "fielders_outside_limit":null,"is_super_over":false
}
```

`this_over` symbols: `•`=dot, `1..6`=runs, `Wd`/`n+Wd`=wide, `Nb`/`n+Nb`=no-ball,
`nB`=byes, `nL`=leg-byes, `W`/`n+W`=wicket.

---

## Presets & rule templates

| Method | Path | Purpose |
|---|---|---|
| GET | `/presets` · `/presets/{format_id}` | built-in formats; full editable `MatchRules` |
| GET/POST | `/rule-templates` | list / save a named custom rulebook *(rules.manage)* |
| GET/DELETE | `/rule-templates/{id}` | fetch / delete a saved template |

`GET /presets/{id}` returns the editable `MatchRules` the builder loads, tweaks,
and posts back inside `POST /matches` as `rules`.

---

## Players · Teams · Tournaments · Stats

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/players` | list / create *(team.create)*; `PATCH`/`DELETE /players/{id}` |
| GET | `/players/{id}/stats` · `/players/{id}/insights` | career stats; batting/bowling breakdowns |
| GET/POST/DELETE | `/players/{id}/photo` | player photo |
| GET/POST | `/teams` | list / create; `GET/DELETE /teams/{id}`; `…/members`, `…/photo`, `…/stats` |
| GET/POST | `/tournaments` | list / create (round-robin or knockout); `GET/DELETE /tournaments/{id}` |
| POST | `/tournaments/fixtures/{fixture_id}/start` | pick XIs → create & link a match |
| GET | `/tournaments/{id}/squads` | per-tournament squads |
| POST/DELETE | `/tournaments/{id}/teams/{team_id}/squad[/{player_id}]` | register / unregister a player |
| GET | `/leaderboards` | runs/avg/SR/sixes/wickets/econ/MVP/catches/best-bowling boards |
| GET | `/insights/compare?player_a=&player_b=` | head-to-head |

---

## Community

| Method | Path | Purpose |
|---|---|---|
| GET | `/search?q=` | unified search (players, teams, tournaments, members*) |
| GET | `/users?role=` | members directory *(auth: shows contact info + records)* |
| GET | `/users/{id}/photo` | a member's photo |
| POST/DELETE | `/social/follow/{user_id}` | follow / unfollow |
| GET | `/social/following` · `/social/feed` | who you follow · activity feed |
| GET | `/social/notifications[/unread]` | notifications |
| POST | `/social/notifications/read` · DELETE `/social/notifications/{id}` | mark read · delete |

\* members appear in search only when a valid token is sent.

---

## Admin & meta

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/role-requests` | pending elevated-role sign-ups *(admin)* |
| POST | `/admin/role-requests/{user_id}/approve` · `…/reject` | approve / reject *(admin)* |
| GET | `/health` | readiness — pings the DB; `503` when degraded |
| GET | `/health/live` | liveness — process is up |

(`GET /healthz`, outside `/api/v1`, is the container liveness probe.)
