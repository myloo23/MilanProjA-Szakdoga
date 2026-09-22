# Lépésenkénti idők a kézi sorozatban

Forrás: a futtatások prompt-időbélyegei (`kezi-NN.txt`). Egy sor értéke két
egymást követő prompt különbsége, tehát a lépés teljes emberi költsége:
gondolkodás, gépelés és futásidő együtt (04-kezi-telepitesi-folyamat.md 5.).

Ez a fájl a 6.4 alfejezet nyersanyaga. A CSV az összesített adat, ez a bontás.

| # | Lépés | 1. (`kezi-NN`) | 2. (`kezi-03`) | 3. (`kezi-04`) |
|---|---|---:|---:|---:|
| 1 | push | 7 mp | 30 mp¹ | 8 mp |
| 2 | ssh | 6 mp² | (az 1-gyel együtt)¹ | 6 mp |
| — | *prompt beállítása (műszer, nem lépés)* | (a 2-vel együtt)² | 9 mp | 4 mp |
| 3 | fetch + checkout | 7 mp | 8 mp | 5 mp |
| 4 | SHA | 6 mp | 11 mp | 8 mp |
| 5 | backend build | 35 mp | 24 mp | 12 mp |
| 6 | frontend build | 3 mp | 4 mp | 2 mp |
| 7 | backend push | 9 mp | 8 mp | 5 mp |
| 8 | frontend push | 7 mp | 7 mp | 3 mp |
| 9 | helm upgrade | 6 mp | 6 mp | 4 mp |
| 10 | rollout backend | 16 mp | 17 mp | 16 mp |
| 11 | rollout frontend | 4 mp | 6 mp | 3 mp |
| 12 | /version | 6 mp | 6 mp | 5 mp |
| 13 | füstteszt | 9 mp | 8 mp | 5 mp |
| | **összesen** | **121 mp** | **144 mp** | **86 mp** |

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

## Amit ez a három sor megmutat — és ami emiatt a 6.1-be kell

**A legdrágább tétel a gördülő csere kivárása, nem a build.** A 10. lépés
mindhárom futtatásban 16–17 mp, és ez az egyetlen tétel, amely *nem* csökken:
gépi idő, amin sem gyakorlat, sem gyorsítótár nem segít. A 6.4 fő érve ez, mert
ugyanez a tétel az automatizált oldalon is ott lesz — a két sorozat különbsége
tehát nem innen jön.

**A többi tétel csökkenő trendet mutat, két különböző okból, és ezt szét kell
választani.** A backend buildje 35 → 24 → 12 mp: ez a réteg-gyorsítótár
bemelegedése, gépi ok. A gépelt lépések (3, 4, 7, 8, 12, 13) együtt 44 → 48 →
31 mp: ez az operátor gyakorlottsága, emberi ok. A kettő egy irányba mutat, és
összekeveredve azt a hamis képet adná, hogy a kézi folyamat „magától" gyorsul.

**Emiatt a három adatpont átlaga most nem értelmezhető.** 121 / 144 / 86 mp —
a szórás nagyobb, mint amekkora különbséget a 3.5 mérésétől várunk, és a sor
csökkenő. A 6.1-ben ezt nyíltan ki kell mondani, és a kiértékelésnek a sorozat
**beállt szakaszára** kell épülnie: ha a maradék futtatások egy szűk sávban
maradnak, az lesz a kézi oldal jellemző értéke, az első futtatások pedig a
tanulási görbe dokumentációjaként maradnak benne. Ha nem áll be, azt is ki kell
mondani, és akkor a kézi oldalt tartománnyal, nem átlaggal kell megadni.

**A 2. futtatás 30 mp-es 1–2. lépése kiugró érték.** A 3.-ban ugyanez 14 mp.
Az eltérés oka nem a folyamat, hanem az, hogy ott nem volt időbélyeges prompt a
laptopon, és a két lépés egybe esik; a sávot ez a pont torzítja felfelé.
