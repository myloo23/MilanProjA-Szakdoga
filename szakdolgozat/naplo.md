# Munkanapló

Lépésenként három mondat: **mit csináltam**, **mi lett volna nélküle**, **mit
bizonyít**. Nem a dolgozat szövege, hanem a nyersanyag hozzá — és a védésre ez
az, amiből felkészülsz, mert itt a saját szavaiddal van leírva.

Legfrissebb elöl.

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
10+11. lépés 19–21 mp, a `helm upgrade --wait` 19–22 mp — ugyanaz a tétel. A
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

## Hol tartok (2026-09-23)

**Kész:** a kézi telepítési sorozat (tíz futtatás), a kézi helyreállítási mérés
(három futtatás), a pipeline telepítő–ellenőrző–visszaállító szakasza, és az
automatizált telepítési sorozat (tíz futtatás).

**Kész 2026-09-23-án:** az automatizált helyreállítási sorozat (A0 + A1–A3, 2.8).

**Következik:** az
`auto-lepesidok.md` (a `lepesidok.md` párja) és az SBOM-ok újragenerálása — az
alapkép-bump miatt a `projecta-flask-a6a4d33.cdx.json` már más képről szól.

**A rollback útja mérve van.** Az A1–A3-ban a visszaállító lépés háromszor
futott le éles hibára, és mindháromszor a gépi version-assert igazolta, hogy az
`e4da1d9`-re lépett vissza.

**Nyitott, apró:** a `hiba-lepesidok.md` szövege még 18 beavatkozást ír; a
2026-09-22-i döntés szerint 19 (a CSV már javítva).

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
