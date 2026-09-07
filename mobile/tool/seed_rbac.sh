#!/usr/bin/env bash
# Build the multi-organizer world the authorization rules are written for, on a
# running server, so the UI can be exercised against something real:
#
#   ADMIN
#    ├── Organizer A (Prayagraj)  → Prayagraj Premier League
#    │     ├── Umpire A, Commentator A
#    │     └── Players A
#    └── Organizer B (Lucknow)    → Lucknow Challenge
#          ├── Umpire B, Commentator B
#          └── Players B
#
#   bash mobile/tool/seed_rbac.sh [base-url]
#
# Run it after seed_demo.sh, against a server started with an in-memory store
# and CRICNETRA_SEED_ADMIN=demoadmin:demo1234. Every account below uses the
# password "demo1234" — these are throwaway fixtures for a local box, not
# credentials for anything real.
set -euo pipefail

BASE="${1:-http://127.0.0.1:8032}"
API="$BASE/api/v1"
PW="demo1234"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

login() {
  curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d "{\"identifier\":\"$1\",\"password\":\"$2\"}" |
    python -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
}

# register <full name> <username> <mobile> -> user id
register() {
  curl -s -X POST "$API/auth/register" -H 'Content-Type: application/json' \
    -d "{\"full_name\":\"$1\",\"username\":\"$2\",\"mobile_no\":\"$3\",\"password\":\"$PW\"}" |
    python -c 'import sys,json;d=json.load(sys.stdin);print(d.get("id",""))'
}

as_admin() { curl -s -X "$1" "$API$2" -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' ${3:+-d "$3"}; }
as_user()  { curl -s -X "$2" "$API$3" -H "Authorization: Bearer $1" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

say "Signing in as the seed admin"
ADMIN=$(login demoadmin "$PW")
[ -n "$ADMIN" ] || { echo "  could not sign in — is the server seeded with demoadmin?"; exit 1; }

say "Accounts (every signup is a general user until an admin grants a role)"
ORG_A=$(register "Abhishek Organizer" orga 9810000001)
ORG_B=$(register "Bhavna Organizer"  orgb 9810000002)
UMP_A=$(register "Rahul Umpire"      umpa 9810000003)
UMP_B=$(register "Sameer Umpire"     umpb 9810000004)
COM_A=$(register "Anita Commentator" coma 9810000005)
COM_B=$(register "Vikram Commentator" comb 9810000006)
echo "  organizers $ORG_A, $ORG_B · umpires $UMP_A, $UMP_B · commentators $COM_A, $COM_B"

say "Areas and organizations"
AREA_P=$(as_admin POST /admin/areas '{"name":"Prayagraj","state":"Uttar Pradesh"}' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
AREA_L=$(as_admin POST /admin/areas '{"name":"Lucknow","state":"Uttar Pradesh"}' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
ORG_P=$(as_admin POST /admin/organizations "{\"name\":\"XYZ Sports\",\"area_id\":\"$AREA_P\"}" | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
ORG_L=$(as_admin POST /admin/organizations "{\"name\":\"Awadh Cricket Board\",\"area_id\":\"$AREA_L\"}" | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "  areas $AREA_P, $AREA_L · organizations $ORG_P, $ORG_L"

say "Appointing the two organizers"
as_admin POST /admin/organizers "{\"user_id\":\"$ORG_A\",\"area_id\":\"$AREA_P\",\"organization_id\":\"$ORG_P\"}" >/dev/null
as_admin POST /admin/organizers "{\"user_id\":\"$ORG_B\",\"area_id\":\"$AREA_L\",\"organization_id\":\"$ORG_L\"}" >/dev/null

say "Each organizer builds their own competition"
TOK_A=$(login orga "$PW")
TOK_B=$(login orgb "$PW")

# team <token> <name> -> id
team() { as_user "$1" POST /teams "{\"name\":\"$2\"}" | python -c 'import sys,json;print(json.load(sys.stdin)["id"])'; }

A1=$(team "$TOK_A" "Prayagraj Kings")
A2=$(team "$TOK_A" "Sangam Warriors")
B1=$(team "$TOK_B" "Lucknow Nawabs")
B2=$(team "$TOK_B" "Awadh Titans")

TOURN_A=$(as_user "$TOK_A" POST /tournaments \
  "{\"name\":\"Prayagraj Premier League\",\"format\":\"round_robin\",\"format_id\":\"t20\",\"team_ids\":[\"$A1\",\"$A2\"]}" |
  python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
TOURN_B=$(as_user "$TOK_B" POST /tournaments \
  "{\"name\":\"Lucknow Challenge\",\"format\":\"round_robin\",\"format_id\":\"t20\",\"team_ids\":[\"$B1\",\"$B2\"]}" |
  python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "  tournament A=$TOURN_A · tournament B=$TOURN_B"

say "Each organizer staffs their own competition"
as_user "$TOK_A" POST "/tournaments/$TOURN_A/staff/umpires" "{\"user_id\":\"$UMP_A\"}" >/dev/null
as_user "$TOK_A" POST "/tournaments/$TOURN_A/staff/commentators" "{\"user_id\":\"$COM_A\"}" >/dev/null
as_user "$TOK_B" POST "/tournaments/$TOURN_B/staff/umpires" "{\"user_id\":\"$UMP_B\"}" >/dev/null
as_user "$TOK_B" POST "/tournaments/$TOURN_B/staff/commentators" "{\"user_id\":\"$COM_B\"}" >/dev/null

say "The rule that matters: A cannot reach B's competition"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X PATCH "$API/tournaments/$TOURN_B/settings" \
  -H "Authorization: Bearer $TOK_A" -H 'Content-Type: application/json' -d '{"dls_enabled":true}')
echo "  A patches B's settings -> $CODE  (expect 403)"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/tournaments/$TOURN_B/staff/umpires" \
  -H "Authorization: Bearer $TOK_A" -H 'Content-Type: application/json' -d "{\"user_id\":\"$UMP_A\"}")
echo "  A staffs B's competition -> $CODE  (expect 403)"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$API/tournaments/$TOURN_B" \
  -H "Authorization: Bearer $TOK_A")
echo "  A deletes B's competition -> $CODE  (expect 403)"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$API/tournaments/$TOURN_A/staff" -H "Authorization: Bearer $TOK_A")
echo "  A reads A's own staff    -> $CODE  (expect 200)"

say "Sign in with any of these to look around"
cat <<TXT
  admin        demoadmin / $PW
  organizer A  orga      / $PW   (Prayagraj Premier League)
  organizer B  orgb      / $PW   (Lucknow Challenge)
  umpire A     umpa      / $PW   (staffed on A)
  commentator  coma      / $PW   (staffed on A)
TXT
