# 2. hét, lépésről lépésre

Kiegészíti: [`01-megvalositasi-terv.md`](01-megvalositasi-terv.md)
Időszak: 2026-09-25 — 2026-10-01

A 2.1–2.3 pont kész: az Azure-fiók megvan, a `szakdoga2-rg` erőforráscsoport
Terraformból épül (swedencentral, `Standard_B2s_v2`, 1-es zóna), a gépen a
cloud-init feltelepítette a k3s-t, és a laptopról a
`KUBECONFIG=~/.kube/szakdoga-azure.yaml kubectl get nodes` egy `Ready`
csomópontot mutat.

---

## 2.4 — A platform átköltöztetése

**Mit csinálunk.** A `platform/compose.yaml`-ból a Gitea, az act_runner és a
registry felmegy a mérőgépre, és igazoljuk, hogy a k3s fürt le tud húzni képet
a gépen futó registryből.

**Mit NEM csinálunk.** A megfigyelhetőségi szolgáltatások (Prometheus, Grafana,
Loki, Alloy, cAdvisor, node-exporter) maradnak — azok a 3.4 pontban kerülnek át,
és ott nem is így: a mostani cAdvisor- és node-exporter-beállítások a Docker
Desktop macOS-beli virtuális gépéhez vannak igazítva, Linuxon mások kellenek.
Ezért van a `platform/compose.azure.yaml`: profil mögé teszi őket, így a
`docker compose up -d` hármat indít, nem kilencet. A 8 GB-os gépen, amin a k3s
és maguk a buildek is futnak, ez nem esztétikai kérdés.

**Két terminál kell.** Az egyikben a laptopod van (a repó gyökerében), a
másikban a gép. Ahol nem egyértelmű, ott oda van írva, melyik.

---

### 1. lépés — A cím és az alapállapot *(laptop)*

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
terraform -chdir=terraform output -raw public_ip; echo
KUBECONFIG=~/.kube/szakdoga-azure.yaml kubectl get nodes
```

Ha a `kubectl` nem látja a fürtöt, ne lépj tovább: a 2.3 kész-feltétele az,
hogy lássa.

---

### 2. lépés — A platform felmásolása *(laptop)*

```bash
./scripts/platform-sync.sh
```

A szkript a `platform/` mappát tükrözi a gép `~/platform/` könyvtárába (a
`.env` kimarad, az a gépen készül), és felviszi a `verify-azure-platform.sh`
ellenőrzőt is. Egy irányba másol: a repó a forrás. Ha a gépen javítasz valamit,
vidd vissza a repóba, különben a következő futás felülírja.

---

### 3. lépés — Belépés és józansági ellenőrzés *(gép)*

```bash
ssh azureuser@$(terraform -chdir=terraform output -raw public_ip)

docker version --format '{{.Server.Version}}'
docker compose version
ls ~/platform
sudo k3s kubectl get nodes
```

Ha a `docker version` jogosultsági hibát ad: a cloud-init hozzáadott a `docker`
csoporthoz, de a *már megnyitott* munkamenet ezt nem tudja. Lépj ki, lépj be
újra (`exit`, majd megint `ssh`).

Egy dolgot érdemes itt megnézni, mert később órákat vihet el: a Docker és a k3s
ugyanazon a gépen saját iptables-szabályokat írnak.

```bash
docker run --rm busybox:1.36 ping -c1 1.1.1.1
```

Ha ez nem megy, a konténerek kifelé menő forgalma az, ami elromlott, nem a
compose-fájl — ezt jegyezd fel, és szólj, mielőtt tovább javítanál.

---

### 4. lépés — A `.env` a gépen *(gép)*

```bash
cd ~/platform
cp .env.example .env
sed -i 's/^GITEA_RUNNER_NAME=.*/GITEA_RUNNER_NAME=projecta-azure-runner/' .env
```

A tokent még nem tudjuk — az a Gitea elindulása után keletkezik. A többi érték
(képverziók, portok) mehet úgy, ahogy van. A `.env` a gépen sem kerül gitbe:
a `platform/.env` a repóban is ki van zárva.

---

### 5. lépés — Gitea és registry indítása *(gép)*

```bash
cd ~/platform
docker compose -f compose.yaml -f compose.azure.yaml up -d gitea registry
docker compose -f compose.yaml -f compose.azure.yaml ps
```

A runner még nem indul, mert regisztrációs token nélkül nincs mit csinálnia.

Várd meg, amíg a Gitea egészségesre vált (`healthy` a `ps` kimenetében), aztán:

```bash
curl -fsS http://localhost:3000/api/healthz; echo
curl -fsS http://localhost:5001/v2/; echo
```

**Miért nem a böngészőből.** A publikált portok a 127.0.0.1-re kötnek, ahogy a
laptopon is — a registrynek nincs hitelesítése, és ez a gép már publikus
IP-címen ül. A felület SSH-alagúton át érhető el (8. lépés), nem a tűzfalon át.

---

### 6. lépés — Admin felhasználó és runner-token *(gép)*

A laptopon a Gitea a webes telepítővarázslón keresztül állt be. Itt nem:
a `compose.azure.yaml` az `INSTALL_LOCK`-kal kikapcsolja, így a `terraform
destroy` + `apply` után sem marad benne kattintós lépés.

```bash
docker exec -u git projecta-gitea gitea admin user create \
  --admin --username milan --email milan.takacs24@gmail.com \
  --password 'ide-egy-erős-jelszót' --must-change-password=false
