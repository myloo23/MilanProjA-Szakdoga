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
