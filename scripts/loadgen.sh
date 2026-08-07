#!/usr/bin/env bash
#
# loadgen.sh — produce the incident from the brief, on demand.
#
# Two phases. First a steady baseline of valid requests, so the error-rate
# panel has a denominator and the "before" is visible on the graph. Then a
# burst of malformed JSON at /echo, which the app rejects with 400, the error
# ratio crosses 10%, and the Grafana rule goes Pending and then Firing.
#
# The baseline is not decoration. An error ratio computed against no traffic is
# either 0/0 or 1.0, and both make a demo that proves nothing — the panel has
# to be seen going from healthy to unhealthy, not from blank to red.
#
# This is the sibling of scripts/rollback-drill.sh: a rehearsal you can run
# again rather than a result you are asked to believe. Same standard as §6 of
# PLAN.md — unrehearsed is unclaimable.
#
# Usage:
#   scripts/loadgen.sh                    # 60s baseline, then a 90s burst
#   scripts/loadgen.sh --baseline 30 --burst 120
#   scripts/loadgen.sh --url http://localhost:8000 --rps 5
#   scripts/loadgen.sh --baseline-only    # traffic with no incident

set -euo pipefail

URL="${LOADGEN_URL:-http://localhost:8000}"
BASELINE_SECONDS=60
BURST_SECONDS=90
RPS=5
BASELINE_ONLY=false

usage() {
    sed -n '3,22p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --url)           URL="$2"; shift 2 ;;
        --baseline)      BASELINE_SECONDS="$2"; shift 2 ;;
        --burst)         BURST_SECONDS="$2"; shift 2 ;;
        --rps)           RPS="$2"; shift 2 ;;
        --baseline-only) BASELINE_ONLY=true; shift ;;
        -h|--help)       usage 0 ;;
        *)               echo "unknown argument: $1" >&2; usage 1 ;;
    esac
done

# Fail here rather than 60 seconds into a run that was never reaching anything.
# A load generator that silently produces no load looks exactly like an
# application with no traffic, and that is the demo failure that wastes the
# most time.
if ! curl --fail --silent --show-error --max-time 5 "$URL/health" >/dev/null; then
    echo "cannot reach $URL/health — is the app deployed?" >&2
    echo "  ansible-playbook playbooks/deploy.yml -e app_version=<sha>" >&2
    exit 1
fi

# --rps is requests per second across the whole phase; this is the gap between
# them. Deliberately crude: `sleep` plus curl start-up means the real rate is a
# little under the requested one, and a load generator that lies by 10% is fine
# for making a graph move. If a number ever needs to be *quoted* from this
# script, replace it with a real tool rather than trusting this arithmetic.
INTERVAL=$(awk -v r="$RPS" 'BEGIN { printf "%.3f", 1 / r }')

# Sent with every request so a line in Loki can be traced back to this script
# rather than to a person clicking around. Sanitised by the app either way —
# app/logging_config.py replaces anything outside [A-Za-z0-9._-].
run_id="loadgen-$(date +%H%M%S)"

hit() {
    local method="$1" path="$2" body="${3:-}" n="$4"
    local args=(--silent --output /dev/null --max-time 5
                --header "X-Request-ID: ${run_id}-${n}")
    if [ "$method" = "POST" ]; then
        args+=(--request POST --header "Content-Type: application/json"
               --data "$body")
    fi
    # `|| true`: a single dropped request must not end the run. The whole point
    # is to keep traffic flowing while something goes wrong.
    curl "${args[@]}" "$URL$path" || true
}

phase() {
    local label="$1" seconds="$2" kind="$3"
    local deadline=$((SECONDS + seconds)) n=0

    echo "[$(date +%T)] $label for ${seconds}s at ~${RPS} rps"

    while [ "$SECONDS" -lt "$deadline" ]; do
        n=$((n + 1))
        if [ "$kind" = "valid" ]; then
            case $((n % 3)) in
                0) hit GET  "/"     ""                       "$n" ;;
                1) hit POST "/echo" '{"from":"loadgen"}'     "$n" ;;
                2) hit GET  "/ready" ""                      "$n" ;;
            esac
        else
            # Three distinct ways to be wrong, because the app rejects them
            # through three different code paths and a demo that only ever
            # shows one has tested one.
            case $((n % 3)) in
                0) hit POST "/echo" '{"unterminated":'       "$n" ;;
                1) curl --silent --output /dev/null --max-time 5 \
                       --request POST --header "Content-Type: text/plain" \
                       --header "X-Request-ID: ${run_id}-${n}" \
                       --data 'not json at all' "$URL/echo" || true ;;
                2) curl --silent --output /dev/null --max-time 5 \
                       --request POST --header "X-Request-ID: ${run_id}-${n}" \
                       --data '{"no":"content type"}' "$URL/echo" || true ;;
            esac
        fi
        sleep "$INTERVAL"
    done

    echo "[$(date +%T)] $label done — $n requests"
}

echo "target:  $URL"
echo "run id:  $run_id   (search Loki for this to find only this run's lines)"
echo

phase "baseline — valid traffic" "$BASELINE_SECONDS" valid

if [ "$BASELINE_ONLY" = true ]; then
    echo
    echo "baseline only; no incident generated."
    exit 0
fi

echo
echo "  Watch: Grafana → Project A → Application golden signals"
echo "  The alert needs 1m above the threshold before it leaves Pending."
echo

phase "incident — malformed JSON at /echo" "$BURST_SECONDS" invalid

cat <<EOF

Done. What should now be true, in order:

  1. Error rate panel is above 10% and coloured red.
  2. Alerting → Alert rules → "/echo is rejecting requests" is Firing.
     (It passes through Pending for 1m first — that is the 'for' clause.)
  3. Clicking the error-rate panel's data link opens Loki filtered to
     status >= 400 over the same window.
  4. Every line there carries a request_id starting $run_id, and clicking
     one shows every log line that single request produced.

The error rate decays over the following 5 minutes as the rate() window
slides past the burst. Take the screenshot before then.
EOF
