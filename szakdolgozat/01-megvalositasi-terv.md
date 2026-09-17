# Megvalósítási terv — Kubernetes, Terraform, frontend, mérés

Készült: 2026-09-17 · Kiegészíti a [`00-terv.md`](00-terv.md) 6. pontját
Keret: **1 hónap** (2026-09-18 — 2026-10-17) · **0 Ft költségvetés**

---

## 0. Az őszinte keret — ezt olvasd el először

Egy hónap alatt, nulla Kubernetes- és Terraform-tapasztalattal, a teljes vállalt
tartalmat (frontend, backend, adatkezelés, Terraform, Kubernetes, Helm,
ellátási lánc, megfigyelhetőség, kétoldalas mérés, és mindezek megírása) **nem
fogod megcsinálni**. Nem azért, mert lassú vagy, hanem mert ebből a
tanulási görbe legalább két hét, és a dolgozat megírása önmagában egy hét.

Ezért a terv nem "minden belefér" logikával készült, hanem prioritási sorrenddel:

1. **A mérés megtörténik.** Ez a dolgozat gerince, enélkül nincs dolgozat.
2. **Kubernetes + Helm.** A mérés célkörnyezete, enélkül nincs mit mérni.
3. **Terraform.** A célkörnyezet létrehozása kóddal — a konzulens kérte.
4. **Frontend + adatkezelés.** A konzulens kérte, de kicsiben teljesíthető.
5. **Ellátási lánc.** Nagyrészt **már kész** (SBOM, Trivy, hash-lockolt
   függőségek), csak át kell vezetni az új környezetre.
6. **Megfigyelhetőség.** Szintén kész, át kell vezetni.

Ami **tudatosan kimarad** és a 7. fejezetbe (Továbbfejlesztési lehetőségek)
kerül: konténerkép-aláírás (cosign), GitOps (ArgoCD/Flux), többcsomópontos
fürt, automatikus skálázás, zero-downtime rolling update finomhangolása,
Terraform modulok és távoli state-tárolás. Ezeket **leírni** kell, nem
megcsinálni. Egy jól megírt 7. fejezet, ami pontosan megmondja, mi hiányzik és
miért, többet ér, mint egy félkész ArgoCD.

**Ha csúszol:** nem a mérésből veszel el, hanem a 4. pontból (frontend). A
mérés az utolsó előtti hétre legyen kész.

---

## 1. Mi micsoda — egy-egy bekezdésben

Nem kell mélyen érteni ahhoz, hogy elkezdd. Ennyi elég az induláshoz, a többi
menet közben rakódik rád.

**Kubernetes (k8s).** Egy rendszer, ami konténereket futtat helyetted, és
folyamatosan gondoskodik róla, hogy az legyen igaz a valóságban, amit te
leírtál. Nem azt mondod meg neki, hogy "indíts el egy konténert", hanem azt,
hogy "ebből a képből mindig fusson kettő példány". Ha egy meghal, újraindítja.
Ha új verziót adsz meg, lecseréli őket egyesével. Ma Ansible-lel te mondod meg,
mit csináljon (imperatív); Kubernetesszel a kívánt végállapotot írod le
(deklaratív), és ő dolgozik rajta. **Ez a különbség önmagában egy fél
alfejezet a 2.5-ben.**

**k3s.** A Kubernetes egy lecsupaszított, egyetlen bináris állományból álló
változata (a Rancher/SUSE készíti). Ugyanaz az API, ugyanazok a parancsok, csak
kicsi és egy gépen is elfut. A "rendes" Kubernetes egy laptopon vagy egy kis
VM-en fájdalmas; a k3s nem.

**k3d.** A k3s Docker-konténerben. Egy paranccsal kapsz egy eldobható fürtöt a
saját gépeden, tíz másodperc alatt. Ez lesz a **tanuló- és fejlesztőkörnyezet**,
nem a mérés helye.

**kubectl.** A parancssori kliens, amivel a fürttel beszélsz. `kubectl apply -f
valami.yaml`, `kubectl get pods`, `kubectl logs`. A "kézi telepítés" a mérés
egyik oldalán lényegében ez.

