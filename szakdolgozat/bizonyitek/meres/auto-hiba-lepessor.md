# Automatizált helyreállítási sorozat — lépéssor és döntések

Ág: `release/meres-hiba` (a `release/**` minta miatt fut rá a pipeline, és
`ships=true`, tehát a `deploy` job is). A `release/meres` tiszta marad.

## Miért négy futtatás, és miért A0 + A1–A3

**A0 — ugyanaz a hiba, változtatás nélkül.** A `meres/hiba-01..03`
injektálása bájtra azonos, csak a jelölősor más (`300`). Előzetes ellenőrzés
(2026-09-23, a `meres/hiba-01` kódján, a CI-vel azonos pytest-hívással):
három teszt bukik —

- `tests/test_app.py::test_echo_valid_json` (500 a várt 200 helyett),
- `tests/test_app.py::test_a_body_at_the_limit_is_still_accepted`,
- `tests/test_observability.py::test_a_request_increments_the_counter_for_its_route`.

Várható tehát, hogy a `build-test-push` job a pytestnél piros lesz, a `deploy`
job a `needs:` miatt el sem indul, és a hibás verzió nem kerül a fürtre. Az A0
ezt méri a pipeline-on: mennyi idő alatt és melyik kapun áll meg ugyanaz a hiba,
amely a kézi úton kijutott és 50–57 mp kiesést okozott. **Kiesés: nincs.** Ez nem
helyreállítási mérés, hanem a hiba *megelőzése*; külön sorban, külön
fájlban rögzítjük (`auto-hiba-a0.csv`).

**A1–A3 — a hiba a unit tesztek elől rejtve.** A visszaállító lépést csak olyan
hiba méri, amely átjut a build kapuin. Az injektálás egyetlen feltétellel bővül:
`and not app.testing`. A futó fürtön a Flask `TESTING` hamis, a viselkedés tehát
azonos a kézi sorozatéval; a pytest fixture-je `TESTING=True`-t állít, ott a hiba
nem jelentkezik. Ez azt a hibaosztályt modellezi, amely ellen a telepítés utáni
ellenőrzés és a visszaállítás egyáltalán létezik: ami a tesztkészleten átmegy,
és csak a futó rendszeren látszik.

Előzetes ellenőrzés a feltételes változaton (2026-09-23): pytest 48/48 zöld,
lefedettség 92,27 % (a kapu 80 %), az `app.py` egyetlen fedetlen sora az
injektált `return`. `TESTING=False` mellett az érvényes JSON-kérés 500-at kap,
a hibás tartalomtípus és a hibás JSON 400-at, a túlméretes törzs 413-at — mint a
kézi sorozat táblázatában. A fürtön a teljes hétsoros táblát a `verify.yml` első
bukó feladata adja (`Echo a valid payload`, 200-at vár).

**A két eltérés a kézi oldaltól, és miért nem érvénytelenítik az összevetést.**
(1) A kézi oldalon a hiba feltétel nélküli volt, itt feltételes — a fürtön futó
kód viselkedése ugyanaz, a különbség csak a pytest számára látható. (2) A kézi
oldalon a hiba a unit teszteken sosem ment át, mert a kézi út nem futtat unit
tesztet. Az A0 pontosan ezt teszi láthatóvá; az A1–A3 azt méri, mi történik,
ha egy hiba ennek ellenére kijut.

## Az A0 eredménye (2026-09-23) — az előrejelzés teljesült

Push 07:05:57, `MERES pipeline-start` 07:06:10, a „Run tests with coverage”
lépés bukása 07:06:21. **Push → megállás 24 mp**, ebből a pipeline saját
ideje 11 mp. Pontosan az előre megnevezett három teszt bukott (3 failed, 45
passed), a lefedettségi kapu nem (92,82 %). Image nem épült, a `deploy` job nem
indult, a fürtön továbbra is az `e4da1d9` fut. **Kiesés: 0 mp.** Adatsor:
`auto-hiba-a0.csv`, log: `workflowlogok/ci-build-test-push-32.log`, jegyzőkönyv:
`auto-hiba-00.txt`.

Összevetve a kézi oldallal: ugyanez a hiba ott kijutott, és 50–57 mp kiesést
okozott, amíg a V1–V6 helyre nem állította.

## Az A1–A3 eredménye (2026-09-23)

Mindhárom futtatás érvényes: a hibás verzió kiment, a verify play az „Echo a
valid payload" feladaton bukott (500), a `helm rollback` lefutott, a
visszaállított verzióra futó verify mind a 10 feladaton átment, és a
version-assert az `e4da1d9`-et igazolta. Kiesés 28 / 26 / 25 mp (medián 26),
helyreállítás 25 / 24 / 23 mp, észlelés 3 / 2 / 2 mp, 2 beavatkozás. Kiértékelés
és összevetés: `auto-hiba-nyers-jegyzet.md`.

## Egy futtatás menete

Előkészítés (nem mért): a jelölősor átírása és a commit — ezt Claude végzi a
repóban. A laptopon, a B ablakban:

```bash
script -q ~/meres/auto-hiba-NN.txt
export TZ=UTC
PROMPT='[%D{%H:%M:%S}] '$PROMPT
git push azure release/meres-hiba
```

Az első futtatásnál (A0) a push új ágat hoz létre az `azure` remote-on — ez a
normál eset, nem hiba. Utána a Gitea felületén követni a futtatást. Amikor a
workflow véget ért (piros lesz, ez a várt eredmény), `exit`, és a jegyzőkönyv
másolása: `cp ~/meres/auto-hiba-NN.txt szakdolgozat/bizonyitek/meres/`.
A joblogok letöltése a `workflowlogok/` alá, a korábbi névmintával
(`ci-build-test-push-<n>.log`, `ci-deploy-<n+1>.log`).

**Mért ablak (A1–A3):** `live` (a hibás verzió él) → `detect` (a verify play
elbukott) → `restored` (a visszaállított verzió átment a verify-on). Mind a
`deploy` job logjának `MERES` soraiból. A `push`-időbélyeg a jegyzőkönyvből.

**Beavatkozás:** 2 — a push, és a piros eredmény elolvasása és elbírálása
(2026-09-22-i döntés, naplo).

**Elfogadás (A1–A3):** a futtatás akkor sikeres, ha a `deploy` job logjában
megvan mind a `detect`, mind a `restored` sor, és a visszaállító lépés
`verify.yml`-je a `PREV_TAG`-re futott le (a „Record the release that is
running now" lépés kiírja: `currently deployed: <sha>`). A workflow maga
**piros marad** — a sikeres visszaállítás nem sikeres telepítés.
