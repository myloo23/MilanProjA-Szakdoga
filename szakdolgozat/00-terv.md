# Szakdolgozat — cím, szerkezet és munkaterv

Konzulens: Kurucz Bence (NJE GAMF)
Nyelv: magyar
Készült: 2026-09-15

---

## 1. A dolgozat címe

**Automatizált telepítési lánc kiépítése és hatásának mérése saját üzemeltetésű CI/CD környezetben**

Tartalék változatok, ha a konzulens másként kéri:

- Automatizált telepítési lánc kiépítése és a telepítési folyamat teljesítményének vizsgálata saját üzemeltetésű CI/CD környezetben
- Kézi és automatizált szoftvertelepítési folyamat összehasonlító vizsgálata saját üzemeltetésű CI/CD környezetben

Amit a cím szándékosan NEM tartalmaz: nem nevez meg eszközt (Gitea, Docker, Ansible), mert ha menet közben változik a stack, a cím akkor is igaz marad; és nem jelenti ki előre az eredményt ("javítás"), csak azt, hogy a hatást mérjük. A DORA sem szerepel benne, mert akkor a teljes, ma már ötelemű metrikakészletet védeni kellene.

---

## 2. Fejezetszerkezet

**1. Bevezetés**
- 1.1 A probléma: a kézi telepítés költsége és kockázata
- 1.2 Célkitűzés és kutatási kérdés
- 1.3 A dolgozat felépítése

**2. Elméleti háttér**
- 2.1 A DevOps mint módszertan
- 2.2 Folyamatos integráció és folyamatos szállítás
- 2.3 Konténerizáció és a változtathatatlan artifact elve
- 2.4 Infrastruktúra mint kód
- 2.5 Megfigyelhetőség: metrika, napló, nyomkövetés
- 2.6 A szoftverszállítás teljesítményének mérése (DORA-metrikák)

**3. A vizsgált rendszer és a kiindulási állapot**
- 3.1 A referenciaalkalmazás
- 3.2 A kiindulási, kézi telepítési folyamat
- 3.3 A kiindulási állapot mérése
- 3.4 Követelmények megfogalmazása

**4. Tervezés**
- 4.1 A rendszer architektúrája
- 4.2 Eszközválasztás és annak indoklása
- 4.3 Elágazási és kiadási stratégia
- 4.4 A tervezési döntések dokumentálása (ADR)

**5. Megvalósítás**
- 5.1 A build szakasz
- 5.2 Artifact-kezelés és registry
- 5.3 Automatizált telepítés Ansible-lel
- 5.4 Telepítés utáni ellenőrzés és visszaállítás
- 5.5 A megfigyelhetőségi réteg kialakítása
- 5.6 Biztonsági kapuk a pipeline-ban

**6. Mérés és értékelés**
- 6.1 A mérés módszertana és protokollja
- 6.2 Az automatizált folyamat mérési eredményei
- 6.3 A kiindulási és a végállapot összevetése
- 6.4 Az eredmények érvényessége és korlátai

**7. Továbbfejlesztési lehetőségek**
- 7.1 Konténer-orkesztráció
- 7.2 Infrastruktúra kiépítése kóddal
- 7.3 Az ellátási lánc biztonsága

**8. Összefoglalás**

Irodalomjegyzék · Ábrajegyzék · Táblázatjegyzék · Mellékletek

A dolgozat súlya a 3–6. fejezeten van, mert ott van a saját munka. A 2. fejezet ne nőjön általános DevOps-tankönyvvé.

---

## 3. Mit küldj el ma a konzulensnek

> Szép napot tanár úr!
>
> Köszönöm, hogy elvállalta. Összeraktam a címet és a fejezeteket.
>
> Cím: Automatizált telepítési lánc kiépítése és hatásának mérése saját üzemeltetésű CI/CD környezetben
>
> A lényeg, hogy lemérem, mennyi időbe és hány kézi lépésbe került a telepítés a pipeline előtt, és mennyibe utána. Ezt a kettőt hasonlítom össze, a hiba utáni helyreállítás idejével együtt.
>
> Fejezetek:
> 1. Bevezetés
> 2. Elméleti háttér
> 3. A vizsgált rendszer és a kiindulási állapot
> 4. Tervezés
> 5. Megvalósítás
> 6. Mérés és értékelés
> 7. Továbbfejlesztési lehetőségek
> 8. Összefoglalás
>
> Jónak tartja így a mérést? És elég ez így egy szakdolgozathoz, vagy bővítenem kellene? Gondoltam Kubernetesre, Terraformra vagy supply-chain biztonságra, illetve arra is, hogy készüljön az alkalmazáshoz egy rendes frontend és backend.
>
> Köszönöm szépen!

---

## 4. A Claude project beállítása

Új project neve: **Szakdolgozat**
Csatolt mappa: `~/Documents/Szakdolgozat`
A leírás szövegét lásd a chatben — másold be a project leírás mezőjébe.

A Work - TCS projectet ne töröld: a gyakorlat alatti munka kontextusa ott van, és a dolgozat nyersanyaga.

---

## 5. Teendők lépésről lépésre

### Ma

