# Runbook — Project A

How to operate the measurement VM, what to do when a deploy goes wrong, and the
evidence that the procedures work.

**Current setup (since 2026-09-21):** one Azure VM built by Terraform, k3s on
it, the application deployed by Helm from the Gitea pipeline. The procedures for
the internship-era Docker host (Ansible deploy) are kept at the end of this
file, under *Archive*, because their rehearsal results are cited.

**(L)** = laptop, repository root · **(G)** = on the VM (`ssh azureuser@4.165.139.1`)

---

## Where things run

| What | Where | Notes |
|---|---|---|
| VM | Azure, `szakdoga2-rg` / `szakdoga2-vm`, swedencentral, Standard_B2s_v2 | static public IP `4.165.139.1` (Terraform output `public_ip`) |
| Gitea, act_runner, registry | Docker Compose on the VM, `~/platform` | Gitea on `127.0.0.1:3000`, registry on `127.0.0.1:5001` — reach them through the SSH tunnel |
| Application | k3s, Helm release `projecta`, namespace `default` | backend ×2, frontend ×2, postgres with a PVC, Traefik on port 80 |
| Database credentials | Secret `db-credentials` | created by hand, never in Git (`szakdolgozat/06-merogep-ujraepitese.md`, step 4) |
| Observability | Compose profile `observability` on the VM | not running by default — the measurement ran without it |

## Start and stop

```bash
az vm start      -g szakdoga2-rg -n szakdoga2-vm          # (L)
az vm deallocate -g szakdoga2-rg -n szakdoga2-vm          # (L) at the end of every session
```

**Deallocate, do not shut down from inside.** A `sudo shutdown` on the VM stops
the OS but keeps the compute billed; only `deallocate` stops the credit burn.
The platform containers and k3s come back on their own after `start`.