**Manifest.** YAML-fájl, ami egy Kubernetes-objektumot ír le (Deployment,
Service, Ingress, Secret, PersistentVolumeClaim). Ezek a "kívánt állapot"
darabkái.

**Helm.** Csomagkezelő Kuberneteshez. A manifesteket sablonná alakítja, és
értékeket (image-verzió, replikaszám, jelszó) kívülről adsz hozzá. Egy
alkalmazás = egy *chart*. Telepítés: `helm upgrade --install app ./chart --set
image.tag=abc123`. **A pipeline-od végén ez az egy parancs fogja lecserélni ezt
a mostani Ansible-lépést.**

**Terraform.** Infrastruktúra kódból. Leírod egy fájlban, hogy kell egy
virtuális gép, egy hálózat, egy tűzfalszabály és egy publikus IP-cím; a
`terraform apply` létrehozza őket a felhőszolgáltatónál. Eltárolja, mit hozott
létre (ez a *state*), így legközelebb csak a különbséget hajtja végre, a
`terraform destroy` pedig mindent letöröl. **A Terraform a gépeket csinálja meg,
a Kubernetes az azokon futó alkalmazást — ezt a határt a dolgozatban is ki kell
mondani.**

**Provider.** A Terraform bővítménye egy adott szolgáltatóhoz (`azurerm` az
Azure-hoz). Ez fordítja le a leírásodat API-hívásokra.

**PersistentVolumeClaim (PVC).** A konténer állapota alapból elveszik, ha a
konténer meghal. A PVC egy tárterületigénylés: "kérek 2 GB-ot, ami túléli a
konténert". Az adatbázisnak ez kell.

---

## 2. A döntések, amiket meghoztam helyetted

Mindegyik mellett ott az indoklás, mert ezeket a védésen meg kell tudnod
védeni, és a 3.6 alfejezetbe (Eszközválasztás és annak indoklása) is ez megy.

**D1 — A fürt k3s lesz, egyetlen csomóponton.**
Indok: a dolgozat tárgya nem a Kubernetes üzemeltetése, hanem a telepítési lánc
automatizálása. Egy csomópont elég ahhoz, hogy a telepítés, a verifikáció és a
visszaállítás mérhető legyen. A többcsomópontos fürt a 7. fejezetbe kerül.

**D2 — A fürt egy Azure-beli virtuális gépen fut, amit a Terraform hoz létre.**
Indok: a Terraform-fejezet csak akkor ér valamit, ha valódi erőforrást hoz
létre. A pénzügyi feltétel: az **Azure for Students** csomag 100 USD kreditet ad
bankkártya nélkül, iskolai e-mail-címmel igazolva, 12 hónapra. Egy hónapnyi kis
virtuális gép ennek a töredéke, tehát **0 Ft-ba kerül**.
*Mielőtt a 2. hétbe belekezdenél: nyisd meg a fiókot a `@gamf.nje.hu` /
egyetemi címeddel, és ellenőrizd, hogy átmegy a hallgatói igazolás.* Ha nem megy
át, a B terv a 6. pontban van.

**D3 — Fejlesztés közben k3d a saját gépeden, a mérés az Azure-os fürtön.**
Indok: a felhős géppel lassú a kísérletezés, és a kredit is fogy. A Helm chartot
és az alkalmazást helyben fejleszted ki, és ugyanaz a chart megy fel a mért
környezetre. **A mérés mindkét oldala — kézi és automatizált — ugyanazon az
Azure-os fürtön történik**, ez a 00-terv 5. pontjának a feltétele.

**D4 — A Terraform hatóköre: az infrastruktúra, és semmi más.**
Létrehozza: erőforráscsoport, virtuális hálózat, alhálózat, hálózati
biztonsági csoport (tűzfal), publikus IP, hálózati interfész, SSH-kulcs,
virtuális gép, és egy cloud-init szkript, ami feltelepíti a k3s-t. Ez nyolc-kilenc
valódi erőforrás, bőven elég egy alfejezethez.
**Nem** kezeli az alkalmazást és nem kezeli a Kubernetes-objektumokat. Indok: ha
a Terraform is telepítené az appot, összemosódna a telepítési lánccal, amit
mérni akarsz.

