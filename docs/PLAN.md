# Project A — Plan

**Owner:** Milán Takács · **Target:** TCS DevOps Internship · **Deploy target:** local Docker host

Roadmap, sprint plan, open work, risks and working conventions. The overview and
current status live in [`../README.md`](../README.md); commands live in
[`DEVELOPMENT.md`](DEVELOPMENT.md).

---

## 1. Design decisions at a glance

| Decision | Choice | Why |
|---|---|---|
| SCM + CI | Gitea + Gitea Actions (`act_runner`) | Light, GitHub-Actions syntax transfers, self-hosted gives a full ownership story ([ADR-0001](adr/0001-self-hosted-gitea-actions.md)) |
| Artifact | Docker image pushed to a local registry (`localhost:5001`) | Build once, deploy an immutable artifact ([ADR-0002](adr/0002-build-once-push-to-registry.md)) |
| Image tag | Git commit SHA. **Never `latest`** | Traceable and rollback-able |
| Deploy | Ansible + `community.docker`, inventory-driven | Idempotent and declarative, with no orchestrator |
| App runtime | Gunicorn, not the Flask dev server | The starter code ships a dev server; production means WSGI plus workers |
| Metrics | `prometheus_client` in-app, plus cAdvisor and node_exporter | Custom app metrics *and* CPU/memory, as the brief requires |
| Logs | JSON to stdout → Alloy → Loki → Grafana | Twelve-factor, and a metric-to-log pivot in one UI |
| Repo shape | One repository — app, pipeline, platform, docs | One deployable unit, atomic cross-cutting changes |

### Why one repository

Polyrepo pays off when independent teams release on independent cadences. This is
one app, one pipeline, one environment, one person — splitting buys nothing and
costs cross-repo version coordination.

Adding a metric touches the app, the Dockerfile, the Prometheus scrape config and a
dashboard JSON. In one repo that is a single pull request, a single review and a
single revert. Across four repos it is four pull requests with an implicit ordering,
and a broken `main` if they merge out of order.

It would be worth splitting when the Ansible roles get shared across projects, when
the platform stack becomes shared infrastructure with a different lifecycle and
different owners, or when compliance requires separate access control on
infrastructure versus application code. None of those is true today.

---

## 2. Roadmap

**Phase 0 — Foundation** ✅
Local prerequisites (Docker, Python 3.12, Ansible), Git repository, branch strategy,
`.gitignore`, `.dockerignore`.
*Exit criteria:* `git push` works to a self-hosted Gitea.

**Phase 1 — Application hardening** 🟡
Make the starter `app.py` production-grade before automating it. Automating a bad
artifact just ships it faster.

- ✅ Explicit `/echo` handling of malformed JSON → `400` plus an `ERROR` log. The
  incident demo depends on this; without it the endpoint returns a 415 or 500 and
  there is no controllable error signal.
- ✅ Split `/health` (liveness) and `/ready` (readiness).
- ✅ Gunicorn entrypoint with `--workers 2 --threads 4`.
- ✅ pytest suite covering the happy path, health, readiness and the invalid-JSON 400.
- ✅ ruff configured for lint and format.
- ⬜ Structured JSON logging (`python-json-logger`) with `request_id`, `method`,
  `path`, `status`, `duration_ms`, `level`.
- ⬜ `/metrics` via `prometheus_client`: `http_requests_total{method,path,status}`
  and an `http_request_duration_seconds` histogram.

**Phase 2 — Containerization** ✅

- Multi-stage Dockerfile; the runtime base is `python:3.12-slim` pinned by digest.
- Non-root `appuser` (UID 10001) and a `HEALTHCHECK` hitting `/health`.
- `.dockerignore` excluding tests, `.git` and the virtualenv.
- ⬜ Remaining: OCI labels (`org.opencontainers.image.revision`, `.source`,
  `.created`, `.version`).

*Exit criteria:* `docker run` serves `/`, `/health`, `/ready` and `/echo` correctly.

**Phase 3 — CI** ✅
Gitea and `act_runner` in compose, runner registered.
`ci.yml` runs on every pull request and on pushes to `main`, fail-fast in cost order:
`lint → tests with coverage gate → build → container smoke test → trivy scan → push`.

- Pip caching keyed on `requirements-dev.txt`.
- Images tagged `localhost:5001/projecta-flask:<git-sha>`.
- ⬜ Remaining: inject build metadata via `--build-arg` and surface it on a
  `/version` endpoint.

