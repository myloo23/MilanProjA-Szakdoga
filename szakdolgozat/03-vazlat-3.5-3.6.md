# 3.5 és 3.6 alfejezet — váz és nyersanyag

Ezt te írod meg, ez csak a szerkezet és a hozzá tartozó bizonyítékanyag.
Minden pont alatt ott van, honnan van az adat, és mire figyelj.

---

## 3.5 A rendszer architektúrája

**Cél:** az olvasó a fejezet végén le tudja rajzolni a rendszert, és tudja,
melyik komponens kinek felel.

### 3.5.1 A kiindulási felállás (Docker Compose, Ansible)

Mi volt: Gitea + act_runner + registry `platform/compose.yaml`-ból, az
alkalmazás egyetlen konténerként egy Docker hoston, a telepítést az
`ansible/deploy_app` szerep végezte.
Forrás: `platform/compose.yaml`, `ansible/`, [ADR-0003].

> **Ábra 1** — a kiindulási architektúra. A meglévő `README.md` Mermaid-ábrája
> a nyersanyag, de a dolgozatba magyar feliratokkal kell.

### 3.5.2 A jelenlegi felállás (Kubernetes, Helm)

Három komponens egy Helm-release-ben: backend (Flask + gunicorn), frontend
(React build nginx-ből), PostgreSQL PVC-n. Ingress → frontend → `/api/` →
backend → Postgres. A séma egy init containerben jön létre.
Forrás: `chart/templates/*.yaml`, `frontend/nginx.conf`.

> **Ábra 2** — a jelenlegi architektúra, ugyanabban a jelölésrendszerben,
> mint az Ábra 1. A kettő csak így hasonlítható össze.

### 3.5.3 Mi változott és miért — a kettő szembeállítva

Táblázat, nem folyószöveg: telepítés egysége, állapotkezelés, visszaállítás,
verziókövetés, egészség-ellenőrzés. Soronként: előtte / utána / miért.

### 3.5.4 A határok kimondása

Mit csinál a Terraform (gép, hálózat, tűzfal, k3s telepítése cloud-inittel) és
mit nem (alkalmazás, Kubernetes-objektumok) — ez a D4 döntés. **Ezt azért kell
kimondani, mert ha a Terraform is telepítené az alkalmazást, összemosódna a
mért telepítési lánccal.** Ez a mondat a mérés érvényességéről szól, nem
eszközválasztásról, tehát ide tartozik és nem a 3.6-ba.

---

## 3.6 Eszközválasztás és annak indoklása

**Cél:** minden választás mellett ott az *elvetett* alternatíva és az indok.
Ami nincs alternatívával szembeállítva, az nem indoklás, hanem leírás.

Szerkezet döntésenként azonos: mit választottam → mi volt a másik két
lehetőség → miért ez → mi az ára. Az „ára" rész nem opcionális; a védésen
pontosan arra fognak kérdezni.

| # | Döntés | Elvetett alternatívák | Forrás |
|---|---|---|---|
| 1 | k3s, egy csomóponton, saját üzemeltetésű VM-en | menedzselt Kubernetes (AKS), kubeadm, maradás Docker Compose-on | ADR-0008 |
| 2 | Azure VM Terraformmal, hallgatói kredittel | helyi VM (Lima/Multipass), egyetemi gép | ADR-0008, D2 |
| 3 | Helm a telepítésre, az Ansible helyett | Ansible `kubernetes.core`, sima `kubectl apply`, Kustomize | ADR-0009 |
| 4 | Fejlesztés k3d-ben, mérés az Azure-os fürtön | minden a felhőben, minden helyben | D3 |
| 5 | Vite + React + nginx a frontendre | Next.js | D6 |
| 6 | Saját PostgreSQL-manifest, nem külső chart | Bitnami chart, felhős adatbázis | D7, ADR-0009 |
| 7 | Egyetlen entitás CRUD-ja | több entitás, felhasználókezelés | D8 |

**Amire figyelj ebben az alfejezetben:**

- A 3. döntésnél hivatkozz vissza az ADR-0003-ra: az Ansible nem rossz
  választás volt, hanem egy másik célkörnyezethez tartozó jó választás. A
  dolgozat így mutatja meg, hogy a döntéseknek kontextusa van, nem divatja.
- Az 5. döntést (nem Next.js) **ne** úgy indokold, hogy „egyszerűbb". Úgy
  indokold, hogy az SSR futó Node-folyamatot, saját health-végpontot és
  konténert jelentene, egy olyan komponensért, ami a dolgozatban eszköz és nem
  tárgy — a statikus build viszont gyorsabban induló konténert ad, ami a
  telepítési idő mérésére is hatással van.
- Ne írj be egyetlen olyan összehasonlítást sem („a Helm gyorsabb, mint az
  Ansible"), amire nincs mérésed. A 6. fejezetig nincs jogod számot mondani.

---

## Mielőtt ezeket megírod — nyitott kérdések, amiket csak te tudsz megválaszolni

1. A kiindulási architektúra ábráján a laptop szerepeljen-e külön
   komponensként? (A mostani felállásban a registry ott futott.)
2. A 3.5.3 táblázatba beveszed-e a megfigyelhetőséget, vagy az a 4. fejezetbe
   megy? Javaslat: ide csak egy sor, a részletek a 4-be.
3. A `platform/compose.yaml` átköltöztetése az Azure VM-re a 3. vagy a 4.
   fejezetben szerepeljen? Javaslat: 4., mert megvalósítás.
