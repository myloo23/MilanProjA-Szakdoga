# Lépésenkénti idők az automatizált sorozatban

A [`lepesidok.md`](lepesidok.md) párja. Ott egy lépés két prompt különbsége;
itt egy szakasz két, a joblogban azonosítható sor időbélyegének különbsége.
Forrás: a `workflowlogok/` alatti joblogok soronkénti időbélyegei, a push a
laptop `auto-NN.txt` jegyzőkönyveiből. Az összesített adat az
[`auto-sorozat.csv`](auto-sorozat.csv), ez a bontás.

## A módszer, és miért így

A Gitea-ból letöltött joblog a fő lépések határait nem jelöli (csak a `Post`
lépésekét), ezért a szakaszhatárokat a lépések saját kimenetének első
jellemző sora adja. Ezek determinisztikusak: minden futtatásban pontosan egyszer
fordulnak elő, ugyanabban a sorrendben.

| Határ | A joblog sora |
|---|---|
| a runner átveszi | `received task N of job …` |
| B1 vége | `MERES pipeline-start` |
| B2 vége (ruff kész) | `All checks passed!` |
| B3 vége (Trivy secret + hadolint kész) | `hadolint v2.14.0: …` |
| B4 vége | `48 passed in …` |
| B5 vége | `Passed: 0 failure(s) …` (ansible-lint) |
| B6 vége | `container healthy` (a build job konténer-füsttesztje) |
| B7 vége | `The push refers to repository [localhost:5001/projecta-flask]` |
| B8 vége | az utolsó `digest: sha256:…` sor |
| D1 vége | `currently deployed: …` |
| D2–D4 | `MERES deploy-start` / `live` / `accepted` (hibásnál `detect`) |
| R1 vége | `Rollback was a success!` |
| R2 vége | `MERES restored` |

**Ellenőrzés: a bontás zárt.** A szakaszok összege futtatásonként 0–1 mp-en
belül egyezik a CSV `teljes_mp` oszlopával (az utóbbi egész másodperces
`MERES`-időbélyegekből számol, ez tizedes logidőkből). A bontás tehát nem hagy
ki és nem számol kétszer semmit.

Az időket tized másodpercre adom, mert a forrás ezt tudja; a kézi oldal
prompt-időbélyegei egész másodpercesek, ezért a két oldal összevetése egész
másodpercre kerekítve értelmes.

## A telepítési sorozat — tíz futtatás

| Szakasz | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | medián | sáv |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F felvétel (push → a runner átveszi) | 8,8 | 6,8 | 7,8 | 5,6 | 7,0 | 6,2 | 7,9 | 6,5 | 6,5 | 6,1 | 6,7 | 5,6–8,8 |
| B1 runner-indítás | 4,8 | 5,7 | 5,2 | 4,8 | 4,8 | 4,8 | 4,8 | 5,0 | 4,9 | 5,1 | 4,9 | 4,8–5,7 |
| B2 checkout, Python, függőségek, ruff | 4,2 | 4,2 | 4,4 | 4,0 | 4,2 | 4,0 | 4,1 | 3,8 | 4,1 | 3,8 | 4,1 | 3,8–4,4 |
| B3 Trivy secret + hadolint | 4,1 | 4,3 | 4,2 | 4,7 | 4,4 | 4,4 | 4,1 | 4,9 | 4,6 | 4,8 | 4,4 | 4,1–4,9 |
| B4 pytest + lefedettség | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4 | 1,4–1,4 |
| B5 lint-függőségek, Galaxy, ansible-lint | 15,9 | 43,6 | 19,3 | 29,8 | 18,0 | 21,9 | 22,9 | 31,2 | 30,3 | 32,2 | 26,3 | 15,9–43,6 |
| B6 két image-build + konténer-füstteszt | 11,9 | 11,9 | 12,2 | 11,9 | 12,5 | 12,1 | 12,4 | 13,4 | 12,2 | 12,3 | 12,2 | 11,9–13,4 |
| B7 Trivy image | 29,3 | 23,2 | 27,1 | 29,3 | 30,3 | 20,4 | 27,4 | 30,4 | 27,9 | 28,2 | 28,0 | 20,4–30,4 |
| B8 push | 0,9 | 1,0 | 0,9 | 0,7 | 0,8 | 0,9 | 0,9 | 0,7 | 1,1 | 1,0 | 0,9 | 0,7–1,1 |
| B9 takarítás, zárás | 1,6 | 1,6 | 1,7 | 1,7 | 1,6 | 1,7 | 1,6 | 1,9 | 1,7 | 1,8 | 1,7 | 1,6–1,9 |
| J job-váltás (build vége → deploy indul) | 3,3 | 3,2 | 3,1 | 3,1 | 3,0 | 3,1 | 3,3 | 3,4 | 3,5 | 3,3 | 3,3 | 3,0–3,5 |
| D1 runner, checkout, Ansible, címfeloldás, PREV_TAG | 10,9 | 11,7 | 11,5 | 12,0 | 11,0 | 11,0 | 11,3 | 11,2 | 11,0 | 11,7 | 11,2 | 10,9–12,0 |
| D2 → deploy-start | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1–0,1 |
| D3 helm upgrade --wait | 19,5 | 22,0 | 20,0 | 19,5 | 20,1 | 19,5 | 21,7 | 19,7 | 19,7 | 20,5 | 19,9 | 19,5–22,0 |
| D4 verify | 3,7 | 3,5 | 3,4 | 3,8 | 3,5 | 3,8 | 3,7 | 3,5 | 3,6 | 3,5 | 3,6 | 3,4–3,8 |
| **Σ push → accepted** | **120,4** | **144,3** | **122,3** | **132,4** | **122,7** | **115,2** | **127,6** | **137,1** | **132,4** | **135,7** | **130,0** | **115,2–144,3** |
| ebből minőségi kapu (B3+B4+B5+B7) | 50,7 | 72,5 | 52,0 | 65,1 | 54,0 | 48,1 | 55,8 | 67,8 | 64,1 | 66,6 | 60,0 | 48,1–72,5 |
| ebből minden más | 69,8 | 71,8 | 70,3 | 67,2 | 68,7 | 67,1 | 71,8 | 69,3 | 68,3 | 69,2 | 69,2 | 67,1–71,8 |