*Exit criteria:* a commit on a feature branch produces a green pipeline and a
scanned, uniquely tagged image in the registry. **Met.**

**Phase 4 — CD with Ansible** 🟡 *Current focus*

- ✅ `ansible/` scaffold: `ansible.cfg`, `requirements.yml`, a `local_docker`
  inventory group and `group_vars`, plus `playbooks/ping.yml` proving the socket,
  the collection and the `projecta-platform` network before any deploy logic.
  `docker_host` is inventory-driven, so a remote target costs an inventory edit
  and no role change.
- ✅ `ansible/roles/deploy_app`: pull the image by SHA, run the container
  (`restart_policy: unless-stopped`, memory and CPU limits, `json-file` log driver
  with rotation), then a post-deploy smoke test (`uri` with retries) that fails the
  play. On failure it dumps the last 50 log lines and prints the exact rollback
  command with the previously running SHA already filled in.

  **Not** `recreate: true`, despite an earlier draft of this plan. Forcing
  recreation would report `changed` on every run and make the idempotence demo
  fail by design. `docker_container` compares the running container against the
  spec and recreates only on a real difference — which a new image tag always is.
  So a new SHA redeploys, a re-run reports `changed=0`, and the claim in the
  review demo is true rather than aspirational.
- Inventory with a real `local_docker` host group, variables in `group_vars/`,
  secrets in `ansible-vault` with the vault password coming from a Gitea Actions
  secret.
- ✅ A `deploy` job gated on `needs: build-test-push` and `refs/heads/main`, passing
  `app_version=${{ github.sha }}` — the exact artifact the pipeline just tested,
  scanned and pushed. **No rebuild in CD.** It runs with
  `deploy_app_smoke_vantage=network`, because a job container's `localhost` is
  itself, not the Docker host.
- Rollback path: the same playbook with `app_version=<previous-sha>`. Document and
  rehearse it.

*Exit criteria:* merge to `main` → container running the new SHA, smoke test passed,
zero manual steps.

**Phase 5 — Observability** ⬜

- Prometheus scrapes the app's `/metrics`, cAdvisor (container CPU and memory) and
  node_exporter (host). Scrape config committed.
- Grafana provisioned as code — datasources and two dashboards committed as JSON:
  1. *App Golden Signals*: request rate, error percentage, p50/p95/p99 latency, in-flight.
  2. *Platform*: container CPU, memory and restarts; host load and disk.
- Alloy tails Docker stdout, labels by `container`, `app` and `env`, and parses JSON
  so `level` and `path` become queryable in Loki.
- A Grafana data link from the error-rate panel to the pre-filtered Loki query. That
  one click *is* the metric-to-log pivot.
- One Prometheus alert rule: error rate above 5% for 2 minutes.

*Exit criteria:* the incident walkthrough from the brief runs end to end in under 60
seconds.

**Phase 6 — Hardening, docs, demo** ⬜

- Remaining ADRs for the decisions in section 1.
- `RUNBOOK.md`: how to deploy, how to roll back, what each alert means, how to read
  the dashboards.
- `DEMO.md`: the exact click-path for the final live demo, plus a script that fires
  the bad-request burst.
- Fresh-machine test: clone and bring the stack up from a clean state, timed.

---

## 3. Sprint plan

Sprints are one week and align to the mandated weekly mentor demo — the sprint
review is already scheduled. Milestones are outcomes, sprints are time; work slips
between sprints, and milestones show whether the outcome is still on track.

| Milestone | Definition of complete | Status |
|---|---|:---:|
| **M1 — Pipeline Foundation** | A commit triggers lint, test, build, scan and push of an immutably tagged image | ✅ |
| **M2 — Automated Delivery** | Merge to `main` deploys that exact image via Ansible, with a smoke test that can fail the deploy | 🟡 |
| **M3 — Observability** | Metric spike → one-click pivot to the matching logs; dashboards provisioned as code | ⬜ |
| **M4 — Production Readiness** | Rollback rehearsed, ADRs written, clean-machine reproducible, demo scripted | ⬜ |

### Sprint 1 — "Commit to Artifact" · M1 ✅

*Goal: a push to any branch produces a tested, scanned, uniquely tagged Docker image
in a local registry, with zero manual steps.*

