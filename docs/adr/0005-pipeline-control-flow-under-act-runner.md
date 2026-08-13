# ADR-0005: Pipeline control flow, bounded by what `act_runner` actually does

## Status

Accepted — 2026-08-05

## Context

In the Sprint 2 review, the mentor asked for five pipeline control-flow
mechanisms: conditional stage and job execution, `timeout-minutes`, "if a stage
fails, carry on", retry on flaky steps, and dynamic fan-out to N parallel jobs.
He added two things that shaped how this was answered. The point is to *try* the
mechanisms rather than to need them — and it does not matter if the tool cannot
do them, as long as you know what you would reach for.

That second half matters here, because this pipeline does not run on GitHub's
hosted runners. It runs on `act_runner`, a reimplementation, and this repository
already carries one unverified assumption about it: `ci.yml`'s ref gate is a
POSIX shell `case` rather than `startsWith()`, on the stated grounds that
expression support "is not something to bet a release gate on." That was written
without testing.

Building all five and finding out mid-sprint which ones are fiction is the
expensive order to do this in. Worse, one of the five fails *silently* — a
detail that only shows up if you look for it.

## Decision

**Spike before planning.** One throwaway workflow,
`.gitea/workflows/spike-act-runner.yml`, on a `spike/**` branch — a namespace
`ci.yml` does not trigger on, so the probe had the capacity-1 runner to itself
and could not build, push or deploy anything. Two runs, 2026-08-05,
`act_runner` **v0.2.12**, `RUNNER_ARCH=ARM64`, image
`docker.gitea.com/runner-images:ubuntu-latest@sha256:e77e2b1e…`.

Findings, with evidence in
[`../spikes/act-runner-capabilities.md`](../spikes/act-runner-capabilities.md):

| Construct | Result |
|---|:--:|
| `if:` with `startsWith()`, `contains()`, `success()`, `always()` | works |
| `timeout-minutes` on a step | works — killed at 1m04s against a 180s sleep |
| `continue-on-error` on a step | works — job green, later steps ran |
| Retry via shell loop | works |
| Retry via `nick-fields/retry@v3` | works — the runner clones actions from github.com |
| Static `strategy.matrix` | works — expanded into three jobs |
| `strategy.matrix` from `fromJSON()` | **does not work** |

**Expressions in a `strategy:` block are not evaluated.** The dynamic matrix ran
as a single job with `matrix.shard` resolving to the empty string. The isolating
probe was a `fromJSON()` over a *literal* string with no `needs:` and no job
outputs involved — it failed identically, while the static matrix beside it
expanded correctly. So the fault is expression evaluation inside `strategy:`,
not `fromJSON()` and not job outputs, which `ci.yml`'s `deploy` job has consumed
in production since `fbc1254`.

**Dynamic fan-out is therefore documented, not built.** Two independent reasons,
and the second would hold even if v0.2.12 gained the feature tomorrow: this
runner has `capacity: 1` (`platform/config.yaml`), so matrix jobs serialise, and
this pipeline has one image and one deploy target — nothing to fan out over.

**`timeout-minutes` goes into `ci.yml` this sprint.** It is the only one of the
five with a real problem behind it. Nothing currently bounds the Trivy download,
the container health wait or the Ansible deploy, and on a capacity-1 runner a
hung step is not a slow build — it is the whole pipeline stopped until a human
notices. Per step, with a value argued from what that step actually does, not
one blanket number at the top of the file.

**`continue-on-error` is proven available and stays unused.** §6 of
[`PLAN.md`](../PLAN.md) says gates fail and never warn, and that rule is
load-bearing: every check in this pipeline can fail the build, which is most of
what makes it worth demonstrating. Availability is not permission. If a step
ever gets this treatment, the argument goes in the same commit.

**Retry stays available and unused for now.** The candidates are the steps that
fail for reasons unrelated to the change — registry pulls, the Galaxy collection
install, the Trivy DB fetch. None has failed yet. Adding retry before a flake
exists hides the first one instead of surfacing it.

**A second workflow file beats another condition when the file stops explaining
itself.** The mentor's warning was that developers pile `if`/`else`/`and` into
one file until nobody can say why a stage was skipped, and at that point two
plain files are the simpler artefact. The threshold adopted here: when a
condition's *purpose* can no longer be stated in the step name, or when two sets
of steps share a file but never run together, split the file. This spike is the
first instance — a workflow whose failures are expected had no business sharing
`ci.yml` with the gate that ships releases.

**The `ref_gate` comment gets corrected.** Expressions work. The gate stays a
POSIX `case`: it works, and the reason the ref is passed through `env:` rather
than `${{ }}` interpolation is injection safety, which is unaffected by whether
expressions evaluate. The code is right and the stated reason is wrong, so the
reason changes.

## Consequences

**Good.** Four of five mechanisms are known-good on the real runner rather than
assumed from GitHub's documentation, and the fifth has a precise cause rather
than a shrug. One documented assumption in `ci.yml` is now tested, and it was
wrong. `timeout-minutes` closes a genuine gap that predates the mentor's
request.

**Bad.** Dynamic fan-out cannot be demonstrated on this stack. If it is a
requirement rather than a suggestion, it needs GitHub-hosted runners — which
would mean giving up the self-hosted execution model of
[ADR-0001](0001-self-hosted-gitea-actions.md) for one feature this project has
no use for. Not worth it.

**The failure mode is the finding worth repeating.** The dynamic matrix did not
error. It reported success, ran once, and printed an empty shard name. A
pipeline feature that silently does nothing while showing a green tick is worse
than one that fails, because nothing prompts you to look. That is the argument
for probing a runner rather than trusting that a construct copied from the
GitHub docs does what the docs say.

**Version-bound.** Every result above is v0.2.12 on ARM64. Re-run the probe
after a runner upgrade before relying on any of it — the workflow is deleted,
but it is recoverable from the `spike/act-runner-capabilities` history.
