# A kézi mérési sorozat — állapot

Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md) 5. pont.
Adatsor: [`kezi-sorozat.csv`](kezi-sorozat.csv) · lépésenkénti bontás: [`lepesidok.md`](lepesidok.md).

## Hol tartunk (2026-09-22) — **a kézi sorozat kész**

| Futtatás | Ág | Állapot |
|---|---|---|
| — | `meres/kezi-00` | módszertani próba, nincs időadat (a stopper elmaradt) |
| — | `meres/kezi-01` | módszertani próba, eldobva (`clear`, előregépelés, ismételt lépések) |
| — | `meres/kezi-02` | **érvénytelen**: az 1. és 3. lépés a `kezi-01` ágat használta, így a már futó verzió települt újra; az elfogadási ellenőrzés emiatt önmagát igazolta vissza |
| **1.** | `meres/kezi-NN` | **érvényes, 121 mp, 13 beavatkozás** |
| **2.** | `meres/kezi-03` | **érvényes, 144 mp, 13 beavatkozás** (a kezdő időbélyeg a `script`-fájl létrehozási idejéből) |
| **3.** | `meres/kezi-04` | **érvényes, 86 mp, 13 beavatkozás**, eltérés nélkül |
| **4.** | `meres/kezi-05` | **érvényes, 67 mp, 13 beavatkozás**, eltérés nélkül |
| — | `meres/kezi-06` | **érvénytelen**: a rögzítés alatt egy korábbi terminálkimenet lett beillesztve promptokkal együtt, három `command not found`, a 2. lépés el sem indult; jegyzőkönyv: `kezi-06-ervenytelen.txt` |
| **5.** | `meres/kezi-07` | **érvényes, 75 mp, 13 beavatkozás**, eltérés nélkül |
| **6.** | `meres/kezi-08` | **érvényes, 71 mp, 13 beavatkozás**, eltérés nélkül |
| **7.** | `meres/kezi-09` | **érvényes, 74 mp, 13 beavatkozás**, eltérés nélkül |
| **8.** | `meres/kezi-10` | **érvényes, 79 mp, 13 beavatkozás**; a 12. lépésben 11 mp-es emberi szünet |
| **9.** | `meres/kezi-11` | **érvényes, 71 mp, 13 beavatkozás**, eltérés nélkül |
| **10.** | `meres/kezi-12` | **érvényes, 64 mp, 13 beavatkozás**, a sorozat leggyorsabb futtatása |

**A tíz érvényes futtatás megvan.** Beállt szakasz (4–10. futtatás): 64–79 mp,
átlag 71,6 mp, medián 71 mp, minden futtatásban 13 emberi beavatkozás, az
elfogadási ellenőrzés 10/10 sikeres. A kiértékelés a `lepesidok.md`-ben.

Az ágnevek nem esnek egybe a sorszámokkal: a `kezi-02` és a `kezi-06` érvénytelen
lett, a számozás pedig nem lett újrakezdve. **Az ág neve azonosító, nem sorszám;
a CSV `futtatas` oszlopa a mérvadó.** Ezt a 6.1-ben egy mondattal ki kell mondani.

## A helyreállítási mérés — **kész** (2026-09-22)

Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md)
6. pont (V1–V6). **Három futtatás**, nem tíz: a 00-terv 7. pontja a futtatásszámot
a telepítési sorozatra írja elő, a hibainjektálásos mérésre nem.

**A beinjektált hiba.** Mindhárom ágon ugyanaz: az `/echo` végpont érvényes
JSON-kérésre 500-at ad. A `/health` és a `/ready` érintetlen, tehát a pod elindul
és készenlétbe kerül — a telepítés *sikeresnek látszik*, és a füstteszt harmadik
ellenőrzése (`POST /echo · valid JSON`) az, ami elbuktatja. Pontosan ezt kéri a
protokoll: ha a pod összeomlana, a „mikor ment ki a hibás verzió" időpont
értelmezhetetlen lenne.

| Futtatás | Ág | Commit | Jelölősor | Állapot |
|---|---|---|---|---|
| H1 | `meres/hiba-01` | `ae354e8` | `101` | **érvényes**, 17/34/50 mp |
| H2 | `meres/hiba-02` | `ce56582` | `102` | **érvényes**, 17/39/56 mp¹ |
| H3 | `meres/hiba-03` | `84c46ae` | `103` | **érvényes**, 20/37/57 mp |
| — | `meres/hiba-04` | `138c660` | `104` | tartalék pótág, felhasználatlan |