Delivered: platform stack via compose; `/echo` 400 handling; `/health` and `/ready`;
Gunicorn; pytest with a coverage gate; ruff; multi-stage non-root digest-pinned
Dockerfile; `ci.yml` through to the registry push; ADR-0001 and ADR-0002.

Still open from this sprint: JSON structured logging and `/metrics`, both moved into
Phase 5's dependency chain.

### Sprint 2 — "Artifact to Running Container" · M2 🟡 *Current*

*Goal: a merge to `main` deploys the exact image CI built, verifies it is healthy,
and can be rolled back in under a minute.*

Scope: the `deploy_app` Ansible role; inventory and `group_vars`; secrets via
ansible-vault; a post-deploy smoke test that fails the play; `cd.yml` on `main`
passing `app_version` from CI with no rebuild; `rollback.yml` plus a rehearsal;
`ansible-lint` and `hadolint` added to CI; branch protection on `main`.

Review demo:

1. Open a pull request — show the required checks blocking the merge.
2. Merge → CD runs → the new container is live and the smoke test passes.
3. `curl /version` — the running SHA matches the merge commit. This is the
   traceability moment.
4. Run the deploy playbook a second time → `changed=0`. Idempotence demonstrated,
   not claimed.
5. Deliberately deploy a broken image → the smoke test fails the deploy → roll back
   to the previous SHA in one command.

Main risk: the `localhost:5001` versus `registry:5000` resolution difference between
the runner and the Docker daemon. Budget half a day.

### Sprint 3 — "See What's Happening" · M3 ⬜

*Goal: when the app misbehaves, spot it on a dashboard and reach the responsible log
line in one click.*

Scope: Prometheus scraping the app, cAdvisor and node_exporter, with scrape config
and alert rules in Git; Grafana provisioned as code with the two dashboards above;
Alloy to Loki with JSON parsing; the Grafana data link from error rate to a
pre-filtered Loki query; one alert rule; a load-generation script for the demo;
ADRs for choosing Loki over ELK and for the metric cardinality policy.

Review demo — the incident scenario from the brief, end to end:

1. Fire a burst of good and malformed requests at `/echo`.
2. The error rate spikes on the Golden Signals dashboard and the alert fires.
3. Click the data link into Loki, filtered to `level=ERROR` and `path=/echo`.
4. Read out the exact failing payload and its `request_id`.
5. Close with: no SSH, no grep, 40 seconds from symptom to root cause.

Then explain why `request_id` is a log field and not a Prometheus label. That one
sentence about cardinality is worth more than another dashboard.

### Hardening week — M4 ⬜

A stabilisation window, not a sprint. **No new features here.** Remaining ADRs,
`RUNBOOK.md`, `CHANGELOG.md`, the clean-machine test, `DEMO.md`, and two timed
rehearsals of the full demo on a cold machine.

---

## 4. Open work

### P0 — must exist or the project fails

- [x] Gitea and act_runner running via compose, runner registered
- [x] Local registry container up, Docker daemon configured for `localhost:5001`
- [x] Multi-stage, non-root, digest-pinned Dockerfile
- [x] `ci.yml`: lint → test → build → scan → push on every push
- [x] A README a stranger can follow to a running stack
- [ ] Ansible playbook deploying the pulled image idempotently
- [ ] `cd.yml` on `main` passing the CI SHA to Ansible
- [ ] Prometheus scraping the app's `/metrics`; a Grafana dashboard with request
      rate, error rate and latency
- [ ] Alloy to Loki, app logs queryable by `level` and `path`

### P1 — the difference between "works" and "senior"

- [x] Explicit `/echo` 400 handling — unblocks the incident demo
- [x] Coverage gate in CI, failing under 80%
- [x] Trivy image scan failing the pipeline on HIGH or CRITICAL
- [x] Gunicorn instead of the Flask dev server
- [x] Secrets kept out of Git (`platform/.env` gitignored)
- [ ] Structured JSON logging with a correlation `request_id`
- [ ] Post-deploy smoke test that fails the deploy
- [ ] Documented and rehearsed rollback
- [ ] Grafana provisioned as code — no click-configured dashboards
- [ ] cAdvisor and node_exporter for CPU and memory
- [ ] `ansible-lint` and `hadolint` in CI
- [ ] Runbook and remaining ADRs

### P2 — only after P0 and P1

