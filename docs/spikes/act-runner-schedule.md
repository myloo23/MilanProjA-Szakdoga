# Spike plan — does a scheduled workflow run here?

⬜ **Not run, with one exception recorded under "Observed by accident" below.**
This is the method and the decision tree, written while the question was fresh
so that running it later costs ten minutes instead of an hour. The predictions
near the end are predictions, labelled as such, and they are not evidence — the
sibling document [`act-runner-capabilities.md`](act-runner-capabilities.md) is
what a finding looks like in this repository, and the difference between the two
is deliberate.

**Question.** F8 in [the security review](../security-review-2026-08-10.md)
wants a workflow that re-runs the existing Trivy scan against the image on
`main` on a timer, so that a CVE published against an idle branch turns the
pipeline red without waiting for someone to push. That is four lines of YAML if
`schedule:` works and a different design entirely if it does not.

**Why it is a spike and not a task.**
[ADR-0005](../adr/0005-pipeline-control-flow-under-act-runner.md) exists because
this repository once carried an unverified assumption about `act_runner` — that
`startsWith()` could not be trusted — and the assumption turned out to be wrong.
The lesson was not "expressions work". It was that assuming a capability carries
over from a subsystem you *did* test is how the first mistake happened. Cron is
a different subsystem.

## The reframing that decides the method

**`act_runner` does not schedule anything.** It polls Gitea for jobs and runs
them. Cron parsing, registration and firing all happen server-side, in Gitea. So
this is a Gitea 1.27.0 question wearing an `act_runner` label, and it inherits
Gitea's constraint rather than the runner's.

That matters because Gitea follows GitHub here: **a scheduled workflow is only
registered from the repository's default branch.** If that holds, two things
follow, and both are more interesting than the yes/no answer:

1. A `spike/**` branch cannot test the mechanism at all. A silent absence of
   runs would be indistinguishable from cron being unsupported, and this project
   has already been bitten once by a check that could not fail.
2. F8's rescan workflow does not start working when it is merged to
   `release/sprint3`. It starts working when the sprint reaches `main` — which
   is exactly the branch whose image it is meant to be re-scanning, so the
   constraint is convenient rather than costly. It is still a thing to know
   rather than to discover.

## Method

Two probes, in this order, because the second is only interpretable once the
first has established that the mechanism works at all.

**Probe 1 — a throwaway repository on the local Gitea.** Its default branch is
ours to choose, so a scheduled workflow can sit there without touching `main` in
this repository. Rule 1 says never commit directly to `main`, and `BRANCHING.md`
additionally needs Gitea's `main` to stay fast-forwardable from GitHub's —
pushing a spike commit there would break both for a throwaway test. A separate
repository costs one minute and breaks neither.

Two workflow files rather than one, so an unsupported syntax in either fails
alone instead of taking the other with it:

- `cron-standard.yml` — POSIX five-field cron, `*/2 * * * *`. The form GitHub
  accepts and the one F8 would use.
- `cron-every.yml` — Gitea's `@every 3m`, supported by the cron library Gitea
  embeds and not by GitHub. If it works and the standard form does not, F8 is
  buildable but not portable, which is worth writing down rather than
  discovering during a migration that never happens.

Both also carry `workflow_dispatch`. That is the sanity check: if the manual
trigger does not run either, the finding is "the scratch repository has no
runner", not "cron is unsupported", and the whole probe is void.

**Probe 2 — this repository, on a `spike/**` branch.** The same standard-cron
workflow on a non-default branch, expected to produce nothing. Its job is to
turn the default-branch constraint from something read in someone else's
documentation into something observed here.

**The probe workflow is kept in this document rather than in
`.gitea/workflows/`.** A file with a `schedule:` trigger sitting in the tree is
one merge away from firing on its own, against a runner with capacity 1, for a
question nobody is asking that week. Write it when the spike is run and delete
it with the branch.

<details>
<summary><code>.gitea/workflows/spike-schedule.yml</code> — probe 2</summary>

Note the absence of `workflow_dispatch`. A manual trigger would give this file a
way to produce a green run, and a green run here proves nothing about cron while
looking exactly like proof. The only signal it can emit is a run that appeared
without anyone asking for one.

```yaml
name: spike-schedule

on:
  schedule:
    - cron: '*/2 * * * *'

jobs:
  tick:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - name: Say when this ran, and what Gitea thinks triggered it
        run: |
          date -u +'fired at %Y-%m-%dT%H:%M:%SZ'
          echo "event=${{ github.event_name }} ref=${{ github.ref }}"
```

</details>

## Running it

⚠️ **The scratch repository fires every two minutes and this runner has capacity
1.** While it exists it competes with the real pipeline for the only runner
there is. Deleting it is a step in the procedure, not tidying afterwards.

Create the repository at `localhost:3000` → **+** → **New Repository**, named
`spike-schedule`, default branch `main`, no README. Then:

```bash
mkdir -p /tmp/spike-schedule/.gitea/workflows && cd /tmp/spike-schedule

cat > .gitea/workflows/cron-standard.yml <<'EOF'
name: cron-standard
on:
  schedule:
    - cron: '*/2 * * * *'
  workflow_dispatch:
jobs:
  tick:
    runs-on: ubuntu-latest
    steps:
      - name: Say when and why it ran
        run: |
          date -u +'fired at %Y-%m-%dT%H:%M:%SZ'
          echo "event=${{ github.event_name }} ref=${{ github.ref }}"
EOF

sed -e 's/cron-standard/cron-every/' \
    -e "s|- cron: '\*/2 \* \* \* \*'|- cron: '@every 3m'|" \
    .gitea/workflows/cron-standard.yml > .gitea/workflows/cron-every.yml

git init -b main && git add -A && git commit -m "spike: does Gitea schedule anything"
git remote add origin http://localhost:3000/milan/spike-schedule.git
git push -u origin main
```

