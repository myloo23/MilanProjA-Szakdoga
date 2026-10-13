# A helyreállítási mérés lépéssora — H1, H2, H3

Ebből a fájlból másolj parancsot, **soha ne a terminál kimenetéből**
(04-kezi-telepitesi-folyamat.md 5. pont, a `kezi-06` bukásának oka).
Jelölés: **(L)** = laptop, **(G)** = mérőgép SSH-munkamenetben.
Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md)
5. pont (1–13. lépés) és 6. pont (V1–V6). Állapot: [`README.md`](README.md).

---

## 0. Egyszeri előkészítés — mindhárom futtatás előtt egyszer, nem mért

**(L) A ablak — SSH-alagút, végig nyitva marad mind a három futtatás alatt:**

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
ssh -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 \
  azureuser@$(terraform -chdir=terraform output -raw public_ip)
```

**(G) ugyanebben az A ablakban — E9 és a kiinduló állapot ellenőrzése:**

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
docker ps --format '{{.Names}}'
helm history projecta | tail -3
curl -s http://localhost/api/version; echo
```

Amit látni kell: pontosan három konténer (`projecta-gitea`, `projecta-registry`,
`projecta-act-runner`) — bármi negyedik egy futó pipeline-munka, várd meg;
a `helm history` utolsó sora `deployed`; a `/version` a `be36f74`-et adja.
Ha a `/version` nem `be36f74`, **állj meg**: a visszaállítás célja csúszott el,
és a V5 várt értéke nem az, ami a README-ben van.

**(L) B ablak — az alagút él-e:**

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:3000/    # 200
curl -sS http://localhost:5001/v2/; echo                            # {}
```

A B ablak munkakönyvtára a repó gyökere kell legyen, mert a 2. lépés
`terraform -chdir=terraform` hivatkozása innen oldódik fel.

A mérés alatt **semmilyen push nem megy a `main` ágra** (E9).

---

## 1. H1 — `meres/hiba-01` (`ae354e8`)

**Rögzítés indítása (L, B ablak) — a sorrend kötött, nem mért:**

```bash
script -q ~/meres/hiba-01.txt
export TZ=UTC
PROMPT='[%D{%H:%M:%S}] '$PROMPT
```

A harmadik parancs után megjelenő időbélyeges prompt az 1. lépés kezdete.

| # | Hol | Parancs | Mit várunk |
|---|---|---|---|
| 1 | L | `git push azure meres/hiba-01` | a push átmegy |
| 2 | L | `ssh azureuser@$(terraform -chdir=terraform output -raw public_ip)` | belépés |
| — | G | `PS1='[\D{%H:%M:%S}] '$PS1` | *műszer, nem lépés* |
| 3 | G | `cd ~/projecta && git fetch --all && git checkout meres/hiba-01 && git pull` | a commit a gépen van |
| 4 | G | `SHA=$(git rev-parse --short HEAD); echo $SHA` | `ae354e8` |
| 5 | G | `docker build -t localhost:5001/projecta-flask:$SHA --build-arg GIT_SHA=$SHA .` | megépül (~11 mp) |
| 6 | G | `docker build -t localhost:5001/projecta-frontend:$SHA frontend/` | gyorsítótárból (~2 mp) |
| 7 | G | `docker push localhost:5001/projecta-flask:$SHA` | a kép a registryben |
| 8 | G | `docker push localhost:5001/projecta-frontend:$SHA` | `Layer already exists` |
| 9 | G | `helm upgrade --install projecta ~/projecta/chart --set image.tag=$SHA` | `STATUS: deployed` |
| 10 | G | `kubectl rollout status deploy/backend --timeout=5m` | `successfully rolled out` |
| 11 | G | `kubectl rollout status deploy/frontend --timeout=5m` | `successfully rolled out` — **innentől él a hibás verzió** |
| 12 | G | `curl -s http://localhost/api/version` | `ae354e8` — a telepítés sikeresnek látszik |
| 13 | G | `~/projecta/scripts/smoke.sh http://localhost/api` | a 3. ellenőrzés (`valid JSON`) **HTTP 500**, a többi hat a szokásos |
| V1 | G | *a 13. lépés kimenetének elbírálása* | **nincs parancs** — az észlelés időpontja a 13. lépés utáni prompt |
| V2 | G | `helm rollback projecta` | `Rollback was a success` |
| V3 | G | `kubectl rollout status deploy/backend --timeout=5m` | `successfully rolled out` |
| V4 | G | `kubectl rollout status deploy/frontend --timeout=5m` | `successfully rolled out` |
| V5 | G | `curl -s http://localhost/api/version` | `be36f74` |
| V6 | G | `~/projecta/scripts/smoke.sh http://localhost/api` | mind a hét ellenőrzés a várt státusszal — **a V6 utáni prompt a helyreállás időpontja** |