**Mind a három futtatás megvan.** Észlelés 16–20 mp (medián 17), helyreállítás
34–39 mp (medián 37), a teljes kiesés 50–57 mp (medián 56), mindhárom futtatásban
18 emberi beavatkozás, a V5 mindháromszor a `be36f74`-et adta, a V6 füstteszt
mindháromszor tiszta. A kiértékelés: [`hiba-lepesidok.md`](hiba-lepesidok.md).

¹ A 11. lépés a 10. futása alatt lett előregépelve, így a két lépés prompt-ideje
összecsúszott (együtt 18 mp), és lépésenkénti bontásuk nem nyerhető ki. **A mért
helyreállítási ablakot ez nem érinti:** az előregépelés a telepítési szakaszban
történt, a „hibás verzió él" mérföldkő (a 11. lépés befejeződése, 09:42:50) valós
időpont, és onnantól minden lépés szabályosan, a prompt bevárásával ment. A
futtatás ezért érvényes, a lépésbontásban pedig lábjegyzetet kap — ugyanúgy,
ahogy a `kezi-03` az 1–2. lépés hiányzó időbélyege miatt. A 13. lépés után egy
üres Enter is rögzült; nem parancs, tehát nem beavatkozás.

A commitokat `git rev-parse --short meres/hiba-01` stb. is megadja; a 4. lépés
kimenete ezekkel kell egyezzen.

**A hiba hatóköre mérve van, nem feltételezve.** Az injektálás első változata a
füstteszt *két* ellenőrzését törte el: a `request.get_json(silent=True)` a mélyen
egymásba ágyazott törzsön `RecursionError`-t dob, azt pedig a `silent=True` nem
nyeli el (csak a `BadRequest`-et), tehát a „mélyen ágyazott JSON → sosem 5xx"
ellenőrzés is 500-at kapott volna 400 helyett. Ez a Flask 3.1.3 /
Werkzeug alatt reprodukálva lett a füstteszt öt törzsével; a javítás egy
`try/except RecursionError` az injektálás köré (`app/app.py`). A javítás után a
mért viselkedés:

| Füstteszt-ellenőrzés | Hibás verzió | Ép verzió |
|---|---|---|
| `GET /health` | 200 | 200 |
| `GET /ready` | 200 | 200 |
| `POST /echo · valid JSON` | **500** | 200 |
| `POST /echo · no Content-Type` | 400 | 400 |
| `POST /echo · malformed JSON` | 400 | 400 |
| `POST /echo · nested JSON` | 400 | 400 |
| `POST /echo · oversized` | 413 | 413 |

Ez azért nem kozmetika: a 6.5-ben azt állítjuk, hogy a beinjektált hiba
minimálisan invazív, és a mérés a *javítást* méri, nem a hiba természetét. Két
eltört ellenőrzés mellett ez az állítás nem állna meg.

**A `scripts/smoke.sh` kilépési kódja mindig 0.** A szkript kiírja az egyes
ellenőrzések HTTP-státuszát, de nem állít semmit (`set -u`, nincs `set -e`, a
`check()` nem hasonlít össze). A 13. lépés tehát **nem gépi kapu, hanem emberi
elbírálás** — pontosan ezért van V1 külön lépésként a protokollban, és ezért
számít beavatkozásnak. A 6.1-ben ki kell mondani. Az automatizált oldalon ez nem
így lesz: ott a `ansible/roles/deploy_app/tasks/smoke.yml` fut, amelynek minden
feladata elbuktatja a playt — a két oldal ugyanazt ellenőrzi, de csak az
automatizált oldalon gépi a döntés. Ez a különbség önmagában is eredmény, nem
mérési hiba.

**A `meres/hiba-*` névminta nincs a `ci.yml` figyelt ágai között**, tehát ezekre
sem indul futtató — ugyanaz a feltétel, mint a kézi sorozatban.

**Minden futtatás menete:** a protokoll 5. pontjának 1–13. lépése (a 13. **bukni
fog**, ennek elbírálása a V1), majd a V2–V6. A három futtatás teljes, parancsra
bontott lépéssora: [`hiba-lepessor.md`](hiba-lepessor.md) — **abból kell másolni**,
nem a terminál kimenetéből. Az előkészítés, az időmérés és a
rögzítés módja a lenti szakasz szerint, `kezi-NN` helyett `hiba-NN` névvel.

