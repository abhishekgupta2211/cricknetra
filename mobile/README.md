# CricNetra — Flutter app

The mobile client for CricNetra. It covers the whole product the website
covers: ball-by-ball scoring with a configurable rulebook, teams and players,
leagues and knockouts, career statistics, and the community side.

The scoring engine lives on the server. Every delivery is appended to an event
log and the full match state is folded back and returned, so this app never
computes a score — it renders whatever the API sends. That is why undo, editing
a past ball and correcting a finished scorecard can never corrupt a statistic.

## Running it

The API address is baked in at build time.

```bash
flutter run --dart-define=CRICNETRA_API=https://your-host
```

With no override the app guesses a local backend: `10.0.2.2:8023` on an Android
emulator (which is how the emulator reaches the host machine) and
`127.0.0.1:8023` everywhere else. Override `CRICNETRA_PORT` to change the port
without spelling out the whole URL.

### Against a backend on your own machine

A physical phone cannot reach your machine's `127.0.0.1`, and a LAN address is
often blocked by the Windows firewall. The reliable route is an ADB tunnel:

```bash
adb reverse tcp:8023 tcp:8023
```

Then run with `--dart-define=CRICNETRA_API=http://127.0.0.1:8023`, and the
phone's localhost resolves to your machine.

### A throwaway backend with demo data

For exercising the app by hand you want a server you can wipe. Start one on an
in-memory store with a seed admin:

```bash
CRICNETRA_DATABASE_URL="" CRICNETRA_SEED_ADMIN="demoadmin:demo1234" CRICNETRA_AUTH_DEV_DELIVERY=true CRICNETRA_CORS_ORIGINS='["*"]' backend/venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --port 8032
```

then fill it:

```bash
bash mobile/tool/seed_demo.sh http://127.0.0.1:8032
```

That gives you two full squads, a live T20 two overs in with shot directions
recorded, a league, grounds and a classifieds post — enough for every screen to
have something real on it. Sign in as `demoadmin` / `demo1234`. Restart the
server for a clean slate; the script is not idempotent.

### Release build

```bash
flutter build apk --release --dart-define=CRICNETRA_API=https://your-host
```

## What is in here

```
lib/
  core/
    api/          transport, typed API surface, build-time config
    auth/         session state and capability checks
    models/       every server DTO, hand-written and defensive
    router/       go_router routes and the sign-in redirect
    storage/      the JWT pair, in the platform keystore
    theme/        twelve palettes, light and dark
    utils/        formatting: relative times, cricket numbers
    widgets/      the shared kit every screen is built from
  features/
    account/      profile, verification, claiming a player profile
    admin/        role approvals, broadcasts, engagement
    auth/         sign in, register, password reset
    highlights/   the cross-match clip gallery
    home/         live matches, quick actions, top scorers
    leaderboards/ twelve boards, plus head-to-head comparison
    looking_for/  the classifieds board
    matches/      the scoring console — the heart of the app
    messages/     direct messages
    more/         everything without its own tab
    network/      member directory and activity feed
    notifications/
    players/      roster, career stats, insights, splits
    rules/        the rule builder and saved rulebooks
    search/       one search across everything
    settings/     look, notifications, security
    shell/        the five-tab frame
    teams/        teams and squads
    tools/        calculators, toss, picker wheel
    tournaments/  leagues, groups, knockouts, fixtures, squads
    venues/       grounds and academies
```

## Two things worth knowing before you change anything

**The models are the contract.** Every screen reads typed models, never a raw
map. An earlier version of this app passed `Map<String, dynamic>` into widgets
with `?? 'default'` on each read; when a key name drifted from the server, the
screen rendered zeros instead of failing, and fifteen screens quietly showed
wrong data for months. If you add a field, add it to the model in
`lib/core/models/` and check the name against `backend/app/schemas/`.

**`batter_out` is a keyword, not a name.** The server validates it against
`^(striker|non_striker)$`. Sending a player's name there is rejected with a 422,
which is how wickets became unrecordable in the previous client.

## Tests

```bash
flutter test
```

The suite covers the parts where a silent mistake is expensive, and every case
in it is one that was actually wrong at some point:

- **The contract.** A rulebook survives a round trip through JSON without
  losing a setting the engine reads; the wicket payload uses the literal
  keyword; overs entered as `12.3` mean twelve overs and three balls.
- **The scoring surface** (`signed_in_screens_test.dart`). The pad offers the
  keys the rulebook allows and hides the rest; a rule-out format swaps the six
  for a dismissal, but a free hit restores it, because the engine drops a
  boundary-out on a free hit without a word; runs completed on a run out are
  carried, and are not offered for a dismissal that ends the ball.
- **Who is fielding** (`fielding_names_test.dart`). The catcher dropdown must
  list the side actually in the field — not `available_bowlers`, which the
  server prunes to who may bowl next, so a bowler who has bowled out would
  vanish and could never be credited with a catch.
- **The look** (`theme_test.dart`). A fresh install follows the phone, and a
  light and a dark palette are remembered separately.
- **Viewers** (`viewer_gating_test.dart`). Somebody who cannot create a match
  is not offered a button that leads to a locked screen.

`test/support/fake_api.dart` holds the fixtures, captured from a real server,
so a screen that renders in a test renders against the real shapes.
