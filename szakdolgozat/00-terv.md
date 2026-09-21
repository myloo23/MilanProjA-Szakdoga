# Szakdolgozat — cím, szerkezet és munkaterv

Konzulens: Kurucz Bence (NJE GAMF)
Nyelv: magyar
Utoljára frissítve: 2026-09-15 (a konzulens visszajelzése után)

---

## 1. A konzulens válasza — mi változik

A konzulens jóváhagyta a címet és a mérési megközelítést. Két kérése volt:

1. Az alkalmazás legyen kellően összetett: **legyen benne minden az említettek közül** — Kubernetes, Terraform, supply-chain biztonság, valamint saját frontend és backend.
2. A 3. és 4. fejezet olvadjon össze, az új címe: **A rendszer megismerése és tervezése**.
3. Kell egy 5–10 mondatos összefoglaló is.

---

## 2. A dolgozat címe

**Automatizált telepítési lánc kiépítése és hatásának mérése saját üzemeltetésű CI/CD környezetben**

A cím a bővített tartalommal is állja a helyét, mert nem nevez meg eszközt, és nem jelenti ki előre az eredményt.

---

## 3. Összefoglaló (7 mondat)

> A szakdolgozat alapja a gyakornokságom alatt épített CI/CD rendszer, ezt fejlesztem tovább egy teljes, automatizált telepítési folyamattá. Készítek hozzá egy saját webalkalmazást, külön frontenddel és backenddel, Docker konténerben. A szervereket, amiken az alkalmazás fut, Terraformmal hozom létre, maga az alkalmazás pedig Kubernetesben fut. A telepítést egy Gitea Actions pipeline végzi: leteszteli a kódot, konténerképet épít belőle, feltölti a registrybe, telepíti, majd leellenőrzi, hogy tényleg működik-e. A pipeline megvizsgálja a felhasznált külső komponenseket is, SBOM-mal és sérülékenységvizsgálattal, a futó rendszert pedig Prometheus, Grafana és Loki figyeli. A dolgozat fő kérdése, hogy mennyit javít mindez a telepítésen: ugyanazt a változtatást kézzel és a pipeline-nal is telepítem, többször egymás után, és mérem az időt, a kézi lépések számát, és azt is, hogy egy elrontott telepítés után mennyi idő visszaállni. Mindkét esetben ugyanoda telepítek, hogy a különbség csak az automatizálásból jöjjön, a végén pedig összehasonlítom a két sorozatot.

---

## 4. Fejezetszerkezet (frissítve)

**1. Bevezetés**
- 1.1 A probléma: a kézi telepítés költsége és kockázata
- 1.2 Célkitűzés és kutatási kérdés
- 1.3 A dolgozat felépítése

**2. Elméleti háttér**
- 2.1 A DevOps mint módszertan
- 2.2 Folyamatos integráció és folyamatos szállítás
- 2.3 Konténerizáció és a változtathatatlan artifact elve
- 2.4 Infrastruktúra mint kód
- 2.5 Konténer-orkesztráció
- 2.6 Az ellátási lánc biztonsága
- 2.7 Megfigyelhetőség: metrika, napló, nyomkövetés
- 2.8 A szoftverszállítás teljesítményének mérése (DORA-metrikák)

**3. A rendszer megismerése és tervezése**
- 3.1 A referenciaalkalmazás és feladata
- 3.2 A kiindulási, kézi telepítési folyamat
- 3.3 A kiindulási állapot mérése
- 3.4 Követelmények megfogalmazása
- 3.5 A rendszer architektúrája
- 3.6 Eszközválasztás és annak indoklása
- 3.7 Elágazási és kiadási stratégia
- 3.8 A tervezési döntések dokumentálása (ADR)

**4. Az alkalmazás és az infrastruktúra megvalósítása**
- 4.1 A backend szolgáltatás
- 4.2 A frontend alkalmazás
- 4.3 Adatkezelés és állapotkezelés
- 4.4 Konténerizáció
- 4.5 Az infrastruktúra leírása kóddal (Terraform)
- 4.6 A Kubernetes-környezet és a Helm chart

**5. A CI/CD folyamat megvalósítása**
- 5.1 A build szakasz
- 5.2 Artifact-kezelés és registry
- 5.3 Automatizált telepítés és telepítés utáni ellenőrzés
- 5.4 Visszaállítás hibás telepítés esetén
- 5.5 Az ellátási lánc biztonsága (függőségrögzítés, SBOM, sérülékenységvizsgálat)
- 5.6 A megfigyelhetőségi réteg kialakítása

**6. Mérés és értékelés**
- 6.1 A mérés módszertana és protokollja
- 6.2 A kézi folyamat mérési eredményei
- 6.3 Az automatizált folyamat mérési eredményei
- 6.4 Összehasonlítás és értékelés
- 6.5 Az eredmények érvényessége és korlátai

**7. Továbbfejlesztési lehetőségek**

**8. Összefoglalás**

Irodalomjegyzék · Ábrajegyzék · Táblázatjegyzék · Mellékletek

A dolgozat súlya a 3–6. fejezeten van. A 2. fejezet ne nőjön általános DevOps-tankönyvvé; a 2.5 és 2.6 alfejezet is rövid, a saját megoldás megértéséhez szükséges mélységű legyen.

---

## 5. A legfontosabb döntés, mielőtt bármit mérnél

**Mi legyen a telepítés célkörnyezete a mérés mindkét oldalán?**

Ha a kézi kiindulási állapotot a mostani Docker Compose-os környezeten méred, a végállapotot viszont már Kubernetesen, akkor a két mérés nemcsak a kézi és automatizált különbségét mutatja, hanem a két platform különbségét is. Ezt a védésen szét fogják szedni.