Tunnel for Gitea and the registry (keep it open in its own window):

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 azureuser@4.165.139.1   # (L)
```

**SSH hangs instead of refusing:** the home IP has changed and the NSG no longer
lets it in. `curl -s ifconfig.me`, update `allowed_cidr` in
`terraform/terraform.tfvars`, `terraform -chdir=terraform plan`. Apply **only if
the plan is a single in-place update of the NSG rule.** A `must be replaced`
line anywhere means stop — that is how the VM was lost on 2026-09-30
(`szakdolgozat/06-merogep-ujraepitese.md`).

## Is it healthy?

```bash
docker ps --format '{{.Names}}: {{.Status}}'      # (G) gitea, registry, act-runner up
kubectl get pods                                  # (G) all Running, READY 1/1
curl -s http://localhost/api/version; echo        # (G) the SHA you expect
~/projecta/scripts/smoke.sh http://localhost/api  # (G) seven expected statuses
```

`smoke.sh` always exits 0: it prints, you judge. In the pipeline the same checks
run as the `verify` play, where every task fails the play.

## A deploy failed

**In the pipeline, the recovery is automatic.** When `Verify the deployed
release` fails, `Roll back to the previous revision` runs `helm rollback --wait`
to the revision recorded before the deploy (`PREV_TAG`) and verifies it with the
same play. In the job log:

```
MERES detect …            verification failed
Rollback was a success!   helm is back on the previous revision
MERES restored …          the previous SHA passed verification
```

**The workflow stays red on purpose.** A recovered deploy is still a failed
deploy; green would hide that the change never shipped. Confirm what is running:

```bash
curl -s http://localhost/api/version; echo        # (G) must equal PREV_TAG from the log
helm history projecta | tail -5                   # (G)
```

Measured three times (A1–A3): outage 25–28 s, two human interventions —
`szakdolgozat/bizonyitek/meres/auto-hiba-sorozat.csv`.

**If the rollback step itself failed, or a bad release is live outside the
pipeline**, roll back by hand:

```bash
helm history projecta                             # (G) find the last good revision
helm rollback projecta <revision> --wait --timeout 5m
kubectl rollout status deploy/backend
kubectl rollout status deploy/frontend
curl -s http://localhost/api/version; echo
~/projecta/scripts/smoke.sh http://localhost/api
```

The manual path, measured: outage 50–57 s, 19 interventions
(`szakdolgozat/bizonyitek/meres/hiba-sorozat.csv`, step list in
`hiba-lepessor.md`).

**If verification fails before anything was deployed** (build, scan, or
`PREV_TAG` could not be read), the rollback step prints `nothing was deployed in
this run` and exits 0. Nothing on the cluster changed.

## The pipeline is red on Trivy, and nothing changed

The vulnerability database moved, not the code: a pinned base image picked up a
newly published advisory. It has happened three times in fourteen days
(`szakdolgozat/naplo.md` 2.7, 3.1, 3.2). **Do not disable the gate and do not
add an ignore entry.** Re-pin:

```bash
scripts/pin-base-images.sh                        # (L) needs Docker
```

It resolves the current upstream digests, scans them with the pipeline's Trivy
and flags, and rewrites the `FROM` lines only if they are clean. `RESULT: not
pinned` means upstream has not rebuilt yet — try again in a day or two. On
`RESULT: pinned`, commit the two Dockerfiles with the report in
`szakdolgozat/bizonyitek/07-alapkep-leptetes.txt` and push.

## The VM was replaced, or its data is gone

The cluster comes back from code (Terraform + cloud-init); Gitea, the registry
contents, the Helm release and the database do not. Step-by-step rebuild:
[`szakdolgozat/06-merogep-ujraepitese.md`](../szakdolgozat/06-merogep-ujraepitese.md).
The measurement evidence is in Git and is not affected.

## Observability

```bash
~/observability-k3s-up.sh                         # (G) start Prometheus, Loki, Alloy, Grafana
ROLLOUT=1 ~/verify-observability-k3s.sh           # (G) end-to-end check incl. a rolling update
```

Grafana through the tunnel: add `-L 3001:127.0.0.1:3001` (port per
`platform/.env`). Design: [ADR-0010](adr/0010-observability-on-k3s.md); last
verification: `szakdolgozat/bizonyitek/05-megfigyeles-k3s-verify.txt`.

---

## A secret reached Git

**Rotate it first.** Everything below is cleanup, not the fix. The moment a
credential is committed it is compromised — a clone, a CI log, a cached fetch or
a mirror is enough, and none of them are undone by rewriting your history. Treat
history surgery as the second task, and never as evidence that the credential is
safe again.

Only once the credential is dead does it matter which of three shapes the leak
has:

| Where the secret is | What removes it | What it costs |
|---|---|---|
| The last commit, not yet pushed | `git reset --hard HEAD~1` | Nothing. The commit is unreferenced and dies at the next `gc` |
| Inside a merge that is already on a shared branch | `git revert -m 1 <merge>` | **Does not remove the secret.** See below |
| Buried in older history | `git filter-repo --invert-paths --path <file>` | Every SHA after the leak changes. Coordinated force-push, and every clone is now wrong |

`filter-branch` is what the mentors' training recommends; Git's own
documentation has recommended against it for years, on both performance and
correctness grounds, and points at `filter-repo` instead. This runbook follows
Git rather than the training, deliberately.

### Rehearsal — 2026-08-10

Run against a throwaway clone of this repository at 50 commits, so the numbers
come from real history rather than a toy. Fake credentials throughout: an
AWS-shaped key pair, a Postgres URL, and an OpenSSH private key with
`DRILLFAKEKEYMATERIALNOTREAL` where the key material goes.

| Case | Fix | Result |
|---|---|---|
| Secret in the last commit | `git reset --hard HEAD~1` | File gone, 0 commits contain the string. The dangling commit still resolved via `git cat-file` |
| Secret inside a merge commit | `git revert -m 1 HEAD` | File gone from the tree, **2 commits still contain the string** |
| Secret 5 commits back | `git filter-repo --invert-paths` | 0 commits contain the string, **500ms** across 74 commits, `origin` dropped |

### What the drill exposed

**`git revert` does not remove a secret, and it reads as though it did.** After
the revert, `git status` is clean, the file is gone from the working tree, and
the branch looks repaired. The credential is still there:

```
$ git show 9948b49:app/db_config.py
DATABASE_URL = "postgresql://admin:<drill password, redacted here>@prod-db.internal:5432/app"
```

The redaction is not squeamishness. This file is inside the checkout that the
Trivy step scans, so a realistic credential pasted into documentation fails the
build exactly as a real one would — the scanner cannot tell that a string is an
example, and a gate that could be talked out of firing would not be a gate.

One SHA and a path, and anyone with the repository has it back. The training
material lists revert as the "safer" option because it keeps an audit trail, and
for a bad *change* that is right. For a leaked *credential* it is the wrong
instrument, and the thing that makes it dangerous is not that it fails — it is
that it looks like it worked. This is the whole reason the first line of this
section is about rotation.

**`filter-repo` drops the remote on purpose.** Zero `git remote` entries
afterwards. That is a safety feature, not a bug: it forces a deliberate re-add
before anything can be force-pushed over a shared branch.

**The cheap case is only cheap before a push.** `reset --hard` cost nothing here
because nothing had left the machine. The same leak one `git push` later is the
third row of the table.

### The hook, verified — 2026-08-10

`pre-commit install`, then a generated AWS-shaped key staged and committed. The
commit failed, which is the whole claim:

```
Detect hardcoded secrets.................................................Failed
- hook id: gitleaks
- exit code: 1
Finding:     KEY = "REDACTED"
RuleID:      generic-api-key
Entropy:     3.546439
File:        leak.py
Line:        1
4:02PM INF 0 commits scanned.
4:02PM INF scanned ~29 bytes (29 bytes) in 22.3ms
4:02PM WRN leaks found: 1
```

Two things in that output are worth more than the pass itself.

**It fired on entropy, not on format.** The rule was `generic-api-key` at
entropy 3.55, not `aws-access-token` — the key was random enough to look like a
secret, and gitleaks never had to recognise it as an AWS key. That is a weaker
guarantee than it first appears: a credential that is structured and *low*
entropy — a short password, a predictable token, a URL with `admin:admin` — is a
different question, and this test does not answer it. Do not present this run as
proof that the hook catches secrets; it is proof that it catches this one.

**`0 commits scanned`.** The hook reads the staged diff, not history — it stops
the next mistake and knows nothing about the previous forty-seven commits.

The CI step does not close that gap either, and an earlier draft of this file
claimed it did. Trivy `fs` scans the *checkout*: every tracked file as it stands
at the commit under test. A credential added and then deleted three commits
later is absent from the checkout and present in history, and nothing in this
pipeline looks there. The only scan of this repository's history is the one the
2026-08-10 security review did by hand across 47 commits, which found nothing —
a result with a date on it, not a standing gate. Tracked in `PLAN.md`.

Also visible: `pre-commit` stashed the unstaged work before running and restored
it afterwards. Expected, but it means a hook failure leaves the tree in a state
worth checking with `git status` rather than assuming.

### The gate, verified — 2026-08-10

A green pipeline proves a gate ran, not that it can fail; those are different
claims and only the second one is worth anything. Tested on
`feature/sprint-3-prove-the-gate`: a generated AWS-shaped key, committed with
`--no-verify`, pushed.

**Gitea run #84 — Failure, 11s.** Red on **Scan the working tree for secrets**,
`exitcode '1'`. The branch was deleted afterwards; the run remains.

```
trivy 0.72.0: scanning 91 tracked files for secrets
...
leak.py (secrets)
Total: 1 (UNKNOWN: 0, LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 1)
CRITICAL: AWS (aws-access-key-id)
 leak.py:1 (offset: 7 bytes)
 1 [ KEY = "********************"
```

`scanning 91 tracked files` is the line that matters as much as the finding: it
is the guard against a scan that silently receives nothing, and 91 is the
tracked tree rather than a zero the step would have failed on.

**The two checks disagreed about what they had found, and that is worth
keeping.** gitleaks matched this same shape of key as `generic-api-key` on
entropy 3.55; Trivy matched it as `aws-access-key-id`, CRITICAL, on format. The
hook is guessing from randomness, the gate is recognising a credential type.
Neither is a copy of the other, so the earlier note in `ci.yml` about wanting
"one scanner rather than two" describes the choice not to add a *second CI*
scanner — it does not mean the local and CI checks enforce the same rules. They
do not, and a secret that is structured but low-entropy is the case where that
gap shows.

Two lines of noise in the log are expected and not findings: a `WARN` that
`site-packages` could not be found, so license detection was skipped, and
`requirements.txt` listed with `-` under Secrets, meaning it was analysed as a
pip manifest rather than secret-scanned as text.

`deploy` did not start, and that proves nothing here: on a `feature/**` branch
the ref gate skips it anyway, exactly as it did in the green run #83. Two
mechanisms would have produced the same empty box and this run cannot separate
them.

The `--no-verify` is the point of the test rather than a way around it. One word
disables the hook, and CI stopped the commit anyway — which is the argument the
hook's own config file makes, demonstrated instead of asserted. If one sentence
has to defend having both checks, it is this run.

**The first attempt produced no run at all**, and that is the more useful half.
The branch was named `throwaway/prove-the-gate`, and the `on: push` filter in
`ci.yml` lists only `main`, `release/**`, `feature/**` and `hotfix/**`. The push
succeeded, Gitea reported nothing, and Actions stayed silent — a pipeline that
does not run is indistinguishable from a pipeline with nothing to complain
about. The filter is deliberate and the comment above it says so; the trap is
that its failure mode is silence. Check that a run *exists* before reading
anything into its colour.

---

# Archive — Docker-host era (until 2026-09-21)

Ansible deployed one container to the Docker host on the laptop
([ADR-0003](adr/0003-deploy-and-verify-strategy.md)). Superseded by Helm on k3s
([ADR-0009](adr/0009-helm-replaces-ansible-for-deployment.md)). Kept because the
rehearsal results below (the ~37 s outage window, three runs) are the
internship-era baseline; the commands no longer apply to the current setup.

## A deploy failed (Ansible, Docker host)

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

**Quote the outage window, not the recovery time.** The role replaces the
running container *before* it verifies the new one, so the broken image served
500s for the whole 27 seconds the smoke test took to give up. The smoke test
bounds downtime; it cannot prevent it.

> **Superseded figure.** The current number to quote is **~37s**, from the
> 2026-08-11 run below — not the ~34s this section measured. The reasoning is
> unchanged; only the measurement moved.

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

### Repeats — 2026-08-04 and 2026-08-11

The drill is a script precisely so it can be re-run rather than believed, so it
has been. Three runs across eleven days:

| Run | Target SHA | Detect | Roll back | Outage | Transcript |
|---|---|---|---|:--:|---|
| 2026-07-31 | `fbc1254e…` | 27s | 7s | ~34s | commit `eac8fe5`, tabled above |
| 2026-08-04 | `02179047…` | 27s | 7s | ~34s | `rollback-drill-20260804-110322.log` |
| 2026-08-11 | `c916924e…` | 29s | 8s | **~37s** | `rollback-drill-20260811-132122.log` |

**The third run drifted by three seconds and the claim was narrowed rather than
the number rounded.** Two identical runs made "reproducible" look like
"identical", and it is not — this is a laptop under whatever load it happened to
be under, and 27→29 and 7→8 is what that costs. What the repeats actually prove
is that the mechanism works every time and the timing repeats to within a few
seconds. That is the claim now made everywhere, and **~37s** is the figure
quoted: the worst of the three, from the freshest transcript.

The 2026-08-11 run also re-proved the recovery on the current commit — it ended
with `now running c916924e…` and `sprint goal MET — under 60s`, and left the
usual `deadbee` residue behind.

The caveat from the first run still stands and is printed by the script itself:
the rollback pulls with `pull=not_present` and the previous image was already on
the host, so these times exclude a registry pull. On a fresh host, add it.