```

Aztán a token, egyből a `.env`-be:

```bash
TOKEN=$(docker exec -u git projecta-gitea gitea actions generate-runner-token | tr -d '\r\n')
echo "$TOKEN"
sed -i "s|^GITEA_RUNNER_REGISTRATION_TOKEN=.*|GITEA_RUNNER_REGISTRATION_TOKEN=${TOKEN}|" ~/platform/.env
grep RUNNER ~/platform/.env
```

*Ha a `gitea admin user create` azzal áll meg, hogy nincs adatbázis vagy nincs
konfiguráció:* állj meg itt. A B terv a webes telepítő (8. lépés alagútja, majd
`http://localhost:3000` a böngészőben, és a token a **Site Administration →
Actions → Runners** alól), de előbb nézzük meg, mit írt a
`docker logs projecta-gitea`.

---

### 7. lépés — A runner indítása *(gép)*

```bash
cd ~/platform
docker compose -f compose.yaml -f compose.azure.yaml up -d act-runner
docker logs -f projecta-act-runner
```

Sikeres regisztráció után a napló azt írja, hogy a runner regisztrált és
figyeli a feladatokat (`Ctrl-C` a követés leállítása, a konténer fut tovább).

Ha a regisztráció bukik és javítás után újrapróbálnád, a runner a már elmentett
állapotot látja; ilyenkor a saját kötetét el kell dobni:

```bash
docker compose -f compose.yaml -f compose.azure.yaml rm -sf act-runner
docker volume rm projecta-runner-data
```

---

### 8. lépés — A kész-feltétel ellenőrzése *(gép)*

```bash
~/verify-azure-platform.sh
```

Ez a 2.4 pont kész-feltétele futtatható alakban. Sorban: a három konténer fut;
a Gitea és a registry válaszol; a k3s containerd-konfigurációjában tényleg ott
van a `localhost:5001` tükör (amit a cloud-init `registries.yaml`-ja írt elő);
felnyom egy próbaképet a registrybe, **törli a gép Docker-gyorsítótárából**,
majd `imagePullPolicy: Always` beállítással elindít belőle egy podot. Ez a
törlés a lényeg: nélküle a teszt csak annyit bizonyítana, hogy a kép megvan
valahol a gépen, nem azt, hogy a fürt a registryből szedte.

A kimenetet mentsd el a bizonyítékok közé:

```bash
~/verify-azure-platform.sh 2>&1 | tee ~/2.4-verify.txt
```

Laptopról lehozni:

```bash
scp azureuser@$(terraform -chdir=terraform output -raw public_ip):2.4-verify.txt \
  szakdolgozat/bizonyitek/03-platform-koltoztetes-verify.txt
```

**A Gitea felülete** (nem kész-feltétel, de érdemes megnézni, hogy a runner
zölden látszik-e) — laptopról:

```bash
ssh -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 \
  azureuser@$(terraform -chdir=terraform output -raw public_ip)
```

Amíg ez az ablak nyitva van, a `http://localhost:3000` a gépen futó Gitea.

---

#### Amit a 3. ellenőrzés kihozott — és ami emiatt változott

A `registries.yaml`, amit a cloud-init kiírt, **nem csinál semmit ezen a
fürtön.** k3s v1.36.4 alatt a fájlból egyetlen sor sem került a generált
containerd-konfigurációba, a kép letöltése mégis sikerült; a fájl átnevezése és
a k3s újraindítása után is sikerült. Ez utóbbi a negatív próba, és ez dönti el:
a magyarázat a containerd alapértelmezése, amely a loopback-címre mutató
registryt kivételként kezeli és TLS nélkül is elfogadja.

Következmény: a `terraform/cloud-init.yaml`-ból a `write_files` blokk kikerült,
a helyén a megállapítás áll kommentben. A 4.5-ben nem szabad azt írni, hogy a
fürt a Terraform registry-beállítása miatt éri el a registryt — attól éri el,
hogy ugyanazon a gépen fut. Ez a D5 döntés melletti érv, nem egy külön
konfigurációé.

Két bizonyítékfájl tartozik hozzá, a laptopra lehozva:

```bash
IP=$(terraform -chdir=terraform output -raw public_ip)
scp azureuser@$IP:2.4-verify.txt \
  szakdolgozat/bizonyitek/03-platform-koltoztetes-verify.txt
scp azureuser@$IP:2.4-verify-registries-nelkul.txt \
  szakdolgozat/bizonyitek/03-platform-koltoztetes-verify-registries-nelkul.txt
```

### 9. lépés — Rögzítés *(laptop)*

A [`bizonyitek/03-platform-koltoztetes.md`](bizonyitek/03-platform-koltoztetes.md)
vázába írd be, ami eltért a leírtaktól, és commitold a repó változásait
(`platform/compose.azure.yaml`, `scripts/platform-sync.sh`,
`scripts/verify-azure-platform.sh`, ez a fájl).

---

### Amit a 2.4-ből tudnod kell — védésre, szóban

Nem a parancsokat kell fejből tudni, hanem ezt a hat dolgot. Mindegyik mögött
ott van, hogy a dolgozat melyik részében hivatkozol rá.

**1. Miért kell a fürtnek registry.** A Kubernetes nem a te gépedről kapja a
konténerképet, hanem *lehúzza* egy címről, amit a Deployment megad. A build
eredménye tehát csak akkor telepíthető, ha előbb felkerül valahová, ahonnan a
fürt kéri. Ez a "build once, push to registry" elv (ADR-0002): egyetlen
képpéldány készül, azt szállítjuk, nem építjük újra minden környezetben.
→ 4.6, és a mérés elfogadási kritériuma is erre épül (a `/version` a
képbe égetett SHA-t adja vissza).

**2. Miért éri el a fürt a `localhost:5001`-et.** Mert a k3s ugyanazon a gépen
fut, mint a registry, és a containerd a loopback-címre mutató registryt
kivételként kezeli: TLS nélkül is elfogadja. Ez nem beállítás kérdése — a
2.4-ben bizonyítottuk, hogy a `registries.yaml` nélkül is megy. Ha bárki
rákérdez, hogy "és ha másik gépen lenne a fürt?", a válasz: akkor vagy TLS és
hitelesítés kellene a registrynek, vagy a containerd `insecure` beállítása —
és pont ez az ára a D5 döntésnek.
→ 4.5, 4.6, D5.

**3. Mi a különbség a `localhost:5001` és a `registry:5000` között.** Ugyanaz a
registry, két nézőpontból. A `5000` a konténer saját portja, ezen a
`projecta-platform` hálózaton lévő konténerek érik el névvel. Az `5001` a
gazdagépre publikált port. Konténeren belül a `localhost` *az a konténer*, nem
a gép — ez a projekt leggyakoribb hibaforrása, a `docs/DEVELOPMENT.md` is ezzel
kezdi a platformfejezetet.
→ 4.6, és a pipeline hibakeresésénél.