## Három megállapítás

**1. A teljes idő többlete pontosan a minőségi kapuk ára.** A kapuk (Trivy
secret, hadolint, pytest, ansible-lint a függőségeivel, Trivy image) nélküli
rész 67–72 mp, medián 69 — a kézi sorozat beállt szakasza 64–79 mp, medián 71.
Ugyanaz a nagyságrend, holott a két 70 mp-et más-más tételek teszik ki: az
automatizált oldalon ~26 mp a futtató saját költsége (F+B1+J+D1: felvétel,
konténerindítás, checkout, Ansible telepítése), a kézi oldalon ugyanennyi
körül az SSH-belépés, a gépelés és a kimenetolvasás. A 6.1 „az automatizálás
lassabb" mondata ezért így pontos: **a pipeline nem lassabb, hanem 48–73 mp-nyi
ellenőrzést végez, amelyet a kézi út egyáltalán nem végez el.** Ezt a mondatot
ez a táblázat bizonyítja, nem a két teljes idő különbsége.

**2. A szórás egyetlen szakaszé.** A teljes idő sávja 29 mp (115–144). Ebből a
B5 egymaga 27,7 mp (15,9–43,6); a „minden más" sor sávja 4,7 mp. A B5 a
`requirements-lint.txt` gyorsítótárazatlan pip-telepítését tartalmazza — ez a
korábbi, landmarkokra bontott elemzés (`auto-nyers-jegyzet.md`) eredményének
független megerősítése, más határsorokkal. A második legnagyobb sáv a B7-é
(10 mp); abban a Trivy adatbázis-letöltése fut, amelyről a korábbi mérés
kimutatta, hogy állandó (6,8–8,5 mp), tehát a maradék a szkennelés maga.

**3. A gépi kivárás a két oldalon ugyanaz.** A D3 (`helm upgrade --wait`)
19,5–22,0 mp; a kézi 10+11. lépés a beállt szakaszban 19–22 mp. A D4 gépi ellenőrzés 3,4–3,8 mp; a
kézi 12+13. lépés (verzió és füstteszt, begépelve és elolvasva) a beállt
szakaszban 6–15 mp. A telepítési szakasz 31 → 24 mp-es javulása tehát a D4-ből
jön, nem a D3-ból — ahogy a `lepesidok.md` előre megírta.

## A helyreállítási sorozat — A1–A3

| Szakasz | A1 | A2 | A3 | a kézi megfelelő (H1–H3) |
|---|---:|---:|---:|---|
| D3 helm upgrade --wait (a hibás verzió él) | 20,2 | 20,0 | 21,7 | 10+11. lépés: 18–20 mp |
| D4 verify, bukik (észlelés) | 2,4 | 2,5 | 2,4 | 12+13. lépés: 16–20 mp |
| R1 helm rollback --wait | 21,4 | 20,3 | 19,4 | V2 (rollback begépelése, 5–11 mp) + V3+V4 (kivárás, 18–19 mp) |
| R2 verify a `PREV_TAG`-re | 4,2 | 3,9 | 4,0 | V5+V6 (verzió + füstteszt): 9–12 mp |
| **helyreállítás (R1+R2)** | **25,6** | **24,2** | **23,4** | V2–V6: 34–39 mp |

A kiesés 37 → 24 mp-es (helyreállítás) és 56 → 26 mp-es (teljes) javulásának
forrása ebből a táblából olvasható le tételesen. Az R1 gépi kivárása 19–21 mp,
a kézi V3+V4 18–19 mp — ugyanaz a tétel. Ami eltűnt: a V2 begépelése
(a pipeline-ban a rollback parancs kiadása a kivárás része, külön nem mérhető
idő), és a V5–V6 9–12 mp-e helyett 4 mp gépi ellenőrzés. Az észlelés 16–20 →
2,4 mp-es különbsége ugyanez a mechanizmus a telepítés után: az ellenőrzés nem
gyorsabb, csak nem kell begépelni és elolvasni.

A hibás verzió telepítése (D3) 20–22 mp, ugyanannyi, mint a zöld futtatásokban —
a hiba a pod indulását és készenlétét nem érinti, ahogy a protokoll megkívánja.
