# A kézi mérési sorozat — állapot

Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md) 5. pont.
Adatsor: [`kezi-sorozat.csv`](kezi-sorozat.csv).

## Hol tartunk (2026-09-21 este)

| Futtatás | Ág | Állapot |
|---|---|---|
| — | `meres/kezi-00` | módszertani próba, nincs időadat (a stopper elmaradt) |
| — | `meres/kezi-01` | módszertani próba, eldobva (`clear`, előregépelés, ismételt lépések) |
| — | `meres/kezi-02` | **érvénytelen**: az 1. és 3. lépés a `kezi-01` ágat használta, így a már futó verzió települt újra; az elfogadási ellenőrzés emiatt önmagát igazolta vissza |
| **1.** | `meres/kezi-NN` | **érvényes, 121 mp, 13 beavatkozás** |
| 2–9. | `meres/kezi-03` … `kezi-10` | hátravan |

## A következő futtatás menete

Az `NN`-t mindenhol ki kell cserélni a futtatás számára: az ág nevében, a
`sed` mintájában, a commit üzenetében és a `script` fájlnevében. A 3. lépésben
ugyanaz az ágnév kell, a 4. lépés SHA-ját pedig össze kell vetni azzal, amit a
laptopon a `git rev-parse --short HEAD` kiírt.

## Ami még nincs a repóban

A `~/meres/kezi-NN.txt` jegyzőkönyv a laptopon van, ide másolandó a sorozat
végén a többivel együtt.