**4. Miért köt minden port a 127.0.0.1-re.** A registrynek nincs hitelesítése,
és a gépnek publikus IP-címe van: ha a `0.0.0.0`-ra kötne, bárki felülírhatná
benne a képeket, amiket a fürt telepít — vagyis a "megváltoztathatatlan
artefaktum", amire az egész lánc épül, idegen kézbe kerülne. Ezért megy a
Gitea felülete SSH-alagúton, nem a tűzfalon át.
→ 6.5 és a biztonsági áttekintés F4 pontja.

**5. Miért nincs a Gitea beállításában kattintós lépés.** Mert a gép
Terraformból épül, és `destroy` + `apply` után újra kellene csinálni. Az
`INSTALL_LOCK` és a parancssori admin-létrehozás azt jelenti, hogy a platform
üzembe helyezése is reprodukálható. Ez ugyanaz az elv, amit a dolgozat mér,
csak eggyel lejjebb: ami kézzel van, az minden ismétlésnél újra fizetendő.
→ 4.5, és a 6. fejezet érvelésében.

**6. Mit ér a negatív próba.** Azt hittem, a `registries.yaml` miatt működik a
letöltés. Az ellenőrzés azt mutatta, hogy a fájl nem jelenik meg a containerd
konfigurációjában — ez még csak gyanú. Bizonyíték az lett, hogy *elvettem* a
fájlt, és a letöltés attól sem romlott el. **Egy állítás akkor bizonyított, ha
az ellenkezőjét is megpróbáltad előállítani.** Ez a 6. fejezet módszertani
része, és ugyanez az elv a visszaállítás-mérésben: a `helm rollback` képességét
nem az mutatja meg, hogy fut, hanem hogy szándékosan elrontott képpel is
visszaáll.
→ 6.1, és a 3.2 pont hibainjektálása.

### Ami a 2.4-gyel NEM lett kész, és tudni kell róla

1. **A chart még nem a registryre mutat.** A `chart/values.yaml`-ban a kép
   `flaskapp` és `frontend`, előtag nélkül — ez a k3d-s fejlesztésre volt jó,
   ahol az images kézzel voltak betöltve a fürtbe. Az Azure-os fürtön
   `localhost:5001/projecta-flask` és `localhost:5001/projecta-frontend` kell.
   Ez a 2.5 első lépése, mert a kézi telepítési folyamat leírása már ezzel
   fog menni.
2. **A tűzfal 3000-es szabálya feleslegessé vált.** A Gitea a loopbackra köt,
   tehát a szabály nem nyit meg semmit — de egy védésen az "ami nyitva van,
   annak indoka van" elv szerint jobb, ha nincs ott. A `terraform/main.tf`
   `http-from-my-ip` szabályából kivehető; a 80/443 marad az alkalmazásnak.
3. **A CI és a mért fürt egy gépen osztozik** (D5 döntés). Most, hogy a runner
   tényleg ott fut, ez már nem elméleti: a build terheli a fürtöt. A 6.5-ben ezt
   ki kell mondani, és a mérésben az a helyes érvelés, hogy ez a *kézi* oldalnak
   kedvez, tehát a kimutatott javulás alsó becslés marad.


---

## 2.5 — A kézi telepítési folyamat rögzítése

**Mit csinálunk.** A chart a registryre mutat, a mérőgép megkapja azt a néhány
eszközt, ami a kézi telepítéshez kell, és a kézi folyamat számozott listává
válik. A lista maga a
[`bizonyitek/04-kezi-telepitesi-folyamat.md`](bizonyitek/04-kezi-telepitesi-folyamat.md)
fájlban van — ez a 3.2 alfejezet nyersanyaga és egyben a mérőeszköz.

**Mit NEM csinálunk.** Nem mérünk. A 2.5 vége egy *próbafuttatás*, aminek az a
célja, hogy a lista hiteles legyen; a mért sorozat a 2.6.

---

### 1. lépés — A chart a registryre mutat *(kész, laptop)*

A `chart/values.yaml` mostantól előtagot is tartalmaz:

```yaml
image:
  registry: localhost:5001
  tag: dev

backend:
  image:
    repository: projecta-flask
frontend:
  image:
    repository: projecta-frontend
```

A két Deployment-sablon a `{{ with .Values.image.registry }}{{ . }}/{{ end }}`
alakot használja, tehát üres `registry` esetén előtag nélküli nevet ad — így a
k3d-s fejlesztés sem tört el. A nevek (`projecta-flask`, `projecta-frontend`)
azonosak azzal, amit a `ci.yml` már most is push-ol, tehát a pipeline
átállításakor (3.1) nem lesz névütközés.

A `scripts/verify-k3d.sh` ugyanezeket a neveket építi és tölti be a k3d-be; a
`localhost:5001/` előtag ott puszta név, mert a kép kézzel kerül a fürtbe, és az
`imagePullPolicy: IfNotPresent` miatt nincs registry-hívás.

Ellenőrzés, mielőtt bármi mást csinálnál *(laptop)*:

```bash
helm template projecta chart/ --set image.tag=abc123 | grep 'image:'
```

Négy sort kell látni: a két saját kép a `localhost:5001/` előtaggal és az
`abc123` taggel, valamint a `postgres:17-alpine` kétszer (a migrate init
container és a Postgres).

---

### 2. lépés — `helm` és `git` a mérőgépre *(gép)*

A cloud-init eddig csak a Dockert és a k3s-t rakta fel. A kézi telepítés a gépen
zajlik (a pipeline is ott fog), tehát a `helm` oda kell.

```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
git --version || sudo apt-get install -y git
```

A `terraform/cloud-init.yaml` ki lett egészítve ugyanezzel, hogy a **következő**
gép már így épüljön. A most futó gépen viszont **ne** csinálj `terraform
destroy` + `apply`-t emiatt: az elvinné a Gitea adatbázisát, a runner
regisztrációját és a registry tartalmát. A kézi felrakás és a cloud-init együtt
azt jelenti, hogy a gép reprodukálható, a mostani munkád meg megmarad.

---

### 3. lépés — A repó a gépen futó Giteába *(laptop + gép)*

A kézi telepítés is a verziókezelőn át kapja a kódot, ugyanúgy, mint a pipeline.
Ehhez a repónak léteznie kell az Azure-os Giteában.

Alagút a laptopról (amíg ez az ablak nyitva van, a `localhost:3000` a gépen futó
Gitea):

```bash
ssh -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 \
  azureuser@$(terraform -chdir=terraform output -raw public_ip)
```

A Gitea felületén hozz létre egy üres `MilanProjA-Szakdoga` repót, majd a
laptopon, a repó gyökerében:

```bash
git remote add azure http://localhost:3000/milan/MilanProjA-Szakdoga.git
git push azure main
```

A gépen ebből lesz a munkapéldány:

```bash
git clone http://localhost:3000/milan/MilanProjA-Szakdoga.git ~/projecta
```

A klón a gépről a saját `localhost:3000`-ére megy, alagút nélkül.

---

### 4. lépés — Secret és kubeconfig a fürtben *(gép)*

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get nodes

kubectl create secret generic db-credentials \
  --from-literal=POSTGRES_USER=projecta \
  --from-literal=POSTGRES_DB=projecta \
  --from-literal=POSTGRES_PASSWORD='ide-egy-erős-jelszót'
