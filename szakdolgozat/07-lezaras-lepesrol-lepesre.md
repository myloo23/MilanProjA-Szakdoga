# A technikai rész lezárása — lépésről lépésre (2026-10-05)

> **Elvégezve 2026-10-13-án** (naplo 3.3): `1c2b23d` alapkép-léptetés, `861f51b` zöld futás, PR #2 merge a `main`-be.

A kód kész (`d62798c`). Ami maradt, az csak a te gépeden futhat, mert kell
hozzá a Docker Hub, az Azure és a Gitea-jelszavad. Kb. egy óra, ebből a
pipeline-futás 3–5 perc.

**(L)** = laptop, a repó gyökerében · **(G)** = a mérőgép

---

## 1. Az alapképek léptetése (L)

Előfeltétel: fut a Docker Desktop.

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
git switch release/meres
scripts/pin-base-images.sh
```

Elvárt utolsó sor: `RESULT: pinned.` Közben látnod kell, hogy az `openssl` és
a `libssl3t64` verziója `3.5.7-1~deb13u3` (vagy újabb).

**Ha `RESULT: not pinned`:** a kiadó még nem építette újra a képet. Ne nyúlj a
Dockerfile-hoz, és ne kapcsold ki a kaput; egy-két nap múlva futtasd újra. Ha
egy hét múlva is piros, szólj, és megbeszéljük (a kimenetet hozd).

## 2. Commit (L)

```bash
git --no-pager diff -- Dockerfile frontend/Dockerfile   # csak a FROM sorok változhattak
git add Dockerfile frontend/Dockerfile szakdolgozat/bizonyitek/07-alapkep-leptetes.txt
git commit -m "alapkep: digestek leptetese (OpenSSL deb13u3), a frontend alapkepeinek rogzitese"
```

## 3. A gép indítása (L)

```bash
az vm start -g szakdoga2-rg -n szakdoga2-vm
ssh azureuser@4.165.139.1 'docker ps --format "{{.Names}}: {{.Status}}"; sudo k3s kubectl get pods'
```

Elvárt: a `projecta-gitea`, `projecta-registry`, `projecta-act-runner` fut, a
`backend`, `frontend`, `postgres` podok `Running`.

**Ha az SSH időtúllépéssel elakad:** valószínűleg megint változott az otthoni
IP-d, és az NSG nem enged be. `curl -s ifconfig.me`, írd át az `allowed_cidr`-t a
`terraform/terraform.tfvars`-ban, majd `terraform -chdir=terraform plan`.
**Csak akkor `apply`, ha a terv kizárólag az NSG-szabály helybeni módosítását
mutatja** (`~ update in-place`). Ha `must be replaced` sor van benne, állj meg
(lásd `06-merogep-ujraepitese.md`).

## 4. Alagút (L, külön terminálablakban, maradjon nyitva)

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 azureuser@4.165.139.1
```

## 5. Push és a pipeline (L)

```bash
git push azure release/meres          # felhasználó: milan, a Gitea-jelszavad
```

Nyisd meg: `http://localhost:3000/milan/MilanProjA-Szakdoga/actions`

Elvárt: a `build-test-push` zöld, benne az új `Lint the frontend Dockerfile` és
`Scan the frontend image with Trivy` lépés is, utána a `deploy` zöld. Ellenőrzés:

```bash
git rev-parse --short HEAD
ssh azureuser@4.165.139.1 'curl -s http://localhost/api/version; echo'
```

A kettőnek ugyanazt a SHA-t kell mutatnia.

**Ha piros:** ne javítgasd a gépen. Töltsd le a bukott job naplóját, tedd a
repóba, és szólj.

## 6. Bizonyíték (L)

A Gitea felületén mindkét job naplóját töltsd le (a futás oldalán, a job
nevénél a „⋯” menü → letöltés), és mentsd ide:

```
szakdolgozat/bizonyitek/08-pipeline-zold-build.log
szakdolgozat/bizonyitek/08-pipeline-zold-deploy.log
```

```bash
git add szakdolgozat/bizonyitek/08-pipeline-zold-*.log
git commit -m "bizonyitek: az elso zold futas a frontend kapukkal"
git push azure release/meres          # ez is pipeline-t indít: várd meg, legyen zöld
```

## 7. Leállítás (L)

Az alagutat zárd be (Ctrl+C), aztán:

```bash
az vm deallocate -g szakdoga2-rg -n szakdoga2-vm
```

## 8. GitHub és a `main` (L)

A `main` 2026-09-17 óta áll, és még az Ansible-es pipeline van benne. A beadott
repó alapértelmezett ága ne ez legyen.

```bash
git push origin release/meres
gh pr create --base main --head release/meres \
  --title "release/meres: a szakdolgozat mert es lezart allapota" \
  --body "Gitea: build-test-push + deploy zold (<SHA>), naplok: szakdolgozat/bizonyitek/08-pipeline-zold-*.log"
```

A PR-t **merge committal** zárd, ne squash-sal (`docs/BRANCHING.md`, 7. szabály).
Utána:

```bash
git switch main && git pull origin main
```

## 9. Szólj

Írd meg, hogy megvan (vagy hol akadt el). Ezután frissítem a naplót és a
00-tervet, és a technikai rész lezárt.
