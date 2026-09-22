# Automatizált sorozat — nyers jegyzet

Minden időbélyeg UTC. A `push` a laptop `script`-jegyzőkönyvének prompt-időbélyege
a `git push` sorban; a többi a Gitea joblogjának `MERES` sorai.

`teljes` = push → accepted. `szakasz` = deploy-start → accepted.

| # | commit | push | pipeline-start | deploy-start | live | accepted | teljes | szakasz | elfogadás | megjegyzés |
|---|---|---|---|---|---|---|---|---|---|---|
| — | b390741 | — | — | 10:42:03 | 10:42:28 | 10:42:32 | — | 29 | sikeres | próbafuttatás, nem mérés |
| 1 | d63eb00 | 10:49:06 | 10:49:19 | 10:50:43 | 10:51:02 | 10:51:06 | 120 | 23 | sikeres | |
| 2 | 5550474 | 11:06:00 | 11:06:12 | 11:07:58 | 11:08:20 | 11:08:24 | 144 | 26 | sikeres | |
| 3 | 9f4f6e2 | 11:12:27 | 11:12:40 | 11:14:05 | 11:14:25 | 11:14:29 | 122 | 24 | sikeres | |
| 4 | 206b3cd | 11:15:58 | 11:16:08 | 11:17:47 | 11:18:06 | 11:18:10 | 132 | 23 | sikeres | |
| 5 | 815171d | 11:22:10 | 11:22:21 | 11:23:49 | 11:24:09 | 11:24:12 | 122 | 23 | sikeres | |
| 6 | ed6ef98 | 11:25:21 | 11:25:32 | 11:26:52 | 11:27:12 | 11:27:16 | 115 | 24 | sikeres | |
| 7 | cc208d2 | 11:28:21 | 11:28:33 | 11:30:03 | 11:30:24 | 11:30:28 | 127 | 25 | sikeres | |
| 8 | 5c52e11 | 11:31:07 | 11:31:18 | 11:33:00 | 11:33:20 | 11:33:24 | 137 | 24 | sikeres | |
| 9 | a876e07 | 11:35:48 | 11:35:59 | 11:37:37 | 11:37:56 | 11:38:00 | 132 | 23 | sikeres | |
| 10 | e4da1d9 | 11:38:43 | 11:38:54 | 11:40:34 | 11:40:55 | 11:40:58 | 135 | 24 | sikeres | |

## Bontás (számolt)

| # | felvétel (push→pipeline-start) | build (pipeline-start→deploy-start) | helm (deploy-start→live) | ellenőrzés (live→accepted) |
|---|---|---|---|---|
| 1 | 13 mp | 84 mp | 19 mp | 4 mp |
| 2 | 12 mp | 106 mp | 22 mp | 4 mp |
| 3 | 13 mp | 85 mp | 20 mp | 4 mp |
| 4 | 10 mp | 99 mp | 19 mp | 4 mp |
| 5 | 11 mp | 88 mp | 20 mp | 3 mp |
| 6 | 11 mp | 80 mp | 20 mp | 4 mp |
| 7 | 12 mp | 90 mp | 21 mp | 4 mp |
| 8 | 11 mp | 102 mp | 20 mp | 4 mp |
| 9 | 11 mp | 98 mp | 19 mp | 4 mp |
| 10 | 11 mp | 100 mp | 21 mp | 3 mp |

## Összesítés (10 érvényes futtatás)

| Mennyiség | Terjedelem | Átlag | Medián |
|---|---|---|---|
| teljes (push→accepted) | 115–144 | 128.6 | 129.5 |
| telepítési szakasz (deploy-start→accepted) | 23–26 | 23.9 | 24.0 |
| felvétel (push→pipeline-start) | 10–13 | 11.5 | 11.0 |
| build (pipeline-start→deploy-start) | 80–106 | 93.2 | 94.0 |
| helm --wait (deploy-start→live) | 19–22 | 20.1 | 20.0 |
| ellenőrzés (live→accepted) | 3–4 | 3.8 | 4.0 |

## A build-szórás forrása (a joblogokból, 2026-09-22)

A `build-test-push` job 72–97 mp között mozgott (25 mp terjedelem). A logok
soronkénti időbélyegeiből a szakasz azonosítható:

| | terjedelem | sáv |
|---|---:|---|
| teljes build | 25,4 mp | 72–97 mp |
| a `pytest` kezdetétől a Galaxy-telepítés kezdetéig | **27,5 mp** | 9–37 mp |
| a build e nélkül | 12,1 mp | 56–68 mp |

Ez a szakasz a pytest futását és az `Install the Ansible control node and
collections` lépés pip-telepítését fedi. A `requirements-lint.txt` csomagjai
**nincsenek gyorsítótárazva**: a build job `setup-python` lépése a
`cache-dependency-path`-ban csak a `requirements-dev.txt`-et nevezi meg, tehát
a lint-függőségek minden futtatásban a PyPI-ról töltődnek le.

A build szórása tehát nem „mérési zaj" és nem is a szkennelések: egyetlen,
gyorsítótárazatlan függőségtelepítés adja. A többi lépés — ruff, hadolint,
Trivy fs, két image-build, Trivy image, push — együtt 56–68 mp között marad.

**Ez nem javítandó a mérés előtt.** A `cache-dependency-path` bővítése
csökkentené az átlagot és a szórást is, de megváltoztatná azt a pipeline-t,
amelyen a tíz futtatás lefutott. A továbbfejlesztési fejezetbe való, mért
számmal alátámasztva.

Korábbi, elvetett magyarázat: a Trivy adatbázis-letöltése és a runner image
pull. Mindkettő megmérve, mindkettő állandó (6,8–8,5 mp, illetve 2,9–3,6 mp),
tehát a szórást nem ők adják. A hipotézist a log cáfolta.
