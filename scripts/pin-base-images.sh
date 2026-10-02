#!/usr/bin/env bash
# Re-pin the three base images to their current upstream digests — but only if
# the new digests pass the same Trivy gate the pipeline applies.
#
# Run on the laptop, from the repository root, with Docker running:
#
#   scripts/pin-base-images.sh
#
# It writes Dockerfile and frontend/Dockerfile in place and a report to
# szakdolgozat/bizonyitek/07-alapkep-leptetes.txt. Review `git diff`, commit,
# push. The pipeline is still the gate that counts; this script exists so the
# push is not a guess.
#
# Why a script and not "look up the digest and paste it": the backend has been
# red since 2026-09-30 on an OpenSSL advisory in the pinned python:3.12-slim
# (installed 3.5.7-1~deb13u2, fixed in deb13u3). Bumping the digest only helps
# if the new image actually carries the fix, and a digest that has not been
# rebuilt upstream yet would produce a commit that changes nothing but the
# history. So the order is: resolve, scan, and only then write.
#
# Why digests, and why the frontend now too: a tag is a pointer the publisher
# moves; a digest is the content. The backend has been pinned by digest since
# the hardening pass; the frontend was pinned by tag only, which made "the
# release is reproducible" true for one of the two images. nginx moves from the
# end-of-life 1.27 line to the `stable-alpine` line; with the digest pinned,
# the tag is only a label for the next person who bumps it.
#
# Scope of the pre-check: Trivy scans the *base* images here, with the CI's
# flags. The pipeline scans the *built* images, which also contain the Python
# packages and the compiled frontend. A clean base is necessary, not
# sufficient — which is why the push still has to go green.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TRIVY_IMAGE="aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
HADOLINT_IMAGE="hadolint/hadolint:v2.14.0"
PLATFORM="linux/amd64"   # the measurement VM's architecture, not the laptop's
REPORT="szakdolgozat/bizonyitek/07-alapkep-leptetes.txt"

PY_REF="python:3.12-slim"
NODE_REF="node:22-alpine"
NGINX_REF="nginxinc/nginx-unprivileged:stable-alpine"

die() { echo "error: $*" >&2; exit 1; }

command -v docker >/dev/null || die "docker not found"
docker buildx version >/dev/null 2>&1 || die "docker buildx not available"
command -v perl >/dev/null || die "perl not found"
git diff --quiet -- Dockerfile frontend/Dockerfile \
  || die "Dockerfile or frontend/Dockerfile has uncommitted changes; commit or stash them first"

mkdir -p "$(dirname "$REPORT")"
exec > >(tee "$REPORT") 2>&1

echo "generated_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host: $(hostname)"
echo "commit: $(git rev-parse --short HEAD)"
echo "trivy_image: $TRIVY_IMAGE"
echo "hadolint_image: $HADOLINT_IMAGE"
echo "platform: $PLATFORM"
echo

# The index digest (the multi-arch list), not one platform's manifest: that is
# what the FROM line pins today, and it lets the same Dockerfile build on the
# arm64 laptop and the amd64 VM.
resolve() {
  local d
  d=$(docker buildx imagetools inspect "$1" --format '{{.Manifest.Digest}}')
  [[ $d =~ ^sha256:[0-9a-f]{64}$ ]] || die "could not resolve a digest for $1 (got: $d)"
  echo "$d"
}

echo "== Resolving digests"
PY_DIGEST=$(resolve "$PY_REF")
NODE_DIGEST=$(resolve "$NODE_REF")
NGINX_DIGEST=$(resolve "$NGINX_REF")
echo "previous backend base: $(grep -m1 -o 'python:3.12-slim@sha256:[0-9a-f]*' Dockerfile || echo none)"
echo "$PY_REF@$PY_DIGEST"
echo "$NODE_REF@$NODE_DIGEST"
echo "$NGINX_REF@$NGINX_DIGEST"
echo

# The two packages the 2026-09-30 failure was about, read straight from the
# image's dpkg database. If this still says deb13u2, the scan below will fail
# for the same reason, and the message says why rather than leaving a wall of
# CVE rows to interpret.
echo "== OpenSSL in the new backend base"
docker run --rm --platform "$PLATFORM" --entrypoint dpkg-query \
  "$PY_REF@$PY_DIGEST" -W -f '${Package} ${Version}\n' openssl libssl3t64
echo

trivy_gate() {
  # Same severity, same --ignore-unfixed, same exit code as ci.yml. A named
  # volume keeps the vulnerability database between the two scans.
  docker run --rm -v projecta-trivy-cache:/root/.cache/ "$TRIVY_IMAGE" image \
    --image-src remote --platform "$PLATFORM" \
    --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed --quiet \
    "$1"
}

echo "== Trivy gate on the runtime bases (the build stage node image does not ship)"
fail=0
trivy_gate "$PY_REF@$PY_DIGEST"       || fail=1
trivy_gate "$NGINX_REF@$NGINX_DIGEST" || fail=1
if (( fail )); then
  echo
  echo "RESULT: not pinned. At least one base still has a fixed-upstream HIGH/CRITICAL"
  echo "finding. The upstream image has not been rebuilt with the fix yet; run again"
  echo "later. Nothing was written to the Dockerfiles."
  exit 1
fi
echo "both bases clean at HIGH/CRITICAL (unfixed ignored)"
echo

echo "== Writing the FROM lines"
# Replaces the reference whether it currently carries a digest or not, and
# whatever nginx tag it had: the match is on the repository name.
perl -pi -e "s{^FROM python:[^\s\@]+(\@sha256:[0-9a-f]+)?}{FROM $PY_REF\@$PY_DIGEST}" Dockerfile
perl -pi -e "s{^FROM node:[^\s\@]+(\@sha256:[0-9a-f]+)?}{FROM $NODE_REF\@$NODE_DIGEST}" frontend/Dockerfile
perl -pi -e "s{^FROM nginxinc/nginx-unprivileged:[^\s\@]+(\@sha256:[0-9a-f]+)?}{FROM $NGINX_REF\@$NGINX_DIGEST}" frontend/Dockerfile

[[ $(grep -c "^FROM $PY_REF@$PY_DIGEST" Dockerfile) -eq 2 ]] \
  || die "expected both backend stages to be rewritten"
grep -q "^FROM $NODE_REF@$NODE_DIGEST" frontend/Dockerfile || die "frontend build stage not rewritten"
grep -q "^FROM $NGINX_REF@$NGINX_DIGEST" frontend/Dockerfile || die "frontend runtime stage not rewritten"
echo

echo "== hadolint (the pipeline's version and threshold)"
for f in Dockerfile frontend/Dockerfile; do
  docker run --rm -i "$HADOLINT_IMAGE" /bin/hadolint --failure-threshold info - < "$f"
  echo "$f: no findings at or above info"
done
echo

echo "== Diff"
git --no-pager diff --stat -- Dockerfile frontend/Dockerfile
git --no-pager diff -U0 -- Dockerfile frontend/Dockerfile | grep '^[-+]FROM' || true
echo
echo "RESULT: pinned. Commit Dockerfile, frontend/Dockerfile and $REPORT together,"
echo "then push release/meres to azure; the pipeline scans the built images."
