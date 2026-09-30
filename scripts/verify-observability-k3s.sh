#!/usr/bin/env bash
#
# A megfigyelő réteg k3s-re kötésének kész-feltétele, egyetlen futtatható
# bizonyítékban — ADR-0010, a dolgozat 5.6 alfejezetének forrása.
#
# EZ A GÉPEN FUT, az observability-k3s-up.sh után:
#   ./verify-observability-k3s.sh 2>&1 | tee ~/5.6-verify.txt
#   ROLLOUT=1 ./verify-observability-k3s.sh ...   # a 7. lépéssel együtt
# majd a laptopon:
#   scp azureuser@<ip>:5.6-verify.txt szakdolgozat/bizonyitek/05-megfigyeles-k3s-verify.txt
#
# Mit bizonyít, és mit nem:
#   1–2. a szolgáltatások futnak, és a TLS-ellenőrzés névválasztása helyes;
#   3.   a pod IP-címe tényleg elérhető a Docker-hálózatról (nem feltételezzük);
#   4.   a Prometheus pontosan annyi backend célpontot lát, ahány backend pod fut;
#   5.   a kérések metrikaként megérkeznek, podonként szétválasztva;
#   6.   a podok JSON-naplója a Lokiban van, `level` címkével, request_id-val;
#   7.   (ROLLOUT=1) egy gördülő csere után az új podok maguktól célponttá válnak.
# Amit NEM bizonyít: a pod-szintű CPU/memória metrikát — az tudatosan nincs
# (ADR-0010, „Consequences").
set -uo pipefail

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"
PROM="http://127.0.0.1:9090"
LOKI="http://127.0.0.1:3100"
GRAFANA="http://127.0.0.1:3001"
APP="http://127.0.0.1/api"

B=$'\033[1m'; G=$'\033[32m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
FAILED=0
step() { printf '\n%s▸ %s%s\n' "$B" "$*" "$N"; }
pass() { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
fail() { printf '  %s✗%s %s\n' "$R" "$N" "$*"; FAILED=$((FAILED + 1)); }
info() { printf '  %s%s%s\n' "$D" "$*" "$N"; }

promq() {  # egy PromQL-kifejezés skaláris eredménye (vagy üres, ha nincs válasz)
  curl -sG "$PROM/api/v1/query" --data-urlencode "query=$1" \
    | python3 -c '
import json,sys
try: r=json.load(sys.stdin)["data"]["result"]
except Exception: r=[]
print(r[0]["value"][1] if r else "")'
}

backend_pods() {
  kubectl -n default get pods -l app=backend \
    --field-selector=status.phase=Running -o jsonpath='{.items[*].metadata.name}'
}

wait_targets() {  # vár, amíg a Prometheus annyi egészséges célpontot lát, ahány pod fut
  local want got
  for _ in $(seq 1 30); do
    want=$(backend_pods | wc -w)
    got=$(promq 'count(up{job="projecta-flask"} == 1)')
    [[ -n "$got" && "$got" == "$want" ]] && { echo "$got"; return 0; }
    sleep 2
  done
  echo "${got:-0}"; return 1
}

echo "Időpont (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Gép: $(hostname)   k3s: $(k3s --version | head -1)"

# Előfeltételek. Ha ezek hiányoznak, a lenti lépések mind elbuknak, és a
# kimenet a tényleges okot harminc következményhiba alá temetné (2026-09-30:
# az újraépült gépen se megfigyelő konténer, se backend nem volt).
pre_fail=0
if ! docker inspect projecta-prometheus >/dev/null 2>&1; then
  printf '%s✗ Előfeltétel: a projecta-prometheus nem fut — előbb ./observability-k3s-up.sh%s\n' "$R" "$N"
  pre_fail=1
fi
if [[ -z "$(backend_pods)" ]]; then
  printf '%s✗ Előfeltétel: nincs futó backend pod a default névtérben — az alkalmazás nincs telepítve%s\n' "$R" "$N"
  info "kubectl get pods -A; KUBECONFIG=$KUBECONFIG helm list -A"
  pre_fail=1
fi
if [[ $pre_fail -ne 0 ]]; then
  echo "Az ellenőrzés nem indul el, amíg az előfeltételek nem teljesülnek."
  exit 2
fi

step "1. A szolgáltatások"
for c in projecta-prometheus projecta-loki projecta-alloy projecta-grafana \
         projecta-cadvisor projecta-node-exporter; do
  st=$(docker inspect -f '{{.State.Status}}{{if .State.Health}}/{{.State.Health.Status}}{{end}}' "$c" 2>/dev/null)
  case "$st" in
    running|running/healthy) pass "$c: $st" ;;
    *) fail "$c: ${st:-nincs ilyen konténer}" ;;
  esac
done
curl -fsS "$GRAFANA/api/health" >/dev/null && pass "Grafana /api/health" || fail "Grafana /api/health"

step "2. Az API-tanúsítvány a Prometheus által ellenőrzött nevet tartalmazza"
san=$(openssl s_client -connect 127.0.0.1:6443 </dev/null 2>/dev/null \
      | openssl x509 -noout -ext subjectAltName 2>/dev/null | tail -1)
info "$san"
grep -q 'DNS:kubernetes.default.svc\b' <<<"$san" \
  && pass "SAN: kubernetes.default.svc (prometheus.k3s.yml tls_config.server_name)" \
  || fail "a kubernetes.default.svc nincs a tanúsítványon — a server_name-et át kell írni"

