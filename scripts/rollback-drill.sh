#!/usr/bin/env bash
#
# Rollback drill — proves the claim instead of asserting it.
#
# Sprint 2's goal says a bad deploy can be rolled back in under a minute. This
# script is how that stops being a sentence in PLAN.md: it deploys a knowingly
# broken image, lets the smoke test fail the deploy, rolls back to the last good
# SHA, and times it. Everything it prints is tee'd to a transcript so the runbook
# can quote real output rather than a reconstruction.
#
#   ./scripts/rollback-drill.sh
#
# There is deliberately no rollback.yml. Rollback is deploy.yml with an earlier
# SHA — one code path, exercised on every ordinary deploy, therefore trustworthy
# in an incident. A second playbook would be a second thing to keep correct and
# the first thing to drift.
#
set -u
set -o pipefail

cd "$(dirname "$0")/.."
REPO="$PWD"

BROKEN_TAG="deadbee"          # valid hex, >= 7 chars: passes the role's assert
APP="projecta-flask"
REGISTRY="localhost:5001"
IMAGE="$REGISTRY/$APP"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$REPO/docs/rollback-drill-$STAMP.log"

B=$'\033[1m'; DIM=$'\033[2m'; R=$'\033[0m'
step() { printf '\n%s══ %s ══%s\n' "$B" "$1" "$R"; }
note() { printf '%s%s%s\n' "$DIM" "$1" "$R"; }
die()  { printf '\n%sABORT: %s%s\n' "$B" "$1" "$R" >&2; exit 1; }

mkdir -p "$REPO/docs"
exec > >(tee "$LOG") 2>&1

printf '%sRollback drill · %s%s\n' "$B" "$(date -Iseconds)" "$R"
note "repo:       $REPO"
note "transcript: $LOG"

# ---------------------------------------------------------------------------
# 0 · Preflight. Fail here, loudly, rather than halfway through the drill.
# ---------------------------------------------------------------------------
step "0 · Preflight"

command -v docker >/dev/null            || die "docker not on PATH"
command -v ansible-playbook >/dev/null  || die "ansible-playbook not on PATH — activate .venv?"
docker info >/dev/null 2>&1             || die "Docker daemon not reachable"

curl -sf -m 5 "http://$REGISTRY/v2/" >/dev/null \
  || die "registry $REGISTRY not answering — is the platform stack up?"

git diff --quiet -- app/app.py \
  || die "app/app.py has uncommitted changes. The drill patches it temporarily and
  restores it from git; refusing to run while that would destroy your work."

docker ps --filter "name=^${APP}$" --format '{{.Names}}' | grep -q . \
  || die "no running $APP container — the drill needs a good deploy to roll back TO.
  Deploy a known-good SHA first:  cd ansible && ansible-playbook playbooks/deploy.yml -e app_version=<sha>"

note "preflight ok"

# ---------------------------------------------------------------------------
# 1 · Record the rollback target. This is the number the whole drill hangs on.
# ---------------------------------------------------------------------------
step "1 · Record the current good SHA"

GOOD_SHA="$(docker inspect --format '{{index .Config.Labels "version"}}' "$APP")"
RUNNING_IMAGE="$(docker inspect --format '{{.Config.Image}}' "$APP")"

echo "running image:  $RUNNING_IMAGE"
echo "version label:  $GOOD_SHA"
echo
echo "registry tags:"
curl -s "http://$REGISTRY/v2/$APP/tags/list"; echo

[ -n "$GOOD_SHA" ] || die "no version label on the running container — it was not
  deployed by the role, so there is no honest rollback target. Deploy properly first."

[ "$GOOD_SHA" != "$BROKEN_TAG" ] || die "the broken tag is already what is running.
  Deploy a good SHA before rehearsing."

echo
echo "→ rollback target: $GOOD_SHA"

echo
echo "health before the drill:"
curl -s -w "  → HTTP %{http_code}\n" "http://localhost:8000/health"

# ---------------------------------------------------------------------------
# 2 · Build a knowingly broken image.
#
# One line: /health starts returning 500. main stays clean — the source is
# patched, built, and restored by a trap that fires on any exit path.
# ---------------------------------------------------------------------------
step "2 · Build the broken image ($BROKEN_TAG)"

restore_source() { git -C "$REPO" checkout -- app/app.py 2>/dev/null || true; }
trap restore_source EXIT