**A visszaállítás célja mindhárom futtatásban a `be36f74`** (a kézi sorozat
10. futtatása, ez fut most a fürtön). A `helm rollback` az előző revízióra lép,
és a visszaállítás maga is új revíziót hoz létre, tehát a H2 és a H3 előtti
állapot is a `be36f74` — az V5 mindhárom futtatásban ezt a SHA-t kell adja.

**A mért időszakaszok:** a 11. lépés vége (a hibás verzió él) → a 13. lépés
bukása (észlelés) → a V6 vége (a szolgáltatás újra jó). Az adatsor:
[`hiba-sorozat.csv`](hiba-sorozat.csv), a jegyzőkönyvek `hiba-NN.txt` néven.

## Az előkészítés (nem mért, a rögzítés előtt)

Jelölés: **(L)** = laptop, **(G)** = mérőgép. A laptopon két terminálablak kell:
az **A ablak** az SSH-alagutat tartja nyitva és végig ott marad, a **B ablak**
az, amelyikben a mérés zajlik.

**1. Az ág és a jelölősor-commit (L, B ablak).** A repó gyökerében:

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
git checkout -b meres/kezi-NN
sed -i '' 's/^# meres-jelolo: .*/# meres-jelolo: 0NN/' app/app.py
git commit -am "meres: kezi-NN"
git rev-parse --short HEAD          # ezt a SHA-t kell a 4. lépésnek visszaadnia
```

A `sed -i ''` a macOS változata; Linuxon `sed -i`.

**2. Az SSH-alagút (L, A ablak) — E8.** Ez az az alagút, amin a `git push azure`
és a registry elérhető; az 1. lépés enélkül elbukik. Külön ablakban indítsd, és
hagyd nyitva a futtatás végéig:

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
ssh -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 \
  azureuser@$(terraform -chdir=terraform output -raw public_ip)
```

Ez egy sima SSH-munkamenet a mérőgépen, csak a két porttovábbítással. **Nem** ez
a protokoll 2. lépése — azt a B ablakban, a rögzítés alatt kell megnyitni.