**D5 — A Gitea, a runner és a registry ugyanarra a virtuális gépre kerül.**
Indok: a fürtnek el kell érnie a registryt, hogy le tudja húzni a konténerképet.
A mostani registry a laptopodon fut `localhost:5001`-en, ahhoz egy felhős fürt
nem fér hozzá. Egy gép a legegyszerűbb megoldás, és a cím ("saját üzemeltetésű
CI/CD környezet") pont ezt állítja.
**Ennek van egy ára, amit a 6.5-ben ki kell mondani:** a CI és a célkörnyezet
ugyanazon a gépen osztozik az erőforrásokon, tehát a pipeline futása terheli a
fürtöt. A mérésre ez a *kézi* oldalnak kedvez, tehát a kimutatott javulás így is
alsó becslés marad.

**D6 — A frontend: Vite + React + TypeScript, nginx-konténerben.**
Indok: ez a te otthonod, egy nap alatt kész. **Nem Next.js**: az SSR futó
Node-folyamatot, saját konténert, saját health-endpointot és
környezetváltozó-kezelést jelentene — merő bonyolítás egy olyan dologért, ami a
dolgozatban eszköz, nem cél. A Vite build statikus fájlokat ad, azt egy nginx
kiszolgálja, a konténer triviális és gyorsan indul (ez a mérésnek is jót tesz).

**D7 — Adatkezelés: PostgreSQL, egy replikával, PVC-n, kézzel írt manifestben.**
Indok: kell valami, ami indokolja az állapotkezelést (4.3 alfejezet), és a PVC,
a Secret és az adatbázis-migráció mind valódi Kubernetes-téma. **Nem** külső
Helm-függőség (Bitnami stb.), hanem húsz sor saját manifest a chartodban — így
érted is, amit leírsz, és nem kell idegen chart verzióváltásaival küzdened.

**D8 — Az alkalmazás funkciója: egyetlen entitás teljes CRUD-ja.**
Például jegyzetek vagy feladatok: létrehozás, listázás, módosítás, törlés.
A meglévő Flask backend marad (`/health`, `/ready`, `/metrics`, `/echo`),
kiegészül az adatbázissal és négy végponttal, plusz egy `/version` végponttal.
**A `/version` kritikus**, mert a mérés elfogadási kritériuma erre épül.
Ne legyen belőle több. A dolgozat tárgya nem az alkalmazás.

**D9 — Ami pénzbe kerülne, azt megbeszéljük a konzulenssel.**
Ez a terv 0 Ft-ból kijön. Ha az Azure-os hallgatói fiók valamiért nem jön össze,
az a konzulensnek szóló kérdés lesz (6. pont, B terv), nem a te pénztárcádé.

---

## 3. Ütemterv

Minden lépésnél ott van, hogy **mikor kész**. Ha egy lépés kész-feltétele nem
teljesül, ne lépj tovább — a Kubernetesben a félig működő dolgok később
kamatostul jönnek vissza.

### 1. hét (szept 18 — szept 24) — Kubernetes a saját gépeden

**1.1 · Fél nap — Eszközök felrakása.**
`brew install k3d kubectl helm`. Fürt: `k3d cluster create szakdoga`.
*Kész, ha:* a `kubectl get nodes` egy `Ready` állapotú csomópontot mutat.

**1.2 · Egy nap — A meglévő Flask app kézzel, YAML-ből.**
Írj hozzá kézzel egy `Deployment`-et és egy `Service`-t. Semmi Helm, semmi
sablon. Nézd meg `kubectl get pods`, `kubectl describe pod`, `kubectl logs`
parancsokkal, mi történik. Öld meg a podot, és nézd meg, hogy visszajön.
*Kész, ha:* `kubectl port-forward` után a böngészőből jön a `/health` válasz, és
el tudod mondani, mi a Pod, a Deployment és a Service.
*Ez a nap a tanulás napja. Ne siess át rajta, mert erre épül minden.*

**1.3 · Fél nap — `/version` végpont és build-metaadat.**
A `--build-arg`-os verziószám és a `/version` végpont már a PLAN.md-ben is nyitott
tétel (7. pont, 5. alpont). Most kell megcsinálni, mert **a mérés elfogadási
kritériuma az, hogy a `/version` az új SHA-t adja vissza**.
*Kész, ha:* a konténer a beépített git SHA-t adja vissza a `/version`-ön.

**1.4 · Egy nap — Backend: adatbázis és CRUD.**
PostgreSQL a fürtben (Deployment + PVC + Secret), a Flask csatlakozik hozzá,
négy CRUD-végpont, pytest-tesztek hozzá (a 80%-os lefedettségi kapu él).
*Kész, ha:* a fürtben futó app kiszolgálja a CRUD-ot, és a pod újraindítása után
is megvannak az adatok.

**1.5 · Egy nap — Frontend.**
Vite + React + TS, egy oldal, ami a CRUD-ot használja. Többlépcsős Dockerfile:
build → nginx. Ugyanolyan szigorral, mint a backendé (nem root felhasználó,
rögzített alapkép).
*Kész, ha:* a fürtben fut, és a böngészőből használható a teljes alkalmazás.

**1.6 · Egy nap — Helm chart.**
A három komponens (frontend, backend, adatbázis) egyetlen chartba. Értékként
kívülről állítható: image-verzió, replikaszám, adatbázisjelszó.
*Kész, ha:* `helm upgrade --install` telepít, `--set image.tag=...` verziót vált,
és `helm rollback` visszaáll az előző verzióra.

**Írás ezen a héten:** 3.5 (architektúra), 3.6 (eszközválasztás) — a D1–D8
döntések szövegesen. Két ADR: "miért k3s" és "miért Helm az Ansible helyett a
telepítéshez".

### 2. hét (szept 25 — okt 1) — Terraform, valódi infrastruktúra, kézi mérés

**2.1 · Fél nap — Azure for Students fiók.**
Iskolai e-mail-cím, hallgatói igazolás. **Ezt csináld meg az 1. hét elején**, ne
itt, mert az igazolás elhúzódhat. Ha elakad: 6. pont, B terv.
*Kész, ha:* be tudsz lépni az Azure portálra, és látod a 100 USD kreditet.

**2.2 · Egy nap — Terraform alapok és az első `apply`.**
`brew install terraform`, `az login`. Írd le: erőforráscsoport, hálózat,
alhálózat, tűzfalszabályok (SSH és HTTPS csak a te IP-címedről), publikus IP,
hálózati interfész, SSH-kulcs, virtuális gép (Ubuntu LTS, 2 vCPU / 8 GB).
Futtass `terraform plan`-t, olvasd el, mit akar csinálni, aztán `apply`.
*Kész, ha:* SSH-val be tudsz lépni a Terraform által létrehozott gépre.
*Tipp: a `terraform destroy` és egy újabb `apply` a legjobb bizonyíték arra,
hogy tényleg kódból van. Csináld meg egyszer, és készíts róla képet a
dolgozatba.*

**2.3 · Fél nap — k3s telepítése cloud-inittel.**
A gép indulásakor futó szkript telepítse a k3s-t. Így a fürt is a Terraform
eredménye, nem kézi munka.
*Kész, ha:* `terraform destroy` + `apply` után **kézi beavatkozás nélkül** kapsz
egy működő fürtöt, és a laptopodról a `kubectl get nodes` látja.

**2.4 · Fél nap — A platform átköltöztetése.**
A `platform/compose.yaml` (Gitea, act_runner, registry) felmegy ugyanerre a
gépre. A k3s-t be kell állítani, hogy a helyi registryből is húzhasson képet
(`registries.yaml`).
*Kész, ha:* a fürt le tud húzni egy képet a gépen futó registryből.

**2.5 · Fél nap — A kézi telepítési folyamat rögzítése.**
Írd le lépésről lépésre, mit csinálsz kézzel egy új verzió telepítéséhez: kód
átvitele, `docker build`, `docker push`, `helm upgrade --set image.tag=...`,
`kubectl rollout status`, `/version` ellenőrzése, füstteszt. **Számozott lista,
minden lépés egy emberi beavatkozás.** Ez lesz a mérés egyik oldala, és ez a
3.2 alfejezet.
*Kész, ha:* a lista alapján valaki más is végig tudná csinálni.

**2.6 · Egy nap — A kézi mérés lefuttatása.**
8–10 futtatás, a 00-terv 7. pontja szerinti protokollal. Minden futtatásnál
ugyanaz a triviális kódváltoztatás. Stopper, lépésszám, futtatás sorszáma.
Plusz 3 hibainjektálásos helyreállítási mérés.
*Kész, ha:* van egy táblázatod 8–10 sorral, és minden sor mögött ott az időbélyeg.
**Innentől a dolgozat feléig nem lehet baj, mert a mérés egyik fele megvan.**

**Írás ezen a héten:** 3.2 (kiindulási folyamat), 3.3 (kiindulási mérés),
4.5 (Terraform), 4.6 (Kubernetes és Helm).

### 3. hét (okt 2 — okt 8) — Pipeline, visszaállítás, automatizált mérés

**3.1 · Egy nap — A pipeline átállítása Kubernetesre.**
A `ci.yml` deploy-lépésében az Ansible helyére `helm upgrade --install` kerül,
utána `kubectl rollout status` (ez vár, amíg az új verzió tényleg fut), majd a
meglévő füstteszt a `/version` ellenőrzésével.
*Kész, ha:* egy push a `release/*` ágra kézi beavatkozás nélkül új verziót
telepít a fürtre.

**3.2 · Fél nap — Visszaállítás.**
Ha a füstteszt bukik, `helm rollback` fusson automatikusan. A meglévő
`rollback-drill.sh` mintájára legyen megismételhető próba.
*Kész, ha:* szándékosan elrontott képpel a pipeline észreveszi, visszaáll, és a
kimeneten látszik, mennyi idő alatt.

**3.3 · Fél nap — Ellátási lánc átvezetése.**
A Trivy-vizsgálat és az SBOM-generálás már megvan; ki kell terjeszteni a
frontend képére is, és újragenerálni az SBOM-okat (a staleness guard úgyis
fogni fog).
*Kész, ha:* mindkét kép át van vizsgálva, és friss SBOM van a `docs/sbom/`-ban.

**3.4 · Egy nap — Megfigyelhetőség a fürtön.**
A Prometheus/Grafana/Loki átvezetése: a Prometheus Kubernetes-alapú
szolgáltatásfelderítéssel szedje a metrikákat, a naplók a podokból menjenek a
Lokiba. A meglévő dashboardok maradnak.
*Kész, ha:* a meglévő két dashboard adatot mutat a fürtről.

**3.5 · Egy nap — Az automatizált mérés.**
20+ futtatás, ugyanazzal a változtatástípussal és ugyanazzal az elfogadási
kritériummal. A pipeline futásidejéből olvasod ki az időt, a kézi lépések száma
definíció szerint 1 (a push).
*Kész, ha:* megvan mindkét sorozat, és az adatok egy táblázatban vannak.

**Írás ezen a héten:** teljes 5. fejezet, és 6.1 (mérési módszertan).

### 4. hét (okt 9 — okt 15) — Kiértékelés és írás

**4.1 · Egy nap — Kiértékelés és ábrák.**
Medián, terjedelem, a kézi sorozat tanulási görbéje, a két sorozat
összehasonlítása. Három-négy ábra, nem több.

**4.2 · Három nap — A 6. fejezet, aztán a 3. és 4. befejezése.**
A hét eleji állapotban a 3–5. fejezet nagy része már megvan a heti írásblokkokból.

**4.3 · Egy nap — 2. fejezet, bevezetés, 7. és 8. fejezet.**
Az elméleti fejezet a végén készül, hogy pontosan annyi legyen benne, amennyi a
saját megoldás megértéséhez kell. A 7. fejezetbe kerül minden, ami kimaradt (a
0. pont listája).

**4.4 · Egy nap — Átolvasás, irodalomjegyzék, ábrajegyzék, mellékletek.**

**Tartalék: okt 16–17.** Ha nincs rá szükség, annál jobb.

---

## 4. Amit mérés közben rögzíteni kell

Ne utólag akard összerakni. Minden futtatásnál, azonnal, egy táblázatba:

| Mező | Megjegyzés |
|---|---|
| futtatás sorszáma | a tanulási hatás kimutatásához |
| kézi vagy automatizált | |
| kezdés és befejezés időbélyege | másodperc pontossággal |
| emberi beavatkozások száma | a 2.5-ben rögzített lépéslista alapján |
| sikeres-e az elfogadási ellenőrzés | `/version` + füstteszt |
| megjegyzés | bármi, ami befolyásolta (hálózat, hiba, újrapróbálkozás) |

A hibainjektálásos helyreállítási méréshez külön három sor: mikor ment ki a
hibás verzió, mikor vetted észre, mikor állt vissza a szolgáltatás.

---

## 5. Írás párhuzamosan — nem alku tárgya

Minden hét végén **fél nap írás**, arról, amit azon a héten csináltál. Nem
csiszolt szöveg, hanem a döntések és a számok rögzítése, amíg emlékszel rájuk.
A 4. héten már nem lesz időd felidézni, hogy miért pont úgy csináltad a
tűzfalszabályt.

Az ADR-eket is menet közben írd, ahogy eddig is — a `docs/adr/` már hét darabot
tartalmaz, ez a dolgozat 3.8 alfejezetének kész anyaga.

---

## 6. Kockázatok és a vészfékek

**R1 — Az Azure-os hallgatói fiók nem jön össze.**
*B terv, ebben a sorrendben:* (1) kérdezd meg a konzulenst, hogy az egyetemnek
van-e hallgatói virtuális gépe vagy felhős keretei — ez a legjobb kimenetel,
mert hivatalos és ingyenes; (2) ha nincs, a fürt a saját gépeden fut k3s-ben egy
Lima/Multipass virtuális gépen, a Terraform pedig a Kubernetes- és Helm-providert
használja a fürt platformrétegére (névterek, kvóták, titkok, ingress). Ez
gyengébb Terraform-fejezet, és a dolgozatban **ki kell mondani, hogy miért ez
lett** — de nem hiteltelen, ha megindokolod.

**R2 — Beragadsz a Kubernetesbe az első héten.**
Ha a 4. nap végén sem fut a Flask app a k3d-ben, állj meg és kérdezz. A
Kubernetes hibaüzenetei az elején kifejezetten rosszul olvashatók
(`ImagePullBackOff`, `CrashLoopBackOff`), és egy fél nap egyedül szenvedés
helyett tíz perc kérdezés a helyes lépés.

**R3 — Az alkalmazás elszabadul.**
Egy entitás, négy végpont, egy oldal. Ha azon kapod magad, hogy
felhasználókezelést vagy dizájnt csinálsz, állj le. A frontend a dolgozatban
fél oldal lesz.

**R4 — A mérés csúszik a 4. hétre.**
Ez a legveszélyesebb forgatókönyv, mert a mérés a dolgozat gerince. A vészfék:
a 2. hét végére a kézi mérésnek meg kell lennie. Ha a 2. hét végén nincs meg,
akkor a frontendet kell kivágni és a 7. fejezetbe tenni, nem a mérést húzni.

**R5 — Egy hónap kevés.**
Ha a 3. hét végén látod, hogy nem lesz kész, **szólj a konzulensnek időben**, ne
a határidő előtt két nappal. Egy féléves csúszás kellemetlen, egy beadott
félkész dolgozat rosszabb.

---

## 7. Az első három dolog

1. **Ma:** nyisd meg az Azure for Students fiókot az egyetemi e-mail-címeddel.
   Ez a leghosszabb átfutású, kézen kívüli lépés, és minden más ráépül.
2. **Ma:** `brew install k3d kubectl helm`, és `k3d cluster create szakdoga`.
   Legyen egy fürtöd, mielőtt bármit is olvasnál róla.
3. **Holnap:** a meglévő Flask képet futtasd le benne kézzel írt YAML-ből.
   Ez az a nap, amitől a Kubernetes megszűnik varázslat lenni.

És egy negyedik, ami nem technikai: **küldd el ezt a tervet a konzulensnek**, a
0. pont őszinte keretével együtt. Ha egy hónapod van, jobb, ha ő is tudja, mi
marad ki és miért.
