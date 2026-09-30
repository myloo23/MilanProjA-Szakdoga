# Munkanapló

Lépésenként három mondat: **mit csináltam**, **mi lett volna nélküle**, **mit
bizonyít**. Nem a dolgozat szövege, hanem a nyersanyag hozzá — és a védésre ez
az, amiből felkészülsz, mert itt a saját szavaiddal van leírva.

Legfrissebb elöl.

---

## 3.1 — A mérőgépet a Terraform újraépítette (2026-09-30)

**Mi történt.** Az `allowed_cidr` átírása (új otthoni IP) utáni `apply` a gépet
törölte és újra létrehozta, mert a `cloud-init.yaml` 09-21-i, soha nem
alkalmazott módosítása függő gépcserét jelentett (a `custom_data` az azurerm-ben
ForceNew). A Gitea, a registry, a release és a Postgres adatai elvesztek; a
mérési bizonyítékanyag nem, mert a repóban van. Részletek és az újraépítés
lépései: `06-merogep-ujraepitese.md`.

**Mi lett volna nélküle.** Ha a bizonyítékok a gépen maradtak volna (joblogok a
Giteában, CSV-k a home-ban), a mérés ma elveszett volna. Hogy nem veszett el,
az annak a szabálynak köszönhető, hogy minden futtatás után minden bekerült a
repóba.

**Mit bizonyít.** A k3s-fürt kódból, kézi beavatkozás nélkül állt fel — ez a
2.3 kész-feltétele élesben. A platform és az alkalmazás visszaállítása viszont
kézi lépéssor: ez őszintén a 7. fejezet anyaga. A gépcsere megelőzésére a
VM `lifecycle { ignore_changes = [custom_data] }` blokkot kapott.

**Tanulság a módszertanhoz.** Az `apply` előtti tervet el kell olvasni: egy
NSG-módosításnak szánt futás egy `-/+ … must be replaced` sort is tartalmazott.

**Az első pipeline-futás az újraépült gépen piros lett — jogosan.** A ruff
E741-et talált a `scripts/sbom-inventory-xlsx.py`-ban (`l` változónév). A
szkript a `368b13e`-ben, a mérés *után* került be, és a `release/meres` azóta
nem ment fel az `azure`-ra, tehát pipeline-on még soha nem futott át. A kapu
azt tette, amire való: nem engedett ki lintelésen át nem ment kódot. Javítva
(`entry`), a ruff helyben tiszta.

