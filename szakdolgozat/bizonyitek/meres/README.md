# A kézi mérési sorozat — állapot

Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md) 5. pont.
Adatsor: [`kezi-sorozat.csv`](kezi-sorozat.csv).

## Hol tartunk (2026-09-22)

| Futtatás | Ág | Állapot |
|---|---|---|
| — | `meres/kezi-00` | módszertani próba, nincs időadat (a stopper elmaradt) |
| — | `meres/kezi-01` | módszertani próba, eldobva (`clear`, előregépelés, ismételt lépések) |
| — | `meres/kezi-02` | **érvénytelen**: az 1. és 3. lépés a `kezi-01` ágat használta, így a már futó verzió települt újra; az elfogadási ellenőrzés emiatt önmagát igazolta vissza |
| **1.** | `meres/kezi-NN` | **érvényes, 121 mp, 13 beavatkozás** |
| **2.** | `meres/kezi-03` | előkészítve (ág és commit kész), futtatásra vár |
| 3–9. | `meres/kezi-04` … `kezi-10` | hátravan |

Az ágnév számozása a `kezi-02`-vel elrontott sorozatból maradt így: a 2. érvényes
futtatás ága a `kezi-03`. Az ág neve azonosító, nem sorszám; a CSV `futtatas`
oszlopa a mérvadó. Ezt a 6.1-ben egy mondattal ki kell mondani.

## Az előkészítés (nem mért, a rögzítés előtt)

A mérőgép oldalán semmit nem kell előkészíteni: az E1–E6 egyszeri lépések
megvannak, a fürtön az előző futtatás verziója fut. A laptopon:

1. Az ág és a jelölősor-commit létrehozása (a 2. futtatásnál ez **kész**):

   ```bash
   git checkout -b meres/kezi-NN
   sed -i '' 's/^# meres-jelolo: .*/# meres-jelolo: 0NN/' app/app.py
   git commit -am "meres: kezi-NN"
   ```

   A `sed -i ''` a macOS változata; Linuxon `sed -i`.
2. Az SSH-alagút (3000, 5001) nyitva van-e (E8) — enélkül az 1. lépés elbukik.
3. A `main` ágra a futtatás alatt nem megy push (E9).

## A mért futtatás indítása

```bash
export TZ=UTC                      # a CSV időbélyegei UTC-ben vannak
PROMPT='[%D{%H:%M:%S}] '$PROMPT    # laptop (zsh)
script -q ~/meres/kezi-NN.txt      # innentől minden rögzül
```

A mérőgépen, az SSH-belépés (2. lépés) **után**, még a 3. lépés előtt:
`PS1='[\D{%H:%M:%S}] '$PS1`. Ez a prompt beállítása, nem a listán szereplő
lépés; a 3. lépés ideje az utána megjelenő promptól számít.

Ezután a protokoll 5. pontjának 1–13. lépése, egyesével, előregépelés nélkül,
`clear` nélkül. A végén `exit` (a `script` lezárása), majd a jegyzőkönyv
másolása ide: `szakdolgozat/bizonyitek/meres/kezi-NN.txt`.

## A futtatás után rögzítendő

A CSV új sora: sorszám, ág, a 4. lépésben kiírt SHA, a 1. lépés **előtti** és a
13. lépés **utáni** prompt időbélyege, a kettő különbsége másodpercben, 13
beavatkozás (vagy a tényleges szám, ha eltérés volt), az elfogadás eredménye,
és minden eltérés megjegyzésben.

## Ami még nincs a repóban

A `~/meres/kezi-NN.txt` jegyzőkönyvek a laptopon vannak, ide másolandók a
sorozat végén a többivel együtt.
