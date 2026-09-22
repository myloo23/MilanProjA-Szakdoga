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

## Hol tartok (2026-09-22)

**Kész:** 2.5 (a kézi telepítési folyamat), a kézi mérési sorozat tíz érvényes
futtatással, és a 2.6 kézi helyreállítási mérése három futtatással.

**Következik:**

1. A pipeline telepítő, ellenőrző és visszaállító szakaszának megépítése. Most
   csak a build van meg; a `.gitea/workflows/ci.yml` `deploy` jobja a kiindulás.
   Az ellenőrző lépéshez nem kell újat írni: a `smoke.yml` szerep már buktat.
   A `helm rollback` beépítése a hiányzó darab.
2. A 3.5 automatizált sorozata **tíz** futtatással (nem hússzal — így szimmetrikus
   a kézi sorozattal), `release/meres` ágra pusholva. Döntési szabály előre: ha az
   első tíz futtatás terjedelme néhány másodpercen belül marad, kész; ha szétszórt,
   megy tovább, amíg be nem áll.
3. Három automatizált helyreállítási futtatás, ugyanazzal a hibainjektálással.

**Feltétel mindkét automatizált sorozatra:** bemelegedett réteg-gyorsítótárral
kell futniuk, különben a különbség egy részét a build adná — pont az az
ellenvetés, amit a 6.4-ben ki akarunk zárni. A fürtön a `be36f74` fut, a
gyorsítótár meleg; `terraform destroy` nem jöhet szóba, mert elvinné a
Gitea-adatbázist, a runner regisztrációját és a registry tartalmát.

**Két eldöntetlen kérdés, mielőtt a szám a 6.4-be kerül:**

- Beavatkozás-e a V1? A kézi sorozatban a 13 a kiadott parancsok száma, eszerint
  a helyreállítás 18. Az 1. pont definíciója szerint („elolvas egy kimenetet és
  dönt róla") 19. A CSV most 18-cal van kitöltve; mindkét sorozatban ugyanazt
  kell alkalmazni, és a 6.1-ben ki kell mondani, melyiket.
- A „hibás verzió él" mérföldkő a 11. lépés vége (így van rögzítve), pedig a hiba
  a backendben van, tehát szigorúan a 10. lépés végén él. A 11. mellett a
  szimmetria szól (az automatizált oldalon is a teljes telepítés a kész-pont).
  Egy mondat a 6.1-ben.