```

A `KUBECONFIG` sort tedd be a `~/.bashrc`-be is, különben minden új
SSH-munkamenetben újra kell. (A cloud-init azért írta a kubeconfigot 0644-gyel,
hogy ez sudo nélkül menjen — a mérőgépen ez vállalható, megosztott gépen nem
lenne az.)

---

### 5. lépés — A nulladik telepítés *(gép)*

A mérés **ismételt** telepítést mér, nem elsőt. Ezért a mérés előtt egyszer
telepíteni kell, hogy legyen mit felülírni, és mindkét sorozat ugyanabból az
állapotból induljon.

```bash
cd ~/projecta
SHA=$(git rev-parse --short HEAD)
docker build -t localhost:5001/projecta-flask:$SHA --build-arg GIT_SHA=$SHA .
docker build -t localhost:5001/projecta-frontend:$SHA frontend/
docker push localhost:5001/projecta-flask:$SHA
docker push localhost:5001/projecta-frontend:$SHA
helm upgrade --install projecta ~/projecta/chart --set image.tag=$SHA
kubectl rollout status deploy/backend  --timeout=5m
kubectl rollout status deploy/frontend --timeout=5m
curl -s http://localhost/api/version; echo
~/projecta/scripts/smoke.sh http://localhost/api
```

Ha a `/version` a `$SHA`-t adja vissza és a füstteszt tiszta, a rendszer a
mérés kiindulási állapotában van.

*Ha a pod `ImagePullBackOff`-ba megy:* a 2.4 megállapítása szerint a letöltés a
containerd loopback-kivételén múlik — ellenőrizd, hogy a kép neve tényleg
`localhost:5001/`-gyel kezdődik-e (`kubectl describe pod ...`), mert bármi más
előtaggal a kivétel nem érvényes.

---

### 6. lépés — A próbafuttatás *(mindkettő)*

Ez az, ami a listát hitelesíti. Vedd elő a
[`bizonyitek/04-kezi-telepitesi-folyamat.md`](bizonyitek/04-kezi-telepitesi-folyamat.md)
5. pontját, és játszd végig **pontosan úgy, ahogy le van írva**, a 3. pont
jelölősorának növelésével, a `meres/kezi-00` ágon.

A próbafuttatás **nem mérési adat**: a lista első végigjátszása a leglassabb
futtatás lenne, és torzítaná a tanulási görbét. Amit hoz: kiderül, hiányzik-e
lépés a listából, és hol pontatlan.

Ha bármi eltért, a listát javítsd, ne a futtatást igazítsd a listához.

---

### 7. lépés — Rögzítés *(laptop)*

A `04-kezi-telepitesi-folyamat.md` 8. pontjában írd át a kész-feltétel státuszát,
és commitold a változásokat (`chart/values.yaml`, `chart/templates/backend.yaml`,
`chart/templates/frontend.yaml`, `scripts/verify-k3d.sh`,
`terraform/cloud-init.yaml`, a két szakdolgozat-fájl).

---

### Amit a 2.5-ből tudnod kell — védésre, szóban

**1. Miért a mérőgépen épül a kép a kézi oldalon is.** Mert a pipeline is ott
épít. Ha a kézi oldal a laptopon építene, a mérés a laptop és a felhős gép
teljesítménykülönbségét is tartalmazná — a 00-terv 5. pontja pont ezt tiltja:
a különbség csak az automatizálásból jöhet.
→ 6.1, 6.5.

**2. Mi a kísérlet egyetlen változója.** Az ágnév. A `ci.yml` a `main`,
`release/**`, `feature/**` és `hotfix/**` ágakra figyel; a `meres/kezi-NN` ág
futtató nélkül marad, tehát ugyanaz a commit ugyanarra a gépre, ugyanabba a
registrybe, ugyanarra a fürtre kerül — csak egyszer emberi kézzel, egyszer a
pipeline-nal.
→ 6.1, 6.4.

**3. Mi számít egy emberi beavatkozásnak.** Egy kiadott parancs, vagy egy
kimenet elolvasása és elbírálása. A várakozás nem az. Enélkül a „13 kontra 1"
szám önkényes lenne, és a védésen az elsőre megkérdezett dolog.
→ 6.1.

**4. Miért kedvez a lista a kézi oldalnak.** A SHA változóba olvasása, a kész
füstteszt-szkript és az, hogy a folyamatot a rendszer ismeretében játsszuk
újra, mind gyorsítja a kézi oldalt. Ez tudatos: a kimutatott javulás így alsó
becslés.
→ 6.5, és a 00-terv 8. pontja.

**5. Miért olyan a beinjektált hiba, amilyen.** Átmegy a készenléti
ellenőrzésen, de megbukik a füstteszten. Ha összeomlásba vinné a podot, a hibás
verzió sosem lenne élő, és nem lenne mihez képest mérni a helyreállítást.
→ 6.1, és az 5.4 alfejezet.
