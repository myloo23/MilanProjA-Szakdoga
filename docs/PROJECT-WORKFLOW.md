# Project A — Delivery Workflow

**Owner:** Milán Takács · **Role split simulated:** Tech Lead + DevOps Engineer + Scrum Master
**Cadence:** 1-week sprints × 3 + hardening week · **Sprint review = the mandated weekly mentor demo**

---

## 0. The GitHub/Gitea question — resolve this first

The brief requires self-hosted CI (Gitea Actions). You're asking about GitHub. These are not in conflict, but you must be deliberate:

**Recommended: GitHub is the system of record, Gitea is the execution environment.**

| Concern | Lives in | Why |
|---|---|---|
| Code, history, PRs, reviews | **GitHub** (`origin`) | Portfolio visibility, GitHub Projects is a far better Kanban than Gitea's, recruiters and TCS mentors can see it |
| Issues, milestones, board | **GitHub** | Same |
| Pipeline execution | **Gitea Actions** (`gitea` remote) | Brief requires self-hosted CI; runs on your laptop next to the Docker host |
| Docs, ADRs | **GitHub** (rendered) | Mermaid + Markdown render natively |

Wire it with a `push` mirror: GitHub Actions job (or a `git push --mirror` in a post-merge hook) replicates `main` to your local Gitea. Workflow files are Actions-syntax-compatible, so `.gitea/workflows/` and `.github/workflows/` share ~90% of their content.

**Document this as ADR-001.** "Why two forges" is exactly the kind of question a mentor will ask, and having a written answer is the whole point.

*If your mentor rules that everything must be self-hosted:* keep Gitea only, use Gitea's built-in Projects/Issues/Milestones, and mirror **out** to a public GitHub repo at the end for portfolio purposes. The board structure below maps 1:1.

---

## 1. Repository structure — one repo

**Recommendation: mono-repo. Do not split.**

The instinct that "professional = many repos" is wrong here, and being able to explain *why* is a stronger signal than the split itself.

**Why one repo:**
- **One deployable unit.** Polyrepo pays off when independent teams release on independent cadences. You have one app, one pipeline, one environment, one person. Splitting buys you nothing and costs you cross-repo version coordination.
- **Atomic changes.** Adding a metric touches the app, the Dockerfile, the Prometheus scrape config and the dashboard JSON. In a mono-repo that's one PR, one review, one revert. Across four repos it's four PRs with an implicit ordering — and a broken `main` if you merge them out of order.
- **The pipeline can test what it deploys.** A CD workflow that consumes an Ansible role from another repo must pin a version of it. Now you're doing release management on your own infrastructure code, during a 4-week internship.
- **Reproducibility.** `git clone && make up` is the strongest demo opener you have. It only works if there's one clone.

**When you *would* split** (say this out loud in the demo, it shows judgment):
- The Ansible roles become shared across multiple projects → extract to a role repo, consume via `requirements.yml`.
- The platform stack (Gitea, Prometheus, Grafana, Loki) is shared infrastructure serving many apps → that's a genuine boundary; infra has a different lifecycle and different owners than app code.
- Compliance requires separate access control on infrastructure vs. application code.

None of those are true today. **Revisit at the boundary, not before.**

### Layout

```
projecta-cicd/
├── .github/
│   ├── workflows/            # ci.yml, cd.yml (mirrored to .gitea/)
│   ├── ISSUE_TEMPLATE/       # user_story.yml, task.yml, bug.yml, spike.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── CODEOWNERS
│   └── dependabot.yml
├── .gitea/workflows/         # self-hosted execution
├── app/
│   ├── src/                  # Flask app, logging, metrics
│   ├── tests/                # pytest
│   ├── Dockerfile
│   ├── gunicorn.conf.py
│   └── pyproject.toml
├── ansible/
│   ├── inventory/            # hosts.yml, group_vars/
│   ├── roles/deploy_app/
│   └── playbooks/            # deploy.yml, rollback.yml
├── platform/
│   ├── compose.yaml          # gitea, runner, registry, prom, grafana, loki, alloy, cadvisor
│   ├── prometheus/           # scrape configs, alert rules
│   ├── grafana/provisioning/ # datasources + dashboards as JSON
│   └── alloy/
├── docs/
│   ├── adr/                  # 001-two-forges.md, 002-registry-vs-local-build.md, ...
│   ├── RUNBOOK.md
│   ├── ARCHITECTURE.md       # Mermaid
│   ├── DEMO.md
│   └── PROGRESS.md           # weekly log
├── scripts/                  # load-gen.sh, reset.sh
├── Makefile
├── CHANGELOG.md
└── README.md
```

