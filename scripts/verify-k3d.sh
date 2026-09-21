#!/usr/bin/env bash
#
# Az 1. hét 6. napjának kész-feltétele, egyetlen futtatható bizonyítékban.
#
# Mit bizonyít (a 01-megvalositasi-terv.md 1.4–1.6 pontjai):
#   1. a chart egyetlen paranccsal telepíti a három komponenst (backend,
#      frontend, PostgreSQL) egy üres k3d fürtre;
#   2. a böngészőből elérhető úton (Ingress → frontend nginx → /api/ → backend)
#      működik a teljes CRUD;
#   3. az adat túléli az adatbázis-pod megszűnését (PVC);
#   4. a `--set image.tag=...` tényleg verziót vált, és ezt a /version igazolja
#      — ez a mérés elfogadási kritériuma;
#   5. a `helm rollback` visszaáll az előző verzióra, és ezt is a /version
#      igazolja — ez a pipeline visszaállítási lépésének az alapja.
#
# Ez FEJLESZTŐI ellenőrzés a saját gépen futó k3d fürtön. A mérés nem itt
# történik, hanem az Azure-on futó k3s fürtön (D3 döntés), és a kézi oldalt
# szándékosan NEM szabad szkriptelni: ott az emberi lépések száma a mérőszám.
#
# Használat a repó gyökeréből:
#   ./scripts/verify-k3d.sh
#
set -uo pipefail

CLUSTER="${CLUSTER:-szakdoga}"
RELEASE="${RELEASE:-projecta}"
PORT="${PORT:-18080}"
TAG_A="verify-a"
TAG_B="verify-b"
BASE="http://localhost:${PORT}"

B=$'\033[1m'; G=$'\033[32m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
FAILED=0
PF=""

