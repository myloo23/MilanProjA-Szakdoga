#!/usr/bin/env bash
# Local development loop for the k3d cluster: build, load into the cluster,
# restart the deployment, wait for it, then prove which version is running.
#
# The cluster's nodes are separate containers with their own image store, so an
# image built here is invisible to them until `k3d image import` copies it in.
# That is the single most common cause of ImagePullBackOff on this setup.
#
# Two tags are pushed on purpose: `dev` is what the local manifests reference,
# and the git SHA is the immutable one the pipeline will use from Sprint 4 on.
# The build argument — not the tag — is what /version reports.
set -euo pipefail

cd "$(dirname "$0")/.."

CLUSTER="${CLUSTER:-szakdoga}"
DEPLOYMENT="${DEPLOYMENT:-backend}"

SHA="$(git rev-parse --short HEAD)"
# An uncommitted change is not in the SHA, so an image built from a dirty tree
# claims a version it does not contain. Measurement runs must start clean.
if ! git diff --quiet || ! git diff --cached --quiet; then
  SHA="${SHA}-dirty"
  echo "WARNING: uncommitted changes — building as ${SHA}" >&2
fi

echo "==> build ${SHA}"
docker build --build-arg GIT_SHA="${SHA}" -t "flaskapp:dev" -t "flaskapp:${SHA}" .

echo "==> import into cluster ${CLUSTER}"
k3d image import "flaskapp:dev" "flaskapp:${SHA}" -c "${CLUSTER}"

echo "==> restart ${DEPLOYMENT}"
kubectl rollout restart "deployment/${DEPLOYMENT}"
kubectl rollout status "deployment/${DEPLOYMENT}" --timeout=120s

echo "==> running version"
kubectl exec "deployment/${DEPLOYMENT}" -- \
  python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/version').read().decode())"
