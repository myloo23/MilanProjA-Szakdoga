# Project A — Plan

**Owner:** Milán Takács · **Deploy target:** local Docker host

Roadmap, sprints, open work and risks. Overview: [`../README.md`](../README.md).
Commands: [`DEVELOPMENT.md`](DEVELOPMENT.md). Branches: [`BRANCHING.md`](BRANCHING.md).

---

## 1. Design decisions

| Decision | Choice | Why |
|---|---|---|
| Review | GitHub — protected branches, CODEOWNERS | Reviewers cannot reach a localhost Gitea ([ADR-0004](adr/0004-github-for-review-gitea-for-execution.md)) |
| CI | Self-hosted Gitea + `act_runner` | Full ownership of runner, registry, daemon ([ADR-0001](adr/0001-self-hosted-gitea-actions.md)) |
| Artifact | Docker image in a local registry, tagged by git SHA. **Never `latest`** | Build once, deploy an immutable artifact ([ADR-0002](adr/0002-build-once-push-to-registry.md)) |
| Deploy | Ansible + `community.docker`, inventory-driven | Idempotent and declarative, no orchestrator ([ADR-0003](adr/0003-deploy-and-verify-strategy.md)) |
| Verification | Every check fails the deploy, none warns | A check that cannot fail is a log line ([ADR-0003](adr/0003-deploy-and-verify-strategy.md)) |
| App runtime | Gunicorn, not the Flask dev server | Production means WSGI plus workers |
| Metrics | `prometheus_client` + cAdvisor + node_exporter | App metrics *and* CPU/memory, as the brief requires |
| Logs | JSON to stdout → Alloy → Loki → Grafana | Twelve-factor, metric-to-log pivot in one UI |
| Repo shape | One repository | One deployable unit, atomic cross-cutting changes |

**Why one repo:** adding a metric touches the app, the Dockerfile, the scrape
config and a dashboard. One repo makes that one pull request and one revert.
Split it when the Ansible roles get shared across projects — not before.

---

## 2. Roadmap

**Phase 0 — Foundation** ✅ Prerequisites, repository, branch strategy.

**Phase 1 — Application hardening** 🟡
Make the app production-grade before automating it; automating a bad artifact
just ships it faster.

- ✅ `/echo` returns 400 on malformed JSON — the incident demo needs a
  controllable error signal
- ✅ `/health` (liveness) split from `/ready` (readiness)
- ✅ Gunicorn, pytest suite, ruff
- ⬜ Structured JSON logging with `request_id`, `path`, `status`, `duration_ms`
- ⬜ `/metrics` via `prometheus_client`

**Phase 2 — Containerization** ✅
Multi-stage, digest-pinned base, non-root `appuser`, `HEALTHCHECK`.
⬜ Remaining: OCI labels (`revision`, `source`, `created`, `version`).

**Phase 3 — CI** ✅
`ruff → hadolint → pytest (80% gate) → build → health gate → network check →
trivy → push`. Fail-fast in cost order.
⬜ Remaining: build metadata via `--build-arg`, surfaced on a `/version` endpoint.

**Phase 4 — CD with Ansible** 🟡

- ✅ `ansible/` scaffold with an inventory-driven `docker_host`, so a remote
  target costs an inventory edit and no role change
- ✅ `deploy_app` role: pull by SHA, run with limits and log rotation, then a
  smoke test that fails the play. On failure it dumps the last 50 log lines and
  prints the rollback command with the previous SHA already filled in
- ✅ `deploy` job gated on `needs: build-test-push` and a ref check. **No rebuild
  in CD** — it deploys the artifact CI tested
- ⬜ **Rollback rehearsal.** The path exists and is documented; it has not been
  executed end to end, so it is not yet a claim that can be made
- ⬜ `ansible-vault` — deliberately not built. Nothing here is secret yet, and
  vault before a secret is ceremony, not security

**Phase 5 — Observability** ⬜ *Next*
Prometheus (app, cAdvisor, node_exporter), Grafana provisioned as code with two
dashboards, Alloy → Loki with JSON parsing, a data link from error rate to the
filtered log query, one alert rule.

---

## 3. Milestones

| Milestone | Complete when | Status |
|---|---|:--:|
| **M1 — Pipeline Foundation** | A commit triggers lint, test, build, scan, push of an immutably tagged image | ✅ |
| **M2 — Automated Delivery** | A reviewed merge deploys that exact image, with a smoke test that can fail the deploy | 🟡 |
| **M3 — Observability** | Metric spike → one click to the matching logs; dashboards as code | ⬜ |
| **M4 — Production Readiness** | Rollback rehearsed, ADRs written, clean-machine reproducible, demo scripted | 🟡 |

### Sprint 1 — "Commit to Artifact" ✅

Platform stack via compose, app hardening, coverage gate, hardened Dockerfile,
`ci.yml` through to the registry push, ADR-0001 and ADR-0002.

### Sprint 2 — "Artifact to Running Container" 🟡

*Goal: a reviewed merge deploys the exact image CI built, verifies it, and can be
rolled back in under a minute.*