**Lezárás (L/G) — nem mért:**

```bash
exit          # (G) kilépés az SSH-munkamenetből
exit          # (L) a script lezárása
cp ~/meres/hiba-01.txt ~/Documents/Szakdolgozat/MilanProjA-Szakdoga/szakdolgozat/bizonyitek/meres/
```

---

## 2. H2 — `meres/hiba-02` (`ce56582`)

Ugyanaz, három helyen más: a jegyzőkönyv neve, az ág neve és a 4. lépés várt SHA-ja.
A fürtöt nem kell visszaállítani: a H1 V2-je már a `be36f74`-re tette vissza.

```bash
script -q ~/meres/hiba-02.txt
export TZ=UTC
PROMPT='[%D{%H:%M:%S}] '$PROMPT
```

| # | Hol | Parancs | Mit várunk |
|---|---|---|---|
| 1 | L | `git push azure meres/hiba-02` | a push átmegy |
| 2 | L | `ssh azureuser@$(terraform -chdir=terraform output -raw public_ip)` | belépés |
| — | G | `PS1='[\D{%H:%M:%S}] '$PS1` | *műszer, nem lépés* |
| 3 | G | `cd ~/projecta && git fetch --all && git checkout meres/hiba-02 && git pull` | a commit a gépen van |
| 4 | G | `SHA=$(git rev-parse --short HEAD); echo $SHA` | `ce56582` |
| 5–13, V1–V6 | | **szó szerint a H1 szerint** | a 12. lépés a `ce56582`-t, a V5 a `be36f74`-et adja |

```bash
exit
exit
cp ~/meres/hiba-02.txt ~/Documents/Szakdolgozat/MilanProjA-Szakdoga/szakdolgozat/bizonyitek/meres/
```

---

## 3. H3 — `meres/hiba-03` (`84c46ae`)

```bash
script -q ~/meres/hiba-03.txt
export TZ=UTC
PROMPT='[%D{%H:%M:%S}] '$PROMPT
```

| # | Hol | Parancs | Mit várunk |
|---|---|---|---|
| 1 | L | `git push azure meres/hiba-03` | a push átmegy |
| 2 | L | `ssh azureuser@$(terraform -chdir=terraform output -raw public_ip)` | belépés |
| — | G | `PS1='[\D{%H:%M:%S}] '$PS1` | *műszer, nem lépés* |
| 3 | G | `cd ~/projecta && git fetch --all && git checkout meres/hiba-03 && git pull` | a commit a gépen van |
| 4 | G | `SHA=$(git rev-parse --short HEAD); echo $SHA` | `84c46ae` |
| 5–13, V1–V6 | | **szó szerint a H1 szerint** | a 12. lépés a `84c46ae`-t, a V5 a `be36f74`-et adja |

```bash
exit
exit
cp ~/meres/hiba-03.txt ~/Documents/Szakdolgozat/MilanProjA-Szakdoga/szakdolgozat/bizonyitek/meres/
```

---

## 4. Ha egy futtatás elszáll

A `script`-et `exit`-tel kell lezárni, a jegyzőkönyvet `hiba-NN-ervenytelen.txt`
néven megtartjuk, és a futtatást **új ágon** kell megismételni — a már felpusholt
ágon az 1. lépés „Everything up-to-date" lenne. A pótág (a laptopon, a repó
gyökerében, a `script`-en kívül):

```bash
git checkout -b meres/hiba-04 11bc38e
git checkout meres/hiba-01 -- app/app.py
sed -i '' 's/^# meres-jelolo: .*/# meres-jelolo: 104/' app/app.py
git commit -am "meres: hiba-04 (szandekos hibainjektalas a helyreallitasi mereshez)"
git rev-parse --short HEAD
git checkout feature/frontend
```

Ha a fürt közben hibás verzión ragadt (a V2 nem futott le), a visszaállítás
kézzel, a mérésen kívül: `helm rollback projecta`, majd
`curl -s http://localhost/api/version` → `be36f74`. `terraform destroy` ebben az
esetben sem jöhet szóba: elvinné a Gitea-adatbázist, a runner regisztrációját,
a registry tartalmát és a bemelegedett réteg-gyorsítótárat.

---

## 5. A három futtatás után

Futtatásonként a [`hiba-sorozat.csv`](hiba-sorozat.csv) egy sora, a három
`hiba-NN.txt` jegyzőkönyv ebbe a mappába másolva, és a lépésenkénti bontás a
`lepesidok.md` mintájára. A CSV oszlopai a jegyzőkönyv három promptidejéből
jönnek: a 11. lépés utáni (a hibás verzió él), a 13. lépés utáni (észlelés) és a
V6 utáni (helyreállt).