A tiszta megoldás: **a célkörnyezet mindkét oldalon ugyanaz a Kubernetes-fürt**, és az egyetlen különbség az, hogy a telepítés kézzel (kubectl és helm parancsok egyesével, kézi ellenőrzéssel) vagy a pipeline-on keresztül történik. Így a mérés pontosan az automatizálás hatását méri, semmi mást.

Ebből az következik, hogy **a kiindulási mérés nem most jön, hanem azután, hogy a Kubernetes-környezet és az alkalmazás kész**. A sorrend tehát: alkalmazás és infrastruktúra megépítése, majd kézi mérés, majd a pipeline rákötése, majd automatizált mérés.

---

## 6. Teendők lépésről lépésre

### Most (ez a hét)

1. Küldd el a konzulensnek az összefoglalót és a frissített fejezetszerkezetet.
2. Hozd létre a `Szakdolgozat` Claude projectet, csatold a `~/Documents/Szakdolgozat` mappát, másold be a leírást.
3. Ellenőrizd, hogy a meglévő rendszer felállítható-e a saját gépeden: `platform/` mappa, `.env` kitöltése, `docker compose up -d`, egy teljes deploy. Ez a jelenlegi állapot alapja, és ebből fog kinőni az új.
4. Dönts a Kubernetes-fürt formájáról. Reális lehetőségek: k3s egy vagy két virtuális gépen a saját gépeden, vagy k3s egy olcsó felhős szerveren. A választás a Terraformot is meghatározza — a Terraformnak valódi erőforrást kell létrehoznia, nem elég a Docker provider.
5. Dönts az alkalmazásról. A backend alapja megvan (Flask, `/version`, `/echo`, metrikák, strukturált naplózás). Ehhez kell egy frontend, és olyan funkció, ami indokolja az adatkezelést. Ne legyen nagy: egy jól körülhatárolt, valódi funkciót ellátó alkalmazás elég, a dolgozat tárgya nem az alkalmazás.

### Ezután, sorrendben

6. Backend kibővítése és adatkezelés.
7. Frontend megírása, konténerizálás.
8. Terraform: az infrastruktúra létrehozása kóddal.
9. Kubernetes és Helm chart: az alkalmazás fusson a fürtön.
10. **Kézi telepítési folyamat rögzítése és megmérése** a kész Kubernetes-környezeten.
11. A pipeline rákötése: build, registry, telepítés, ellenőrzés, visszaállítás.
12. Supply-chain lépések: függőségrögzítés, SBOM, sérülékenységvizsgálat, képaláírás.
13. Megfigyelhetőségi réteg átvezetése a Kubernetes-környezetre.
14. **Automatizált mérés**, kiértékelés, ábrák.
15. A 3–6. fejezet megírása. A 2. fejezet és a bevezetés a végén.

---

## 7. A mérési protokoll váza

**A mért folyamat kezdő- és végpontja.** Kezdet: a forráskódban véglegesített változtatás. Vég: az új verzió fut a fürtön, és az elfogadási ellenőrzés sikeres. Mindkét folyamatnál azonos.

**Az elfogadási kritérium.** Egyetlen, automatikusan ellenőrizhető feltétel: a `/version` végpont az új verziószámot adja vissza, és a füstteszt sikeres.

**A változtatás.** Minden futtatásnál azonos típusú, triviális kódváltoztatás, hogy a fejlesztési idő ne keveredjen a telepítési időbe.

**Futtatásszám.** Kézi: 8–10 futtatás, a futtatás sorszámának rögzítésével, hogy a tanulási hatás kimutatható legyen. Automatizált: 20 vagy több, mert olcsó.

| Jellemző | Hogyan mérve |
|---|---|
| Változtatástól a működő telepítésig eltelt idő | stopperrel, illetve a pipeline futásidejéből |
| Emberi beavatkozások száma | a rögzített lépéslista alapján számolva |
| A telepítés végrehajtási ideje | mérve |
| Helyreállítási idő hibás telepítés után | szándékos hibainjektálás, majd mérés |
| Reprodukálhatóság | a futtatások szórása alapján értékelve |

**Amit ne mérj.** A telepítési gyakoriságot egyszemélyes projektben értelmetlen összevetni. A hibás telepítések arányát 8–10 elemű mintán ne add meg százalékként — helyette a hibainjektálásos helyreállítási időt használd.

**Statisztika.** Medián és terjedelem, nem csak átlag.

---

## 8. A mérés érvényességét fenyegető tényezők (6.5 fejezet)

**Utólagos újrajátszás.** A kézi folyamatot a rendszer ismeretében játszod újra, ez nem történeti megfigyelés. Nevezd így: kontrollált körülmények között újrajátszott kiindulási folyamat.

**Ez a javadra szól.** Mivel a rendszert ismerve végzed a kézi telepítést, a kézi értékek a valóságosnál kedvezőbbek, tehát a kimutatott javulás alsó becslés. Írd le explicit módon, konzervatív becslésként.

**Egyetlen operátor.** Ellensúlyozás: rögzített lépéslista, azonos elfogadási kritérium, a futtatási sorrend közlése.

**Egyetlen alkalmazás, egyetlen célkörnyezet.** Az eredmény erre a rendszerre érvényes, általánosítani nem lehet. Mondd ki.

---

## 9. Kockázatok

**A terjedelem.** Frontend, backend, Terraform, Kubernetes, supply-chain és a mérés együtt sok. A mérés a dolgozat gerince — ha valami csúszik, a 7. fejezetbe kerül, nem a mérés rovására megy.

**A Terraform célpontja.** Ha nincs valódi erőforrás, amit létrehoz, a fejezet súlytalan lesz. Ezt korán tisztázd.

**Az alkalmazás elszabadulása.** A frontend és a backend eszköz, nem cél. Ne menjen el rá hetek munkája.
