# 6. fejezet — Mérés és értékelés: váz és nyersanyag

Ezt te írod meg; ez a szerkezet, a számok forrása és a buktatók listája.
Minden szám a `bizonyitek/meres/` alatti fájlokból van, és 2026-09-30-án a
CSV-kből újra lett számolva (medián, sáv, átlag) — mind egyezik a README-vel,
két kivétellel, lásd a végén a **„Javítandó a fejezet előtt"** részt.

Rövidítések: **K** = kézi sorozat, **A** = automatizált sorozat,
**H** = kézi helyreállítás, **AH** = automatizált helyreállítás.

---

## 6.1 A mérés módszertana és protokollja

**Cél:** az olvasó a 6.1 végén meg tudná ismételni a mérést, és tudja, pontosan
mi számít egy mért másodpercnek és egy beavatkozásnak.

### 6.1.1 A kísérlet felállása
- Egy gép, egy fürt: `szakdoga2-vm` (Standard_B2s_v2, swedencentral), egycsomópontos
  k3s; ugyanott a Gitea, a runner és a registry.
  Forrás: `bizonyitek/02-regio-es-meret-valasztas.md`, `bizonyitek/01-terraform-plan.txt`.
- **A független változó az ágnév:** `meres/*` → nincs futtató, kézzel telepítesz;
  `release/meres` → a pipeline telepít. Forrás: `04-kezi-telepitesi-folyamat.md` 4. pont.
- **Ezt a mondatot pontosítani kell:** a két sorozat között az alapkép digestje és
  az image-építő is különbözik (`04-kezi-telepitesi-folyamat.md` 4.b, 4.c).

### 6.1.2 A mért ablak és az elfogadási kritérium
- Kezdet: a változtatás commitolva van, az első parancs előtti prompt időbélyege
  (K), illetve a push előtti prompt (A).
- Vég: a `/version` az új SHA-t adja, és a füstteszt tiszta.
- Telepítési szakasz: K 9–13. lépés összege; A `MERES deploy-start → accepted`.
- Forrás: `04-kezi-telepitesi-folyamat.md` 5. és 8. pont, `auto-lepesidok.md` „A módszer".

### 6.1.3 A változtatás
- Egyetlen jelölősor (`# meres-jelolo: NNN`) az `app/app.py` végén, K-ban `0NN`, A-ban `2NN`.
  Forrás: `04-kezi-telepitesi-folyamat.md` 3. pont, és a `git diff be36f74 d63eb00 -- app chart`
  (csak a jelölősor tér el).

### 6.1.4 A beavatkozás definíciója
- „Az operátor tesz valamit: kiad egy parancsot, vagy elolvas egy kimenetet és dönt róla."
  Forrás: `04-kezi-telepitesi-folyamat.md` 1. pont.
- Következmény, mindkét oldalon ugyanúgy: K = 13, H = 19 (V1 külön elbírálás),
  A = 2, AH = 2. Döntés és indoklás: `naplo.md`, „A két nyitott kérdés — eldöntve".
- Ki kell mondani, hogy a `scripts/smoke.sh` kilépési kódja mindig 0, ezért a kézi
  13. lépés emberi elbírálás, nem gépi kapu (`meres/README.md`).

### 6.1.5 Időmérés és rögzítés
- K: `script` + időbélyeges prompt, 1 mp-es felbontás. A: joblog `MERES` sorai
  (tizedes), push a laptopos jegyzőkönyvből. Minden UTC.
- Visszavezethetőség: a 40 pipeline-időbélyeg egyezik a `workflowlogok/` joblogjaival.
- Forrás: `meres/README.md` „A mérés menete", `auto-lepesidok.md`.

### 6.1.6 Futtatásszám és érvénytelen futtatások
- K: 10 érvényes; 4 elvetett (kezi-00, -01 próba; -02 és -06 érvénytelen, indokkal).
  Az ágnév azonosító, nem sorszám — a CSV `futtatas` oszlopa mérvadó.
- A: 10 érvényes, egy elvetett bemelegítő (Trivy-bukás, lásd 6.3).
- H és AH: 3–3 futtatás, plusz A0. Indoklás: a 00-terv 7. pontja a futtatásszámot
  a telepítési sorozatra írja elő.
- Statisztika: medián és sáv, átlag csak kiegészítésként. **Három pontnál csak sávot
  közölj, szórásról ne állíts semmit.**

