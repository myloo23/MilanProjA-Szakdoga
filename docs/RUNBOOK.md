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
