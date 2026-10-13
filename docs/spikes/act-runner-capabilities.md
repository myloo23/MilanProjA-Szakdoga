# Spike — what `act_runner` actually supports

**Question.** Which of the pipeline control-flow constructs requested in the
Sprint 2 review work on this runner, and which do not?

**Why it is a spike and not a task.** The mentor's request was to *try* these
mechanisms. He also said, in the same message, that it does not matter if the
tool cannot do them — the point is to know what you would reach for. That makes
an unsupported construct a finding rather than a failure, and it is cheaper to
find out in half a day than to plan a sprint around a construct that does not
run here.

This repository already carries one unverified assumption about `act_runner`:
`ci.yml`'s ref gate is a POSIX shell `case` rather than `startsWith()`, on the
stated grounds that expression support "is not something to bet a release gate
on." That was a defensible call at the time and it has never been checked.
Probe 1 checks it.

**Method.** One throwaway workflow, `.gitea/workflows/spike-act-runner.yml`,
on a `spike/**` branch. `ci.yml` triggers on `main`, `release/**`, `feature/**`
and `hotfix/**` only, so a spike branch gets no pipeline run and the probe has
the capacity-1 runner to itself. Nothing in it builds, pushes or deploys.

**The run is expected to be red.** Probe 2 fails on purpose. Read the job
results, not the overall status.

```bash
git checkout release/sprint3
git checkout -b spike/act-runner-capabilities
git push gitea spike/act-runner-capabilities
```

Watch it at `localhost:3000/milan/Milan-ProjectA/actions`. The spike branch is
never pushed to `origin` — there is nothing to review and nothing to merge.

---

## Results — round 1

Run #62 on `spike/act-runner-capabilities`, 2026-08-05, 1m47s total.
Runner `projecta-local-runner` **v0.2.12**, `RUNNER_ARCH=ARM64`,
image `docker.gitea.com/runner-images:ubuntu-latest`
(`sha256:e77e2b1e…`). A finding is only good for the version that produced it.

| # | Construct | Works | Evidence |
|---|---|:--:|---|
| 1 | `startsWith()` in `if:` | ✅ | step ran on `refs/heads/spike/…` |
| 1 | `contains()` in `if:` | ✅ | step ran |
| 1 | Negative condition correctly skipped | ✅ | `startsWith(github.ref,'refs/heads/main')` produced no output |
| 1 | `success()` / `always()` | ✅ | both ran |
| 2 | `timeout-minutes` (step) | ✅ | killed at **1m04s** against a 180s sleep |
| 2 | `timeout-minutes` (job) | — | not exercised; the step bound fired first |
| 3 | `continue-on-error` (step) | ✅ | step exited 1, job conclusion **success**, later step ran |
| 4 | Shell retry loop | ✅ | three attempts, succeeded on the third |
| 4 | `nick-fields/retry@v3` | ✅ | runner cloned it from github.com, `outcome=success` |
| 5 | `fromJSON()` matrix expands | ❌ | **one job, `matrix.shard` empty** — see below |
| 5 | Matrix runs in parallel | ❌ | moot, and independently false: `capacity: 1` |

**Serial execution confirmed.** Job durations sum to 104s against a reported
total of 107s. `platform/config.yaml` line 14 sets `capacity: 1`, and the run
matches it. Nothing here runs concurrently, whatever the syntax says.

### The one that failed, precisely

`emit-matrix` succeeded and the downstream job ran — but it ran **once**, with
an empty shard:

```
expression 'format(…, matrix.shard, matrix.shard)' evaluated to
  'echo "PROBE matrix -> shard= started $(date +%T)" …'
PROBE matrix -> shard= started 12:59:54
PROBE matrix -> shard= ended   13:00:04
```

So `matrix.shard` resolved to the empty string rather than to `alpha`, `beta`
and `gamma`. The job did not fail — it silently degraded to a single unnamed
run, which is the worse failure mode of the two: a green tick on a fan-out that
never fanned out.

**What this does not yet tell us** is *which* part broke. Three candidates, and
the writeup has to name one:

1. matrices do not work at all under v0.2.12
2. `fromJSON()` is not available in a `strategy:` block, though it works elsewhere
3. `needs.<job>.outputs` does not resolve when consumed from `strategy:`

(3) is the least likely — `ci.yml`'s `deploy` job already reads
`needs.build-test-push.outputs.ships` in production and has done since
`fbc1254`. Round 2 separates them rather than guessing.

**Ignore this log line.** It appears in `probe-matrix` *and* in `probe-retry`,
which worked:

```
'runs-on' key not defined in Spike — act_runner capabilities/emit-matrix
No steps found
```

It is how act_runner narrates resolving a `needs:` dependency, not an error.
Worth writing down because it looks exactly like the cause and is not.

**Cosmetic, but note it.** Expression results are logged as
`'%!t(string=refs/heads/spike/act-runner-capabilities)'` — a Go format-verb bug
in act_runner's own logging. The values are correct; only the log is wrong.
Anyone reading these logs for the first time will think something is broken.

### Corrections this forces

`ci.yml`'s `ref_gate` step says expression support under `act_runner` "is not
something to bet a release gate on." **That is now known to be false** for
`startsWith()`, `contains()`, `success()` and `always()`. The gate stays a
POSIX `case` — it works, and the security argument for passing the ref through
`env:` instead of `${{ }}` interpolation is untouched — but the comment gets
rewritten. A stale reason is its own kind of defect, and this one would be
embarrassing to be asked about at review.