> **Táblázat 6.1** — a mérés felállása: K és A oszlop, soronként gép, fürt, chart,
> elfogadási kritérium, alapkép digest és image-építő (itt látszik a két eltérés),
> trigger, rögzítés módja, és hogy a megfigyelő réteg **nem futott** (ADR-0010).

---

## 6.2 A kézi folyamat mérési eredményei

### 6.2.1 Telepítés (10 futtatás)
| | mind a 10 | beállt szakasz (4–10.) |
|---|---:|---:|
| medián | 74,5 mp | 71 mp |
| sáv | 64–144 mp | 64–79 mp |
| átlag | 85,2 mp | 71,6 mp |
| beavatkozás | 13 | 13 |
| elfogadás | 10/10 | 7/7 |

Telepítési szakasz (9–13. lépés): beállt 29–40 mp, medián 31; mind a tíz 29–43 mp,
medián 32,5 (a `lepesidok.md` táblájából számolva — **ezt a fájl még nem közli**).
Forrás: `kezi-sorozat.csv`, `lepesidok.md`.

> **Ábra 6.1** — futtatásonkénti teljes idő a sorszám függvényében (K), a beállt
> szakasz jelölésével. Ez mutatja a „tanulási hatást", amit a 00-terv kér.

**Mire figyelj:** a korai futtatások lassúsága **nem csak tanulás**. A backend build
az 1–2. futtatásban 35 és 24 mp, utána 10–12 mp: ez a réteg-gyorsítótár
bemelegedése, gépi ok. A 6.2-ben szétválasztva írd le (`lepesidok.md` 5. sor).

### 6.2.2 Lépésbontás
- A három tétel három viselkedése: gépi kivárás (10–11. lépés, 19–22 mp a beállt
  szakaszban), gépelés-és-olvasás (12–13.), build (5–8.). Forrás: `lepesidok.md`
  „Három tétel, három viselkedés".

> **Ábra 6.2** — halmozott oszlop a 13 lépésre, a beállt szakasz mediánjaival,
> gépi / emberi színezéssel.

### 6.2.3 Helyreállítás (H1–H3)
- A beinjektált hiba: `/echo` érvényes JSON-ra 500; `/health`, `/ready` ép, tehát a
  telepítés sikeresnek látszik. A hiba hatóköre mérve (egyetlen ellenőrzés bukik;
  a `RecursionError` javítása). Forrás: `meres/README.md` hibatábla.
- Észlelés 16–20 (med. 17), helyreállítás 34–39 (med. 37), kiesés 50–57 (med. 56),
  19 beavatkozás, V5 3/3 `be36f74`. Forrás: `hiba-sorozat.csv`, `hiba-lepesidok.md`.

---

## 6.3 Az automatizált folyamat mérési eredményei

### 6.3.1 A pipeline, amin mérve lett
- Egy bekezdés: a `deploy` job a sorozat előtt Ansible + Docker volt, Helm + k3s
  lett (ADR-0009), és két hiba derült ki (frontend kép nem épült, `GIT_SHA` hiányzott).
  **Ez az 5. fejezetbe tartozik; itt csak hivatkozz rá.** Forrás: `meres/README.md`
  „Mi változott a pipeline-ban".

### 6.3.2 Telepítés (10 futtatás)
- Teljes: 115–144 mp, medián 129,5; telepítési szakasz 23–26 mp, medián 24;
  2 beavatkozás; 10/10 elfogadás. Forrás: `auto-sorozat.csv`.
- Bontás: minőségi kapuk (B3+B4+B5+B7) 48–73 mp, „minden más" 67–72 mp.
  Forrás: `auto-lepesidok.md` (a tábla két utolsó sora).
- A szórás forrása: B5 (gyorsítótárazatlan `requirements-lint.txt`), 15,9–43,6 mp;
  a Trivy DB-letöltés és a runner image pull állandó. Forrás: `auto-lepesidok.md`
  2. megállapítás, `auto-nyers-jegyzet.md`.

> **Ábra 6.3** — halmozott oszlop futtatásonként: F+B1+J+D1 (futtató költsége),
> kapuk, build+push, D3 kivárás, D4 ellenőrzés. Egy ábrán látszik, hogy a sáv a B5-ből jön.

### 6.3.3 Helyreállítás (A0 és A1–A3)
- **A0:** ugyanaz a hiba, változtatás nélkül → a pytest 3 teszten bukik, a deploy
  nem indul, kiesés 0 mp, push → megállás 24 mp. Forrás: `auto-hiba-a0.csv`.