- [ ] Prometheus alert rule plus Alertmanager routing to a local webhook
- [ ] Blue/green or compose-based zero-downtime swap
- [ ] Semantic release or auto-changelog on tags
- [ ] SBOM generation (`syft`) as a pipeline artifact
- [ ] Automated dependency update job

---

## 5. Risks and open questions

### Blockers

| # | Issue | Impact | Action |
|---|---|---|---|
| B1 | **Admin rights on the TCS laptop.** Docker Desktop, hypervisors and daemon config (`insecure-registries`) usually need admin. | Kills the project if unresolved | Ask the mentor immediately. Fallbacks: Rancher Desktop, Podman, colima, or run the whole stack inside WSL2 |
| B2 | **Corporate proxy and TLS interception.** `docker pull`, `pip install` and `ansible-galaxy` can all fail behind the TCS network. | Blocks setup | Get proxy environment variables and the CA certificate early; bake them into build args and the runner environment |
| B3 | **Docker socket access from the CI runner.** The runner needs `/var/run/docker.sock` mounted to build images and for Ansible to deploy. | Blocks CI and CD | Mount the socket, and state in the docs that this is a privilege-escalation path in real environments. The production answer is rootless Docker or BuildKit-in-container |
| B4 | **`localhost:5001` (host) and `registry:5000` (in-network) mean different things inside and outside a container.** The runner pushes to `localhost:5001` fine, then Ansible or the daemon cannot resolve it. | Silent CD failure | Use a fixed hostname on the shared Docker network rather than `localhost` |

### Open questions for the mentor

1. Is the "local machine" the TCS laptop or a personal one? This determines B1 and B2.
2. Is a second host (a VM via Multipass or Vagrant) allowed as the deploy target? A
   real SSH-based Ansible inventory is a much stronger story than `connection: local`,
   but it costs RAM.
3. Does depth on observability count for more than pipeline sophistication? Bias
   effort accordingly.
4. Is committing the whole platform stack, including Gitea itself, acceptable — or
   should Gitea be treated as pre-existing infrastructure?

### Assumptions

- Single node, single environment. No staging/production split; if one is wanted, it
  is a second Ansible inventory group, not a second pipeline.
- Port 5000 collides between Flask and the registry. The app runs on 8000 and the
  registry is published on 5001.
- No persistent application data, so no database and no migration story. Adding one
  would make migrations the hardest part of CD and would need explicit scoping.

### Standing risks

- **Scope creep.** The brief invites bolting on Terraform, Vault and Kubernetes.
  Resist. A tight, fully explained pipeline beats a sprawling half-working one, and
  every line has to be explainable.
- **Demo fragility.** Cold Docker starts, port conflicts, stale containers. Mitigate
  by rehearsing a full reset and bring-up twice on a clean machine.
- **Explainability gap.** "Why did you choose this?" is coming. Write the ADRs as
  decisions are made, not at the end.
- **Laptop resources.** Gitea, runner, registry, Prometheus, Grafana, Loki, Alloy,
  cAdvisor and the app together need roughly 3–4 GB. Set memory limits in compose;
  drop node_exporter first if constrained.

---

## 6. Working conventions

### Branching — trunk-based

Short-lived `<type>/<kebab-description>` branches off a protected `main`, rebased
before review, squash-merged through a pull request, deleted after. Nothing lives
longer than about two days; only `main` publishes an image. Rules, the GitFlow
trade-off and the exact branch-protection settings: [`BRANCHING.md`](BRANCHING.md).

Tags: `v0.1.0`, `v0.2.0` at each milestone, annotated rather than lightweight.

### Commits — Conventional Commits

```
<type>(<scope>): <imperative summary under 72 chars>

<why, not what — the diff already shows what>

Refs: #42
```

Types: `feat`, `fix`, `docs`, `ci`, `build`, `refactor`, `test`, `chore`, `perf`.
Scopes: `app`, `ci`, `cd`, `ansible`, `docker`, `obs`, `docs`.

```
feat(cd): deploy image by git SHA instead of latest

Pinning to the CI-produced SHA makes deploys reproducible and enables
single-command rollback. `latest` gave no way to know what was actually
running.

Refs: #23
```

This buys auto-generated changelogs and makes `git log` a readable project
narrative — which mentors will scroll through.

### Pull requests — yes, even solo

Working alone is not a reason to push to `main`. The pull request is where reasoning
gets recorded, and reviewable reasoning is the whole point.

