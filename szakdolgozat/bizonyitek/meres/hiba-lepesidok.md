# A helyreállítási mérés — lépésenkénti bontás

Két egymást követő prompt különbsége egy lépés teljes emberi költsége
(04-kezi-telepitesi-folyamat.md 5. pont). Ez a fájl a 6.4 nyersanyaga,
az összesített adat a [`hiba-sorozat.csv`](hiba-sorozat.csv).

| # | Lépés | H1 (`hiba-01`) | H2 (`hiba-02`) | H3 (`hiba-03`) |
|---|---|---:|---:|---:|
| 1 | push | 7 mp | 3 mp | 3 mp |
| 2 | ssh | 4 mp | 5 mp | 4 mp |
| — | *prompt beállítása (műszer, nem lépés)* | 2 mp | 2 mp | 2 mp |
| 3 | fetch + checkout | 3 mp | 3 mp | 3 mp |
| 4 | SHA | 8 mp | 6 mp | 3 mp |
| 5 | backend build | 13 mp | 12 mp | 12 mp |
| 6 | frontend build | 2 mp | 2 mp | 2 mp |
| 7 | backend push | 4 mp | 3 mp | 3 mp |
| 8 | frontend push | 3 mp | 2 mp | 3 mp |
| 9 | helm upgrade | 4 mp | 3 mp | 5 mp |
| 10 | rollout backend | 18 mp | 18 mp¹ | 16 mp |
| 11 | rollout frontend | 2 mp | (a 10-zel együtt)¹ | 3 mp |
| | **a hibás verzió él** | **09:38:46** | **09:42:50** | **09:47:48** |
| 12 | /version | 6 mp | 9 mp | 8 mp |
| 13 | füstteszt (bukik) | 10 mp | 8 mp | 12 mp |
| | **észlelés** | **09:39:02** | **09:43:07** | **09:48:08** |
| V2 | helm rollback | 5 mp | 11 mp | 6 mp |
| V3 | rollout backend | 15 mp | 17 mp | 16 mp |
| V4 | rollout frontend | 3 mp | 2 mp | 3 mp |
| V5 | /version | 5 mp | 4 mp | 8 mp |
| V6 | füstteszt (tiszta) | 6 mp | 5 mp | 4 mp |
| | **helyreállt** | **09:39:36** | **09:43:46** | **09:48:45** |

¹ A H2-ben a 11. lépés a 10. futása alatt lett előregépelve, így a két lépés
prompt-ideje összecsúszott (együtt 18 mp). Ez a telepítési szakaszban történt, a
mért helyreállítási ablakot nem érinti; részletesen a [`README.md`](README.md)-ben.

## A három mért szakasz

| | H1 | H2 | H3 | medián | terjedelem |
|---|---:|---:|---:|---:|---:|
| észlelés (11. lépés vége → 13. lépés bukása) | 16 mp | 17 mp | 20 mp | 17 mp | 16–20 mp |
| helyreállítás (bukás → V6 vége) | 34 mp | 39 mp | 37 mp | 37 mp | 34–39 mp |
| **teljes (hibás verzió él → szolgáltatás jó)** | **50 mp** | **56 mp** | **57 mp** | **56 mp** | **50–57 mp** |
| emberi beavatkozás | 18 | 18 | 18 | 18 | — |
| telepítési szakasz (1–13. lépés) | 86 mp | 76 mp | 79 mp | 79 mp | 76–86 mp |

Mindhárom futtatásban a V5 a `be36f74`-et adta vissza, a V6 füstteszt mind a hét
ellenőrzésen a várt státuszt, és a hibás verzió pontosan egy ellenőrzésen bukott
(`POST /echo · valid JSON` → 500) — a beinjektált hiba hatóköre tehát mind a
három futtatásban azonos volt.

## Amit ebből a 6.4-nek ki kell mondania

1. **A helyreállítás gépi tételei uralják az időt.** A 34–39 mp-ből a két
   gördülő csere kivárása (V3+V4) 18–19 mp, vagyis nagyjából a fele. Ez az
   automatizált oldalon is ott lesz, változatlanul: a `helm rollback` ugyanazt a
   fürtöt ugyanúgy állítja vissza. A javulás tehát a maradékból jöhet, nem
   ebből.
2. **Az észlelés ideje nem általánosítható.** A 16–20 mp azért ilyen rövid, mert
   az operátor közvetlenül a telepítés után ellenőriz. A 6.5-ben ezt ki kell
   mondani: a mérés nem az észlelést hasonlítja össze, hanem a javítást.
3. **A szórás kicsi és azonosítható eredetű.** Az 50–57 mp-es sáv szélességét a
   V2 rollback ingadozása (5 / 11 / 6 mp) és a bukó füstteszt hossza (8–12 mp)
   adja; a gördülő csere mindhárom futtatásban 18–19 mp.
