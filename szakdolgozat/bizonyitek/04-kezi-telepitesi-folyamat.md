# 2.5 — A kézi telepítési folyamat

Dátum: 2026-09-21 · Státusz: **vázlat, az első próbafuttatás még nem erősítette meg**
Forrás: [`../01-megvalositasi-terv.md`](../01-megvalositasi-terv.md) 2.5 pont ·
Protokoll: [`../00-terv.md`](../00-terv.md) 7. pont
Ez a fájl a 3.2 alfejezet („A kiindulási, kézi telepítési folyamat") nyersanyaga,
és egyben a mérőeszköz: a 2.6 pontban az emberi beavatkozások számát **ez** a
lista definiálja.

---

## 1. Mit rögzít ez a lista, és mit nem

A mért folyamat kezdő- és végpontja a 00-terv 7. pontjából jön, és a mérés
mindkét oldalán azonos:

- **Kezdet:** a változtatás véglegesítve van a forráskódban (a commit megvan a
  laptopon). A szerkesztés és a commit ideje **nem** része a mérésnek — az
  fejlesztési idő, nem telepítési.
- **Vég:** az új verzió fut a fürtön, és az elfogadási ellenőrzés sikeres: a
  `/version` az új rövid SHA-t adja vissza, és a füstteszt hibátlan.

**Egy emberi beavatkozás definíciója.** Egy beavatkozás az, amikor az operátor
tesz valamit: kiad egy parancsot, vagy elolvas egy kimenetet és dönt róla. A
várakozás önmagában nem beavatkozás (a `kubectl rollout status` várakozása egy
beavatkozás, nem annyi, ahány másodpercig tart). Ez a definíció a 6.1-be is
bekerül, mert enélkül a lépésszám nem összehasonlítható semmivel.

**A lépéseket egyesével kell kiadni.** A mért futtatásokban minden parancs külön
megy el, az operátor elolvassa a kimenetét, és csak utána jön a következő. Egy
előre összeállított, egyben beillesztett parancsblokk valójában *egy*
beavatkozás — vagyis a kézi oldal titokban szkriptelve lenne, és pontosan azt
mérnénk el, amit vizsgálni akarunk. A 01-megvalositasi-terv D3 döntése ugyanezt
mondja ki a fejlesztői ellenőrzésről: a kézi oldalt szándékosan nem szabad
szkriptelni, mert ott az emberi lépések száma a mérőszám.

**Amit a lista nem tartalmaz:** az egyszeri előkészítést (2. pont). Az a gép
üzembe helyezése, nem telepítés; minden futtatás előtt ugyanúgy adott, tehát a
mérésbe nem számít bele.

---

## 2. Egyszeri előkészítés (a mérés előtt, egyszer)

Ezek a lépések a mérőgépet hozzák abba az állapotba, amelyből minden futtatás
indul. A mérés előtt kell megtenni őket, és nem számítanak bele a mért időbe.

| # | Mit | Hol | Miért |
|---|---|---|---|
| E1 | `helm` telepítése | mérőgép | A cloud-init csak a k3s-t és a Dockert rakta fel; a `helm upgrade` a gépen fut. |
| E2 | `git` megléte, a repó klónja `~/projecta`-ba a gépen futó Giteából | mérőgép | A kód a gépre a verziókezelőn át jut, ugyanúgy, ahogy a pipeline-nak. |
| E3 | A repó létrehozása a gépen futó Giteában, `azure` remote a laptopon, első push | laptop + gép | Enélkül nincs honnan klónozni. |
| E4 | `db-credentials` Secret létrehozása a fürtben | mérőgép | A chart nem tartalmazza (a jelszó nem megy gitbe), lásd `chart/values.yaml`. |
| E5 | `export KUBECONFIG=/etc/rancher/k3s/k3s.yaml` a gépen | mérőgép | A k3s 0644-gyel írja ki, tehát sudo nélkül olvasható (cloud-init indoklása). |
| E6 | **Nulladik telepítés:** a chart egyszer feltelepítve egy kiinduló SHA-val | mérőgép | A mérés *ismételt* telepítést mér, nem elsőt. Mindkét sorozat ugyanebből az állapotból indul. |
| E7 | A mérési változtatás helyének rögzítése | repó | Lásd a 3. pontot. |

**A mérőgép eszközverziói** (2026-09-21, a mérés megismételhetőségéhez):

| Eszköz | Verzió | Honnan |
|---|---|---|
| k3s | v1.36.4+k3s1 | cloud-init |
| helm | v3.22.0 | a hivatalos `get-helm-3` szkript |
| git | 2.43.0 | Ubuntu 24.04 csomag |
| Docker | a `docker.io` csomagból | cloud-init |

A `get-helm-3` mindig a legutolsó stabil kiadást rakja fel, tehát egy későbbi
`terraform destroy` + `apply` más helm-verziót adhat. Ha a mérés menet közben
megismétlődne, a fenti verziót kell visszaállítani (`get-helm-3 --version
v3.22.0`), különben a telepítés eszköze változna a két sorozat között.

E1 — a `helm` **a futó gépre kézzel kerüljön fel**, ne `terraform destroy` +
`apply` útján: az a Gitea-adatbázist, a runner regisztrációját és a registry
tartalmát is elvinné. A `terraform/cloud-init.yaml` viszont ki lett egészítve
vele, hogy a *következő* gép már tartalmazza — a reprodukálhatóság így marad
igaz, a most futó gép meg nem sérül.

---

## 3. A változtatás, amit minden futtatásnál telepítünk

Azonos típusú, triviális, viselkedést nem érintő módosítás, hogy a fejlesztési
idő ne keveredjen a telepítési időbe (00-terv 7.). Konkrétan: az `app/app.py`
végén álló jelölősor futtatásszámának növelése.

```python
# meres-jelolo: 007
```

Miért ez: új commit SHA keletkezik tőle (az elfogadási kritérium erre épül),
de nem változtat viselkedést, nem bukhat el rajta teszt, lintelés vagy
lefedettségi kapu — tehát az automatizált sorozatban sem okoz zajt.

---

## 4. Ág- és sorozatválasztás — ez a kísérlet egyetlen változója

A `.gitea/workflows/ci.yml` a `main`, `release/**`, `feature/**` és `hotfix/**`
ágakra figyel; **minden más ág futtató nélkül marad**.

- **Kézi sorozat:** `meres/kezi-NN` ágra push. A pipeline nem indul, a telepítést
  végig az operátor végzi.
- **Automatizált sorozat (3.5):** `release/meres` ágra push, ugyanazzal a
  változtatással. A pipeline elvégzi ugyanezt.

Így a két sorozat között egyetlen különbség van: melyik ágnévre ment a push.
Ugyanaz a gép, ugyanaz a registry, ugyanaz a fürt, ugyanaz a chart, ugyanaz az
elfogadási kritérium. A 6.4-ben ezt ki kell mondani, mert ez az, ami a
összehasonlítást érvényessé teszi.

---

## 5. A kézi telepítés lépései

Jelölés: **(L)** = laptop, **(G)** = mérőgép SSH-munkamenetben.

**Az időmérés módja.** Nem stopperrel, hanem időbélyeges parancssorral: minden
futtatás előtt, mindkét gépen be kell állítani, hogy a prompt kiírja a pontos
időt. Így a terminál kimenete maga a mérési jegyzőkönyv, és nincs kézi
óraleolvasás, ami elfelejthető vagy pontatlan.

```bash
# laptop (zsh)
PROMPT='[%D{%H:%M:%S}] '$PROMPT

# mérőgép (bash)
PS1='[\D{%H:%M:%S}] '$PS1
```

A prompt időbélyege akkor jelenik meg, amikor az előző parancs befejeződött.
Két egymást követő prompt különbsége tehát egy lépés teljes emberi költsége:
gondolkodás, gépelés és futásidő együtt. Ez helyes így — a gépelés a kézi
folyamat valódi költsége, és a pipeline-nak nincs ilyen tétele.

A futtatás ideje az **1. lépés előtti** prompt időbélyegétől a **13. lépés utáni**
prompt időbélyegéig tart. A teljes terminálkimenetet minden futtatásnál el kell
menteni (`bizonyitek/meres/kezi-NN.txt`), mert ez az elsődleges forrás; a
táblázat ebből készül, nem fordítva. A mentés a laptopon, az 1. lépés *előtt*
indított munkamenet-rögzítővel történik, tehát nem tartozik a mért lépésekhez:

```bash
script -q ~/meres/kezi-NN.txt     # innentől minden rögzül, az ssh-munkamenettel együtt
#   ... az 1–13. lépés ...
exit                               # a rögzítés lezárása
```

| # | Hol | Parancs / művelet | Mit várunk |
|---|---|---|---|
| 1 | L | `git push azure meres/kezi-NN` | a push átmegy |
| 2 | L | `ssh azureuser@$(terraform -chdir=terraform output -raw public_ip)` | belépés |
| 3 | G | `cd ~/projecta && git fetch --all && git checkout meres/kezi-NN && git pull` | a commit a gépen van |
| 4 | G | `SHA=$(git rev-parse --short HEAD); echo $SHA` | a telepítendő verzió azonosítója |
| 5 | G | `docker build -t localhost:5001/projecta-flask:$SHA --build-arg GIT_SHA=$SHA .` | a backend képe megépül |
| 6 | G | `docker build -t localhost:5001/projecta-frontend:$SHA frontend/` | a frontend képe megépül |
| 7 | G | `docker push localhost:5001/projecta-flask:$SHA` | a kép a registryben |
| 8 | G | `docker push localhost:5001/projecta-frontend:$SHA` | a kép a registryben |
| 9 | G | `helm upgrade --install projecta ~/projecta/chart --set image.tag=$SHA` | `STATUS: deployed` |
| 10 | G | `kubectl rollout status deploy/backend --timeout=5m` | `successfully rolled out` |
| 11 | G | `kubectl rollout status deploy/frontend --timeout=5m` | `successfully rolled out` |
| 12 | G | `curl -s http://localhost/api/version` | a válasz a 4. lépés SHA-ja |
| 13 | G | `~/projecta/scripts/smoke.sh http://localhost/api` | minden ellenőrzés a várt státusszal |

**Emberi beavatkozások száma: 13.** Az automatizált oldalon definíció szerint
**1** (a push).

Megjegyzések a lépésekhez:

- **4. lépés.** A SHA-t változóba olvassuk, nem kézzel másoljuk át négy
  parancsba. Ez **a kézi oldalnak kedvez** — a pipeline ezt ingyen kapja
  (`github.sha`), a valóságos kézi munkában pedig a kimásolás jellemző
  hibaforrás. Tudatos, konzervatív döntés: a kimutatott javulás így alsó becslés
  marad (6.5).
- **5–8. lépés.** A build és a push **a mérőgépen** történik, nem a laptopon.
  Indok: a pipeline is ott épít, és ha a kézi oldal a laptopon építene, a mérés
  a laptop és a felhős gép teljesítménykülönbségét is tartalmazná, nem csak az
  automatizálás hatását.
- **9. lépés.** A `--set image.tag` mindkét képre hat, mert a chart egy közös
  tagot használ (`chart/values.yaml`). A registry előtagja a chartban van
  (`image.registry: localhost:5001`), nem a parancsban.
- **12. lépés.** A `localhost:80` a k3s Traefik bejárata; onnan az Ingress a
  frontend nginx-éhez megy, az `/api/` előtagot az nginx vágja le
  (`frontend/nginx.conf`).
- **10–11. lépés.** Két külön parancs, mert két külön Deployment. Ez a kézi
  oldal egyik jellegzetes költsége: minden komponens külön figyelmet kér.

---

## 6. A hibainjektálásos helyreállítási mérés (kézi oldal)

A 2.6-ban három futtatás méri, mennyi idő visszaállni egy hibás telepítés után.

**A beinjektált hiba.** Olyan változtatás, amely **átmegy** az indulási és
készenléti ellenőrzésen, de **megbukik** az elfogadási kritériumon: az `/echo`
végpont érvényes kérésre 500-at ad. Miért így: ha a hiba a podot
összeomlásba vinné (`CrashLoopBackOff`), a hibás verzió sosem lenne „élő",
és a „mikor ment ki a hibás verzió" időpont értelmezhetetlen lenne. Így viszont
a telepítés sikeresnek *látszik*, és a füstteszt az, ami elbuktatja — vagyis
mindkét sorozatban ugyanaz az út fut le: telepítés → ellenőrzés → visszaállítás.

**A mért időszakaszok.** Kimenetel: a 11. lépés befejeződése (a hibás verzió él)
→ a 13. lépés bukása (észlelés) → a visszaállítás vége (a szolgáltatás újra jó).

| # | Hol | Parancs | Mit várunk |
|---|---|---|---|
| V1 | G | a 13. lépés kimenetének elbírálása | a füstteszt bukik |
| V2 | G | `helm rollback projecta` | `Rollback was a success` |
| V3 | G | `kubectl rollout status deploy/backend --timeout=5m` | `successfully rolled out` |
| V4 | G | `kubectl rollout status deploy/frontend --timeout=5m` | `successfully rolled out` |
| V5 | G | `curl -s http://localhost/api/version` | az **előző** SHA |
| V6 | G | `~/projecta/scripts/smoke.sh http://localhost/api` | hibátlan |

**Korlát, amit a 6.5-ben ki kell mondani:** itt az észlelés azonnali, mert az
operátor közvetlenül a telepítés után ellenőriz. A valóságban a hibás verzió
észrevétele órákig is tarthat. A mérés tehát **nem** az észlelést hasonlítja
össze, hanem a javítást — a két sorozat ebben a tekintetben azonos feltételű.

---

## 7. Amit rögzíteni kell minden futtatásnál

A 01-megvalositasi-terv 4. pontja szerint, azonnal, nem utólag:

futtatás sorszáma · kézi/automatizált · kezdés és befejezés időbélyege
(másodperc pontossággal) · emberi beavatkozások száma (e lista alapján) ·
az elfogadási ellenőrzés sikeres-e · megjegyzés.

---

## 7.b A nulladik telepítés — megtörtént

2026-09-21, `szakdoga2-vm`, commit `438647b`. Az E1–E6 előkészítés után a
chart elsőre feltelepült, kézi javítás nélkül:

| Lépés | Eredmény |
|---|---|
| backend kép buildje (gyorsítótár nélkül) | 27,4 s |
| frontend kép buildje (gyorsítótár nélkül) | 35,7 s |
| `helm upgrade --install` | `STATUS: deployed`, `REVISION: 1` |
| `kubectl rollout status` (backend, frontend) | `successfully rolled out` |
| `/version` | `{"version":"438647b"}` |
| füstteszt | mind a hét ellenőrzés a várt státusszal |

Két dolog, ami ebből a dolgozatba megy:

1. **A build nem domináns tétel.** Együtt sem éri el a másfél percet, ráadásul
   ez a *leglassabb* eset (üres réteg-gyorsítótár, minden alapkép letöltve).
   A 6.4-ben ez azért fontos, mert kizárja azt az ellenvetést, hogy a kézi és
   az automatizált oldal közti különbség valójában build-időkülönbség.
2. **A `localhost:5001` előtag a fürtben is működik.** A kép a Docker
   gyorsítótárából került a registrybe, a fürt onnan húzta le — a 2.4
   megállapítása (containerd loopback-kivétel) a valódi alkalmazásképekre is
   áll, nem csak a próbaképre.

Megjegyzés: a `docker build` a régi (legacy) építőt használja, mert a gépen
nincs buildx. A pipeline is ugyanezt fogja használni, tehát a két oldal ebben
sem tér el — ha a runner konténerében mégis buildx lenne, azt a 3.1-ben
egyeztetni kell, különben a build-idők nem összemérhetők.

---

## 7.c A próbafuttatás — megtörtént

2026-09-21, ág `meres/kezi-00`, commit `8f40012`. A lista mind a tizenhárom
lépése végigment, kézi javítás és kiegészítő lépés nélkül; a `/version` a
`{"version":"8f40012"}` választ adta, a füstteszt mind a hét ellenőrzésen
átment. A `helm upgrade` a 2. revíziót hozta létre, a két Deployment gördülő
cserével állt át.

**Amit a próbafuttatás kimutatott, és ami emiatt bekerült a protokollba:**

1. **Az időmérés módja.** Az első próbafuttatás alatt nem készült időadat, mert
   a stopperes mérés kézi mozzanat, és pont az veszett el. Ezért lett belőle
   időbélyeges parancssor (5. pont) — a mérőeszköz nem függhet attól, hogy az
   operátor emlékszik-e megnyomni valamit.
2. **A parancsok egyesével adandók ki.** A próbafuttatás alatt több parancs
   egyben, beillesztve ment el. A mérésben ez elfogadhatatlan, mert a
   lépésszámot értelmetlenné teszi (1. pont).
3. **A frontend képe nem épül újra.** A mérési változtatás az `app/app.py`-t
   érinti, a frontend forrása változatlan, és a frontend képe nem hordoz
   `GIT_SHA`-t, tehát bitre azonos marad: a build végig gyorsítótárból jön
   (azonos kép-azonosító), a push pedig csak egy új taget ír be (`Layer already
   exists`). A 6. és 8. lépés költsége ezért közel nulla minden futtatásban.
   Ez **nem torzít**, mert mindkét sorozatban ugyanígy lesz, de a 6.5-ben ki
   kell mondani: a mérés a frontend buildjét nem terheli, tehát az eredmény egy
   egykomponensű változtatás telepítésére vonatkozik.

A próbafuttatás **nem mérési adat**: a lista első végigjátszása a leglassabb
futtatás lenne, és torzítaná a tanulási görbét. Ezt a 6.1-ben is le kell írni.

---

## 7.d A második próbafuttatás (`kezi-01`) — a mérőeszköz behangolása

2026-09-21, commit `14cae9b`, jegyzőkönyv: [`meres/kezi-01.txt`](meres/kezi-01.txt).
Az időbélyeges prompt működött, a telepítés hibátlan volt (`/version` →
`14cae9b`, füstteszt tiszta), de a futtatás **adatsornak nem használható**:

- két `clear` parancs 53 másodperc holtidőt vitt bele;
- az 1. és a 12. lépés feleslegesen megismétlődött;
- több helyen előregépelés történt (a következő parancs a futó előző alatt), így
  a 7–8. és a 10–11. lépés prompt-időbélyegei összecsúsztak, lépésenkénti
  bontás nem nyerhető ki belőlük.

A kinyerhető szakaszidők (tájékoztatásul, nem mérési adat):

| Lépés | Idő |
|---|---|
| 1 · push | 18 mp |
| 2 · ssh | 8 mp |
| 3 · fetch + checkout | 7 mp |
| 4 · SHA | 8 mp |
| 5 · backend build | 18 mp |
| 6 · frontend build | 3 mp |
| 7–8 · registry push (össze­vont) | 14 mp |
| 9 · helm upgrade | 8 mp |
| 10–11 · rollout status (össze­vont) | 35 mp |
| 12 · /version | 3 mp |
| 13 · füstteszt | 8 mp |

Tiszta munkaidő kb. 2 perc 10 mp, teljes eltelt idő 3 perc 18 mp. **A
legdrágább tétel a gördülő csere kivárása (35 mp), nem a build** — ez a 6.4-ben
újabb érv amellett, hogy a két sorozat különbsége nem build-időkülönbség.

**Ebből következő szabályok a mért futtatásokra** (a 6.1-be is):

1. Nem gépelünk előre: minden parancs a prompt megjelenése után indul.
2. Nincs `clear`, és nincs semmilyen a listán kívüli parancs a rögzítés alatt.
3. Egy lépés nem ismételhető meg feleslegesen. Elrontott parancs benne marad —
   az valódi kézi költség —, de a szükségtelen ismétlés nem az.

**A mért sorozat ezért a `kezi-02`-vel kezdődik** és `kezi-11`-ig tart (tíz
futtatás). A `kezi-00` és a `kezi-01` módszertani próbafuttatás; a dolgozatban
ezt ki kell mondani, nem elhallgatni: a mérőeszközt két futtatáson hangoltuk be,
és az adatgyűjtés csak utána indult. Ez a 6.1 része, és a 00-terv 8. pontjának
„egyetlen operátor" korlátjához is tartozik.

Az adatsor gyűjtőfájlja: [`meres/kezi-sorozat.csv`](meres/kezi-sorozat.csv).

---

## 8. A kész-feltétel

> *Kész, ha:* a lista alapján valaki más is végig tudná csinálni.

Állapot: **teljesült** (2026-09-21). A lista a próbafuttatáson kiegészítés
nélkül végigvihető volt, a három fenti megállapítás pedig a protokollt
pontosította, nem a lépéssort. A 2.6 (a mért sorozat) indulhat.