Fire `workflow_dispatch` by hand first. If that does not run, stop and fix the
runner before reading anything into the cron result. Then wait ten minutes.

Cleanup: delete `spike-schedule` in the Gitea UI (Settings → Danger Zone), and
`git push gitea --delete spike/act-runner-schedule` if probe 2 was pushed.

## What to record

Gitea version, `act_runner` version and runner image alongside every row — a
finding is only good for the versions that produced it.

| # | Probe | Question |
|---|---|---|
| 1 | Scratch repo | `workflow_dispatch` runs at all — the sanity check |
| 2 | Scratch repo | `*/2 * * * *` fires unattended |
| 3 | Scratch repo | `@every 3m` fires unattended |
| 4 | Scratch repo | Firing interval matches the spec, within a tick |
| 5 | Scratch repo | `github.event_name` on a scheduled run |
| 6 | This repo | A `spike/**` branch produces no scheduled run |
| 7 | Both | Where a registered schedule is visible in the UI |

## What each result decides

**If probe 2 fires.** F8 is four lines of YAML and one decision: put the rescan
in its own workflow file rather than as a third job in `ci.yml`, because a
scheduled run has no artifact to deploy and joining it to `needs:` would either
skip it or deploy on a timer. It lands on `release/sprint3` like any other
change and begins firing at the sprint merge, for the default-branch reason
above. Say that in the pull request, or the first person to look for it will
conclude it is broken.

**If only probe 3 fires.** Same workflow, Gitea-specific syntax, and a comment
saying so. The pipeline is already tied to this forge by ADR-0004, so the cost
is a line of documentation rather than real lock-in.

**If neither fires.** F8 closes as a documented limitation, which is the outcome
the mentor already accepted for workstream B. The fallback worth naming rather
than building: `launchd` on this laptop calling Gitea's API to dispatch the
workflow, which moves the schedule off the forge and onto the host — and is
honest about the fact that a laptop that is asleep scans nothing. Say that in
the limitation rather than implying parity.

**If probe 1 does not fire.** Nothing else means anything. Fix the runner and
start again.

**If probe 6 fires** — a non-default branch does get scheduled — then the
constraint this method is built around does not hold here, and the reasoning
above needs revisiting rather than the result being filed as a curiosity. Gitea
would be diverging from GitHub, and F8 would need a branch filter it does not
currently have.

## Observed by accident — probe 6, partially

Probe 2 was committed and pushed before the decision was taken not to run this
spike, so the workflow above sat on `spike/act-runner-schedule` — a non-default
branch — for a measured window before being removed. That is probe 6 running
whether or not anyone intended it, and the numbers are exact because they come
from the reflog rather than from memory:

| | |
|---|---|
| Workflow present on Gitea | 2026-08-10 **11:11:50** → **11:25:43** +0200 (13m53s) |
| Schedule | `*/2 * * * *` |
| Firings the spec calls for in that window | **7** (11:12, 11:14 … 11:24) |
| Runs named `spike-schedule` in the Actions list | **0** |
| Versions | Gitea 1.27.0, `act_runner` 0.2.12 |

**This is consistent with the default-branch constraint. It does not
demonstrate it.** Two different worlds predict exactly this observation: one
where Gitea schedules only from the default branch and cron otherwise works, and
one where cron does not work on this deployment at all. Silence cannot tell them
apart, which is the entire reason probe 1 exists and runs in a repository whose
default branch we control. Reading this row as "the constraint is confirmed"
would be the same mistake ADR-0005 was written to correct — a comfortable
explanation adopted because it was the one already in mind.

Two further weaknesses, stated rather than left for someone to find:

- **Absence over fourteen minutes is not absence.** It bounds the delay before a
  first firing at well under the window; it says nothing about a scheduler that
  registers lazily, on a slower tick, or on the next server restart.
- **Nobody checked whether Gitea registered a schedule at all.** The repository's
  cron registration was never looked at, only the Actions list. A registered but
  unfired schedule and an unregistered one are different findings, and this
  observation does not separate them. That is what row 7 in the table above is
  for.

So: row 6 has supporting evidence, rows 1 through 5 and 7 remain ⬜, and the
question this document exists to answer is still open.

## Predictions, which are not results

Written down before running so that being wrong is visible afterwards rather
than quietly reinterpreted. Confidence is roughly 80% on each, which is exactly
why the spike is worth ten minutes: 80% is not a number to put in a pull request
description.

| # | Prediction |
|---|---|
| 1 | `workflow_dispatch` works — Gitea has supported it for several releases |
| 2 | `*/2 * * * *` fires; scheduled workflows landed in Gitea 1.20 and this is 1.27 |
| 3 | `@every 3m` also fires, via the embedded robfig/cron. Least trustworthy of the five |
| 4 | Runs lag their nominal time by up to a tick — a `10:02` run appearing at `10:03` |
| 6 | Silent, confirming the default-branch constraint |

The one that would cost the most to get wrong is 6. If a non-default branch does
schedule, then every `feature/**` branch carrying the rescan workflow would fire
it, and a capacity-1 runner would spend the sprint scanning images instead of
building them.

Prediction 6 survived a fourteen-minute window on 2026-08-10 — see "Observed by
accident" above, and note that surviving is not the same as being confirmed,
because the observation is equally consistent with cron not working here at all.
Left in the table unchanged rather than upgraded, so that what was predicted
before any evidence existed stays legible.
