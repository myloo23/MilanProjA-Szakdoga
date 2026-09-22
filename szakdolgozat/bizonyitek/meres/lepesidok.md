# Lépésenkénti idők a kézi sorozatban

Forrás: a futtatások prompt-időbélyegei (`kezi-NN.txt`). Egy sor értéke két
egymást követő prompt különbsége, tehát a lépés teljes emberi költsége:
gondolkodás, gépelés és futásidő együtt (04-kezi-telepitesi-folyamat.md 5.).

Ez a fájl a 6.4 alfejezet nyersanyaga. A CSV az összesített adat, ez a bontás.

| # | Lépés | 1. (`kezi-NN`) | 2. (`kezi-03`) | 3. (`kezi-04`) | 4. (`kezi-05`) | 5. (`kezi-07`) | 6. (`kezi-08`) | 7. (`kezi-09`) | 8. (`kezi-10`) | 9. (`kezi-11`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | push | 7 mp | 30 mp¹ | 8 mp | 4 mp | 5 mp | 5 mp | 5 mp | 3 mp | 3 mp |
| 2 | ssh | 6 mp² | (az 1-gyel együtt)¹ | 6 mp | 4 mp | 9 mp | 5 mp | 4 mp | 4 mp | 4 mp |
| — | *prompt beállítása (műszer, nem lépés)* | (a 2-vel együtt)² | 9 mp | 4 mp | 2 mp | 3 mp | 3 mp | 5 mp | 3 mp | 2 mp |
| 3 | fetch + checkout | 7 mp | 8 mp | 5 mp | 4 mp | 4 mp | 5 mp | 3 mp | 3 mp | 3 mp |
| 4 | SHA | 6 mp | 11 mp | 8 mp | 3 mp | 4 mp | 4 mp | 3 mp | 5 mp | 3 mp |
| 5 | backend build | 35 mp | 24 mp | 12 mp | 11 mp | 11 mp | 11 mp | 11 mp | 11 mp | 12 mp |
| 6 | frontend build | 3 mp | 4 mp | 2 mp | 2 mp | 2 mp | 2 mp | 3 mp | 4 mp | 3 mp |
| 7 | backend push | 9 mp | 8 mp | 5 mp | 3 mp | 4 mp | 3 mp | 3 mp | 4 mp | 4 mp |
| 8 | frontend push | 7 mp | 7 mp | 3 mp | 3 mp | 3 mp | 3 mp | 4 mp | 2 mp | 5 mp |
| 9 | helm upgrade | 6 mp | 6 mp | 4 mp | 4 mp | 3 mp | 3 mp | 4 mp | 4 mp | 3 mp |
| 10 | rollout backend | 16 mp | 17 mp | 16 mp | 16 mp | 18 mp | 17 mp | 19 mp | 18 mp | 17 mp |
| 11 | rollout frontend | 4 mp | 6 mp | 3 mp | 3 mp | 2 mp | 3 mp | 3 mp | 3 mp | 4 mp |
| 12 | /version | 6 mp | 6 mp | 5 mp | 4 mp | 4 mp | 4 mp | 4 mp | 11 mp³ | 4 mp |
| 13 | füstteszt | 9 mp | 8 mp | 5 mp | 4 mp | 3 mp | 3 mp | 3 mp | 4 mp | 4 mp |
| | **összesen** | **121 mp** | **144 mp** | **86 mp** | **67 mp** | **75 mp** | **71 mp** | **74 mp** | **79 mp** | **71 mp** |

¹ A `kezi-03`-ban a laptop promptja nem volt időbélyeges (a `PROMPT` a `script`
előtt lett beállítva, így az új héj nem örökölte), ezért az 1. és a 2. lépés nem
bontható szét, és a 30 mp felfelé torzít. A kezdő időbélyeg a `script`-fájl
létrehozási idejéből jön, ami pontosan a rögzítő héj indulása — a mérés kezdő-
és végpontja tehát érvényes, csak a két első lépés bontása hiányzik.

³ A 8. futtatásban a 12. lépés 11 mp volt a szokásos 4–6 helyett: emberi szünet
a kimenet elolvasásakor. Bent marad, mert valódi kézi költség (a protokoll 1.
pontja szerint a lépés ideje a gondolkodást is tartalmazza) — de a sávot ez az
egy tétel tágítja 75-ről 79-re.