Hogy tényleg él-e, a B ablakban (L):

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:3000/    # 200
curl -sS http://localhost:5001/v2/; echo                            # {}
```

Ha az első nem 200-at ad vagy a második „connection refused", az alagút nincs
fent: nézd meg az A ablakot.

**3. Nem fut idegen build a runneren — E9.** A `ci.yml` a `main`-re figyel, a
futtató pedig a mérőgépen van: egy párhuzamos build ugyanazt a gépet terheli,
amit mérünk. Az A ablakban (G):

```bash
docker ps --format '{{.Names}}'
```

Pontosan hármat kell látni: `projecta-gitea`, `projecta-registry`,
`projecta-act-runner`. Bármi negyedik egy futó pipeline-munka konténere — várd
meg, amíg eltűnik, és csak utána indítsd a rögzítést.

E9 másik fele egy szabály, nem parancs: a futtatás alatt **ne** adj ki
`git push azure main`-t (és semmilyen más pushot a `main`-re), se a B ablakban,
se máshol. A B ablakban a `git branch --show-current` a mérési ágat adja vissza
— ha nem azt, állj meg.

## A mért futtatás indítása

**A sorrend kötött, és nem cserélhető fel:** előbb a `script`, és csak utána a
`TZ` meg a `PROMPT`. A `script` új héjat indít, amely a beállításokat nem
örökli: ha a prompt a `script` *előtt* lesz időbélyeges, a rögzítésben a laptop
lépései időbélyeg nélkül maradnak (ez buktatta meg a `kezi-03` időadatát).

A B ablakban (L):

```bash
script -q ~/meres/kezi-NN.txt
export TZ=UTC
PROMPT='[%D{%H:%M:%S}] '$PROMPT
```

A harmadik parancs után megjelenő időbélyeges prompt az 1. lépés kezdete.

A mérőgépen, az SSH-belépés (2. lépés) **után**, még a 3. lépés előtt:
`PS1='[\D{%H:%M:%S}] '$PS1`. Ez a prompt beállítása, nem a listán szereplő
lépés; a 3. lépés ideje az utána megjelenő promptól számít.

Ezután a protokoll 5. pontjának 1–13. lépése, egyesével, előregépelés nélkül,
`clear` nélkül. A parancsokat úgy kell beilleszteni, hogy **csak a parancs**
kerüljön a sorba, és semmi más:

- a protokoll táblázatának „Mit várunk" oszlopa nem része a parancsnak
  (a `kezi-03` 12. lépésébe így került bele a várt kimenet szövege);
- **soha ne a terminál kimenetéből másolj vissza parancsot**, mert a promptot is
  viszi magával, és a beillesztett blokk több sorban elindul (ez buktatta meg a
  `kezi-06`-ot). Mindig a protokollból vagy a lépéslistából másolj.

Ha mégis elszállt a futtatás: a `script`-et `exit`-tel kell lezárni, a
jegyzőkönyvet `kezi-NN-ervenytelen.txt` néven megtartjuk, és a futtatást **új
ágon** kell megismételni — a már felpusholt ágon az 1. lépés „Everything
up-to-date" lenne, ami a `kezi-02` hibáját hozná vissza.

A végén `exit` (a `script` lezárása), majd a jegyzőkönyv másolása ide:
`szakdolgozat/bizonyitek/meres/kezi-NN.txt`.

## A futtatás után rögzítendő

A CSV új sora: sorszám, ág, a 4. lépésben kiírt SHA, a 1. lépés **előtti** és a
13. lépés **utáni** prompt időbélyege, a kettő különbsége másodpercben, 13
beavatkozás (vagy a tényleges szám, ha eltérés volt), az elfogadás eredménye,
és minden eltérés megjegyzésben.

## Ami még nincs a repóban

A `~/meres/kezi-NN.txt` jegyzőkönyvek a laptopon vannak, ide másolandók a
sorozat végén a többivel együtt.

---

# Az automatizált sorozat — állapot

Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md)
4. pont (ágválasztás) · Adatsor: [`auto-sorozat.csv`](auto-sorozat.csv) ·
Joblogok: [`workflowlogok/`](workflowlogok/)

## Hol tartunk (2026-09-22) — **a telepítési sorozat kész**

Tíz érvényes futtatás a `release/meres` ágon, mindegyik zöld, az elfogadási
ellenőrzés 10/10 sikeres. A helyreállítási sorozat (három hibainjektálásos
futtatás) **még hátravan**.

## Mi változott a pipeline-ban a sorozat előtt

A `ci.yml` `deploy` jobja a sorozat előtt Ansible-lel egy Docker konténert
telepített a gazdagépre — vagyis **nem arra a rendszerre, amit a kézi sorozat
mér**. Ha így maradt volna, a 6.4 állítása („az egyetlen különbség az ágnév")
hamis lett volna. Az ADR-0009 döntését követve a job most `helm upgrade
--install`-lal telepít a k3s-fürtre, `--wait`-tel vár, az ingressen át ellenőriz,
és bukás esetén `helm rollback`-kel áll vissza. A részletek és az indoklás az
ADR-0009 kiegészítésében.

Két hiányosság is a sorozat előtt derült ki, és mindkettő a mérést érintette
volna:

- a pipeline **nem építette a frontend képet**, pedig a chart egy közös taggel
  mindkét Deploymentre hat — a frontend pod `ImagePullBackOff`-ba futott volna;
- a `docker build` nem kapta meg a `GIT_SHA` build-argumentumot, így a `/version`
  `dev`-et adott volna, és az automatizált oldal nem tudta volna teljesíteni azt
  az elfogadási kritériumot, amit a kézi oldal igen.

## Az eredmény

| | Kézi (beállt szakasz, 4–10.) | Automatizált (10 futtatás) |
|---|---:|---:|
| teljes idő, medián | 71 mp | 129,5 mp |
| teljes idő, sáv | 64–79 mp | 115–144 mp |
| **telepítési szakasz, medián** | **31 mp** | **24 mp** |
| telepítési szakasz, sáv | 29–40 mp | 23–26 mp |
| emberi beavatkozás | 13 | 1 |
| elfogadási ellenőrzés | 7/7 sikeres | 10/10 sikeres |

A „telepítési szakasz" a kézi oldalon a 9–13. lépés összege, az automatizált
oldalon a `MERES deploy-start` → `MERES accepted` ablak. Ez a két mennyiség fedi
ugyanazt a munkát; a teljes idők nem, mert az automatizált oldal teljes ideje
tartalmazza a lintelést, a teszteket és a szkenneléseket, amelyekből a kézi oldal
egyet sem végez.

**A `lepesidok.md` előrejelzése beigazolódott.** Ott az áll, hogy a gördülő csere
kivárása az automatizált oldalon sem lesz gyorsabb: a kézi 10+11. lépés 19–21 mp,
a `helm upgrade --wait` 19–22 mp. Ugyanaz a tétel, ugyanaz a nagyságrend. A 24
mp-es automatizált szakaszból tehát ~20 mp az, amit a kézi oldal is fizet, és a
javulás a maradékból jön. Ugyanott az is szerepel, hogy lényegesen nagyobb
javulás esetén a mérés felállását kell megnézni — nem lett nagyobb: 31 → 24 mp.

## A mérés menete

Futtatásonként: a jelölősor `2NN`-re állítása és a commit (nem mért idő,
a protokoll 2. pontja szerint), majd `script`-tel rögzített, időbélyeges
prompttal egyetlen parancs, a `git push azure release/meres`.

A mért ablak kezdete a push előtti prompt időbélyege a laptopon, vége a
`MERES accepted` sor a `deploy` job logjában. A pipeline négy mérföldkövet ír a
logba: `pipeline-start`, `deploy-start`, `live`, `accepted` (hibás futtatásnál
`detect` és `restored`). Minden időbélyeg UTC.

**Az adatok visszavezethetők.** A CSV mind a 40 pipeline-időbélyege egyezik a
`workflowlogok/` alatti joblogokkal, a 10 push-időbélyeg pedig a laptop
`auto-NN.txt` jegyzőkönyveivel. A joblogok neve a Gitea belső feladatszámát
viseli: a `ci-build-test-push-<n>` és a `ci-deploy-<n+1>` páros egy futtatás,
(12,13) az 1., (30,31) a 10.

## A szórás forrása — mérve, nem feltételezve

A teljes idő sávja (115–144 mp) tágabb, mint a kézi sorozat beállt szakaszáé.
A szórás teljes egészében a `build-test-push` jobban van (72–97 mp), és azon
belül **egyetlen szakaszban**: a `pytest` kezdetétől a Galaxy-telepítés
kezdetéig tartó rész 9–37 mp között ingadozik (27,5 mp terjedelem), miközben a
build minden más lépése együtt 56–68 mp (12,1 mp).

Ebben a szakaszban az `Install the Ansible control node and collections` lépés
pip-telepítése fut. A `requirements-lint.txt` csomagjai **nincsenek
gyorsítótárazva**: a `setup-python` `cache-dependency-path`-ja csak a
`requirements-dev.txt`-et nevezi meg, tehát ezek minden futtatásban a PyPI-ról
töltődnek le.

Elvetett magyarázat, mérés alapján: a Trivy adatbázis-letöltése (6,8–8,5 mp) és
a runner image pullja (2,9–3,6 mp) mindkettő állandó, tehát a szórást nem ők
adják.

**A `cache-dependency-path` bővítése nem a mérés előtt esedékes**, mert
megváltoztatná azt a pipeline-t, amelyen a tíz futtatás lefutott. A
továbbfejlesztési fejezetbe tartozik, mért számmal alátámasztva.

## Közben kiderült: a zöld szkennelésnek szavatossági ideje van

Az első `release/meres` előtti bemelegítő futtatás **elbukott** a Trivy
image-szkennelésen: 43 találat (40 HIGH, 3 CRITICAL) a `python:3.12-slim`
alapkép Debian-csomagjaiban, egy olyan commiton, amely sem a Dockerfile-t, sem
egyetlen függőséget nem érintett. A Trivy frissítette az adatbázisát.

A szkenner verziója pinelve van, az adatbázisa nem — és nem is lehet. A
reprodukálható build és a tiszta szkennelés tehát **két különböző garancia**: az
elsőt a digest-pin feltétel nélkül adja, a másodikat újra és újra ki kell
érdemelni. A kézi telepítési út nem bukik el ezen; csak sosem teszi fel a
kérdést. A javítás az alapkép digestjének léptetése Debian 13.7-re (a friss kép
szkennelése 0 találat); a részletek a `docs/sbom/README.md` végén.

## Ami még hátravan

1. Három automatizált helyreállítási futtatás, ugyanazzal a hibainjektálással,
   mint a `meres/hiba-*` ágakon. Adatsor: [`auto-hiba-sorozat.csv`](auto-hiba-sorozat.csv)
   (fejléc kész, sorok még nincsenek).
2. A `auto-lepesidok.md` — a `lepesidok.md` párja, a szakaszbontással.
3. Az `SBOM`-ok újragenerálása: a `projecta-flask-a6a4d33.cdx.json` más
   alapképről készült.
4. A 6.1-be: melyik két számot közöljük mindkét oldalra (teljes és telepítési
   szakasz), és beavatkozás-e a kimenet elolvasása — a V1-kérdés az automatizált
   oldalon úgy jelenik meg, hogy a pipeline zöld/piros eredményének elbírálása
   is beavatkozás-e. **Ugyanazt a szabályt kell alkalmazni mindkét sorozatra.**
