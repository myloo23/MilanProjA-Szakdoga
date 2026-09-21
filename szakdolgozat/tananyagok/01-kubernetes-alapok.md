# Kubernetes alapok — amit az 1. és 2. napon csináltál

Egyszerű nyelven, a parancsokhoz kötve. Nem a dolgozat szövege, hanem az, hogy
te értsd. Ha bármelyik rész homályos marad, az nem baj — a 3. naptól úgyis
használni fogod, és használat közben rögzül.

---

## 1. A legfontosabb mondat

**Nem parancsolsz, hanem kívánságot írsz le, és a rendszer megvalósítja.**

Gondolj a termosztátra. Nem azt mondod neki, hogy „kapcsold be a fűtést 12
percre". Azt mondod, hogy **legyen 22 fok**. A termosztát ezután magától
méricskél, és ha hidegebb van, fűt. Ha kinyitod az ablakot, megint fűt. Nem
kérdez, nem áll le, csak tartja, amit kértél.

A Kubernetes ugyanez, csak konténerekre. Te azt mondod: „ebből a képből mindig
fusson 2 példány". Onnantól folyamatosan fut egy program, ami nézi, hogy hány
példány van, és ha kevesebb, csinál újat.

Ezt láttad, amikor kitöröltél egy podot és magától visszajött. **Nem
újraindult** — a rendszer észrevette, hogy 2-t kértél és csak 1 van, és csinált
egy másikat.

Az Ansible, amit eddig használtál, a másik világ: ott lépésenként megmondod,
mit csináljon, a playbook lefut, véget ér, és utána már senki nem figyel semmit.
Ha éjjel meghal a konténer, reggelig halott marad.

---

## 2. Mi az a fürt

A fürt (cluster) két félből áll.

Az **agy**: ide küldöd a kívánságaidat, itt tárolódnak, és itt futnak azok az
apró programok, amik megvalósítják őket. A `kubectl` mindig ezzel beszél.

A **kezek**: egy vagy több gép, amiken a konténerek ténylegesen futnak.
Mindegyiken ül egy ügynök, ami elindítja és figyeli a rá bízott konténereket.
Ezeket hívják csomópontnak (node) — ezért látsz kettőt a `kubectl get nodes`
parancsra.

A **k3s** ennek az egésznek egy kicsi, egyszerűsített változata, ami elfut egy
gépen is. A **k3d** pedig annyit csinál, hogy a k3s-t Docker-konténerekbe
csomagolja, hogy a laptopodon harminc másodperc alatt legyen fürtöd. A
csomópontjaid tehát valójában Docker-konténerek, amik úgy tesznek, mintha gépek
lennének.

---

## 3. A három dolog, amivel dolgoztál

### Pod — a futó alkalmazás

A pod a legkisebb egység, amit a Kubernetes futtat. Nagyjából egy konténer, egy
vékony burokban.

A lényeg, amit el kell fogadni: **a pod eldobható**. Nincs állandó neve, nincs
állandó IP-címe, bármikor meghalhat, és ha meghal, nem ő éled újra, hanem
**helyette jön egy másik, más névvel**. Ez nem hiba, hanem szándék. Ne építs
soha semmit egy konkrét pod nevére.

### Deployment — a kívánság

Ez az, amit valójában leírtál a YAML-ben: melyik képből, hány darab fusson, és
mi történjen verzióváltáskor. Te ezt írod, a podokat már nem te csinálod.

Emlékszel erre a névre: `backend-547dbb8965-bl2dj`? Három részből áll, és pont
a láncot mutatja:

- `backend` — a Deployment neve, ezt te adtad
- `547dbb8965` — a *verzió* azonosítója (a hivatalos neve ReplicaSet)
- `bl2dj` — maga a pod, véletlen végződéssel

Ez a középső rész később fontos lesz: **minden verzióhoz tartozik egy ilyen
csoport, és a régi nem tűnik el azonnal**. Verzióváltásnál az új csoport nő
2-re, a régi csökken 0-ra. Visszaállításkor pedig fordítva. Ezért lesz majd a
visszaállítás pár másodperc, nem pedig újratelepítés.

### Service — az állandó cím

Mivel a podok jönnek-mennek és változik az IP-jük, kell egy fix cím, ami mindig
megtalálja az éppen élő példányokat. Ez a Service. Kap egy nevet, és a fürtön
belül ezen a néven eléred, ő pedig szétosztja a kéréseket a podok között.

A 4. napon a backended a `postgres` néven fogja elérni az adatbázist. Nem
IP-cím, nem hosztnév — egyszerűen a Service neve.

---

## 4. Címkék: a ragasztó, ami elsőre nem látszik

