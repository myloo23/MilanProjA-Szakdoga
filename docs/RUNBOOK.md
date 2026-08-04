# Runbook — Project A

What to do when a deploy goes wrong, and the evidence that it works.

How the deploy path is built and why is in
[`DEVELOPMENT.md` § Deploy, roll back, dry run](DEVELOPMENT.md) — this file does
not repeat it. Here: the incident procedure, and the measured results of
rehearsing it.

---

## A deploy failed

The play stops, prints the last 50 log lines, and prints the rollback command
with the previous SHA already filled in. Run that line:

```bash
cd ansible
ansible-playbook playbooks/deploy.yml -e app_version=<previous-sha>
```

You do not have to recall the SHA under pressure — the role records what was
running before it changed anything, so the failure names its own way back.

The failed container is left running **for inspection only**. It did not pass
its checks, so it is not live, whatever `docker ps` suggests.

If the printed command is missing (nothing was running before, or the same
version was already deployed, both of which the failure message says explicitly),
pick a SHA by hand:

```bash
curl -s localhost:5001/v2/projecta-flask/tags/list
docker inspect --format '{{index .Config.Labels "version"}}' projecta-flask
```

There is no `/version` HTTP endpoint yet — use the label, do not claim the
endpoint.

---

## Rehearsal — 2026-07-31

Run with `scripts/rollback-drill.sh`: it deploys a knowingly broken image, lets
the smoke test fail the deploy, runs the printed rollback command, and times it.
Full transcript in commit `eac8fe5`.

| | |
|---|---|
| Rollback target | `fbc1254e…` |
| Broken tag | `deadbee` (`/health` → 500) |
| Time to **detect** the bad deploy | **27s** (10 retries × ~2.5s, exit 2) |
| Time to **roll back** | **7s** (exit 0) |
| **Total outage window** | **~34s** |

The failure named its own way back, unprompted:

```
TASK [deploy_app : Fail the deploy and name the way back] **********************
fatal: [docker-host]: FAILED! => Deploy of deadbee failed verification. The
container was left running for inspection — it did not pass its checks, so do
not treat it as live.

Roll back:
  ansible-playbook playbooks/deploy.yml -e app_version=fbc1254eac5f72f0584fb48c29ecae2ac73f3f1a
```

That line, run verbatim, restored service — `ok=11 changed=1 failed=0`, with
`/health` 200 `{"status":"UP"}`, `/ready` 200, `/echo` 200.

### What the drill exposed

**Quote 34 seconds, not 7.** The role replaces the running container *before* it
verifies the new one, so the broken image served 500s for the whole 27 seconds
the smoke test took to give up. The smoke test bounds downtime; it cannot
prevent it.

That shape was already known — "zero-downtime swap" sits under P2 in `PLAN.md`.
What the rehearsal added was the number. Do not tighten
`deploy_app_smoke_retries` to make it look better: that trades a real second
chance for a transient blip against a cosmetic win. The honest fix is verifying
the new container before it takes traffic, and that is Sprint 4 scope.

The rollback play also logged one `FAILED - RETRYING (9 retries left)` before
passing — the app needs about two seconds to accept traffic after start. A fixed
`sleep` would have had to guess that; the retry loop measures it.

### Residue

`localhost:5001/projecta-flask:deadbee` is still in the registry, alongside the
real SHAs. Left deliberately as evidence the rehearsal happened. Drop the local
copy with `docker rmi localhost:5001/projecta-flask:deadbee`.