² Az 1. futtatásban a prompt beállítása a 2. lépés utáni promptig tartott, ezért
nem különíthető el. Ez a tétel mindegyik futtatásban műszerköltség, nem a
folyamat része — a 6.4-ben jelezni kell, de levonni nem, mert a mért szakaszon
belül van, és a 6.5 konzervatív elve szerint a kézi oldalt terhelő tételt nem
szépítjük.

---

## Három tétel, három viselkedés

**A gördülő csere kivárása állandó.** A 10. lépés mind az öt futtatásban
16–18 mp, és ez az egyetlen tétel, amely egyáltalán nem csökken: gépi idő,
amin sem gyakorlat, sem gyorsítótár nem segít. A 6.4 fő érve ez, mert ugyanez a
tétel az automatizált oldalon is ott lesz — a két sorozat különbsége nem innen
jön. A 11. lépéssel együtt 19–20 mp, ami az utolsó két futtatás teljes idejének
kb. negyede-harmada.

**A backend buildje beállt.** 35 → 24 → 12 → 11 → 11 mp. A csökkenés a réteg-
gyorsítótár bemelegedése volt, gépi ok; a 11 mp a padló, mert a `COPY app/`
rétegtől lefelé minden lépés újraépül. Ez innentől nem mozog.

**A gépelt lépések is beálltak.** A 3., 4., 7., 8., 12. és 13. lépés együtt
44 → 48 → 31 → 21 → 22 mp. A tanulási görbe a 4. futtatásra kifutott: az utolsó
két futtatásban a különbség egyetlen másodperc.

## A sorozat beállt — mit jelent ez a kiértékelésre

121 / 144 / 86 / **67 / 75 / 71 / 74 / 79 / 71** mp. Az első három futtatás a tanulási
görbe és a hideg réteg-gyorsítótár együttes hatását mutatja; a 4. futtatástól a
sor egy **67–75 mp-es sávban** mozog. A sávon belüli eltérés azonosítható
tételekre bontható, nem „mérési zaj":

- a gépelt lépések összege a hat futtatásban 21 / 22 / 22 / 20 / 29 / 23 mp; a
  29-es érték egyetlen tételtől nő meg (a 8. futtatás 12. lépésének 11 mp-es
  emberi szünete), e nélkül 22 mp — az operátor tehát már nem változik;
- a backend buildje mind a hatszor 11–12 mp;
- a gördülő csere kivárása 16 / 18 / 17 / 19 / 18 / 17 mp, és az SSH-kapcsolódás
  4 és 9 mp között ingadozik — **a sáv szélességét jórészt ez a két gépi tétel
  adja**.

Ez a 6.4-nek fontos: a kézi oldal maradék szórása is gépi eredetű, és ugyanez a
két tétel az automatizált oldalon is jelen lesz.

Amit a 6.1-nek ki kell mondania, és amire a 6.4 kiértékelésének épülnie kell:

1. A kézi oldal jellemző értéke a sorozat **beállt szakasza**, vagyis a 4.
   futtatástól kezdődő rész. Az első három futtatás nem törlendő: a tanulási
   görbe maga is eredmény, és a 6.5-ben érv amellett, hogy a kézi folyamat
   költsége operátorfüggő.
2. A beállt szakasz szórása néhány másodperc, és a maradék eltérés is gépi
   eredetű (SSH-kapcsolódás, gördülő csere) — ezt a 6.4-ben tételesen ki lehet
   mutatni a lépésbontásból, nem kell „mérési zaj"-jal elintézni.
3. Ha a beállt szakasz a további futtatásokon kilépne ebből a sávból, a kézi
   oldalt tartománnyal kell megadni, nem átlaggal.

**A fenti ok miatt a 3.5 automatizált sorozatát is bemelegedett gyorsítótárral
kell futtatni**, ahogy a kézi sorozat beállt szakaszát. Ha a pipeline hideg
gyorsítótárral indulna, a különbség egy részét a build adná — az pedig pont az
az ellenvetés, amit a 6.4-ben ki akarunk zárni.
