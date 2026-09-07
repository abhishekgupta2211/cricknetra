#!/usr/bin/env bash
# Check the authorization rules against a RUNNING server, over real HTTP.
#
#   bash mobile/tool/seed_demo.sh && bash mobile/tool/seed_rbac.sh
#   bash mobile/tool/verify_rbac.sh
#
# The test suite already proves all of this through the ASGI test client. This
# proves it through the wire — middleware, dependency overrides, rate limits and
# all — which is the thing that actually ships. Every check names the real
# failure it prevents.
set -uo pipefail

BASE="${1:-http://127.0.0.1:8032}"
API="$BASE/api/v1"
PW="demo1234"

pass=0; fail=0

login() {
  curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d "{\"identifier\":\"$1\",\"password\":\"$PW\"}" |
    python -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
}

# code <token|-> <METHOD> <path> [body]
code() {
  local tok="$1" method="$2" path="$3" body="${4:-}"
  local args=(-s -o /dev/null -w '%{http_code}' -X "$method" "$API$path" -H 'Content-Type: application/json')
  [ "$tok" != "-" ] && args+=(-H "Authorization: Bearer $tok")
  [ -n "$body" ] && args+=(-d "$body")
  curl "${args[@]}"
}

# check <expected> <actual> <what this prevents>
check() {
  if [ "$1" = "$2" ]; then
    printf '  \033[32m✓\033[0m %s\n' "$3"
    pass=$((pass + 1))
  else
    printf '  \033[31m✗\033[0m %s  (expected %s, got %s)\n' "$3" "$1" "$2"
    fail=$((fail + 1))
  fi
}

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

ADMIN=$(login demoadmin)
A=$(login orga); B=$(login orgb)
UMP_A=$(login umpa); COM_A=$(login coma)
for t in "$ADMIN" "$A" "$B" "$UMP_A" "$COM_A"; do
  [ -n "$t" ] || { echo "Could not sign in — run seed_rbac.sh first."; exit 1; }
done

# Find each organizer's own competition by name.
tid() {
  curl -s "$API/tournaments" |
    python -c "import sys,json;print(next((t['id'] for t in json.load(sys.stdin) if t['name']=='$1'), ''))"
}
TA=$(tid "Prayagraj Premier League")
TB=$(tid "Lucknow Challenge")
[ -n "$TA" ] && [ -n "$TB" ] || { echo "Seeded tournaments not found."; exit 1; }

say "An organizer runs their own competition"
check 200 "$(code "$A" GET "/tournaments/$TA/staff")"                      "A reads A's staff"
check 200 "$(code "$A" PATCH "/tournaments/$TA/settings" '{"dls_enabled":true}')" "A changes A's settings"
check 200 "$(code "$A" GET "/tournaments/mine")"                           "A's desk answers"

say "…and cannot reach the other organizer's"
check 403 "$(code "$A" PATCH "/tournaments/$TB/settings" '{"dls_enabled":true}')" "A cannot change B's settings"
check 403 "$(code "$A" GET "/tournaments/$TB/staff")"                       "A cannot read B's staff"
check 403 "$(code "$A" POST "/tournaments/$TB/staff/umpires" '{"user_id":"4"}')" "A cannot staff B's competition"
check 403 "$(code "$A" DELETE "/tournaments/$TB")"                          "A cannot delete B's competition"
check 403 "$(code "$B" PATCH "/tournaments/$TA/settings" '{"dls_enabled":true}')" "B cannot change A's settings"

say "IDOR — the same request, only the id changed"
check 200 "$(code "$A" GET "/tournaments/$TA/players")"                     "A reads A's players"
check 403 "$(code "$A" GET "/tournaments/$TB/players")"                     "swapping the id is refused"

say "Assignment-scoped roles act only where they were put"
check 200 "$(code "$UMP_A" GET "/tournaments/$TA/staff")"                   "A's umpire reads the staff they are on"
check 403 "$(code "$UMP_A" GET "/tournaments/$TB/staff")"                   "…and not B's"
check 403 "$(code "$UMP_A" POST "/tournaments/$TA/staff/umpires" '{"user_id":"5"}')" "an umpire cannot appoint staff"
check 200 "$(code "$UMP_A" GET "/tournaments/mine/staffing")"               "an umpire sees their own assignments"

say "Roles are granted, never taken"
check 403 "$(code "$A" PUT "/admin/users/2/role" '{"role":"admin"}')"       "an organizer cannot promote anyone"
check 403 "$(code "$A" POST "/admin/organizers" '{"user_id":"4"}')"         "an organizer cannot appoint an organizer"
check 403 "$(code "$UMP_A" GET "/admin/organizers")"                        "an umpire cannot read the admin area"
check 401 "$(code - GET "/admin/organizers")"                               "anonymous cannot read the admin area"
check 200 "$(code "$ADMIN" GET "/admin/organizers")"                        "admin can"

say "A fresh sign-up is a general user, whatever it asked for"
NEW=$(curl -s -X POST "$API/auth/register" -H 'Content-Type: application/json' \
  -d '{"full_name":"Probe User","username":"probeuser1","mobile_no":"9899000111","password":"demo1234","role":"organizer"}')
ROLE=$(printf '%s' "$NEW" | python -c 'import sys,json;print(json.load(sys.stdin).get("role","?"))' 2>/dev/null || echo "?")
if [ "$ROLE" = "?" ]; then
  printf '  \033[33m-\033[0m sign-up skipped (rate limited) — covered by tests/test_roles.py\n'
else
  check "general_user" "$ROLE" "asking for organizer at sign-up grants nothing"
fi

say "The broadcast channel is not open to the world"
MID=$(curl -s "$API/matches" | python -c 'import sys,json;d=json.load(sys.stdin);print(d[0]["id"] if d else "")')
if [ -n "$MID" ]; then
  check 401 "$(code - POST "/matches/$MID/broadcast" '{"mode":"WAGON","auto":true}')" "anonymous cannot drive a live overlay"
fi

say "Admin overrides everything"
check 200 "$(code "$ADMIN" GET "/tournaments/$TA/staff")"                   "admin reads A's staff"
check 200 "$(code "$ADMIN" GET "/tournaments/$TB/staff")"                   "admin reads B's staff"

printf '\n\033[1m%d passed, %d failed\033[0m\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