step() { printf '\n%s▸ %s%s\n' "$B" "$*" "$N"; }
pass() { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
fail() { printf '  %s✗%s %s\n' "$R" "$N" "$*"; FAILED=$((FAILED + 1)); }
info() { printf '  %s%s%s\n' "$D" "$*" "$N"; }
die()  { printf '\n%s✗ %s%s\n\n' "$R" "$*" "$N"; exit 1; }

# A háttérben futó port-forward leállítása. A `disown` azért kell, mert enélkül
# a bash a job-vezérlés miatt kiírna egy "Terminated: 15" sort minden kilövésnél.
stop_pf() {
  [ -n "$PF" ] || return 0
  kill "$PF" 2>/dev/null
  wait "$PF" 2>/dev/null
  PF=""
}
cleanup() { stop_pf; }
trap cleanup EXIT

# A port-forward a pod élettartamához kötődik: minden helm-művelet után új
# podok jönnek, ezért újra kell indítani. Ezért van külön függvényben.
pf_restart() {
  stop_pf
  kubectl port-forward "svc/frontend" "${PORT}:80" >/dev/null 2>&1 &
  PF=$!
  disown "$PF" 2>/dev/null
  for _ in $(seq 1 60); do
    curl -sf "${BASE}/healthz" >/dev/null 2>&1 && return 0
    sleep 1
  done
  die "A frontend nem válaszol a ${BASE}/healthz címen (port-forward vagy pod hiba)."
}

json_field() { python3 -c "import json,sys;print(json.load(sys.stdin)[\"$1\"])"; }
version_now() { curl -sf "${BASE}/api/version" | json_field version; }

build_and_import() {
  local tag="$1"
  info "backend build (GIT_SHA=${tag}) …"
  docker build -q -t "flaskapp:${tag}" --build-arg "GIT_SHA=${tag}" . >/dev/null \
    || die "A backend képe nem épült meg."
  info "frontend build …"
  docker build -q -t "frontend:${tag}" frontend/ >/dev/null \
    || die "A frontend képe nem épült meg."
  # A k3d fürt saját konténer-futtatókörnyezetet használ: a gépeden meglévő kép
  # nem látszik benne automatikusan. Enélkül ImagePullBackOff lenne a vége.
  info "képek betöltése a fürtbe …"
  k3d image import "flaskapp:${tag}" "frontend:${tag}" -c "$CLUSTER" >/dev/null 2>&1 \
    || die "A k3d image import elbukott."
}

# ── 0. Előfeltételek ─────────────────────────────────────────────────────────
step "0 · Előfeltételek"
[ -f chart/Chart.yaml ] || die "Futtasd a repó gyökeréből (nem található chart/Chart.yaml)."
for tool in docker k3d kubectl helm python3 curl; do
  command -v "$tool" >/dev/null || die "Hiányzik: ${tool}"
done
docker info >/dev/null 2>&1 || die "A Docker nem fut. Indítsd el a Docker Desktopot."
pass "minden eszköz megvan, a Docker fut"

# ── 1. Fürt ──────────────────────────────────────────────────────────────────
step "1 · k3d fürt (${CLUSTER})"
if k3d cluster list "$CLUSTER" >/dev/null 2>&1; then
  k3d cluster start "$CLUSTER" >/dev/null 2>&1
  info "meglévő fürt"
else
  info "nincs ilyen fürt, létrehozom …"
  k3d cluster create "$CLUSTER" >/dev/null || die "A fürt létrehozása elbukott."
fi
kubectl config use-context "k3d-${CLUSTER}" >/dev/null 2>&1 || die "Nincs k3d-${CLUSTER} kontextus."
kubectl wait --for=condition=Ready node --all --timeout=120s >/dev/null \
  || die "A csomópont nem lett Ready."
pass "$(kubectl get nodes --no-headers | wc -l | tr -d ' ') csomópont Ready"

# ── 2. Titok ─────────────────────────────────────────────────────────────────
step "2 · db-credentials Secret"
# A jelszó szándékosan nincs a chartban (values.yaml). Fejlesztői fürtön
# fix érték; az Azure-os fürtön ide más jelszó kerül majd.
if kubectl get secret db-credentials >/dev/null 2>&1; then
  pass "már létezik"
else
  kubectl create secret generic db-credentials \
    --from-literal=POSTGRES_USER=projecta \
    --from-literal=POSTGRES_DB=projecta \
    --from-literal=POSTGRES_PASSWORD=devpw >/dev/null || die "A Secret létrehozása elbukott."
  pass "létrehozva (fejlesztői jelszó)"
fi

# ── 3. Telepítés az A verzióval ──────────────────────────────────────────────
step "3 · Telepítés (image.tag=${TAG_A})"
build_and_import "$TAG_A"
helm upgrade --install "$RELEASE" ./chart \
  --set "image.tag=${TAG_A}" --wait --timeout 8m >/dev/null \
  || die "A helm upgrade --install elbukott. Nézd meg: kubectl get pods, kubectl describe pod <név>"
REV_A="$(helm status "$RELEASE" -o json | json_field version)"
pass "telepítve, Helm-revízió: ${REV_A}"
pf_restart

# ── 4. Verzió és CRUD a böngésző útvonalán ───────────────────────────────────
step "4 · Alkalmazás a frontend → /api/ → backend úton"
V="$(version_now)"
[ "$V" = "$TAG_A" ] && pass "/api/version = ${V}" || fail "/api/version = ${V}, várt: ${TAG_A}"

NOTE="$(curl -sf -X POST -H 'Content-Type: application/json' \
  -d '{"title":"verify-k3d","body":"ezt a szkript hozta létre"}' "${BASE}/api/notes")"
ID="$(printf '%s' "$NOTE" | json_field id 2>/dev/null)"
[ -n "${ID:-}" ] && pass "POST /api/notes → id=${ID}" || fail "POST /api/notes nem adott vissza id-t"

curl -sf "${BASE}/api/notes" | grep -q "verify-k3d" \
  && pass "GET /api/notes tartalmazza" || fail "GET /api/notes nem tartalmazza"

curl -sf -X PUT -H 'Content-Type: application/json' \
  -d '{"title":"verify-k3d-modositva","body":"PUT"}' "${BASE}/api/notes/${ID}" | grep -q "modositva" \
  && pass "PUT /api/notes/${ID}" || fail "PUT /api/notes/${ID} elbukott"

# ── 5. Adat túléli a pod megszűnését ─────────────────────────────────────────
step "5 · Adattartósság (PVC)"
kubectl delete pod -l app=postgres --wait=true >/dev/null 2>&1
kubectl rollout status deploy/postgres --timeout=180s >/dev/null || fail "A Postgres nem jött vissza"
# A backend kapcsolatai a Postgres újraindulása alatt elhasalnak; a /ready
# addig 503-at ad. Megvárjuk, amíg újra kiszolgál.
for _ in $(seq 1 60); do
  curl -sf "${BASE}/api/notes" >/dev/null 2>&1 && break
  sleep 2
done
curl -sf "${BASE}/api/notes" | grep -q "verify-k3d-modositva" \
  && pass "a jegyzet a pod törlése után is megvan" \
  || fail "a jegyzet elveszett a Postgres pod törlésekor"

# ── 6. Verzióváltás ──────────────────────────────────────────────────────────
step "6 · Verzióváltás (image.tag=${TAG_B})"
build_and_import "$TAG_B"
helm upgrade --install "$RELEASE" ./chart \
  --set "image.tag=${TAG_B}" --wait --timeout 8m >/dev/null \
  || die "A verzióváltó helm upgrade elbukott."
pf_restart
V="$(version_now)"
[ "$V" = "$TAG_B" ] && pass "/api/version = ${V}" || fail "/api/version = ${V}, várt: ${TAG_B}"

# ── 7. Visszaállítás ─────────────────────────────────────────────────────────
step "7 · helm rollback → ${REV_A}. revízió"
helm rollback "$RELEASE" "$REV_A" --wait --timeout 8m >/dev/null \
  || die "A helm rollback elbukott."
pf_restart
V="$(version_now)"
[ "$V" = "$TAG_A" ] && pass "/api/version = ${V} (visszaállt)" || fail "/api/version = ${V}, várt: ${TAG_A}"

# ── 8. Takarítás és összegzés ────────────────────────────────────────────────
step "8 · Takarítás"
[ -n "${ID:-}" ] && curl -sf -X DELETE "${BASE}/api/notes/${ID}" >/dev/null 2>&1
info "a teszt-jegyzet törölve; a fürt és a release megmarad"
printf '\n%s' "$D"; helm history "$RELEASE" | tail -5; printf '%s' "$N"

printf '\n'
if [ "$FAILED" -eq 0 ]; then
  printf '%s%s✓ A 6. nap kész-feltétele teljesül.%s\n\n' "$B" "$G" "$N"
  exit 0
fi
printf '%s%s✗ %d ellenőrzés bukott. Ne lépj tovább a 2. hétre.%s\n\n' "$B" "$R" "$FAILED" "$N"
exit 1