**Directory ownership via CODEOWNERS** — even solo. It documents boundaries and makes the mono-repo's internal structure explicit.

---

## 2. Board structure

**GitHub Projects (v2), board view.** One project, named `Project A — CI/CD Pipeline`.

### Columns

| Column | WIP limit | Entry criteria |
|---|---|---|
| **Backlog** | — | Written as a user story or task, but not yet estimated |
| **Ready** | 10 | Estimated, acceptance criteria written, dependencies unblocked. *Only pull from here.* |
| **In Progress** | **2** | Branch created, actively worked |
| **In Review** | 3 | PR open, CI green, self-review comment posted |
| **Blocked** | — | Has a `blocked` label and a comment naming the blocker + who can unblock |
| **Done** | — | Merged, deployed, acceptance criteria verified |

**The WIP limit of 2 is the single most important rule on this board.** Interns fail by having eight things 80% done on demo day. Two in flight, maximum.

Do **not** create per-sprint columns (`Sprint 1`, `Sprint 2`...). That's a common mistake — it conflates *when* with *what state*. Sprint is a **field** (iteration), status is the **column**. Use the built-in `Iteration` field and filter the board by current sprint. This gives you a real burndown; per-sprint columns give you nothing.

### Custom fields
- `Iteration` — Sprint 1 / 2 / 3 / Hardening (built-in iteration field, 1-week duration)
- `Estimate` — story points, Fibonacci (1, 2, 3, 5, 8). Anything at 8 must be split.
- `Priority` — P0 / P1 / P2 (mirrors the execution plan)
- `Type` — Story / Task / Bug / Spike / Chore
- `Risk` — flag items with unknown unknowns; these get timeboxed

### Views to create
1. **Board** — grouped by Status, filtered to current iteration.
2. **Sprint backlog** — table, grouped by Iteration, shows point totals.
3. **Roadmap** — timeline view by Milestone. This is your mentor-facing view.
4. **Blocked & at risk** — filter `label:blocked OR Risk:High`. Check daily.

---

## 3. Issues and milestones

### Milestones (map to deliverable outcomes, not to sprints)

| Milestone | Definition of complete |
|---|---|
| **M1 — Pipeline Foundation** | A commit triggers lint, test, build, scan, push of an immutably-tagged image |
| **M2 — Automated Delivery** | Merge to `main` deploys that exact image via Ansible, with a smoke test that can fail the deploy |
| **M3 — Observability** | Metric spike → one-click pivot to the matching logs, dashboards provisioned as code |
| **M4 — Production Readiness** | Rollback rehearsed, ADRs written, clean-machine reproducible, demo scripted |

Milestones ≠ sprints deliberately. Sprints are time; milestones are outcomes. Work slips between sprints — milestones let you see whether the *outcome* is still on track.

### Issue hierarchy

Three levels: **Epic → Story → Task.** Use GitHub's sub-issues to nest them.

```
EPIC: Continuous Deployment                          [M2]
 └─ STORY: As a DevOps engineer, I want merges to main to deploy
           automatically, so releases require no manual steps.   [5 pts]
     ├─ TASK: Write deploy_app Ansible role                      [3]
     ├─ TASK: Add post-deploy smoke test with retries            [2]
     ├─ TASK: Wire cd.yml to pass CI image SHA as app_version    [2]
     └─ TASK: Verify idempotence — second run reports changed=0  [1]
```

**Stories carry the acceptance criteria. Tasks carry the work.** Only stories get demoed.

### Labels

Four namespaces, colour-coded:
- `type:` story, task, bug, spike, chore, docs
- `area:` app, ci, cd, ansible, observability, security, docs
- `priority:` p0, p1, p2
- `status:` blocked, needs-decision, good-first-look

### Issue template requirements

Every story needs, enforced by template:
- User story sentence (`As a… I want… so that…`)
- Acceptance criteria as a checklist — **written before work starts**
- Definition of Done reference
- Demo notes: *how will I show this works?*

That last field is the one people skip and the one that saves you. If you can't describe the demo, the story isn't ready.

### Definition of Done (pin this to the project README)

- [ ] Acceptance criteria met and verified manually
- [ ] Code + config committed, no secrets in history
- [ ] CI green (lint, test, coverage gate, image scan)
- [ ] Peer or self-review completed with written reasoning
- [ ] Documentation updated (README / ADR / runbook as applicable)
- [ ] Change is reproducible from a clean clone
- [ ] Demoable in under 2 minutes

---

## 4. Sprint plan

