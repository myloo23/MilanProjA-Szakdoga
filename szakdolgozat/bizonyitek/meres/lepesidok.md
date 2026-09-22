# Lépésenkénti idők a kézi sorozatban

Forrás: a futtatások prompt-időbélyegei (`kezi-NN.txt`). Egy sor értéke két
egymást követő prompt különbsége, tehát a lépés teljes emberi költsége:
gondolkodás, gépelés és futásidő együtt (04-kezi-telepitesi-folyamat.md 5.).

Ez a fájl a 6.4 alfejezet nyersanyaga. A CSV az összesített adat, ez a bontás.

| # | Lépés | 1. (`kezi-NN`) | 2. (`kezi-03`) | 3. (`kezi-04`) | 4. (`kezi-05`) |
|---|---|---:|---:|---:|---:|
| 1 | push | 7 mp | 30 mp¹ | 8 mp | 4 mp |
| 2 | ssh | 6 mp² | (az 1-gyel együtt)¹ | 6 mp | 4 mp |
| — | *prompt beállítása (műszer, nem lépés)* | (a 2-vel együtt)² | 9 mp | 4 mp | 2 mp |
| 3 | fetch + checkout | 7 mp | 8 mp | 5 mp | 4 mp |
| 4 | SHA | 6 mp | 11 mp | 8 mp | 3 mp |
| 5 | backend build | 35 mp | 24 mp | 12 mp | 11 mp |
| 6 | frontend build | 3 mp | 4 mp | 2 mp | 2 mp |
| 7 | backend push | 9 mp | 8 mp | 5 mp | 3 mp |
| 8 | frontend push | 7 mp | 7 mp | 3 mp | 3 mp |
| 9 | helm upgrade | 6 mp | 6 mp | 4 mp | 4 mp |
| 10 | rollout backend | 16 mp | 17 mp | 16 mp | 16 mp |
| 11 | rollout frontend | 4 mp | 6 mp | 3 mp | 3 mp |
| 12 | /version | 6 mp | 6 mp | 5 mp | 4 mp |
| 13 | füstteszt | 9 mp | 8 mp | 5 mp | 4 mp |
| | **összesen** | **121 mp** | **144 mp** | **86 mp** | **67 mp** |

¹ A `kezi-03`-ban a laptop promptja nem volt időbélyeges (a `PROMPT` a `script`
előtt lett beállítva, így az új héj nem örökölte), ezért az 1. és a 2. lépés nem
bontható szét, és a 30 mp felfelé torzít. A kezdő időbélyeg a `script`-fájl
létrehozási idejéből jön, ami pontosan a rögzítő héj indulása — a mérés kezdő-
és végpontja tehát érvényes, csak a két első lépés bontása hiányzik.

² Az 1. futtatásban a prompt beállítása a 2. lépés utáni promptig tartott, ezért
nem különíthető el. Ez a tétel mindegyik futtatásban műszerköltség, nem a
folyamat része — a 6.4-ben jelezni kell, de levonni nem, mert a mért szakaszon
belül van, és a 6.5 konzervatív elve szerint a kézi oldalt terhelő tételt nem
szépítjük.

---

## Három tétel, három viselkedés

**A gördülő csere kivárása állandó.** A 10. lépés mind a négy futtatásban
16–17 mp, és ez az egyetlen tétel, amely egyáltalán nem csökken: gépi idő,
amin sem gyakorlat, sem gyorsítótár nem segít. A 6.4 fő érve ez, mert ugyanez a
tétel az automatizált oldalon is ott lesz — a két sorozat különbsége nem innen
jön. A 11. lépéssel együtt 19 mp, ami a 4. futtatás teljes idejének 28%-a.

**A backend buildje beállt.** 35 → 24 → 12 → 11 mp. A csökkenés a réteg-
gyorsítótár bemelegedése volt, gépi ok; a 11-12 mp körüli érték a padló, mert
a `COPY app/` rétegtől lefelé minden lépés újraépül. Ez innentől nem mozog.

**A gépelt lépések még csökkennek.** A 3., 4., 7., 8., 12. és 13. lépés együtt
44 → 48 → 31 → 21 mp. Ez az operátor gyakorlottsága, emberi ok, és ez a sorozat
egyetlen még nyitott trendje.

## A sorozat nem állt be — mit jelent ez a kiértékelésre

121 / 144 / 86 / 67 mp. A 2. futtatás óta a sor szigorúan csökkenő, és a
csökkenés a 4. futtatásra sem állt le. Négy adatpont átlaga (104,5 mp) ezért
nem a kézi folyamat jellemző értéke, hanem a tanulási görbe egy pontja — a
dolgozatban átlagként leírni félrevezető lenne.

Amit a 6.1-nek ki kell mondania, és amire a 6.4 kiértékelésének épülnie kell:

1. A kézi oldal jellemző értéke a sorozat **beállt szakasza**, nem az egész
   sorozat. Beálltnak az a szakasz számít, ahol az egymást követő futtatások
   már néhány másodpercen belül maradnak.
2. Az első futtatások nem törlendők: a tanulási görbe maga is eredmény, és a
   6.5-ben érv amellett, hogy a kézi folyamat költsége operátorfüggő.
3. Ha a maradék futtatásokon sem áll be a sor, a kézi oldalt **tartománnyal**
   kell megadni, nem átlaggal.

**A fenti ok miatt a 3.5 automatizált sorozatát is bemelegedett gyorsítótárral
kell futtatni**, ahogy a kézi sorozat vége. Ha a pipeline hideg
gyorsítótárral indulna, a különbség egy részét a build adná — az pedig pont az
az ellenvetés, amit a 6.4-ben ki akarunk zárni.
