# A kézi mérési sorozat — állapot

Protokoll: [`../04-kezi-telepitesi-folyamat.md`](../04-kezi-telepitesi-folyamat.md) 5. pont.
Adatsor: [`kezi-sorozat.csv`](kezi-sorozat.csv) · lépésenkénti bontás: [`lepesidok.md`](lepesidok.md).

## Hol tartunk (2026-09-22)

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
| **6.** | `meres/kezi-08` | előkészítve (ág és commit kész), futtatásra vár |
| 7–10. | `meres/kezi-09` … `kezi-12` | hátravan |

A cél **tíz érvényes futtatás** (00-terv 7., 04-kezi 7.d). Az érvénytelen
futtatások miatt az ágnevek elcsúsztak a sorszámoktól; a CSV `futtatas` oszlopa
a mérvadó.

Az ágnév számozása a `kezi-02`-vel elrontott sorozatból maradt így: a 2. érvényes
futtatás ága a `kezi-03`. Az ág neve azonosító, nem sorszám; a CSV `futtatas`
oszlopa a mérvadó. Ezt a 6.1-ben egy mondattal ki kell mondani.

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
