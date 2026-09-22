# Lépésenkénti idők a kézi sorozatban

Forrás: a futtatások prompt-időbélyegei (`kezi-NN.txt`). Egy sor értéke két
egymást követő prompt különbsége, tehát a lépés teljes emberi költsége:
gondolkodás, gépelés és futásidő együtt (04-kezi-telepitesi-folyamat.md 5.).

Ez a fájl a 6.4 alfejezet nyersanyaga. A CSV az összesített adat, ez a bontás.

| # | Lépés | 1. (`kezi-NN`) | 2. (`kezi-03`) |
|---|---|---:|---:|
| 1 | push | 7 mp | 30 mp¹ |
| 2 | ssh | 6 mp² | (az 1-gyel együtt)¹ |
| — | *prompt beállítása (műszer, nem lépés)* | (a 2-vel együtt)² | 9 mp |
| 3 | fetch + checkout | 7 mp | 8 mp |
| 4 | SHA | 6 mp | 11 mp |
| 5 | backend build | 35 mp | 24 mp |
| 6 | frontend build | 3 mp | 4 mp |
| 7 | backend push | 9 mp | 8 mp |
| 8 | frontend push | 7 mp | 7 mp |
| 9 | helm upgrade | 6 mp | 6 mp |
| 10 | rollout backend | 16 mp | 17 mp |
| 11 | rollout frontend | 4 mp | 6 mp |
| 12 | /version | 6 mp | 6 mp |
| 13 | füstteszt | 9 mp | 8 mp |
| | **összesen** | **121 mp** | **144 mp** |

¹ A `kezi-03`-ban a laptop promptja nem volt időbélyeges (a `PROMPT` a `script`
előtt lett beállítva, így az új héj nem örökölte), ezért az 1. és a 2. lépés nem
bontható szét. A kezdő időbélyeg a `script`-fájl létrehozási idejéből jön, ami
pontosan az a pillanat, amikor a rögzítő héj elindult — a mérés kezdő- és
végpontja tehát érvényes, csak a két első lépés bontása hiányzik.

² Az 1. futtatásban a prompt beállítása a 2. lépés utáni promptig tartott, ezért
nem különíthető el; a `kezi-03`-ban külön látszik (9 mp). Ez a tétel mindkét
sorozatban műszerköltség, nem a folyamat része — a 6.4-ben ezt jelezni kell, de
levonni nem kell, mert a mért időszakon belül van, és a 6.5 konzervatív elve
szerint a kézi oldalt terhelő tételt nem szépítjük.

## Amit ez a két sor már most megmutat

A két legdrágább tétel mindkét futtatásban ugyanaz: a **backend buildje**
(35 / 24 mp) és a **gördülő csere kivárása** (16+4 / 17+6 mp). A build a második
futtatásra 11 mp-cel gyorsult, mert a réteg-gyorsítótár időközben bemelegedett —
ezt a 6.4-ben ki kell mondani: a sorozaton belül a build ideje csökkenő trendet
mutathat, és ez nem az operátor tanulási görbéje.