**A második futás a Trivy-kapun bukott — másodszor ugyanazon a jelenségen.**
A `a4be106` backend képében (Debian 13.7, `python:3.12-slim@sha256:2f17fc04…`)
6 HIGH találat: CVE-2026-75804 és CVE-2026-84782 az OpenSSL-ben
(`libssl3t64`, `openssl`, `openssl-provider-legacy`), telepítve
`3.5.7-1~deb13u2`, javítva `3.5.7-1~deb13u3`-ban. Ugyanaz a digest 09-22-én
0 találatot adott. Nyolc nap alatt másodszor „jár le" egy zöld szkennelés —
az 5.5 állítása („a tiszta szkennelést újra és újra ki kell érdemelni") most
két független eseten áll. Teendő: az alapkép digestjének léptetése, ha a
Docker Hub képe már a `deb13u3`-at tartalmazza; addig a pipeline piros marad,
a kapu nem kerül kikapcsolásra.

**A megfigyelés ellenőrizve (ADR-0010).** `bizonyitek/05-megfigyeles-k3s-verify.txt`:
minden lépés zöld, a gördülő csere után 27 mp-cel a célpontok pontosan az új
podok. Az első futás (`…-verify-elso.txt`) a 7. lépésen bukott: a leálló pod
fázisa még `Running`, a script ezt nem várta — a script javítva, a
`prometheus.k3s.yml` téves kommentje is. Ábra: `05-grafana-golden-signals.png`
(a naplópanel „No data"-ja helyes: a panel csak warning/error sorokat mutat, és
ilyen nem volt).

---

## 3.0 — Javítások a 6. fejezet előtt, és a megfigyelés átkötése a k3s-re (2026-09-30)

**Mit csináltam.** A 6. fejezet vázának (`05-vazlat-6-fejezet.md`) írása közben
minden számot újraszámoltam a CSV-kből. A számok stimmeltek, de a módszertan egy
állítása nem: a 04-es protokoll 4. pontja szerint a két sorozat között az ágnév az
egyetlen különbség. Valójában kettő van még: a backend alapképének digestje
(`0efc8a2`, a kézi sorozatok után léptetve) és az image-építő (kézzel legacy,
a pipeline-ban BuildKit — a 7.b pont ezt előre megjósolta, és egyeztetést írt
elő, ami elmaradt). Mindkettőt a protokoll 4.b és 4.c pontjába írtam, a hatásukat
a már meglévő mérésből zártam ki: a gördülő csere 19–22 vs 19,5–22,0 mp, a build
12–15 vs 11,9–13,4 mp, a telepítési szakasz buildet nem tartalmaz.
Mellette: a `lepesidok.md` elavult („mind az öt futtatásban") bekezdése javítva,
a kézi telepítési szakasz mind a tíz futtatásra kiszámolva (29–43 mp, medián
32,5), a 129,5 / 130,0 mp eltérés megmagyarázva.

**Mi lett volna nélküle.** A bíráló egy `git diff be36f74 d63eb00 -- Dockerfile`
paranccsal megcáfolta volna a dolgozat egyik alapállítását, és onnantól minden
számot gyanúsnak nézett volna. Így a dolgozat maga mondja ki, és méréssel
mutatja, hogy nem számít.

**Mit bizonyít.** Hogy a mérés érvényességét nem az állítja, hogy „csak az
ágnév tér el", hanem hogy a többi eltérés hatása a mért tételeken belül ki van
zárva.

**A megfigyelés (ADR-0010).** A Prometheus/Loki/Grafana a mérőgépen profil
mögött volt és nem futott — a mérésnek ez jó volt (E9: pontosan három konténer),
az 5.6-nak nem. Most a stack a compose-ban marad, de a Prometheus a k3s API-tól
kérdezi le a backend podokat egy csak-olvasó ServiceAccounttal, az Alloy pedig a
`/var/log/pods` alól olvassa a naplókat. A dashboardok változatlanok.
Konfiguráció ellenőrizve (promtool, alloy, compose config, shellcheck; az Alloy
CRI-láncát hamis podnaplóval próbáltam ki), **a gépen még nem futott**:
`observability-k3s-up.sh`, majd `ROLLOUT=1 ./verify-observability-k3s.sh`.

**A képaláírás (cosign) nem készül el**, a 7. fejezetbe kerül. Indok: a mérés
lezárult, az aláírás a mért láncot megváltoztatná, és az 5.5 enélkül is áll
(függőségrögzítés, SBOM, sérülékenységvizsgálat — mind mérve/bizonyítva).

---

## 2.5 — A kézi telepítési folyamat rögzítése (2026-09-21)

**Mit csináltam.** A chart a `localhost:5001/` registry-előtagra állt át, a
mérőgép megkapta a helmet és a gitet, a repó felkerült a gépen futó Giteába, és
a kézi telepítés tizenhárom számozott lépéssé vált
(`bizonyitek/04-kezi-telepitesi-folyamat.md`). Két próbafuttatás igazolta a
listát, és hangolta be a mérőeszközt.

**Mi lett volna nélküle.** A kézi oldalnak nem lenne definíciója. „Kézzel
telepítettem" önmagában nem mérhető: ha nincs rögzített lépéslista, akkor az
emberi beavatkozások száma nem szám, hanem benyomás, és a 6.4 összehasonlítás
támadhatóvá válik.

**Mit bizonyít.** Hogy a mérés két oldala ugyanarra a gépre, ugyanabba a
registrybe és ugyanarra a fürtre telepít, és az egyetlen különbség az ágnév,
ami eldönti, indul-e futtató.

**Amit közben megtanultam.** Hármat.

1. *A mérőeszközt is meg kell mérni.* Az első próbafuttatásnál elfelejtettem
   stoppert indítani, a másodikban pedig előregépeltem és `clear`-t nyomtam —
   mindkettő használhatatlanná tette az adatot. A megoldás nem fegyelem, hanem
   eszköz: időbélyeges parancssor és `script`-tel rögzített jegyzőkönyv. Egy
   mérés, ami az operátor emlékezetén múlik, nem mérés.
2. *A pipeline olyat is megfog, amit az idő nem mutat.* A `main`-re pusholt
   doksijavítás elindította a futtatót, és az elbukott: a `requirements.in`-be
   felvett `psycopg` a `requirements-dev.txt`-be sosem lett újrafordítva, így a
   tesztek importja dőlt el. A konténerkép ettől jól működött, mert az a
   `requirements.txt`-ből épül — a hiba **csak** a tesztkörnyezetben létezett,
   és kézi telepítéssel soha nem derült volna ki. Ez az automatizálás olyan
   haszna, amit a 6.4-ben az időadatokon kívül külön ki kell mondani.
3. *A CI és a mért fürt egy gépen van (D5), és ez a mérés alatt kockázat.* Amíg
   a kézi sorozat tart, a `main` ágra nem szabad pusholni, mert a futtató a
   mérőgépet terheli. A 6.5-be ez a mérés érvényességének feltételeként kerül be.

---

## 2.4 — A platform átköltöztetése (2026-09-21)

**Mit csináltam.** A Gitea, az act_runner és a registry felment az Azure-os
mérőgépre, és igazoltam, hogy a k3s fürt le tud húzni képet a gépen futó
registryből.

**Mi lett volna nélküle.** A registry a laptopomon maradt volna, ahhoz pedig a
felhős fürt nem fér hozzá: a pipeline felépítené a képet, de telepíteni nem
tudná sehová. Ez a D5 döntés gyakorlati része.

**Mit bizonyít.** Hogy a lánc két vége összeért: ahová a build tesz, onnan a
fürt vesz. A `03-platform-koltoztetes-verify.txt` a bizonyíték.

**Amit közben megtanultam.** Azt hittem, a cloud-init `registries.yaml`-ja miatt
működik a letöltés. Nem: a fájl tartalma meg sem jelent a containerd
konfigurációjában, és a fájlt elvéve is működött. A valódi ok az, hogy a
containerd a `localhost:` előtagú registryt kivételként kezeli, mert az
ugyanazon a gépen van. **Egy állítás akkor bizonyított, ha az ellenkezőjét is
megpróbáltam előállítani.**

---

## 2.6 — A kézi helyreállítási mérés (2026-09-22)

**Mit csináltam.** Három hibainjektálásos futtatás a kézi oldalon
(`meres/hiba-01`, `-02`, `-03`). Mindháromban ugyanaz a beinjektált hiba: az
`/echo` érvényes JSON-kérésre 500-at ad, a `/health` és a `/ready` érintetlen,
tehát a telepítés sikeresnek látszik, és a füstteszt buktatja el. Utána
`helm rollback`, majd ellenőrzés.

**Az eredmény.** Észlelés 16–20 mp (medián 17), helyreállítás 34–39 mp (medián
37), a teljes kiesés 50–57 mp (medián 56). Mindhárom futtatásban 18 emberi
beavatkozás, a V5 mindháromszor a `be36f74`-et adta vissza. Adatsor:
`bizonyitek/meres/hiba-sorozat.csv`, kiértékelés: `bizonyitek/meres/hiba-lepesidok.md`.

**Amit közben megtanultam — két dolog, ami a 6.4-be és a 6.5-be megy.**

1. *A hibainjektálás hatókörét mérni kell, nem feltételezni.* Az injektálás első
   változata a `request.get_json(silent=True)`-t a meglévő `try` blokk elé tette.
   A füstteszt mélyen egymásba ágyazott törzsén ez `RecursionError`-t dob, amit a
   `silent=True` nem nyel el (csak a `BadRequest`-et), tehát a „mélyen ágyazott
   JSON → sosem 5xx" ellenőrzés is elbukott volna. A hiba így nem egy, hanem két
   ellenőrzést tört volna el, és a 6.5 „minimálisan invazív hiba" állítása nem
   állt volna meg. A javítás egy `try/except RecursionError` az injektálás körül;
   utána mind a három futtatásban pontosan egy ellenőrzés bukott.
2. *A `scripts/smoke.sh` kilépési kódja mindig 0.* Nincs `set -e`, a `check()`
   nem hasonlít össze semmit. A 13. lépés tehát **emberi elbírálás, nem gépi
   kapu** — ezért van a V1 külön lépésként a protokollban. Az automatizált
   oldalon ez nem így lesz: ott az `ansible/roles/deploy_app/tasks/smoke.yml`
   fut, amelynek minden feladata elbuktatja a playt. Ugyanaz az
   ellenőrzéskészlet, de csak az egyik oldalon gépi a döntés — ez önmagában is
   eredmény a 6.4-ben, nem mérési hiba.

**Ami a 6.4-nek elöl viendő.** A 34–39 mp helyreállításból 18–19 mp a két gördülő
csere kivárása (V3+V4), vagyis nagyjából a fele. Ez az automatizált oldalon is
ugyanennyi lesz: a `helm rollback` ott sem gyorsabb. A javulás a maradék ~20
mp-ből jöhet, és ha lényegesen több jönne ki, a mérés felállását kell megnézni.

---

## 2.7 — Az automatizált telepítési sorozat (2026-09-22)

**Mit csináltam.** Megépítettem a pipeline telepítő, ellenőrző és visszaállító
szakaszát, majd lefuttattam a tíz mért futtatást a `release/meres` ágon.

**Mi lett volna nélküle.** Nem a mérés maradt volna el, hanem ennél rosszabb: a
mérés lefutott volna, és rossz számot adott volna. A `deploy` job addig
Ansible-lel egy Docker konténert telepített a gazdagépre — vagyis **nem arra a
rendszerre, amit a kézi sorozat mér**. Ugyanaz az ágnév, ugyanaz a gép, csak épp
két különböző célpont. A 6.4 központi mondata („az egyetlen különbség az
ágnév") hamis lett volna, és ezt a táblázatból senki nem látta volna.

Ehhez jött két hiányosság, amelyek külön-külön is megbuktatták volna a
sorozatot: a pipeline nem építette a frontend képet (a chart egy közös taggel
mindkét Deploymentre hat, tehát a frontend pod `ImagePullBackOff`-ba futott
volna), és a `docker build` nem kapta meg a `GIT_SHA` argumentumot, így a
`/version` `dev`-et adott volna — az automatizált oldal nem tudta volna
teljesíteni azt az elfogadási kritériumot, amit a kézi oldal igen.

**Az eredmény.** Tíz érvényes futtatás, mind zöld, az elfogadás 10/10. Teljes
idő 115–144 mp (medián 129,5), telepítési szakasz 23–26 mp (medián 24), egy
emberi beavatkozás. A kézi beállt szakasz ugyanezekre: 64–79 mp (medián 71),
29–40 mp (medián 31), tizenhárom beavatkozás. Adatsor: `bizonyitek/meres/auto-sorozat.csv`,
kiértékelés: `bizonyitek/meres/README.md`, joblogok: `bizonyitek/meres/workflowlogok/`.

**Mit bizonyít.** Hogy a `lepesidok.md` előrejelzése állt. Azt írtam benne, hogy
a gördülő csere kivárása az automatizált oldalon sem lesz gyorsabb, és hogy ha
lényegesen nagyobb javulás jönne ki, a mérés felállását kell megnézni. A kézi
10+11. lépés 19–22 mp, a `helm upgrade --wait` 19–22 mp — ugyanaz a tétel. A
javulás 31 → 24 mp, vagyis a telepítési szakaszból az a rész javult, ami
gépelés és kimenetolvasás volt, a gépi rész nem. **Az előrejelzés teljesülése
itt erősebb bizonyíték, mint maga a szám**, mert azt mutatja, hogy a mérés azt
méri, aminek a mechanizmusát előre le tudtam írni.

**Amit közben megtanultam.** Hármat.

1. *Az automatizálás a teljes falióraidőben lassabb, és ezt előre ki kell
   mondani.* 129,5 mp a 71 mp-pel szemben. A különbség nem rejtély: a 93 mp-es
   build ruffot, Trivy secret-szkennelést, hadolintot, pytestet lefedettségi
   kapuval, ansible-lintet, két image-buildet és Trivy image-szkennelést futtat,
   amiből a kézi oldal egyet sem. A két teljes idő nem ugyanazt a munkát fedi, a
   telepítési szakasz viszont igen. Ha ezt a 6.1 nem mondja ki előre, a 6.4-ben
   végig magyarázkodás lesz belőle.

2. *A zöld sérülékenység-szkennelésnek szavatossági ideje van.* A bemelegítő
   futtatás elbukott 43 találattal a `python:3.12-slim` Debian-csomagjaiban, egy
   olyan commiton, amely sem a Dockerfile-t, sem egyetlen függőséget nem
   érintett. A Trivy frissítette az adatbázisát. A szkenner verzióját pineltem,
   az adatbázisát nem tudom — és nem is szabad: egy sérülékenység-adatbázis, ami
   nem változik, hibás. **A reprodukálható build és a tiszta szkennelés két
   különböző garancia**: az elsőt a digest-pin feltétel nélkül adja, a másodikat
   újra és újra ki kell érdemelni, és az egyetlen mechanizmus, ami kiérdemli,
   egy pipeline, ami minden commitra lefuttatja. A kézi út nem bukik el ezen;
   csak sosem teszi fel a kérdést. Ez a 6.4-be az időadatok mellé tartozik,
   ugyanúgy, mint a `psycopg`-eset.

3. *A szórás okát meg kell mérni, nem megtippelni.* Az első magyarázatom a
   72–97 mp-es build-sávra a hálózatfüggő tételek voltak: a Trivy
   adatbázis-letöltése és a runner image pullja. Kimértem őket a joblogokból, és
   mindkettő állandó (6,8–8,5 mp, illetve 2,9–3,6 mp) — a hipotézisem tehát
   téves volt. A valódi forrás egyetlen szakasz: a `pytest` kezdetétől a
   Galaxy-telepítés kezdetéig tartó rész 9–37 mp között ingadozik, miközben a
   build minden más lépése együtt 56–68 mp. Ott a `requirements-lint.txt`
   pip-telepítése fut, és annak a csomagjai nincsenek gyorsítótárazva: a
   `setup-python` `cache-dependency-path`-ja csak a `requirements-dev.txt`-et
   nevezi meg. Ugyanaz a módszer, amivel a kézi sorozat szórását bontottam
   tételekre — és ugyanaz a tanulság, mint a 2.4-ben a `registries.yaml`-nál:
   **egy magyarázat akkor magyarázat, ha megpróbáltam megcáfolni.**

**Amit nem javítottam, és miért.** A `cache-dependency-path` bővítése
csökkentené az átlagot és a szórást is. Nem nyúltam hozzá: megváltoztatná azt a
pipeline-t, amelyen a tíz futtatás lefutott. A továbbfejlesztési fejezetbe megy,
mért számmal. Ugyanez a frontend képre: nincs rajta hadolint és Trivy, mert egy
új kapu a mérési sorozat előtt vörösre tud menni egy alap-image-riasztástól,
ami nem a vizsgált változtatásról szól — és az mérési futtatásokat éget el.

---

## 2.8 — Az automatizált helyreállítási sorozat (2026-09-23)

**Mit csináltam.** Négy futtatás a `release/meres-hiba` ágon: A0 a kézi
sorozat injektálásával változatlanul, A1–A3 egy feltétellel (`and not
app.testing`).

**Mi derült ki a futtatás előtt.** A kézi sorozat hibája a pipeline-on el sem
jutott volna a fürtig: a `test_echo_valid_json` és még két teszt elbukik rajta,
a `deploy` job a `needs:` miatt nem indul, a visszaállító lépés tehát ebben a
formában soha nem futott volna le. Ha ezt nem ellenőrzöm előre, három futtatás
égett volna el úgy, hogy a CSV-ben üres `detect`/`restored` oszlopok maradnak.

**Az eredmény.** A0: a pytest megállította a hibát, push → megállás 24 mp,
kiesés 0. A1–A3: kiesés 25–28 mp (medián 26), a kézi 50–57 mp (medián 56)
ellenében; helyreállítás 23–25 mp a 34–39 mp ellenében; 2 beavatkozás a 19
ellenében. A rollback mindháromszor az `e4da1d9`-re lépett vissza, és ezt a
pipeline maga igazolta a version-assert-tel.

**Amit közben megtanultam.**

1. *Ugyanaz a hiba nem ugyanaz a kísérlet a két oldalon.* A kézi út nem futtat
   unit tesztet, tehát ott a hiba mindig kijut; a pipeline-on nem. A „mennyi
   idő alatt áll helyre" kérdés az automatizált oldalon csak olyan hibára
   értelmezhető, amely átjut a build kapuin — ezért kellett a feltétel, és
   ezért kellett az A0 is, hogy a feltétel ne rejtse el azt, hogy az eredeti
   hibát a pipeline meg sem engedi. A 6.5-ben mindkettőt ki kell mondani.
2. *Az előrejelzés másodszor is állt.* A gördülő csere kivárása a pipeline-ban
   19–21 mp, kézzel 18–19 mp. A javulás nem a gépi részből jön, hanem abból,
   hogy a V2 és a V5–V6 begépelése és elolvasása helyett ~4 mp gépi ellenőrzés
   fut.

---

## 2.9 — Az SBOM-ok harmadik generációja (2026-09-23)

**Mit csináltam.** Újrageneráltam az SBOM-okat az `e4da1d9`-re, vagyis arra a
release-re, amelyen a mérés futott, és amely most a fürtön fut. A generálás a
mérőgépen, a saját regisztrijéből történt, egy scripttel
(`scripts/sbom-generate.sh`). Új elem a frontend image SBOM-ja. Hét fájl, 771
komponens (előtte hat fájl, 621). Az xlsx nézetet is script építi
(`scripts/sbom-inventory-xlsx.py`), így az nem térhet el a JSON-októl.

**Amit nem vártam.** Az előző generáció **arm64** artifaktumokat írt le: a
laptopon épített image-et és a laptopon futó platformot, a 2.4-es költözés
előtt. Az új SBOM-okban minden architektúrafüggő purl `amd64`/`x86_64`. A
platform-image-eknél a csomagnevek és a verziók mindkét architektúrán
azonosak, ezért ez a komponenslistából nem látszott; csak a purl
`arch=` minősítője árulta el. A régi elavulás-őr útvonalakat figyelt, és
azok rendben voltak: nem a fájlok voltak rosszak, hanem a gép. **A 6.x-ben ezt
ki kell mondani: egy SBOM annyit ér, amennyire bizonyított, hogy ugyanarról az
artifaktumról szól, amely fut.** Ezt nem egy ellenőrzés, hanem a generálás
helye zárja ki.

**A többi változás megmagyarázható.** A backend image 26 csomagja a Debian
13.6 → 13.7 bumppal mozdult. Köztük van mind a hat csomagcsalád, amelyen a
2026-09-22-i CI-szkennelés a 43 találatot adta (`util-linux`, `perl-base`,
`libpcre2`, `libsqlite3`, `openssl`, `gzip`), most a leltár oldaláról nézve. A
4 új Python-csomag (`psycopg`, `psycopg-binary`, `prometheus_client`,
`typing_extensions`) a közben bejött adatbázis- és metrikaréteg. A frontend
image SBOM-jában nincs egyetlen npm-komponens sem, mert a React statikus
fájlokba van fordítva; ezeket csak a fájlrendszer-SBOM látja
(`frontend/package-lock.json`).

---

## Hol tartok (2026-09-23)

**Kész:** a kézi telepítési sorozat (tíz futtatás), a kézi helyreállítási mérés
(három futtatás), a pipeline telepítő–ellenőrző–visszaállító szakasza, és az
automatizált telepítési sorozat (tíz futtatás).

**Kész 2026-09-23-án:** az automatizált helyreállítási sorozat (A0 + A1–A3, 2.8).

**Kész 2026-09-23-án:** az `auto-lepesidok.md`. A teljes idő 115–144 mp-éből
48–73 mp a minőségi kapuké (Trivy secret, hadolint, pytest, ansible-lint,
Trivy image); a többi 67–72 mp, ugyanabban a sávban, mint a kézi beállt 64–79
mp. Közben kiderült, hogy a README és ez a napló a kézi 10+11. lépést 19–21
mp-nek írta; a `lepesidok.md` tábla szerint a beállt szakaszban 19–22 mp.
Javítva, a következtetést nem érinti.

**Kész 2026-09-23-án:** az SBOM-ok újragenerálása (2.9).

**Következik:** a 6. fejezet (Mérés és értékelés) vázlata, 6.1–6.5, állításonként
a bizonyítékfájlra hivatkozva, és a bíráló által legkönnyebben megtámadható
pontok listájával. A mérés lezárva, új futtatás nem kell.

**Függőben:** a `release/meres` pusholása az `azure`-ra (csak dokumentáció és
két script; a következő VM-indításkor).

**A rollback útja mérve van.** Az A1–A3-ban a visszaállító lépés háromszor
futott le éles hibára, és mindháromszor a gépi version-assert igazolta, hogy az
`e4da1d9`-re lépett vissza.

**Javítva 2026-09-23-án:** a `hiba-lepesidok.md` beavatkozásszáma 18 → 19, a
javítás indoklásával együtt.

---

## A két nyitott kérdés — eldöntve (2026-09-22)

Mindkettő azért volt nyitva, mert a választás **mindkét sorozatra** hat, és a
kézi oldal számait már rögzítettem. Most, hogy az automatizált oldal is megvan,
eldönthető, és a 6.1-be így megy.

### 1. Melyik időt közlöm

**Kettőt, mindkét oldalra: a teljes időt és a telepítési szakaszt.**

A teljes idő a protokoll szerinti ablak: a commit megvan → a működő telepítés
elfogadva. Kézi oldalon a 13 lépés, automatizált oldalon a push-tól a
`MERES accepted`-ig. Ez a becsületes szám, és ez az, amiben az automatizálás
**lassabb** (129,5 mp a 71 mp-pel szemben).

A telepítési szakasz a kézi 9–13. lépés, illetve a `deploy-start → accepted`
ablak. Ez a két mennyiség fedi ugyanazt a munkát — telepítés, kivárás,
ellenőrzés —, és ebben az automatizálás gyorsabb (24 mp a 31 mp-pel szemben).

Miért nem elég az egyik. Ha csak a teljeset közlöm, azt állítom, hogy az
automatizálás 1,8-szer lassabb, miközben a két szám nem ugyanazt a munkát fedi:
a pipeline lintel, tesztel és szkennel, a kézi út nem. Ha csak a szakaszt, akkor
elhallgatom, hogy a változtatás valójában kétszer annyi idő alatt ér a fürtre —
és azt joggal kérdezik meg. **A kettő együtt az igaz állítás**, és a kettő
különbsége maga az eredmény: az automatizálás nem gyorsabb, hanem *többet
csinál ugyanabban a nagyságrendben, egy beavatkozással tizenhárom helyett.*

### 2. Beavatkozás-e a kimenet elolvasása

**Igen, és mindkét sorozatban ugyanúgy.** A 04-es protokoll 1. pontja így
definiálja: „egy beavatkozás az, amikor az operátor tesz valamit: kiad egy
parancsot, **vagy elolvas egy kimenetet és dönt róla**". Ezt a definíciót nem
írom felül utólag azért, mert kényelmetlen.

Következmények, végigvezetve:

- A kézi **telepítési** sorozat 13 kiadott parancs, és a 13. lépés kimenetének
  elbírálása nem külön tétel, mert a 13. parancs és az elbírálása ugyanaz a
  lépés. Marad **13**.
- A kézi **helyreállítási** sorozat 13 + V1–V6. A V1 nem parancs, hanem kizárólag
  elbírálás (a `scripts/smoke.sh` kilépési kódja mindig 0, tehát a bukást az
  operátor állapítja meg). A definíció szerint tehát beavatkozás: **19**, nem 18.
  A CSV-t és a `hiba-lepesidok.md`-t javítani kell, és a javítás tényét
  megjegyzésben rögzíteni — nem csendben átírni.
- Az automatizált **telepítési** sorozat a push, plusz a pipeline zöld/piros
  eredményének elolvasása és elbírálása: **2**, nem 1.
- Az automatizált **helyreállítási** sorozat ugyanígy **2** lesz.

A 2 a 13 ellen ugyanazt mondja, mint az 1 a 13 ellen, és cserébe belső
ellentmondás nélkül. Ha az egyik oldalon beszámítom az olvasást, a másikon nem,
az a mérés legtámadhatóbb pontja lenne — pont az a fajta, amit egy bíráló
egyetlen kérdéssel kinyit.

**Egy különbséget viszont ki kell mondani a 6.4-ben:** a két oldalon ugyanaz az
ellenőrzéskészlet fut, de nem ugyanaz dönt. A kézi oldalon az operátor olvassa a
státuszokat és ítél; az automatizált oldalon a `smoke.yml` minden feladata
elbuktatja a playt, és az ember csak a kész verdiktet veszi tudomásul. A
beavatkozásszám ezt nem mutatja — mindkettő „egy olvasás" —, pedig a kettő nem
ugyanaz a kockázat. Ez a különbség szövegben tartozik a 6.4-be, nem számban.