1. **Ellenőrizd, hogy a rendszer újraindítható-e a saját gépeden.** Ez a legfontosabb lépés, mert az egész mérési terv erre épül. A `platform/compose.yaml` mind a kilenc szolgáltatást tartalmazza (Gitea, registry, act-runner, Prometheus, cAdvisor, node-exporter, Loki, Alloy, Grafana), az Ansible célpontja `local_docker`, tehát elvileg nem függ céges infrastruktúrától.
   - `cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga/platform`
   - `cp .env.example .env` és töltsd ki
   - `docker compose up -d`
   - Nézd meg, hogy a Gitea, a registry és a Grafana elérhető-e
   - Futtass egy teljes deployt, és jegyezd fel, mi nem működik
   - Ha valami nem áll fel, azt MA derítsd ki, ne a mérés napján
2. Küldd el a konzulensnek a címet és a fejezetszerkezetet.
3. Hozd létre a Claude projectet, csatold a mappát, másold be a leírást.
4. Commitold ezt a fájlt: `git add szakdolgozat && git commit -m "docs: szakdolgozat terve" && git push`

### A héten

5. **Írd meg a 3.2-t: a kézi telepítési folyamat pontos lépéslistája.** Minden lépés külön sor, parancsokkal együtt, úgy, ahogy egy másik ember is végre tudná hajtani. Ez lesz a mérési protokoll alapja is. Amíg ez nincs meg, mérni nincs mit.
6. **Rögzítsd a mérési protokollt** (lásd a 6. pontot lent), és mutasd meg a konzulensnek jóváhagyásra, mielőtt mérsz. Ha utólag kell változtatni rajta, az összes addigi mérés megy a kukába.
7. Gyűjtsd össze a szakirodalmat a 2. fejezethez. Legalább egy könyv (Accelerate / Continuous Delivery), a DORA jelentések, és néhány lektorált cikk.

### Utána

8. Mérés: előbb a kézi sorozat, aztán az automatizált sorozat.
9. Kiértékelés, ábrák, 6. fejezet.
10. A 4. és 5. fejezet megírása — ehhez az anyag nagy része már megvan a repóban (ADR-ek, `docs/PLAN.md`, `docs/RUNBOOK.md`, `docs/sprint3-verification.md`, a sprint2 és sprint3 demó képek).
11. Bevezetés és összefoglalás a végén, amikor már tudod, mi jött ki.

---

## 6. A mérési protokoll váza

Ezt a 6.1 fejezet fogja tartalmazni. Fontos, hogy a mérés előtt legyen kész és jóváhagyott.

**A mért folyamat kezdő- és végpontja.** Kezdet: a forráskódban véglegesített változtatás. Vég: az új verzió fut, és az elfogadási ellenőrzés sikeres. Mindkét folyamatnál pontosan ugyanez.

**Az elfogadási kritérium.** Egyetlen, automatikusan ellenőrizhető feltétel — például a `/version` végpont az új verziószámot adja vissza, és a füstteszt sikeres. Nem szubjektív megítélés.

**A változtatás.** Minden futtatásnál azonos típusú, triviális kódváltoztatás (például a verziószám növelése), hogy a fejlesztési idő ne keveredjen bele a telepítési időbe.

**Futtatásszám.** Kézi folyamat: 8–10 futtatás. Automatizált: 20 vagy több, mert olcsó. A futtatás sorszámát is rögzítsd, hogy a tanulási hatás kimutatható legyen.

**Mért mennyiségek.**

| Jellemző | Hogyan mérve |
|---|---|
| Változtatástól a működő telepítésig eltelt idő | stopperrel, illetve a pipeline futásidejéből |
| Emberi beavatkozások száma | a lépéslista alapján számolva |
| A telepítés végrehajtási ideje | mérve |
| Helyreállítási idő hibás telepítés után | szándékos hibainjektálás, majd mérés |
| Reprodukálhatóság | a futtatások szórása alapján értékelve |

**Amit ne mérj.** A telepítési gyakoriságot (deployment frequency) egyszemélyes, kontrollált projektben értelmetlen összevetni. A hibás telepítések arányát 8–10 elemű mintán ne számszerűsítsd százalékként, mert statisztikailag nem mond semmit — helyette a hibainjektálásos helyreállítási időt használd.

**Statisztika.** Medián és terjedelem (minimum–maximum), nem csak átlag. Tíz elem alatt az átlag érzékeny a kiugró értékekre.

---

## 7. A mérés érvényességét fenyegető tényezők

Ezt a 6.4 fejezetben ki kell mondani, mielőtt a bíráló teszi fel a kérdést.

**Utólagos újrajátszás.** A kézi folyamatot most, a rendszer ismeretében játszod újra. Ez nem történeti megfigyelés. A módszertanban így nevezd: kontrollált körülmények között újrajátszott kiindulási folyamat.

**Ez viszont a javadra szól.** Mivel a rendszert ismerve végzed a kézi telepítést, a kézi értékek a valóságosnál kedvezőbbek. A kimutatott javulás tehát alsó becslés, a tényleges különbség ennél nagyobb. Ezt az érvet írd le explicit módon — konzervatív becslésként sokkal erősebb, mint elhallgatni a torzítást.

**Egyetlen operátor.** Te vagy a mérés alanya és a dolgozat szerzője is. Ellensúlyozás: rögzített lépéslista, azonos elfogadási kritérium, a futtatási sorrend közlése.

**Egyetlen alkalmazás, egyetlen célkörnyezet.** Az eredmény erre a rendszerre érvényes, általánosítani nem lehet. Mondd ki.

---

## 8. Nyitott kérdések a konzulensnek

- Milyen formai sablont és hivatkozási stílust vár el a tanszék?
- Elfogadható-e a fenti mérési protokoll, vagy más metrikákat lát szívesebben?
- Van-e elvárt minimális oldalszám vagy fejezetarány?
- Mikorra kéri az első részanyagot?
