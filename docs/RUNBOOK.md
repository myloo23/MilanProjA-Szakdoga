# Runbook — Project A

Operational procedures for the deployed Flask service. Everything here has been
run, not designed. Where a number appears it was measured; where a transcript
appears it was pasted, not retyped.

Scope today: **Deploy** and **Rollback**. Observability procedures arrive with
Sprint 3.

---

## Facts you need before doing anything

| | |
|---|---|
| Service | `projecta-flask` |
| Container name | `projecta-flask` |
| Docker network | `projecta-platform` |
| Published address | `http://localhost:8000` |
| Registry (from the host) | `localhost:5001` |
| Registry (from a container on `projecta-platform`) | `registry:5000` |
| Health / readiness | `GET /health`, `GET /ready` |

That last registry distinction is the single most common way a deploy fails
confusingly: the address depends on who is asking. It is recorded once in
`ansible/inventory/group_vars/local_docker.yml` as `registry_endpoint`, and the
smoke test picks its vantage point with `deploy_app_smoke_vantage` (`host` when
a human runs it, `network` when CD does).

---

## Deploy

A deploy is one command. It never builds — it pulls the exact image CI already
built, tested, scanned and pushed, because rebuilding at deploy time would
destroy the guarantee that what runs is what was tested.

```bash
cd ansible
ansible-playbook playbooks/deploy.yml -e app_version=<git-sha>
```

`app_version` has no default, deliberately. A default would let a deploy quietly
ship a different artifact than the pipeline tested. The role asserts the value
is at least 7 hex characters and refuses to proceed otherwise.

**What it does, in order:** asserts the version is deployable → records what is
currently running (so a failure can name its own way back) → pulls the image by
SHA → runs the container with memory, CPU and log-rotation limits → runs the
smoke test, which fails the play if the app cannot prove it works.

**Which SHA is running right now:**

```bash
docker inspect --format '{{index .Config.Labels "version"}}' projecta-flask
```

The role stamps that label on every container it creates, so the running
artifact can always identify itself. (There is no `/version` HTTP endpoint yet —
it is still open in `PLAN.md`. Use the label; do not claim the endpoint.)

**Which SHAs are available to deploy:**

```bash
curl -s localhost:5001/v2/projecta-flask/tags/list
```

**Idempotence.** Running the same deploy twice reports `changed=0`. The image
pull uses `pull: not_present` because a SHA tag is immutable, and the container
module recreates only when the spec actually differs. This is worth
demonstrating rather than asserting — it is what makes re-running a deploy safe
when you are unsure whether the first one landed.

### When a deploy fails

The play stops and prints the last 50 log lines from the container plus the
exact rollback command with the previous SHA already filled in. The failed
container is left running **for inspection only** — it did not pass its checks,
so it is not live, whatever `docker ps` suggests.

---

## Rollback

**There is no `rollback.yml`, and that is a decision, not an omission.**

Rollback is `deploy.yml` with an earlier SHA:

```bash
cd ansible
ansible-playbook playbooks/deploy.yml -e app_version=<previous-sha>
```

A separate rollback playbook would duplicate the pull, run, and verify logic,
and would then be exercised only during incidents — which is to say, tested
least at the moment it matters most. Sharing one code path means every ordinary
deploy is also a rehearsal of the rollback. Expect this to look like a gap on
first inspection; the answer is that the gap is the point.

The failure message from a broken deploy prints this command for you, with the
previous SHA already substituted. You do not have to remember the SHA under
pressure — the tooling remembers it for you. That is the whole reason the role
records what is running *before* it changes anything.

### Rehearsal

<!-- DRILL-RESULT-START -->
Rehearsed **2026-07-31**. Full transcript: `docs/rollback-drill-20260731-103657.log`.

| | |
|---|---|
| Good SHA (rollback target) | `fbc1254eac5f72f0584fb48c29ecae2ac73f3f1a` |
| Broken tag | `deadbee` (`/health` → 500) |
| Time to **detect** the bad deploy | **27s** (10 retries × ~2.5s, playbook exit 2) |
| Time to **roll back** | **7s** (playbook exit 0) |
| **Total outage window** | **~34s** |

