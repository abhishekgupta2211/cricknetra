#!/usr/bin/env bash
# Seed a running CricNetra backend with the demo data the app is exercised
# against: two squads, a live T20 innings mid-over, a league, and some grounds.
#
#   bash mobile/tool/seed_demo.sh [base-url]
#
# Expects the server to have been started with an in-memory store and
# CRICNETRA_SEED_ADMIN=demoadmin:demo1234. Running it twice creates duplicates,
# so restart the server for a clean slate.
set -euo pipefail

BASE="${1:-http://127.0.0.1:8032}"
API="$BASE/api/v1"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

say "Signing in as the seed admin"
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"demoadmin","password":"demo1234"}' |
  python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
AUTH=(-H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json')

post() { curl -s -X POST "$API$1" "${AUTH[@]}" -d "$2"; }
id_of() { python -c 'import sys,json;print(json.load(sys.stdin)["id"])'; }

say "Players"
# Two full-ish squads, so a scorecard has real names on both sides.
MUMBAI_NAMES=(
  "Rohit Sharma" "Virat Kohli" "Suryakumar Yadav" "KL Rahul" "Hardik Pandya"
  "Ravindra Jadeja" "Rishabh Pant" "Jasprit Bumrah" "Mohammed Shami"
  "Yuzvendra Chahal" "Shubman Gill"
)
CHENNAI_NAMES=(
  "Ruturaj Gaikwad" "Devon Conway" "Ajinkya Rahane" "Shivam Dube"
  "Ravindra Ashwin" "MS Dhoni" "Deepak Chahar" "Arshdeep Singh"
  "Prasidh Krishna" "Avesh Khan" "Rinku Singh"
)

declare -a MUMBAI_IDS CHENNAI_IDS
for n in "${MUMBAI_NAMES[@]}"; do
  MUMBAI_IDS+=("$(post /players "{\"name\":\"$n\"}" | id_of)")
done
for n in "${CHENNAI_NAMES[@]}"; do
  CHENNAI_IDS+=("$(post /players "{\"name\":\"$n\"}" | id_of)")
done
echo "  ${#MUMBAI_IDS[@]} + ${#CHENNAI_IDS[@]} players"

say "Teams"
TEAM_A=$(post /teams '{"name":"Mumbai Strikers","location":"Mumbai"}' | id_of)
TEAM_B=$(post /teams '{"name":"Chennai Kings","location":"Chennai"}' | id_of)
for pid in "${MUMBAI_IDS[@]}"; do
  post "/teams/$TEAM_A/members" "{\"player_id\":\"$pid\"}" >/dev/null
done
for pid in "${CHENNAI_IDS[@]}"; do
  post "/teams/$TEAM_B/members" "{\"player_id\":\"$pid\"}" >/dev/null
done
echo "  $TEAM_A, $TEAM_B"

say "Grounds and academies"
post /venues '{"name":"Wankhede Ground","kind":"ground","city":"Mumbai","contact":"9820011223"}' >/dev/null
post /venues '{"name":"Shivaji Park Academy","kind":"academy","city":"Mumbai","contact":"9820011224"}' >/dev/null

# A match must carry the player IDS as well as the names, or nothing it
# produces reaches anybody's career record — the link table is keyed by id.
match_body() {
  python - "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" <<'PY'
import json, sys
names_a, ids_a, names_b, ids_b, tournament, no, team_a_id, team_b_id = sys.argv[1:9]
print(json.dumps({
    "team_a": "Mumbai Strikers", "team_b": "Chennai Kings",
    # The team ids matter as much as the player ids: without them nothing the
    # match produces reaches either team's record, and team stats read zero.
    "team_a_id": team_a_id, "team_b_id": team_b_id,
    "format_id": "t20", "bat_first": "a",
    "toss_winner": "a", "toss_decision": "bat",
    "squad_a": names_a.split("|"), "squad_b": names_b.split("|"),
    "squad_a_ids": ids_a.split("|"), "squad_b_ids": ids_b.split("|"),
    "venue": "Wankhede Ground", "tournament": tournament, "match_no": no,
}))
PY
}

join() { local IFS="|"; echo "$*"; }

say "A live T20 match, two overs in"
MATCH=$(post /matches "$(match_body   "$(join "${MUMBAI_NAMES[@]}")" "$(join "${MUMBAI_IDS[@]}")"   "$(join "${CHENNAI_NAMES[@]}")" "$(join "${CHENNAI_IDS[@]}")"   "City Premier League" "1" "$TEAM_A" "$TEAM_B")" | id_of)
echo "  match $MATCH"

ball() { post "/matches/$MATCH/balls" "$1" >/dev/null; }

# Over 1 — Deepak Chahar. A wide, a four, and a six with shot directions, so
# the wagon wheel and the charts have something real in them.
post "/matches/$MATCH/bowler" '{"bowler":"Deepak Chahar"}' >/dev/null
ball '{"action":"runs","value":1}'
ball '{"action":"wide"}'
ball '{"action":"runs","value":4,"wagon_x":0.62,"wagon_y":0.48}'
ball '{"action":"runs","value":0}'
ball '{"action":"runs","value":6,"wagon_x":-0.35,"wagon_y":0.85}'
ball '{"action":"leg_bye","value":1}'
ball '{"action":"runs","value":1}'

# Over 2 — Arshdeep Singh, including the wicket the app shows in key moments.
post "/matches/$MATCH/bowler" '{"bowler":"Arshdeep Singh"}' >/dev/null
ball '{"action":"runs","value":2,"wagon_x":0.15,"wagon_y":-0.7}'
ball '{"action":"runs","value":4,"wagon_x":0.8,"wagon_y":0.1}'
ball '{"action":"wicket","dismissal":"bowled","batter_out":"striker"}'
ball '{"action":"runs","value":0}'
ball '{"action":"runs","value":3,"wagon_x":-0.6,"wagon_y":-0.2}'
ball '{"action":"runs","value":1}'

say "A finished match in a second competition"
MATCH2=$(post /matches "$(match_body   "$(join "${MUMBAI_NAMES[@]}")" "$(join "${MUMBAI_IDS[@]}")"   "$(join "${CHENNAI_NAMES[@]}")" "$(join "${CHENNAI_IDS[@]}")"   "Winter Shield" "3" "$TEAM_A" "$TEAM_B")" | id_of)
ball2() { post "/matches/$MATCH2/balls" "$1" >/dev/null; }

# Bowl a side out. An over ends after six legal balls and the server then waits
# for the next bowler, so the loop has to re-pick one or the innings stalls
# half-dismissed — which is how this match used to end up with no result.
bowl_out() {
  for _round in 1 2 3 4 5 6 7 8; do
    local state done_yet next
    state=$(curl -s "$API/matches/$MATCH2")
    done_yet=$(echo "$state" | python -c 'import sys,json;m=json.load(sys.stdin);print("yes" if m.get("result") or m.get("can_start_second_innings") else "no")')
    [ "$done_yet" = "yes" ] && return 0
    next=$(echo "$state" | python -c 'import sys,json;m=json.load(sys.stdin);b=m.get("available_bowlers") or [];print(b[0] if b else "")')
    [ -n "$next" ] && post "/matches/$MATCH2/bowler" "{\"bowler\":\"$next\"}" >/dev/null
    for _b in 1 2 3 4 5 6; do
      ball2 '{"action":"wicket","dismissal":"bowled","batter_out":"striker"}'
    done
  done
}

post "/matches/$MATCH2/bowler" '{"bowler":"Deepak Chahar"}' >/dev/null
for v in 6 4 4 2 6 4; do ball2 "{\"action\":\"runs\",\"value\":$v}"; done
bowl_out
post "/matches/$MATCH2/second-innings" "{}" >/dev/null
bowl_out
echo "  match $MATCH2"

say "A league with both teams"
TOURN=$(post /tournaments "{\"name\":\"City Premier League\",\"format\":\"round_robin\",\"team_ids\":[\"$TEAM_A\",\"$TEAM_B\"]}" | id_of)
echo "  tournament $TOURN"

say "A looking-for post and some commentary"
post /looking-for '{"kind":"player","text":"Need a fast bowler for Sunday league.","location":"Mumbai"}' >/dev/null
post "/matches/$MATCH/commentary" '{"text":"Cracking start from the openers."}' >/dev/null

say "Done"
curl -s "$API/matches/$MATCH" | python -c '
import sys, json
m = json.load(sys.stdin)
i = m["innings"][m["current_innings"] - 1]
print("  {} {}/{} ({})".format(
    i["batting_team"], i["runs"], i["wickets"], i["overs_str"]))
print("  striker {}, bowler {}".format(i.get("striker"), i.get("bowler")))
'
