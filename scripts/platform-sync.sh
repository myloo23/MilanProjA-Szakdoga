#!/usr/bin/env bash
#
# A platform/ mappa felmásolása az Azure-os mérőgépre (2.4 pont).
#
# Miért rsync, és miért nem git clone a gépen: a Gitea még nem fut ott, a
# GitHub-távoli pedig a gép kifelé menő forgalmát feltételezné. A platform
# leírása ráadásul infrastruktúra, nem az alkalmazás kódja — a mért telepítési
# lánc az alkalmazást szállítja, ezt a réteget nem. Egy irányba másolunk: a
# repó a forrás, a gépen lévő példány másolat. Ha a gépen javítasz valamit,
# vidd vissza a repóba, különben a következő futás felülírja.
#
# A .env kimarad: az a regisztrációs tokent tartalmazza, a gépen készül, és a
# --delete sem bántja (az rsync a kizárt fájlokat a fogadó oldalon is védi).
#
# Használat a repó gyökeréből:
#   ./scripts/platform-sync.sh
#   VM_HOST=1.2.3.4 ./scripts/platform-sync.sh     # ha nincs kéznél a terraform
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_USER="${VM_USER:-azureuser}"
VM_HOST="${VM_HOST:-$(terraform -chdir="$REPO_ROOT/terraform" output -raw public_ip)}"

if [[ -z "$VM_HOST" ]]; then
  echo "Nincs cél-IP. Add meg: VM_HOST=<ip> $0" >&2
  exit 1
fi

echo "▸ platform/ → ${VM_USER}@${VM_HOST}:~/platform/"
# A k8s-credentials a gépen jön létre (scripts/observability-k3s-up.sh), a
# laptopon nincs meg. Kizárás nélkül a --delete minden szinkronnál letörölné —
# a fájlok ráadásul a Prometheus felhasználójáé, így a törlés hibával állna meg.
rsync -az --delete --exclude '.env' \
  --exclude 'observability/prometheus/k8s-credentials/' \
  "$REPO_ROOT/platform/" "${VM_USER}@${VM_HOST}:platform/"

echo "▸ scripts/{verify-azure-platform,observability-k3s-up,verify-observability-k3s}.sh → ${VM_USER}@${VM_HOST}:~/"
rsync -az "$REPO_ROOT/scripts/verify-azure-platform.sh" \
  "$REPO_ROOT/scripts/observability-k3s-up.sh" \
  "$REPO_ROOT/scripts/verify-observability-k3s.sh" \
  "${VM_USER}@${VM_HOST}:"

echo "✓ Kész. Belépés: ssh ${VM_USER}@${VM_HOST}"