Sprint boundaries align to the mandated weekly mentor demo — **your sprint review is already scheduled for you.** Capacity assumption: ~15–20 points/week for a full-time intern; ~8–10 if part-time alongside university. Calibrate after Sprint 1 and don't over-commit in Sprint 2.

---

### Sprint 1 — "Commit to Artifact"  ·  Milestone M1

**Sprint goal:** *A push to any branch produces a tested, scanned, uniquely-tagged Docker image in a local registry — with zero manual steps.*

**Scope**
- Platform stack up via compose (Gitea, act_runner, registry)
- App hardening: JSON structured logging, `/echo` 400 handling, `prometheus_client` `/metrics`, Gunicorn, `/health` + `/ready`
- pytest suite + coverage gate + ruff
- Multi-stage Dockerfile, non-root, digest-pinned base
- `ci.yml`: lint → test → build → trivy → push, tagged by git SHA
- ADR-001 (two forges), ADR-002 (registry vs. same-host build)

**Sprint review demo (10 min)**
1. Push a commit live on a branch → pipeline runs in front of the mentor.
2. Show the failure path first: push code that breaks a test, watch CI go red. **Demoing the gate is more convincing than demoing the happy path.**
3. Fix, push, green.
4. `docker images` — show the SHA tag, show the image is < 150 MB and runs as non-root.
5. Show the trivy report.

**Risks:** admin rights, corporate proxy, Docker socket access for the runner. All three are Sprint 1 blockers — raise them on day 1, not day 4.

---

### Sprint 2 — "Artifact to Running Container"  ·  Milestone M2

**Sprint goal:** *A merge to `main` deploys the exact image CI built, verifies it's healthy, and can be rolled back in under a minute.*

**Scope**
- Ansible `deploy_app` role: pull by tag, run container, resource limits, restart policy
- Inventory + `group_vars`, secrets via ansible-vault
- Post-deploy smoke test (`uri` module, retries) that fails the play
- `cd.yml` on `main`, passing `app_version` from CI — **no rebuild**
- `rollback.yml` + rehearsal
- `ansible-lint`, `hadolint` added to CI
- Branch protection on `main` enabled
- ADR-003 (Ansible over shell), ADR-004 (immutable tags, no `latest`)

**Sprint review demo (10 min)**
1. Open a PR → show required checks blocking merge.
2. Merge → CD runs → new container live, smoke test passes.
3. `curl /version` — the running SHA matches the merge commit. This is the traceability money shot.
4. **Run the deploy playbook a second time → `changed=0`.** Idempotence, demonstrated not claimed.
5. Deliberately deploy a broken image → smoke test fails the deploy → roll back to the previous SHA in one command.

**Risks:** the `localhost:5000` resolution trap between runner and Docker daemon. Budget a half-day.

---

### Sprint 3 — "See What's Happening"  ·  Milestone M3

**Sprint goal:** *When the app misbehaves, I can spot it on a dashboard and reach the responsible log line in one click.*

**Scope**
- Prometheus scraping app, cAdvisor, node_exporter; scrape config + alert rules in Git
- Grafana provisioned as code: datasources + two dashboards as committed JSON
  - App Golden Signals (RED): rate, error %, p50/p95/p99 latency
  - Platform (USE): container CPU/mem/restarts, host load
- Alloy → Loki, JSON parsing so `level` and `path` are queryable
- Grafana data link: error-rate panel → pre-filtered Loki query
- One alert rule: error rate > 5% for 2m
- `scripts/load-gen.sh` + `make demo-incident`
- ADR-005 (Loki over ELK), ADR-006 (metric cardinality policy)

**Sprint review demo (10 min)** — run the incident scenario from the brief, end to end:
1. `make demo-incident` fires a burst of good and malformed requests at `/echo`.
2. Error rate spikes on the Golden Signals dashboard; the alert fires.
3. Click the data link → Loki, filtered to `level=ERROR` and `path=/echo`.
4. Read out the exact failing payload and its `request_id`.
5. Close with: "no SSH, no grep, 40 seconds from symptom to root cause."

Then explain why `request_id` is a log field and not a Prometheus label. That one sentence about cardinality is worth more than another dashboard.

---

### Hardening week — Milestone M4

Not a sprint; a stabilisation window. **Do not plan new features here.**

- Remaining ADRs, `RUNBOOK.md`, `ARCHITECTURE.md` (Mermaid), `CHANGELOG.md`
- Clean-machine test: wipe volumes, `git clone && make up`, time it, fix what breaks
- `docs/DEMO.md` — exact click-path for the final presentation
- Rehearse the full demo twice, timed, on a cold machine
- Retrospective written up in `docs/PROGRESS.md`

---

## 5. Branching, commits, PRs