Delivered: the `deploy_app` role; the in-role smoke test; the `deploy` job;
health-gated waits replacing a fixed `sleep`; `hadolint`; ADR-0003 and ADR-0004.

Unplanned but delivered: the review model changed mid-sprint. GitHub became the
source of truth for review, Gitea kept execution. Protection and CODEOWNERS are
configured but not enforced — that needs a public repository on this plan, and
the work stays private.

Still open: `ansible-lint`; the rollback rehearsal.

**Review demo**

1. Open a pull request — the merge is blocked until a code owner approves.
2. Merge → CD runs → the new container is live and the smoke test passes.
3. The container's `version` label matches the merge commit:
   `docker inspect --format '{{index .Config.Labels "version"}}' projecta-flask`
   against `git rev-parse HEAD`.
4. Run the deploy a second time → `changed=0`. Idempotence shown, not claimed.
5. Deploy a broken image → the smoke test fails the deploy and prints its own
   rollback command → roll back with one line.

### Sprint 3 — "See What's Happening" ⬜ *Next*

Prometheus, Grafana as code, Alloy → Loki, the metric-to-log data link, one
alert rule, a load-generation script, ADRs for Loki-over-ELK and for metric
cardinality.

**Review demo** — the incident from the brief: fire malformed requests at
`/echo`, watch the error rate spike and the alert fire, click through to the
filtered logs, read out the failing payload and its `request_id`. No SSH, no
grep. Then explain why `request_id` is a log field and not a Prometheus label —
that sentence about cardinality is worth more than another dashboard.

### Hardening week ⬜

No new features. Remaining ADRs, `RUNBOOK.md`, `CHANGELOG.md`, the clean-machine
test, `DEMO.md`, two timed rehearsals on a cold machine.

---

## 4. Open work

**P0 — must exist or the project fails**

- [x] Platform stack, registry, CI through to push, Ansible deploy, deploy job
- [x] A README a stranger can follow to a running stack
- [ ] Prometheus scraping `/metrics`; a dashboard with rate, errors, latency
- [ ] Alloy → Loki, logs queryable by `level` and `path`

**P1 — the difference between "works" and "senior"**

- [x] `/echo` 400 handling, coverage gate, Trivy scan, Gunicorn, secrets out of Git
- [x] Post-deploy smoke test that fails the deploy
- [x] `hadolint` in CI
- [ ] `ansible-lint` in CI
- [ ] **Rollback rehearsed**, not just documented
- [ ] Structured JSON logging with `request_id`
- [ ] Grafana provisioned as code, cAdvisor and node_exporter
- [ ] Runbook and remaining ADRs

**P2 — only after P0 and P1**

- [ ] Alert routing, zero-downtime swap, auto-changelog, SBOM, dependency updates

---

## 5. Risks

| # | Risk | Action |
|---|---|---|
| B1 | Admin rights on the TCS laptop for Docker and daemon config | Ask early. Fallbacks: Rancher Desktop, Podman, colima, WSL2 |
| B2 | Corporate proxy and TLS interception breaking pulls and installs | Get proxy variables and the CA certificate; bake into build args and the runner |
| B3 | The runner needs the Docker socket — a privilege-escalation path | Accepted for a local single-owner setup, and documented. The production answer is rootless Docker or BuildKit-in-container |
| B4 | ~~`localhost` means different things inside and outside a container~~ | **Resolved**, and not where expected: the registry push always worked, because the daemon resolves it. It bit the *smoke test*, which runs inside the job container. Handled by `deploy_app_smoke_vantage` |

**Standing risks**

- **Scope creep.** The brief invites Terraform, Vault and Kubernetes. Resist —
  every line has to be explainable.
- **Demo fragility.** Cold starts, port conflicts, stale containers. Rehearse a
  full reset twice on a clean machine.
- **Explainability gap.** Write ADRs as decisions are made, not at the end.
- **Laptop resources.** The full stack needs ~3–4 GB. Set memory limits; drop
  node_exporter first if constrained.

**Open questions for the mentor**

1. Is the "local machine" the TCS laptop or a personal one? Decides B1 and B2.
2. Does depth on observability count for more than pipeline sophistication?
3. Is committing the platform stack, Gitea included, acceptable?

---

## 6. Conventions

- **Branches, merges, protection:** [`BRANCHING.md`](BRANCHING.md).
- **Commits:** Conventional Commits. The body says *why*, not *what* — the diff
  already says what.
- **Pull requests:** every change, no exceptions. Read your own diff first and
  leave a comment on anything non-obvious.
- **Definition of Done:** merged through a reviewed pull request, CI green,
  documentation updated in the same change, and the claim demonstrable live.
- **Pipeline:** fail fast in cost order; gates fail, they never warn; the
  artifact is immutable and built once.
- **Security:** no secrets in Git; the image runs non-root; scans block on
  HIGH/CRITICAL; dependencies are hash-locked.
- **Documentation:** if a claim in these docs cannot be demonstrated, it is
  marked ⬜. An unproven claim is worse than a missing one.

---

## 7. Next actions

1. `ansible-lint` in CI, as a step inside `build-test-push`.
2. Rehearse the rollback end to end and record the result.
3. Start the logging and `/metrics` work — Sprint 3 depends on both.