step "3. A pod IP-címe elérhető a Docker-hálózatról"
pod_ip=$(kubectl -n default get pods -l app=backend \
  --field-selector=status.phase=Running -o jsonpath='{.items[0].status.podIP}')
info "backend pod: $pod_ip"
if docker exec projecta-prometheus wget -qO- "http://$pod_ip:8000/metrics" 2>/dev/null \
     | grep -q '^http_requests_total'; then
  pass "a projecta-prometheus konténerből a http://$pod_ip:8000/metrics válaszol"
else
  fail "a projecta-prometheus konténerből a pod nem érhető el (FORWARD szabály? kube-router?)"
fi

step "4. A Prometheus annyi célpontot lát, ahány backend pod fut"
pods=$(backend_pods)
info "futó backend podok: $pods"
if got=$(wait_targets); then
  pass "up{job=\"projecta-flask\"} == 1: $got célpont, $(wc -w <<<"$pods") pod"
else
  fail "célpont: $got, pod: $(wc -w <<<"$pods")"
  curl -s "$PROM/api/v1/targets?state=active" | python3 -c '
import json,sys
for t in json.load(sys.stdin)["data"]["activeTargets"]:
    if t["labels"].get("job")=="projecta-flask":
        print("   ", t["labels"].get("pod"), t["health"], t.get("lastError",""))'
fi

step "5. A kérések metrikaként megérkeznek, podonként"
before=$(promq 'sum(http_requests_total{job="projecta-flask",endpoint="/version"})')
for _ in $(seq 1 40); do curl -s -o /dev/null "$APP/version"; done
info "40 kérés a $APP/version címre; várakozás két lekérdezési ciklusra (30 mp)"
sleep 30
after=$(promq 'sum(http_requests_total{job="projecta-flask",endpoint="/version"})')
info "http_requests_total{endpoint=\"/version\"} összesen: ${before:-0} → ${after:-0}"
python3 -c "import sys; sys.exit(0 if float('${after:-0}')-float('${before:-0}')>=40 else 1)" \
  && pass "a növekmény legalább 40" || fail "a növekmény kevesebb 40-nél"
per_pod=$(promq 'count(count by (pod) (http_requests_total{job="projecta-flask",endpoint="/version"}))')
[[ "${per_pod:-0}" -ge 2 ]] \
  && pass "a kérések $per_pod podon oszlanak meg, a sorozatok podonként külön" \
  || info "a kérések csak ${per_pod:-0} podon jelentek meg (a Service elosztásán múlik, nem hiba)"

step "6. A podok naplója a Lokiban"
q='{container="projecta-flask", level=~".+"} | json | endpoint="/version"'
n=$(curl -sG "$LOKI/loki/api/v1/query_range" --data-urlencode "query=$q" \
      --data-urlencode "since=5m" --data-urlencode "limit=100" \
    | python3 -c 'import json,sys; print(sum(len(s["values"]) for s in json.load(sys.stdin)["data"]["result"]))')
info "LogQL: $q"
[[ "${n:-0}" -gt 0 ]] && pass "$n sor az utolsó 5 percből, level címkével" \
                      || fail "nincs találat (Alloy: docker logs projecta-alloy)"
sample=$(curl -sG "$LOKI/loki/api/v1/query_range" --data-urlencode "query=$q" \
      --data-urlencode "since=5m" --data-urlencode "limit=1" \
    | python3 -c 'import json,sys; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["values"][0][1] if r else "")')
info "minta: $sample"
grep -q '"request_id"' <<<"$sample" && pass "a sorban van request_id (a derived field erre épül)" \
                                     || fail "a sorban nincs request_id"
labels=$(curl -sG "$LOKI/loki/api/v1/labels" --data-urlencode "since=5m" \
    | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["data"]))')
info "Loki címkék: $labels"
grep -qw 'filename' <<<"$labels" && fail "a filename címke bent maradt (ADR-0007)" \
                                 || pass "nincs filename/pod címke (ADR-0007)"

if [[ "${ROLLOUT:-0}" == "1" ]]; then
  step "7. Gördülő csere után az új podok maguktól célponttá válnak"
  old=$(backend_pods)
  kubectl -n default rollout restart deployment/backend >/dev/null
  kubectl -n default rollout status deployment/backend --timeout=120s
  new=$(backend_pods)
  info "előtte: $old"; info "utána:  $new"
  if got=$(wait_targets); then
    targets=$(curl -s "$PROM/api/v1/targets?state=active" | python3 -c '
import json,sys
print(" ".join(sorted(t["labels"]["pod"] for t in json.load(sys.stdin)["data"]["activeTargets"]
      if t["labels"].get("job")=="projecta-flask" and t["health"]=="up")))')
    [[ "$targets" == "$(tr ' ' '\n' <<<"$new" | sort | xargs)" ]] \
      && pass "a célpontok pontosan az új podok: $targets" \
      || fail "a célpontok ($targets) nem egyeznek az új podokkal"
  else
    fail "a gördülő csere után a célpontok száma nem állt be"
  fi
fi

echo
if [[ $FAILED -eq 0 ]]; then
  printf '%s✓ Minden ellenőrzés sikeres.%s\n' "$G" "$N"
else
  printf '%s✗ %d ellenőrzés sikertelen.%s\n' "$R" "$FAILED" "$N"
fi
exit $FAILED
