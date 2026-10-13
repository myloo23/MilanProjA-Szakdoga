#!/usr/bin/env bash
#
# A megfigyelő réteg elindítása a mérőgépen, a k3s-re kötve — ADR-0010.
#
# EZ A GÉPEN FUT, nem a laptopon (itt van egyszerre a k3s és a Docker):
#   scripts/platform-sync.sh                  # a laptopon: platform/ és a szkriptek fel
#   ssh azureuser@<ip>
#   ./observability-k3s-up.sh
#
# Mit csinál, sorrendben — és miért ebben a sorrendben:
#   1. felveszi a prometheus-sd ServiceAccountot, a Role-t és a tokent;
#   2. kivárja, amíg a Kubernetes a tokent a Secretbe írja (ez aszinkron:
#      a Secret létrejön, a token-vezérlő pár száz ms-mal később tölti ki);
#   3. kiírja a tokent és a CA-t oda, ahová a Prometheus konténere csatolja,
#      a Prometheus felhasználójának (nobody, 65534) olvashatóan, másnak nem;
#   4. elindítja a hat megfigyelő szolgáltatást.
# Ha a 3. lépés a 4. után jönne, a Prometheus üres könyvtárat csatolna, és a
# projecta-flask job „credentials_file: no such file" hibával indulna.
#
# Többször is futtatható: a kubectl apply és a compose up is idempotens.
set -euo pipefail

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"
COMPOSE_DIR="${COMPOSE_DIR:-$HOME/platform}"
CRED_DIR="$COMPOSE_DIR/observability/prometheus/k8s-credentials"
PROM_UID=65534   # a prom/prometheus kép `nobody` felhasználója

echo "▸ 1. RBAC: prometheus-sd (default névtér, csak pods get/list/watch)"
kubectl apply -f "$COMPOSE_DIR/observability/k8s/prometheus-sd-rbac.yaml"

echo "▸ 2. A token kivárása"
token=""
for _ in $(seq 1 20); do
  token=$(kubectl -n default get secret prometheus-sd-token \
    -o jsonpath='{.data.token}' 2>/dev/null || true)
  [[ -n "$token" ]] && break
  sleep 0.5
done
if [[ -z "$token" ]]; then
  echo "✗ A prometheus-sd-token Secret 10 mp után is üres." >&2
  echo "  kubectl -n default describe secret prometheus-sd-token" >&2
  exit 1
fi

echo "▸ 3. Token és CA → $CRED_DIR"
# A fájlok a Prometheus felhasználójáé, 0400-as joggal: a gépen más felhasználó
# (és más konténer) ne olvassa a tokent. Ehhez kell a sudo — a könyvtár
# azureuseré, a fájlok nem.
mkdir -p "$CRED_DIR"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf '%s' "$token" | base64 -d > "$tmp/token"
kubectl -n default get secret prometheus-sd-token \
  -o jsonpath='{.data.ca\.crt}' | base64 -d > "$tmp/ca.crt"
test -s "$tmp/token" && test -s "$tmp/ca.crt"
sudo install -o "$PROM_UID" -g "$PROM_UID" -m 0400 "$tmp/token"  "$CRED_DIR/token"
sudo install -o "$PROM_UID" -g "$PROM_UID" -m 0444 "$tmp/ca.crt" "$CRED_DIR/ca.crt"

echo "▸ 4. A megfigyelő szolgáltatások indítása"
cd "$COMPOSE_DIR"
docker compose -f compose.yaml -f compose.azure.yaml --profile observability up -d
# A Prometheus a konfigurációt csak induláskor olvassa; ha már futott (második
# futtatás, új token), a --force-recreate nélküli `up` nem indítaná újra.
docker compose -f compose.yaml -f compose.azure.yaml --profile observability \
  restart prometheus alloy

echo
echo "✓ Kész. Ellenőrzés: ./verify-observability-k3s.sh"
echo "  Grafana a laptopról: ssh -L 3001:127.0.0.1:3001 azureuser@<ip>, majd http://localhost:3001"