Round 1 also refuted a prediction made in this document before the run: that
`nick-fields/retry@v3` was the less likely of the two retry approaches to work,
because the runner might not reach github.com. It cloned the action without
trouble. Recorded rather than deleted, because the prediction was the reason
the probe was written that way.

---

## What each result decides

**1 — expressions.** If they work, the comment in `ci.yml`'s `ref_gate` step is
wrong and gets corrected. The gate itself stays a shell `case`: it works, it is
POSIX, and the security argument for passing the ref through `env:` rather than
`${{ }}` interpolation is unaffected by whether expressions evaluate. Change the
justification, not the code — a stale reason is its own kind of defect.

**2 — `timeout-minutes`.** The only item here with a real problem behind it.
Nothing currently bounds the Trivy download, the health wait or the Ansible
deploy. On a runner with capacity 1 a hung step is not a slow build, it is the
whole pipeline stopped until someone notices. If this works, it goes into
`ci.yml` in Sprint 3 with a value per step rather than one blanket number.

**3 — `continue-on-error`.** Availability is not permission. §6 of `PLAN.md`
says gates fail and never warn, and that rule is load-bearing — every check in
this pipeline can fail the build, which is most of what makes it worth
demonstrating. If a step ever gets this treatment, the argument goes in the same
commit and the exception gets named. Likely honest outcome: proven to work,
deliberately unused, and that sentence is worth more at review than a use of it.

**4 — retry.** Worth having for the steps that fail for reasons unrelated to the
change: registry pulls, the Galaxy collection install, the Trivy DB fetch. If
the third-party action cannot be fetched, the shell loop is the answer and the
inability to pull actions is itself a finding about this runner worth writing
down — it constrains every future workflow, not just this one.

**5 — dynamic fan-out.** Two questions that must not be merged in the writeup:
whether `fromJSON()` builds the matrix, and whether the jobs run in parallel.
The second is already answered — capacity is 1, so three shards serialise
regardless of syntax. This pipeline also has nothing to parallelise: one image,
one deploy target. So the honest framing is a capability demonstrated on a
runner that cannot exploit it, and saying that is stronger than presenting three
serialised jobs as fan-out.

---

## Results — round 2

Run #63, same branch and runner, 2m08s. Three probes, one question: *which*
part of the dynamic matrix broke.

| Job | Jobs produced | Verdict |
|---|:--:|---|
| `probe-matrix-static` — literal list | **3** (alpha, beta, gamma) | matrices work |
| `probe-matrix-fromjson-literal` — `fromJSON()` over a literal, no `needs:` | **1** | expression not evaluated |
| `probe-needs-output` — same output read from an ordinary step | 1, green | outputs resolve fine |

Decisive because the literal case has no `needs:` and no job outputs anywhere
in it. It still collapsed to one job, while the static matrix beside it expanded
correctly.

**Conclusion: `act_runner` v0.2.12 does not evaluate expressions inside a
`strategy:` block.** Not a `fromJSON()` bug, not a job-output bug. Static
matrices work; dynamic ones do not.

Note that this was never *reported* as a failure. Both dynamic-matrix jobs
finished green, having run once with an empty shard name. That is the finding
worth carrying into the review: a control-flow feature that silently does
nothing while showing a tick is worse than one that errors, because nothing
prompts you to check.

---

## Output

Written up as
[ADR-0005](../adr/0005-pipeline-control-flow-under-act-runner.md) — what the
runner supports, what goes into `ci.yml` as a result (`timeout-minutes`, this
sprint), and what is deliberately left out (`continue-on-error` and retry:
available, unused, with the reason stated). Kovalcsik's other point is in it
too: the threshold at which a second workflow file beats another condition in
an existing one. This spike is the first instance of that rule, which shows the
principle more cheaply than asserting it.

The probe workflow is deleted with the branch. The ADR is the artefact; this
document is the evidence behind it; the workflow was scaffolding. It stays
recoverable from `spike/act-runner-capabilities` history if a runner upgrade
makes it worth re-running — every result here is bound to v0.2.12 on ARM64.

## Results — round 3 (2026-09-22): `if: failure()`

One question, asked because `ci.yml`'s rollback stage depends on the answer and
round 1 never asked it.

`.gitea/workflows/spike-if-failure.yml`, branch `spike/if-failure`, run #5,
act_runner v0.2.12, `RUNNER_ARCH=X64`, image
`docker.gitea.com/runner-images:ubuntu-latest`.

| Step | Condition | Ran? |
|---|---|:--:|
| `Fail on purpose` (`exit 1`) | — | yes, failed |
| `Runs only if something failed` | `failure()` | yes — printed `FAILURE-BRANCH-RAN` |
| `Runs only if everything succeeded` | `success()` | no — no output |
| `Runs either way` | `always()` | yes — printed `ALWAYS-BRANCH-RAN` |

The job's final state was failed, which is the other half of what the rollback
stage needs: a step that runs on `failure()` does not reset the job's verdict,
so a successful rollback still leaves the run red.

Worth noting from the log, because it explains what the runner is doing rather
than only what it concluded: the runner prints `evaluating expression
'success()'` before the job starts and `evaluating expression ''` before each
step, so conditions are evaluated one at a time against the accumulated job
status rather than resolved up front.