- **A1–A3:** a hiba a unit tesztek elől rejtve (`and not app.testing`), hogy a
  visszaállító lépés mérhető legyen. Észlelés 2–3 (med. 2), helyreállítás 23–25
  (med. 24), kiesés 25–28 (med. 26), 2 beavatkozás, version-assert 3/3 `e4da1d9`.
  Forrás: `auto-hiba-sorozat.csv`, `auto-hiba-nyers-jegyzet.md`, `auto-hiba-lepessor.md`.

### 6.3.4 Mellékeredmény: a zöld szkennelés szavatossága
- A bemelegítő futtatás 43 Trivy-találaton bukott változatlan függőségekkel, mert
  frissült a sérülékenység-adatbázis. Egy rövid bekezdés, mert a supply-chain
  rész (5.5) állítását méréssel támasztja alá. Forrás: `meres/README.md`, `docs/sbom/README.md`.

---

## 6.4 Összehasonlítás és értékelés

> **Táblázat 6.2** — a fő összevetés, egy táblában:

| Mutató | Kézi | Automatizált | Forrás |
|---|---:|---:|---|
| teljes idő, medián (sáv) | 71 mp (64–79)¹ | 129,5 mp (115–144) | `kezi-`, `auto-sorozat.csv` |
| ebből kapuk nélkül | 71 mp (64–79)¹ | 69 mp (67–72) | `auto-lepesidok.md` |
| telepítési szakasz, medián (sáv) | 31 mp (29–40)¹ | 24 mp (23–26) | `lepesidok.md`, `auto-sorozat.csv` |
| emberi beavatkozás (telepítés) | 13 | 2 | CSV-k |
| kiesés hibás telepítés után, medián (sáv) | 56 mp (50–57) | 26 mp (25–28) | `hiba-`, `auto-hiba-sorozat.csv` |
| emberi beavatkozás (helyreállítás) | 19 | 2 | CSV-k |
| kiesés, ha a hibát teszt fedi (A0) | 50–57 mp² | 0 mp | `auto-hiba-a0.csv` |

¹ beállt szakasz (4–10.), mellette közöld a tíz futtatás értékét is.
² a kézi útnak nincs tesztkapuja, tehát ugyanaz a hiba kimegy.

### A négy állítás, amit a 6.4 kimond (és ami alátámasztja)
1. **Az automatizálás nem gyorsabb, hanem többet végez ugyanabban a nagyságrendben.**
   Kapuk nélkül 67–72 mp vs 64–79 mp; a többlet pontosan a kapuk ára.
   → `auto-lepesidok.md` 1. megállapítás.
