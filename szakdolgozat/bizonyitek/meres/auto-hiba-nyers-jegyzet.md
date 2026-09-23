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
