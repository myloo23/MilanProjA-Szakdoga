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
