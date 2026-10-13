#!/usr/bin/env bash
#
# Run helm against the k3s cluster on the Docker host, from inside a CI job
# container — and by hand, from anywhere the Docker socket is reachable:
#
#   scripts/helm-on-host.sh status projecta
#   scripts/helm-on-host.sh upgrade --install projecta /chart --set image.tag=1a2b3c4 --wait
#
# **Why this exists at all.** The deploy job runs in a container on the
# projecta-platform bridge. The k3s API server listens on the host's
# 127.0.0.1:6443, which from that container is the container itself, and the
# bridge gateway is not an option either: terraform/cloud-init.yaml starts k3s
# with `--tls-san <public_ip>`, so the server certificate names 127.0.0.1,
# localhost and the public address — not 172.x.0.1. Reaching the API over the
# bridge fails certificate verification, and the fix for that is not a flag, it
# is a different route to the API.
#
# The route taken here is the one the build job already relies on: the job
# container holds the *host's* Docker socket. A container created through it
# with `--network host` lands in the host's network namespace, where
# 127.0.0.1:6443 is the API server and 127.0.0.1:80 is Traefik — exactly what
# the operator sees in the manual protocol. Nothing new is installed on the
# host, the runner keeps its registration, and no platform service changes.
#
# **The helm version is pinned to the one the measuring machine runs**
# (szakdolgozat/bizonyitek/04-kezi-telepitesi-folyamat.md, E1: helm v3.22.0
# from get-helm-3). If the two series deployed with different helm versions,
# the deployment tool would be a second variable next to the branch name, and
# the comparison in §6.4 would have to defend it.
#
# **The chart is copied in, not mounted.** `-v "$PWD/chart:/chart"` fails here
# for the same reason the Trivy filesystem scan does not bind-mount the
# checkout: $PWD is a path inside the job container, and the daemon resolving
# it is the host's, where that path does not exist. `git archive` ships exactly
# the tracked chart at the commit under test instead — same idiom, same
# non-empty guard, for the same reason.
set -euo pipefail

HELM_IMAGE="${HELM_IMAGE:-alpine/helm:3.22.0}"
KUBECONFIG_HOST_PATH="${KUBECONFIG_HOST_PATH:-/etc/rancher/k3s/k3s.yaml}"
CHART_PATH="${CHART_PATH:-chart}"

# --mount, not -v, and the difference matters: a bind mount whose source is
# missing is silently created as an empty *directory* by `-v`, so a wrong
# kubeconfig path would surface as helm complaining about a directory it cannot
# parse. --mount refuses instead, and the error names the path.
cid=$(docker create \
  --network host \
  --mount "type=bind,source=${KUBECONFIG_HOST_PATH},target=/kubeconfig,readonly" \
  -e KUBECONFIG=/kubeconfig \
  "$HELM_IMAGE" "$@")

cleanup() { docker rm --force "$cid" >/dev/null 2>&1 || true; }
trap cleanup EXIT

tar=$(mktemp)
git archive --format=tar --prefix=chart/ "HEAD:${CHART_PATH}" > "$tar"
files=$(tar -tf "$tar" | grep -cv '/$')
test "$files" -gt 0 || { echo "git archive produced an empty chart" >&2; exit 1; }
docker cp - "$cid:/" < "$tar"
rm -f "$tar"

# Exits with the container's exit code, so a failed helm command fails the step.
docker start --attach "$cid"