### Branching — trunk-based, short-lived branches

```
main (protected, always deployable)
 └── feat/cd-ansible-role      ← lives < 2 days
 └── fix/echo-invalid-json
 └── docs/adr-registry-choice
```

**Not GitFlow.** GitFlow's `develop` + `release/*` + `hotfix/*` exists to coordinate multiple teams shipping versioned releases on separate cadences. You have one person and continuous deployment to one environment. GitFlow here is cargo-culting, and a good interviewer will spot it. Trunk-based development is the modern default and the correct answer for a CD pipeline — *be ready to explain that trade-off, because you will be asked.*

Branch naming: `<type>/<short-kebab-description>`, optionally `<type>/<issue#>-<desc>`.

**Rules**
- Branch from `main`, rebase onto `main` before opening a PR.
- Delete after merge (enable auto-delete).
- Nothing lives longer than ~2 days. Long branches mean the story was too big.

**Tags:** `v0.1.0`, `v0.2.0` at each milestone. Annotated, not lightweight. Tag pushes can trigger a release workflow later.

### Commits — Conventional Commits

```
<type>(<scope>): <imperative summary under 72 chars>

<why, not what — the diff already shows what>

Refs: #42
```

Types: `feat`, `fix`, `docs`, `ci`, `build`, `refactor`, `test`, `chore`, `perf`
Scopes: `app`, `ci`, `cd`, `ansible`, `docker`, `obs`, `docs`

```
feat(cd): deploy image by git SHA instead of latest

Pinning to the CI-produced SHA makes deploys reproducible and
enables single-command rollback. `latest` gave no way to know
what was actually running.

Refs: #23
```

Enforce with `commitlint` + Husky, or a CI check on PR titles. This buys you auto-generated changelogs and makes `git log` a readable project narrative — which mentors *will* scroll through.

### Pull requests — yes, even solo

Working solo is not a reason to push to `main`. The PR is where your reasoning gets recorded, and reviewable reasoning is the entire senior signal.

**Branch protection on `main`:**
- Require PR before merge
- Require status checks: `lint`, `test`, `coverage`, `hadolint`, `ansible-lint`, `trivy`
- Require branches up to date before merging
- Require conversation resolution
- No force push, no deletion
- Linear history (squash merge only)

**Squash merge**, always. One story = one commit on `main` = one clean revert.

**PR template must include:** what changed and why, linked issue (`Closes #42`), how it was tested, screenshot/log evidence, risk + rollback plan, docs updated checkbox.

**Self-review discipline:** before requesting review, read your own diff in the GitHub UI and leave at least one comment explaining a non-obvious decision. This catches roughly a third of your own mistakes and leaves a visible trail of your thinking. Ask a mentor or a fellow intern for a real review on the two or three architecturally significant PRs.

---

## 6. Documentation to maintain

**Living — updated as you work, not at the end:**

| Doc | Purpose | Update trigger |
|---|---|---|
| `README.md` | What / quickstart / how to deploy / how to roll back. Two screens max. | Any interface change |
| `docs/adr/*.md` | One decision each: context, options, decision, consequences | **When you decide, same day** |
| `docs/RUNBOOK.md` | Deploy, rollback, alert meanings, dashboard guide, common failures | Every operational change |
| `docs/ARCHITECTURE.md` | Mermaid diagram + component responsibilities + data flow | Any new component |
| `CHANGELOG.md` | Keep-a-Changelog format, generated from conventional commits | Each milestone tag |
| `docs/PROGRESS.md` | Weekly: done / next / blockers / decisions / lessons | Every Friday |
| `docs/DEMO.md` | Scripted click-path with expected output at each step | Before each review |

**ADRs are the highest-leverage thing on this list.** The brief explicitly requires you to explain your configuration. Six short ADRs written as you go are a better answer than any amount of retroactive documentation — and they make the final report a compilation exercise rather than a writing marathon.

**Anti-pattern to avoid:** documenting at the end. You will not remember why you chose Loki over ELK in week 4. Write it in week 1, in five sentences.

**Final deliverable** (PDF/Word per the brief) is assembled *from* these files, not written separately. Pandoc the Markdown.

---

## 7. First actions

1. Confirm the GitHub/Gitea arrangement with your mentor — this decision gates the repo setup.
2. Create the repo, push the skeleton, enable branch protection before the first real commit.
3. Create the Project, the four milestones, the labels, the issue templates.
4. Write the four epics and break Sprint 1 into stories with acceptance criteria.
5. Raise the three Sprint 1 blockers (admin rights, proxy, Docker socket) with your mentor **on day 1**.
6. Write ADR-001 before writing any code. It sets the habit.