Honnan tudja a Service, hogy melyik podokhoz tartozik? **Nem név szerint.**

A podok kapnak egy címkét (a YAML-edben ez az `app: backend`), a Service pedig
azt mondja: „engem azok a podok érdekelnek, amiken `app: backend` címke van".
Ennyi az egész kapcsolat köztük. Ugyanígy találja meg a Deployment is a saját
podjait.

Ez elsőre felesleges bürokráciának tűnik, de rugalmas: egy Service egyszerre
mutathat két verzióra, és egy pod több Service-hez is tartozhat.

**A leggyakoribb kezdő hiba is itt van:** ha elgépeled a címkét, minden
„működik", csak a Service mögött nincs egyetlen pod sem, és a kérésed a
semmibe megy.

---

## 5. A két ellenőrzés a YAML-edben

Két hasonló blokk van a manifestedben, és nagyon nem ugyanaz.

A **livenessProbe** azt kérdezi: *élsz még?* Ha a `/health` nem válaszol, a
rendszer megöli és újraindítja a konténert. Ezt eddig a Dockerfile-od
`HEALTHCHECK` sora csinálta.

A **readinessProbe** azt kérdezi: *fogadhatsz már forgalmat?* Amíg a `/ready`
nem válaszol rendesen, a pod **fut, de nem kap kérést** — kimarad a Service
mögül.

Ez a második az, ami eddig nem létezett nálad, és ez a fontosabb. **Ettől lehet
verziót váltani kiesés nélkül:** az új pod csak akkor kap forgalmat, amikor
már készen áll, és a régit csak utána lövik ki. A mostani Ansible-es
megoldásodnál mért kiesés (kb. 37 másodperc) nagyrészt azért van, mert ott
nincs semmi, ami ezt megcsinálná. A dolgozatban ez a két szám egymás mellé fog
kerülni.

---

## 6. Miért jött az ImagePullBackOff

Mert a képet nem a te Dockered adja oda, hanem a **csomópont** keresi meg. A
csomópontjaid külön konténerek, saját képtárral, és fogalmuk sincs arról, mi
van a Mac-ed Dockerében.

A `k3d image import` szó szerint átmásolja a képet a csomópontokba. Az
`imagePullPolicy: IfNotPresent` pedig azt jelenti: ha már megvan helyben, ne
próbálja letölteni az internetről.

Élesben ez úgy oldódik meg, hogy van egy registry, amit a csomópont el tud érni
— nálad a 2. héten ez a virtuális gépen futó saját registry lesz, és a pipeline
fogja feltölteni. Ugyanaz a probléma, csak ott nem kézzel oldod meg.

---

## 7. Két apróság, amit használtál

**`kubectl apply -f fájl.yaml`** — beküldi a kívánságodat, és eltárolja. A
fájl verziókövethető, megismételhető. Az 1. napon használt `kubectl run` ezzel
szemben azonnal csinál egy podot, fájl nélkül — kísérletezésre jó, éles
használatra nem.

**`kubectl port-forward`** — alagút a laptopodról a fürt belsejébe. A Service
címe csak a fürtön belül létezik, kívülről nincs hozzá út. Az 5. napon az
Ingress oldja meg ugyanezt rendesen, böngészőbarát módon.

---

## 8. Három parancs, amit reflexből használj

Ez a hibakeresés 90%-a:

```bash
kubectl get pods            # mi van most
kubectl describe pod <név>  # MIÉRT olyan — az "Events" rész az alján a lényeg
kubectl logs <név>          # mit mondott maga az alkalmazás
```

A `describe` kimenetének az alja majdnem mindig szó szerint kimondja a hibát.
Mielőtt keresel vagy kérdezel, ezt nézd meg.

---

## Szótár

| Szó | Egy mondatban |
|---|---|
| fürt (cluster) | az egész rendszer: az agy és a gépek, amiken a konténerek futnak |
| csomópont (node) | egy gép a fürtben, ami konténereket futtat |
| pod | egy futó konténer a fürtben; eldobható, bármikor cserélhető |
| Deployment | a kívánság: miből, hányat, hogyan |
| ReplicaSet | egy adott verzióhoz tartozó podcsoport; a régi megmarad, ezért gyors a visszaállás |
| Service | állandó belső név és cím, ami mindig az élő podokra mutat |
| címke (label) | apró felirat a podon; ez alapján találják meg egymást a dolgok |
| livenessProbe | élsz még? ha nem, újraindítás |
| readinessProbe | fogadhatsz forgalmat? ha nem, kimaradsz a Service mögül |
| manifest | a YAML-fájl, amiben a kívánság le van írva |
| `apply` | a kívánság beküldése; ez a normál működés |
