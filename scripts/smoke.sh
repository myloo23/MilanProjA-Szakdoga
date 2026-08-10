#!/usr/bin/env bash
#
# Local smoke test — the same checks the CI pipeline runs against the container,
# runnable by hand. Every stage must be reproducible locally; this is that stage.
#
#   ./scripts/smoke.sh                        # against localhost:8000
#   ./scripts/smoke.sh http://host:8000       # against anything else
#
set -u

BASE="${1:-http://localhost:8000}"
B=$'\033[1m'; D=$'\033[2m'; R=$'\033[0m'

check() {
  local label="$1"; shift
  printf '\n%s%s%s\n' "$B" "$label" "$R"
  curl -s -w "${D}  → HTTP %{http_code}${R}"'\n' "$@"
}

printf '\n%sSmoke test · %s%s\n' "$B" "$BASE" "$R"

JSON=(-H 'Content-Type: application/json')

# The two hostile bodies, built here rather than pasted, because a literal of
# either would be unreadable and would silently lose its point if someone
# reflowed the file. The nesting is the deepest that fits inside the 64 KiB
# body limit; the padded body is just past it.
NESTED="$(printf '[%.0s' $(seq 1 32000))$(printf ']%.0s' $(seq 1 32000))"
OVERSIZED="{\"pad\": \"$(printf 'x%.0s' $(seq 1 66000))\"}"

check "GET /health"                    "$BASE/health"
check "GET /ready"                     "$BASE/ready"
check "POST /echo · valid JSON"        "${JSON[@]}" -d '{"hi":"there"}' "$BASE/echo"
check "POST /echo · no Content-Type"                -d '{"a":1}'        "$BASE/echo"
check "POST /echo · malformed JSON"    "${JSON[@]}" -d '{"a'            "$BASE/echo"

# Read the status line, not the body: these two used to return 500 and an
# unbounded reflection respectively, and the visible difference is entirely in
# the code. The nested one may answer 200 or 400 depending on how much stack
# this host gives the parser — see ansible/roles/deploy_app/defaults/main.yml.
# Anything 5xx from either is the regression.
check "POST /echo · nested JSON → 200 or 400, never 5xx" \
                                        "${JSON[@]}" --data-binary "$NESTED"    "$BASE/echo"
check "POST /echo · oversized → 413"    "${JSON[@]}" --data-binary "$OVERSIZED" "$BASE/echo"

printf '\n'