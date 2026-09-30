# A mérőgép újraépítése (2026-09-30)

## Mi történt

A 2026-09-30-i `terraform apply` (az `allowed_cidr` átírása az új otthoni
IP-re) a gépet **törölte és újra létrehozta**. Ok: a `cloud-init.yaml`
2026-09-21-én változott (`cbbecef`, a registries.yaml kivezetése), ezt a
változást a futó gépre soha nem alkalmaztuk, és az azurerm-ben a `custom_data`
változása gépcserét jelent. Az NSG-módosítás `apply`-ja ezt a függő cserét is
végrehajtotta.

Bizonyíték: a `terraform.tfstate.backup` és a `terraform.tfstate`
`virtual_machine_id`-je (`29cfc322…` → `2fff48cb…`), új OS-lemez; a gépen minden
kube-system pod kora 13 perc volt; az SSH-hostkulcs megváltozott.

**Ami elveszett:** a gépen futó Gitea (repó, admin, runner-regisztráció,
workflow-futások), a registry képei, a Helm-release, a `db-credentials` Secret,
a Postgres adatai.

**Ami nem veszett el:** a mérés teljes bizonyítékanyaga — a CSV-k, a
jegyzőkönyvek, a joblogok (`bizonyitek/meres/workflowlogok/`) és az SBOM-ok a
repóban vannak. A mérést nem kell megismételni.

**Ami ebből a dolgozatba kerül.** A k3s-fürt kézi beavatkozás nélkül, kódból
állt fel (Traefik, CoreDNS, local-path — a 2.3 kész-feltétele, ezúttal nem
tervezetten, hanem élesben igazolva). A platform (Gitea, runner) és az alkalmazás
viszont kézi lépésekkel jön vissza (lent) — ez a 7. fejezetbe tartozik: a
platform-bootstrap automatizálása.

**Hogy ne ismétlődjön:** `terraform/main.tf`, a VM `lifecycle { ignore_changes =
[custom_data] }` blokkja, indoklással. Gépcsere ezentúl csak kimondottan:
`terraform apply -replace=azurerm_linux_virtual_machine.main`.

---

## Újraépítés — lépésenként

**(L)** = laptop, a repó gyökerében · **(G)** = a mérőgépen (`ssh azureuser@4.165.139.1`)

### 0. A lifecycle-javítás ellenőrzése (L)

```bash
terraform -chdir=terraform plan
```

Elvárt: **No changes.** Ha bármit cserélne vagy módosítana, állj meg.

### 1. Commit és a fürt környezete (L, majd G)

A laptopon commitold a mai munkát (a két commit: mérési dokumentáció, illetve
ADR-0010 + konfiguráció + ez a fájl), mert a gépre ebből klónozunk. Utána:

```bash
scripts/platform-sync.sh                                  # (L)
```

```bash
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc   # (G)
source ~/.bashrc
test -f /var/lib/cloud/instance/k3s-ready && echo "cloud-init kész"
helm version --short
```

### 2. Gitea és registry (G)

```bash
cd ~/platform
cp .env.example .env
sed -i 's/^GITEA_RUNNER_NAME=.*/GITEA_RUNNER_NAME=projecta-azure-runner/' .env
docker compose -f compose.yaml -f compose.azure.yaml up -d gitea registry
docker compose -f compose.yaml -f compose.azure.yaml ps      # várd meg: healthy
curl -fsS http://localhost:3000/api/healthz; echo
curl -fsS http://localhost:5001/v2/; echo                     # {}
```

Admin (új jelszó; ne írd fájlba):

```bash
read -rs -p 'Gitea jelszó: ' GPW; echo
docker exec -u git projecta-gitea gitea admin user create \
  --admin --username milan --email milan.takacs24@gmail.com \
  --password "$GPW" --must-change-password=false
```

A repó létrehozása API-n (a webes felület helyett):

```bash
curl -fsS -u "milan:$GPW" -H 'Content-Type: application/json' \
  -d '{"name":"MilanProjA-Szakdoga","private":true}' \
  http://localhost:3000/api/v1/user/repos >/dev/null && echo "repó kész"
```

**A runnert még NE indítsd.** Ha most indulna, a 3. lépés pushára a pipeline
lefutna, és a `deploy` job elbukna, mert még nincs Helm-release, amihez képest a
visszaállítási pontot (`PREV_TAG`) rögzítené.

### 3. A kód feltöltése (L)

Egy külön ablakban az alagút (nyitva kell maradjon):

```bash
ssh -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 azureuser@4.165.139.1
```

A másikban:

```bash
git push azure main
```

(Felhasználó: `milan`, a 2. lépés jelszava.)

### 4. Secret és a nulladik telepítés (G)

```bash
git clone http://localhost:3000/milan/MilanProjA-Szakdoga.git ~/projecta
read -rs -p 'Postgres jelszó: ' DBPW; echo
kubectl create secret generic db-credentials \
  --from-literal=POSTGRES_USER=projecta \
  --from-literal=POSTGRES_DB=projecta \
  --from-literal=POSTGRES_PASSWORD="$DBPW"

cd ~/projecta
SHA=$(git rev-parse --short HEAD)
docker build -t localhost:5001/projecta-flask:$SHA --build-arg GIT_SHA=$SHA .
docker build -t localhost:5001/projecta-frontend:$SHA frontend/
docker push localhost:5001/projecta-flask:$SHA
docker push localhost:5001/projecta-frontend:$SHA
helm upgrade --install projecta ~/projecta/chart --set image.tag=$SHA
kubectl rollout status deploy/backend  --timeout=5m
kubectl rollout status deploy/frontend --timeout=5m
curl -s http://localhost/api/version; echo                   # a $SHA
~/projecta/scripts/smoke.sh http://localhost/api             # 7 várt státusz
```

### 5. A runner (G)

```bash
TOKEN=$(docker exec -u git projecta-gitea gitea actions generate-runner-token | tr -d '\r\n')
sed -i "s|^GITEA_RUNNER_REGISTRATION_TOKEN=.*|GITEA_RUNNER_REGISTRATION_TOKEN=${TOKEN}|" ~/platform/.env
cd ~/platform
docker compose -f compose.yaml -f compose.azure.yaml up -d act-runner
docker logs --tail 20 projecta-act-runner
```

A 3. lépés pusha várakozó futásként ott áll; a runner felveszi, és a `main`-t
végigviszi a pipeline-on — ez egyben a pipeline próbája az újraépült gépen.
A Gitea felületén (alagúton át, `http://localhost:3000`) nézd meg, zöld-e.

### 6. A megfigyelő réteg (G)

```bash
~/observability-k3s-up.sh
ROLLOUT=1 ~/verify-observability-k3s.sh 2>&1 | tee ~/5.6-verify.txt
```

### 7. Vissza a laptopra, és leállítás (L)

```bash
scp azureuser@4.165.139.1:5.6-verify.txt szakdolgozat/bizonyitek/05-megfigyeles-k3s-verify.txt
az vm deallocate -g szakdoga2-rg -n szakdoga2-vm
```
