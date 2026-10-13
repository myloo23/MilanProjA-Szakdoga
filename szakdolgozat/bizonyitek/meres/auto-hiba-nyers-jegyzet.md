# Automatizált helyreállítási sorozat — nyers jegyzet

Minden időbélyeg UTC. A `push` a laptop `script`-jegyzőkönyvének prompt-időbélyege
a `git push` sorban; a `rollback kész` a deploy joblog „Rollback was a success"
sorának időbélyege; a többi a joblog `MERES` sorai.

`észlelés` = live → detect. `helyreállítás` = detect → restored. `kiesés` = live → restored
(a kézi `hiba-sorozat.csv` `teljes_mp` oszlopának megfelelője).

| # | commit | push | pipeline-start | deploy-start | live | detect | rollback kész | restored | észlelés | helyreállítás | kiesés | logok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 544f895 | 07:05:57 | 07:06:10 | — | — | — | — | — | — | — | 0 | build-32 (pytest bukott, deploy nem indult) |
| A1 | dbe433c | 07:11:48 | 07:11:58 | 07:13:31 | 07:13:51 | 07:13:54 | 07:14:15 | 07:14:19 | 3 | 25 | 28 | build-33, deploy-34 |
| A2 | be3a91c | 07:16:38 | 07:16:51 | 07:18:43 | 07:19:03 | 07:19:05 | 07:19:25 | 07:19:29 | 2 | 24 | 26 | build-35, deploy-36 |
| A3 | a9129e6 | 07:20:51 | 07:21:03 | 07:22:35 | 07:22:57 | 07:22:59 | 07:23:18 | 07:23:22 | 2 | 23 | 25 | build-37, deploy-38 |

## Bontás (számolt, A1–A3)

| # | helm upgrade --wait (deploy-start→live) | észlelés (live→detect) | helm rollback --wait (detect→rollback kész) | ellenőrzés (rollback kész→restored) |
|---|---:|---:|---:|---:|
| A1 | 20 mp | 3 mp | 21 mp | 4 mp |
| A2 | 20 mp | 2 mp | 20 mp | 4 mp |
| A3 | 22 mp | 2 mp | 19 mp | 4 mp |

## Összevetés a kézi helyreállítással (3–3 futtatás)

| | Kézi (H1–H3) | Automatizált (A1–A3) |
|---|---:|---:|
| észlelés, medián (sáv) | 17 mp (16–20) | 2 mp (2–3) |
| helyreállítás, medián (sáv) | 37 mp (34–39) | 24 mp (23–25) |
| **kiesés, medián (sáv)** | **56 mp (50–57)** | **26 mp (25–28)** |
| a gépi kivárás a helyreállításban | V3+V4: 18–19 mp | `helm rollback --wait`: 19–21 mp |
| emberi beavatkozás | 19 | 2 |
| a visszaállítás célja | `be36f74`, 3/3 | `e4da1d9`, 3/3 (gépi version-assert) |

**A `hiba-lepesidok.md` előrejelzése itt is teljesült.** Azt írta, hogy a
helyreállítás gépi tétele (a gördülő csere kivárása) az automatizált oldalon sem
lesz rövidebb. Nem lett: 18–19 mp kézzel, 19–21 mp a pipeline-ban. A 37 → 24 mp
javulás teljes egészében a nem gépi részből jön: a kézi V2 (rollback begépelése,
5–11 mp) és V5–V6 (verzió és füstteszt, 9–12 mp) helyére egy ~4 mp-es gépi
ellenőrzés lép.

**Az észlelés 17 → 2 mp csak ezen a felálláson igaz.** Mindkét oldalon közvetlenül
a telepítés után fut az ellenőrzés; a különbség az, hogy kézzel a 12–13. lépés
begépelése és a kimenet elolvasása 16–20 mp, gépileg a verify play első öt
feladata ~2 mp. Olyan hibára, amelyet a füstteszt nem fed, egyik oldal sem észlel
semmit — ez a 6.5-be tartozik, ugyanúgy, mint a kézi oldalon.

**Három futtatás, nem tíz**, ugyanazzal az indoklással, mint a kézi oldalon (a 00-terv
7. pontja a futtatásszámot a telepítési sorozatra írja elő). A sáv szűk (a kiesés
25–28 mp), de három pontból szórásról nem állítunk többet, mint hogy a három
futtatás 3 mp-en belül egyezik.
