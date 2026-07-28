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

check "GET /health"                    "$BASE/health"
check "GET /ready"                     "$BASE/ready"
check "POST /echo · valid JSON"        "${JSON[@]}" -d '{"hi":"there"}' "$BASE/echo"
check "POST /echo · no Content-Type"                -d '{"a":1}'        "$BASE/echo"
check "POST /echo · malformed JSON"    "${JSON[@]}" -d '{"a'            "$BASE/echo"

printf '\n'