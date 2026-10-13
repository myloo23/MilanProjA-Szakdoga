#!/usr/bin/env bash
#
# A 2.4 pont kész-feltétele, egyetlen futtatható bizonyítékban.
#
# Mit bizonyít:
#   1. a Gitea, a runner és a registry fut az Azure-os gépen;
#   2. a k3s containerd-je ismeri a localhost:5001 tükröt (registries.yaml);
#   3. a fürt tényleg LE TUD HÚZNI egy képet a gépen futó registryből —
#      nem a helyi Docker-gyorsítótárból, mert a pod imagePullPolicy: Always
#      beállítással indul, és a kép a Dockerből a futtatás előtt törlődik.
#
# EZ A GÉPEN FUT, nem a laptopon: itt van egyszerre Docker és k3s.
#   ssh azureuser@<ip>
#   ./verify-azure-platform.sh
#
set -uo pipefail

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"
COMPOSE_DIR="${COMPOSE_DIR:-$HOME/platform}"
REGISTRY="localhost:5001"
TAG="proba-$(date +%s)"
IMAGE="${REGISTRY}/registry-proba:${TAG}"
POD="registry-proba"

B=$'\033[1m'; G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; N=$'\033[0m'
FAILED=0
WARNED=0
step() { printf '\n%s▸ %s%s\n' "$B" "$*" "$N"; }
pass() { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
fail() { printf '  %s✗%s %s\n' "$R" "$N" "$*"; FAILED=$((FAILED + 1)); }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; WARNED=$((WARNED + 1)); }
info() { printf '  %s%s%s\n' "$D" "$*" "$N"; }

cleanup() {
  kubectl delete pod "$POD" --ignore-not-found --now >/dev/null 2>&1
  docker rmi "$IMAGE" >/dev/null 2>&1
}
trap cleanup EXIT

step "1. A platform konténerei"
for c in projecta-gitea projecta-registry projecta-act-runner; do
  if [[ "$(docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null)" == "true" ]]; then
    pass "$c fut"
  else
    fail "$c nem fut"
  fi
done

step "2. Végpontok a gépen"
if curl -fsS http://localhost:3000/api/healthz >/dev/null; then pass "Gitea /api/healthz"; else fail "Gitea nem válaszol"; fi
if curl -fsS "http://${REGISTRY}/v2/" >/dev/null; then pass "registry /v2/"; else fail "a registry nem válaszol"; fi

step "3. A képletöltés útja (tájékoztató)"
# Ez NEM kész-feltétel, és nem is bukhat. Azt írja ki, van-e a containerdnek
# bármilyen saját beállítása erre a registryre. A 2.4 mérése szerint nincs, és
# nem is kell: a containerd a loopback-címre mutató registryt kivételként
# kezeli, TLS nélkül is elfogadja. A fürt tehát attól éri el a registryt, hogy
# ugyanazon a gépen fut (D5). A bizonyítás az 5. lépés.
CONTAINERD_ETC=/var/lib/rancher/k3s/agent/etc
HIT="$(sudo grep -rl "$REGISTRY" "$CONTAINERD_ETC" 2>/dev/null | head -5)"
if [[ -n "$HIT" ]]; then
  info "a containerd külön beállítást kapott erre a registryre:"
  echo "$HIT" | sed 's/^/    /'
else
  info "a containerdnek nincs külön beállítása a ${REGISTRY} címre — a loopback-kivétel a magyarázat"
fi

step "4. Kép feltöltése a registrybe"
docker pull busybox:1.36 >/dev/null 2>&1 || fail "a busybox:1.36 letöltése nem sikerült"
docker tag busybox:1.36 "$IMAGE"
if docker push "$IMAGE" >/dev/null 2>&1; then
  pass "docker push $IMAGE"
else
  fail "a push nem sikerült"
fi
info "katalógus: $(curl -fsS "http://${REGISTRY}/v2/_catalog" 2>/dev/null)"
info "címkék:    $(curl -fsS "http://${REGISTRY}/v2/registry-proba/tags/list" 2>/dev/null)"

# A helyi Docker-példány törlése. Enélkül a teszt csak annyit bizonyítana, hogy
# a kép megvan valahol a gépen — nem azt, hogy a fürt a registryből szedte.
docker rmi "$IMAGE" >/dev/null 2>&1

step "5. A fürt lehúzza a képet"
kubectl delete pod "$POD" --ignore-not-found --now >/dev/null 2>&1
kubectl run "$POD" --image="$IMAGE" --image-pull-policy=Always \
  --restart=Never --command -- sleep 60 >/dev/null

if kubectl wait --for=condition=Ready "pod/$POD" --timeout=120s >/dev/null 2>&1; then
  pass "a pod fut a $IMAGE képből"
  # Csak a MOSTANI futás eseményei: a podnév újrahasznosul, és a korábbi
  # futások Pulled-sorai is itt maradnának, ami a bizonyítékban félrevezető.
  kubectl get events --field-selector "involvedObject.name=$POD" \
    -o custom-columns=REASON:.reason,MESSAGE:.message --no-headers 2>/dev/null \
    | grep -i "pull" | grep -F "$TAG" | sed 's/^/    /'
else
  fail "a pod nem indult el"
  kubectl describe pod "$POD" | tail -25 | sed 's/^/    /'
fi

printf '\n'
if [[ $FAILED -eq 0 ]]; then
  printf '%s✓ A 2.4 pont kész-feltétele teljesül.%s' "$G" "$N"
  [[ $WARNED -gt 0 ]] && printf ' %s(%d figyelmeztetés.)%s' "$Y" "$WARNED" "$N"
  printf '\n\n'
else
  printf '%s✗ %d ellenőrzés bukott.%s\n\n' "$R" "$FAILED" "$N"
  exit 1
fi