2. **A gépi kivárás mindkét oldalon ugyanaz**, a javulás a begépelt és elolvasott
   lépések helyéről jön. D3 19,5–22,0 vs kézi 10+11. lépés 19–22; D4 3,4–3,8 vs
   kézi 12+13. lépés 6–15 mp. → `auto-lepesidok.md` 3. megállapítás, `lepesidok.md`.
   Ez az előrejelzés a mérés *előtt* le volt írva (`lepesidok.md` „Mire kell
   számítani") — ezt emeld ki, erősebb, mint egy utólagos magyarázat.
3. **A helyreállítás kiesése kb. a felére csökken** (56 → 26 mp); a gépi kivárás
   itt is azonos (18–19 vs 19–21 mp), a V2 begépelése és a V5–V6 olvasása tűnik el.
   → `auto-hiba-nyers-jegyzet.md`, `auto-lepesidok.md` A1–A3 tábla.
4. **A legnagyobb hatás nem időben mérhető:** az A0-ban a hiba ki sem ment.
   A kézi úton ugyanez 50–57 mp kiesés.
- Szöveges különbség (nem szám): a két oldalon ugyanaz az ellenőrzéskészlet fut, de
  K-ban ember dönt, A-ban gép, az ember csak a verdiktet olvassa. → `naplo.md`.

> **Ábra 6.4** — két oszloppár (telepítési szakasz, kiesés) gépi / emberi
> részre bontva. Ez a fejezet fő ábrája.

**Ne írd le:** „X-szer gyorsabb", „Y %-os javulás" a teljes időre. A 24/31 és a
26/56 arány közölhető, de mindig a sávval és a 6.5 korlátaival együtt.

---

## 6.5 Az eredmények érvényessége és korlátai

Mindegyikhez: mi a fenyegetés → mit tettél ellene → mi marad.

1. **Utólagos újrajátszás, egyetlen operátor.** A kézi értékek a rendszert ismerve
   készültek, tehát a valóságosnál kedvezőbbek → a javulás alsó becslés.
   Ellensúlyozás: rögzített lépéslista, azonos kritérium, sorrend közölve. (00-terv 8.)
2. **A beállt szakasz kiválasztása csak a kézi oldalon.** Indoklás: gépi (cache) és
   emberi bemelegedés, mindkettő kimutatva. Közöld mindkét nézetet (lásd 6.2 tábla).
3. **Két nem szándékos eltérés a sorozatok között:** az alapkép digestje és az
   image-építő (legacy vs BuildKit). Bizonyíték, hogy nem torzít: a gördülő csere
   K 19–22, A 19,5–22,0 mp; a build K 12–15, A 11,9–13,4 mp; a telepítési szakasz
   buildet nem tartalmaz. Forrás: `04-kezi-telepitesi-folyamat.md` 4.b, 4.c.
4. **A mesterségesen rejtett hiba (A1–A3).** Az `and not app.testing` a tesztkaput
   szándékosan kerüli meg; ez a visszaállító utat méri, nem a kapukat. Az A0 mutatja,
   mi történik nélküle. Ha ezt nem mondod ki, a bíráló azt kérdezi, hogy „nem
   csaltad-e ki a rollbacket".
5. **Az észlelési idő felállásfüggő.** Mindkét oldal közvetlenül a telepítés után
   ellenőriz; olyan hibát, amit a füstteszt nem fed, egyik sem észlel.
   (`hiba-lepesidok.md` 2., `auto-hiba-nyers-jegyzet.md`)
6. **Kis minta a helyreállításban (n = 3).** Csak sáv, nincs szórás, nincs szignifikancia.
7. **Eltérő időfelbontás** (K 1 mp, A 0,1 mp) → összevetés egész másodpercen.
8. **Egy gép, egy alkalmazás, egy fürt.** A runner, a registry és a fürt egy 8 GB-os
   gépen; általánosítani nem lehet. A B5 szórása gyorsítótár-beállítás, nem a
   módszer jellemzője → 7. fejezet.
9. **A Trivy-adatbázis időfüggése.** Ugyanaz a commit más napon piros lehet; a
   mért tíz futtatás egy adatbázis-állapoton ment.

---

## A bíráló legvalószínűbb kérdései — és a válasz helye

| Kérdés | Válasz | Hol |
|---|---|---|
| „Az automatizált út lassabb. Akkor minek?" | kapuk nélkül azonos; a többlet ellenőrzés | 6.4/1, `auto-lepesidok.md` |
| „A kézi oldalon miért csak 7 futtatást nézel?" | mindkettőt közlöd, és indokolod | 6.2, 6.5/2 |
| „Tényleg csak az ágnév különbözik?" | nem, a digest és az építő is; egyik sem hat a mért tételekre | 6.1.1, 6.5/3 |
| „Nem kicsalt hiba az A1–A3?" | szándékos, az A0 a kontroll | 6.3.3, 6.5/4 |
| „Az olvasás miért beavatkozás?" | a protokoll előre így definiálta, mindkét oldalon | 6.1.4 |
| „Három futtatásból mit lehet mondani?" | csak sávot | 6.5/6 |
| „Mi van, ha a füstteszt nem fedi a hibát?" | egyik oldal sem észleli | 6.5/5 |

---

## Javítandó a fejezet előtt — elvégezve 2026-09-30

1. ~~A „egyetlen változó az ágnév" állítás~~ — javítva: `bizonyitek/04-kezi-telepitesi-folyamat.md`
   **4.b** (alapkép-digest) és **4.c** (legacy építő vs BuildKit — ezt a javítás közben
   találtuk, a 7.b pont jóslata nem teljesült). Mindkettő hatása mérve korlátos,
   a telepítési szakaszt egyik sem érinti. A `meres/README.md`-ben hivatkozás.
   **A 6.1.1-ben és a 6.5/3-ban mindkét eltérést közöld.**
2. ~~129,5 vs 130,0 mp~~ — magyarázat az `auto-lepesidok.md` tábla alatt; a dolgozatban 129,5.
3. ~~A kézi telepítési szakasz mind a tízre~~ — a `lepesidok.md` új szakasza (29–43 mp,
   medián 32,5). Közben javítva ugyanott egy elavult bekezdés („mind az öt futtatásban").
4. **Szóhasználat** (ez nem fájljavítás, hanem írási szabály): a helyreállításnál
   **kiesési idő**, a telepítésnél **teljes idő**.