The rollback itself is 7 seconds. **The number to quote in a review is 34
seconds**, because the broken container was live and serving 500s for the 27
seconds it took the smoke test to give up on it. See "What the drill exposed"
below — that gap is a property of the design, not a defect in the rehearsal.

The failure named its own way back, unprompted:

```
TASK [deploy_app : Fail the deploy and name the way back] **********************
fatal: [docker-host]: FAILED! => Deploy of deadbee failed verification. The container was
left running for inspection — it did not pass its checks, so do not
treat it as live.

Roll back:
  ansible-playbook playbooks/deploy.yml -e app_version=fbc1254eac5f72f0584fb48c29ecae2ac73f3f1a

Last 50 log lines from projecta-flask:
192.168.65.1 - - [31/Jul/2026:08:37:26 +0000] "GET /health HTTP/1.1" 500 18 "-" "ansible-httpget"
```

Running that line, verbatim, restored service:

```
PLAY RECAP *********************************************************************
docker-host                : ok=11   changed=1    unreachable=0    failed=0    rescued=0

  image=localhost:5001/projecta-flask:fbc1254eac5f72f0584fb48c29ecae2ac73f3f1a
  /health → HTTP 200   {"status":"UP"}
  /ready  → HTTP 200   {"status":"READY"}
  /echo   → HTTP 200   {"received":{"drill":"complete"}}
```

Note the rollback play also logged one `FAILED - RETRYING ... (9 retries left)`
before the health check passed. That is the health-gated wait doing its job —
the app needs about two seconds to accept traffic after the container starts. A
fixed `sleep` would have had to guess that interval; the retry loop measures it.

### What the drill exposed

**The deploy is replace-then-verify, so a bad deploy is a real outage.** The role
swaps the running container for the new image *before* the smoke test runs. The
smoke test therefore cannot prevent downtime — it can only bound it. The 27
seconds is `deploy_app_smoke_retries` (10) × `deploy_app_smoke_delay` (2) plus
request overhead, and it is tunable, but no tuning makes it zero.

This was a known shape, not a surprise: `PLAN.md` lists "zero-downtime swap"
under P2. What the drill did was turn it from an architectural note into a
measured 27 seconds. Do not tighten the retry budget to make the number look
better — that would trade a real second chance for a transient blip against a
cosmetic improvement. The honest fix is a swap that verifies the new container
before it takes traffic, and that is Sprint 4 scope.
<!-- DRILL-RESULT-END -->

The drill is scripted in `scripts/rollback-drill.sh` so it can be repeated
whenever the deploy path changes. It:

1. records the running SHA from the container's `version` label — the rollback target;
2. patches `/health` to return 500, builds and pushes that as tag `deadbee`, then
   restores the source from git (so `main` stays clean while the real failure
   path is still exercised);
3. deploys the broken tag and confirms the smoke test **fails the deploy** and
   prints its own rollback command;
4. runs that command and times it;
5. verifies `/health`, `/ready` and `/echo` independently of the playbook's own
   opinion.

**Caveat, to be stated before anyone asks:** the measured time assumes the
previous image is still in the local image store, so it excludes a registry
pull. `pull: not_present` will fetch on a host that has been cleaned. The honest
claim is "under a minute on a warm host", not "under a minute always".

---

## Known residue

- `localhost:5001/projecta-flask:deadbee` — the deliberately broken image from
  the drill. Left in the registry as evidence the rehearsal happened. Remove the
  local copy with `docker rmi localhost:5001/projecta-flask:deadbee`.

---

## Not covered yet

`ansible-lint` in CI, structured JSON logging, `/metrics`, a `/version`
endpoint, and everything in Sprint 3's observability stack. Listed here so their
absence is a recorded fact rather than something a reader has to infer.