python3 - <<'PY'
import pathlib
p = pathlib.Path("app/app.py")
src = p.read_text()
old = 'return jsonify(status="UP")'
new = 'return jsonify(status="DOWN"), 500  # rollback drill: deliberate failure'
assert old in src, f"could not find {old!r} in app/app.py — has /health changed?"
p.write_text(src.replace(old, new, 1))
print("patched /health to return 500")
PY
[ $? -eq 0 ] || die "could not patch app/app.py"

git --no-pager diff --stat -- app/app.py
echo

docker build -t "$IMAGE:$BROKEN_TAG" "$REPO" || die "build failed"
docker push "$IMAGE:$BROKEN_TAG"             || die "push failed"

restore_source
echo
echo "source restored:"
git status --short -- app/app.py || true
echo "(no output above = working tree clean)"

# ---------------------------------------------------------------------------
# 3 · Deploy the broken image. This is EXPECTED to fail.
# ---------------------------------------------------------------------------
step "3 · Deploy the broken image — expecting the smoke test to fail the deploy"

cd "$REPO/ansible"
BAD_START=$SECONDS
ansible-playbook playbooks/deploy.yml -e "app_version=$BROKEN_TAG"
BAD_RC=$?
BAD_ELAPSED=$(( SECONDS - BAD_START ))

echo
echo "→ deploy exit code: $BAD_RC  (non-zero is the correct outcome here)"
echo "→ time to detect failure: ${BAD_ELAPSED}s"

if [ "$BAD_RC" -eq 0 ]; then
  echo
  echo "!! The broken deploy PASSED. That is a finding, not a nuisance: the smoke"
  echo "!! test does not actually gate on /health the way we believed. Stop and fix"
  echo "!! the role before claiming a rollback capability."
fi

echo
echo "state after the failed deploy (left running for inspection, NOT live):"
docker inspect --format '  image={{.Config.Image}}  version={{index .Config.Labels "version"}}' "$APP" || true
curl -s -w "  /health → HTTP %{http_code}\n" "http://localhost:8000/health" || true

# ---------------------------------------------------------------------------
# 4 · Roll back. The timed step — this is the sprint goal.
# ---------------------------------------------------------------------------
step "4 · Roll back to $GOOD_SHA — timed"

echo "command: ansible-playbook playbooks/deploy.yml -e app_version=$GOOD_SHA"
echo

RB_START=$SECONDS
ansible-playbook playbooks/deploy.yml -e "app_version=$GOOD_SHA"
RB_RC=$?
RB_ELAPSED=$(( SECONDS - RB_START ))

echo
echo "→ rollback exit code: $RB_RC"
echo "→ ROLLBACK TIME: ${RB_ELAPSED}s"

# ---------------------------------------------------------------------------
# 5 · Verify by hand. The playbook says it is healthy; check it independently.
# ---------------------------------------------------------------------------
step "5 · Verify the rollback"

docker inspect --format '  image={{.Config.Image}}  version={{index .Config.Labels "version"}}' "$APP" || true
echo
curl -s -w "  /health → HTTP %{http_code}\n" "http://localhost:8000/health"
curl -s -w "  /ready  → HTTP %{http_code}\n" "http://localhost:8000/ready"
curl -s -w "  /echo   → HTTP %{http_code}\n" -H 'Content-Type: application/json' \
     -d '{"drill":"complete"}' "http://localhost:8000/echo"

# ---------------------------------------------------------------------------
# 6 · Summary — the lines the runbook quotes.
# ---------------------------------------------------------------------------
step "6 · Result"

NOW_SHA="$(docker inspect --format '{{index .Config.Labels "version"}}' "$APP" 2>/dev/null || echo '?')"

cat <<EOF
  date              $(date -Iseconds)
  good SHA          $GOOD_SHA
  broken tag        $BROKEN_TAG
  failure detected  ${BAD_ELAPSED}s   (deploy exit $BAD_RC)
  ROLLBACK TIME     ${RB_ELAPSED}s    (deploy exit $RB_RC)
  now running       $NOW_SHA
  sprint goal       $( [ "$RB_ELAPSED" -lt 60 ] && echo "MET — under 60s" || echo "MISSED — ${RB_ELAPSED}s, over 60s; record why" )

  Caveat to state out loud in the review: the rollback pulls with pull=not_present
  and the previous image was still on the host, so this time excludes a registry
  pull. On a fresh host, add the pull. Say it before a mentor asks.

  transcript: $LOG

  Leftover: $IMAGE:$BROKEN_TAG is still in the registry and in the local image
  store. That is the drill's honest residue. Remove the local copy with:
    docker rmi $IMAGE:$BROKEN_TAG
EOF