Branch protection on `main`: require a pull request before merge; require the status
checks (`lint`, `test`, coverage, `trivy`, and later `hadolint` and `ansible-lint`);
require branches to be up to date; no force push; squash merge only, so one story is
one commit and one clean revert.

Before requesting review, read your own diff in the web UI and leave at least one
comment explaining a non-obvious decision. It catches roughly a third of your own
mistakes and leaves a visible trail of your thinking.

### Definition of Done

- [ ] Acceptance criteria met and verified manually
- [ ] Code and config committed, no secrets in history
- [ ] CI green — lint, tests, coverage gate, image scan
- [ ] Self-review completed with written reasoning
- [ ] Documentation updated (README, ADR or runbook as applicable)
- [ ] Change reproducible from a clean clone
- [ ] Demoable in under two minutes

### Pipeline practices

- CI produces an artifact; CD consumes it, and **never rebuilds** — rebuilding in
  the deploy stage breaks the immutability guarantee the pipeline exists to give.
  They are separate *jobs* rather than separate workflows: the runner has
  capacity 1, so two independently triggered workflows can be scheduled in either
  order, and CD would wait for an image CI has not pushed while CI waits for the
  runner. `needs:` makes the ordering a fact rather than a hope. Split them into
  separate workflow files only once there is a trigger that guarantees ordering.
- Fail fast, cheapest first: lint, then tests, then build, then scan, then push.
- Every stage must be runnable locally. A stage that only works in CI cannot be
  debugged.
- Pin everything: base image digests, action versions, requirements with hashes.

### Security practices

- Non-root container user, dropped capabilities, never `--privileged`.
- Zero secrets in Git.
- Trivy on the image and the filesystem; fail the build rather than only reporting.
- Least-privilege registry — even locally, running it with auth shows you know it is
  normally required.

### Ansible practices

- Roles, not one giant playbook: `defaults/`, `tasks/`, `handlers/`, `templates/`.
- Idempotence is the whole point. Run the playbook twice; the second run must report
  `changed=0`. Demo this.
- `ansible-lint` in CI, with `--check` mode documented as the dry-run path.
- Never hardcode versions in the playbook. `app_version` is always an extra variable
  from CI.

### Observability practices

- RED for the app (Rate, Errors, Duration), USE for the host (Utilization,
  Saturation, Errors).
- Label discipline: never put unbounded values such as request or user IDs in
  Prometheus labels — that is a cardinality explosion. Put them in the log line
  instead. Mention this in the demo.
- Dashboards as code. If it was clicked and is not in Git, it does not exist.
- One alert that actually fires during the demo beats twenty that do not.

### Documentation

| Doc | Purpose | Update trigger |
|---|---|---|
| `README.md` | What it is, how to run it, current status | Any interface change |
| `docs/PLAN.md` | Roadmap, sprints, open work, conventions | Weekly, and whenever a phase completes |
| `docs/DEVELOPMENT.md` | Commands, platform operations, Git workflow | Any tooling or workflow change |
| `docs/BRANCHING.md` | Branch model, merge policy, `main` protection settings | Any change to how work reaches `main` |
| `docs/adr/*.md` | One decision each: context, decision, consequences | **The day the decision is made** |
| `docs/RUNBOOK.md` *(planned)* | Deploy, rollback, alert meanings, common failures | Every operational change |
| `docs/DEMO.md` *(planned)* | Scripted click-path with expected output | Before each review |

ADRs are the highest-leverage item on this list. The brief explicitly requires
explaining the configuration, and six short ADRs written as the decisions are made
beat any amount of retroactive documentation. Documenting at the end does not work —
you will not remember in week 4 why you chose Loki over ELK. Write it in week 1, in
five sentences.

The final deliverable required by the brief is assembled *from* these files rather
than written separately.

---

## 7. Next actions

1. ✅ Ansible scaffold and inventory — `ansible-playbook playbooks/ping.yml` green.
2. Write the `deploy_app` role: pull by SHA, run the container.
3. Add the post-deploy smoke test that can fail the play.
4. Add `cd.yml` on `main`, passing the CI-built SHA as `app_version`.
5. Rehearse the rollback and document it.
6. Enable branch protection on `main` with the current CI checks as required.
7. Write the ADR for choosing Ansible over a shell script, the same day the role lands.
