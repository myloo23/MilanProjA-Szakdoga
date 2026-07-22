# Project A — Classic CI/CD: Execution Plan

**Owner:** Milán Takács · **Target:** TCS DevOps Internship · **Deploy target:** local Docker host

---

## 0. Architecture decision summary

| Decision | Choice | Why |
|---|---|---|
| SCM + CI | Gitea + Gitea Actions (`act_runner`) | Light, GitHub-Actions syntax = transferable, self-hosted = full ownership story |
| Artifact | Docker image, pushed to local registry `localhost:5000` | Build-once/deploy-immutable. Option 1 (build+run same host) is a demo, not a pipeline |
| Image tag | `<git-sha-short>` + `v<semver>` on tags. **Never `latest`** | Traceable, rollback-able, forces immutability |
| Deploy | Ansible + `community.docker`, inventory-driven | Idempotent, declarative, no orchestrator |
| App runtime | **Gunicorn**, not `flask run` / `app.run()` | The starter code ships a dev server — production-grade means WSGI + workers |
| Metrics | `prometheus_client` in-app + cAdvisor + node_exporter | Custom app metrics *and* CPU/mem, as required |
| Logs | JSON to stdout → Alloy → Loki → Grafana | Twelve-factor; metric→log pivot in one UI |
| Everything | One Git repo, IaC + dashboards + alerts as code | "It's all in the repo" is the senior signal |

### Repo layout (mono-repo)

```
.
├── app/                  # Flask app, Dockerfile, requirements, tests
├── .gitea/workflows/     # ci.yml, cd.yml
├── ansible/              # inventory/, roles/deploy_app/, playbooks/
├── platform/             # docker-compose for Gitea, registry, Prom, Grafana, Loki, Alloy
│   └── grafana/provisioning/   # datasources + dashboards as code (JSON)
├── docs/                 # ADRs, runbook, architecture diagram, demo script
├── Makefile              # make up / test / lint / deploy / rollback / demo-incident
└── README.md
```

---

## 1. High-level roadmap

**Phase 0 — Foundation (Day 1–2)**
Local prereqs (Docker, Python 3.12, Ansible, ansible-galaxy collection), Git repo initialized, branch strategy (`main` protected + short-lived feature branches), `.gitignore`, `.dockerignore`, Makefile skeleton, README stub.
*Exit criteria:* `git push` works to a self-hosted Gitea; `make help` runs.

**Phase 1 — Application hardening (Day 2–4)** — *depends on Phase 0*
Take the starter `app.py` and make it production-grade before automating it. Automating a bad artifact just ships bad faster.
- Structured JSON logging (`python-json-logger`) with `request_id`, `method`, `path`, `status`, `duration_ms`, `level`.
- Fix `/echo`: explicit `try/except` on malformed JSON → `400` + `level=ERROR` log. **This is what your incident demo depends on** — without it the endpoint returns a 415/500 and you have no controllable error signal.
- Add `/metrics` via `prometheus_client`: `http_requests_total{method,path,status}`, `http_request_duration_seconds` histogram, plus one business-ish gauge.
- Split `/health` (liveness) and `/ready` (readiness).
- Gunicorn entrypoint, config file, `--workers 2 --threads 4`.
- `pytest` suite: happy path, health, invalid-JSON 400, metrics endpoint exposes counters. Target ≥80% coverage on app code.
- `ruff` (lint+format) config.
*Exit criteria:* `make test lint` green locally.

**Phase 2 — Containerization (Day 4–5)** — *depends on Phase 1*
- Multi-stage Dockerfile: builder installs wheels, runtime is `python:3.12-slim` pinned **by digest**.
- Non-root `USER app` (UID 10001), read-only rootfs where possible, `HEALTHCHECK` hitting `/health`.
- OCI labels: `org.opencontainers.image.revision`, `.source`, `.created`, `.version`.
- `.dockerignore` (tests, .git, venv) — image should be < 150 MB.
*Exit criteria:* `docker run` → curl `/`, `/health`, `/metrics`, `/echo` all correct; `docker history` shows no secrets.

**Phase 3 — CI (Day 5–8)** — *depends on Phase 2*
Gitea + `act_runner` in docker-compose, runner registered with a label (`local-docker`).
Pipeline `ci.yml` on every push + PR, stages in order, fail-fast:
`lint → unit tests (+coverage gate) → build image → trivy scan (fail on HIGH/CRITICAL) → push to local registry`.
- Dependency + pip cache to keep runs under ~2 min.
- Tags: `localhost:5000/flaskapp:${GITHUB_SHA::7}`.
- Build metadata injected via `--build-arg`, surfaced by the app on `/` or a `/version` endpoint.
*Exit criteria:* a commit to a feature branch produces a green pipeline and a pushed, scanned, uniquely-tagged image.

**Phase 4 — CD with Ansible (Day 8–11)** — *depends on Phase 3*
- `ansible/roles/deploy_app`: pull image by tag → run container (`recreate: true`, `restart_policy: unless-stopped`, resource limits, log driver) → **post-deploy smoke test** (`uri` module polling `/health` with retries) → fail the play if unhealthy.
- Inventory with a real `local_docker` host group; variables in `group_vars/`, secrets in `ansible-vault` (vault password from a Gitea Actions secret, never in repo).
- `cd.yml` triggers only on `main` (or on tag), passes `app_version` = the exact CI-built SHA. **No rebuild in CD** — deploy the artifact CI produced.
- `rollback` path: same playbook, `app_version=<previous-sha>`. Document and rehearse it.
*Exit criteria:* merge to `main` → container running the new SHA, smoke test passed, zero manual steps.

**Phase 5 — Observability (Day 11–15)** — *depends on Phase 4*
- Prometheus scrapes: app `/metrics`, cAdvisor (container CPU/mem), node_exporter (host), plus Gitea/registry if exposed. Scrape config in repo.
- Grafana **provisioned as code**: datasources (Prometheus + Loki) and 2 dashboards committed as JSON —
  1. *App Golden Signals*: request rate, error rate (%), p50/p95/p99 latency, in-flight.
  2. *Platform*: container CPU/mem/restarts, host load, disk.
- Alloy tails Docker stdout, labels by `container`, `app`, `env`; parses JSON so `level` and `path` become queryable labels/fields in Loki.
- Add a Grafana **data link** from the error-rate panel to the pre-filtered Loki query — that one click *is* the metric→log pivot.
- One Prometheus alert rule (`ErrorRate > 5% for 2m`) — proves you understand alerting, not just dashboards.
*Exit criteria:* the incident walkthrough from the brief runs end-to-end in under 60 seconds.

**Phase 6 — Hardening, docs, demo (Day 15–18)** — *depends on all*
- ADRs (4–6 short ones) for the decisions in the table above.
- Runbook: how to deploy, how to roll back, what each alert means, how to read the dashboards.
- Architecture diagram (Mermaid, in-repo, renders on Gitea).
- `docs/DEMO.md`: exact scripted click-path for the final live demo + `make demo-incident` that fires the bad-request burst.
- Fresh-machine test: `git clone && make up` on a clean state, timed.

---

## 2. Prioritized TODO checklist

### P0 — must exist or the project fails
- [ ] Gitea + act_runner running via docker-compose, runner registered
- [ ] Local registry container up, Docker daemon configured for `localhost:5000` as insecure registry
- [ ] Dockerfile multi-stage, non-root, digest-pinned base
- [ ] `ci.yml`: lint → test → build → push, triggered on push
- [ ] Ansible playbook deploys pulled image idempotently
- [ ] `cd.yml` on `main` passes the CI SHA to Ansible
- [ ] Prometheus scraping app `/metrics`; Grafana dashboard with request rate + error rate + latency
- [ ] Alloy → Loki; app logs queryable by `level` and `path`
- [ ] README that a stranger can follow to a running stack

### P1 — the difference between "works" and "senior"
- [ ] Structured JSON logging with correlation `request_id`
- [ ] `/echo` explicit 400 handling (unblocks the incident demo)
- [ ] Coverage gate in CI (fail under threshold)
- [ ] Trivy image scan, pipeline fails on HIGH/CRITICAL
- [ ] Post-deploy smoke test that fails the deploy
- [ ] Documented + rehearsed rollback
- [ ] Grafana provisioned-as-code (no click-configured dashboards)
- [ ] cAdvisor + node_exporter for CPU/memory
- [ ] `ansible-lint` + `hadolint` in CI
- [ ] Secrets in Gitea Actions secrets / ansible-vault, zero secrets in Git
- [ ] ADRs + runbook + Mermaid diagram
- [ ] Gunicorn instead of the Flask dev server

### P2 — do only if P0+P1 are done
- [ ] Prometheus alert rule + Alertmanager routing to a local webhook
- [ ] Blue/green or `docker compose`-based zero-downtime swap
- [ ] Semantic-release / auto-changelog on tags
- [ ] SBOM generation (`syft`) attached as a pipeline artifact
- [ ] Renovate or Dependabot-style dependency update job
- [ ] Trace context (OpenTelemetry) — nice, but scope creep for 4 weeks

---

## 3. Risks, blockers, missing information

**Blockers to resolve in week 1**

| # | Issue | Impact | Action |
|---|---|---|---|
| B1 | **Admin rights on the TCS laptop.** Docker Desktop, VM hypervisors and daemon config (`insecure-registries`) usually need admin. | Kills the whole project if unresolved | Ask your mentor day 1. Fallbacks: Rancher Desktop / Podman / colima; or run the whole stack inside WSL2 |
| B2 | **Corporate proxy / TLS interception.** `docker pull`, `pip install`, `ansible-galaxy` may all fail behind the TCS network. | Blocks Phase 0 | Get proxy env vars + CA cert early; bake into Dockerfile build args and CI runner env |
| B3 | **Docker socket access from the CI runner.** Gitea Actions runner needs `/var/run/docker.sock` mounted to build images and for Ansible to deploy. | Blocks Phase 3–4 | Mount the socket, and **state in your docs that you know this is a privilege-escalation path** in real environments; name rootless Docker / BuildKit-in-container as the production answer |
| B4 | **`localhost:5000` means different things inside and outside a container.** Classic trap: the runner pushes to `localhost:5000` fine, then Ansible/daemon can't resolve it. | Silent Phase 4 failure | Use a fixed hostname (`registry:5000` on a shared Docker network + `/etc/hosts` entry) rather than `localhost` |

**Open questions to confirm with your mentor**
1. Is the "local machine" the TCS laptop or a personal one? Determines everything in B1/B2.
2. Is a second host (VM via Multipass/Vagrant) allowed as deploy target? A real SSH-based Ansible inventory is a much stronger story than `connection: local` — but costs RAM.
3. Grading weight: does depth on observability count more than pipeline sophistication? Bias effort accordingly.
4. Project duration and demo cadence — the phases above assume ~4 weeks with weekly checkpoints.
5. Is committing the whole platform stack (Gitea itself) to the repo acceptable, or should Gitea be treated as pre-existing infrastructure?

**Assumptions made**
- Single-node, single-environment (dev only). No staging/prod split; if you want one, do it as a second Ansible inventory group, not a second pipeline.
- Port 5000 conflict: Flask and the registry both default to 5000. Move the app to 8000. Fix this now, not during the demo.
- No persistent app data — no database, so no migration story needed. If you add one, migrations become the hardest part of CD and you should scope for it explicitly.

**Risks**
- *Scope creep* — this brief invites bolting on Terraform/Vault/K8s. Resist. A tight, fully-explained pipeline beats a sprawling half-working one, and you must be able to explain every line.
- *Demo fragility* — cold Docker starts, port conflicts, stale containers. Mitigate with `make reset && make up` rehearsed twice on a clean machine before the final demo.
- *Explainability gap* — you'll be asked "why". Write the ADRs as you go, not at the end.
- *Laptop resources* — Gitea + runner + registry + Prometheus + Grafana + Loki + Alloy + cAdvisor + app ≈ 3–4 GB. Set memory limits in compose; drop node_exporter first if constrained.

---

## 4. Recommended best practices

**Pipeline**
- CI and CD are separate workflows. CI produces an artifact; CD consumes it. Never rebuild in the deploy stage — that breaks the immutability guarantee.
- Fail fast, cheap-to-expensive ordering: lint (5s) → test (30s) → build (2m) → scan → push.
- Every pipeline stage must be runnable locally via `make` — if it only works in CI, you can't debug it.
- Pin everything: base image digests, action versions (SHA, not `@v4`), `requirements.txt` with hashes.

**Security**
- Non-root container user, dropped capabilities, no `--privileged`.
- Zero secrets in Git — enforce with `gitleaks` as a pre-commit hook *and* a CI stage.
- Trivy on image + filesystem; fail the build, don't just report.
- Least-privilege registry: even locally, run it with auth to show you know it's normally required.

**Ansible**
- Roles, not one giant playbook. `defaults/`, `tasks/`, `handlers/`, `templates/`.
- Idempotence is the whole point — run the playbook twice, second run must be `changed=0`. Demo this.
- `ansible-lint` in CI. `--check` mode documented as the dry-run path.
- Never hardcode versions in the playbook; `app_version` is always an extra-var from CI.

**Observability**
- RED method for the app (Rate, Errors, Duration), USE for the host (Utilization, Saturation, Errors).
- Label discipline: never put unbounded values (request IDs, user IDs) in Prometheus labels — cardinality explosion. Put them in the log line instead. **Mention this in your demo; it's a strong senior signal.**
- Dashboards as code. If you clicked it and it isn't in Git, it doesn't exist.
- One alert that actually fires during the demo beats twenty that don't.

**Repo & docs**
- Conventional Commits + protected `main` + PR-only merges, even solo. It makes the pipeline meaningful.
- README answers: what, how to run, how it's built, how to deploy, how to roll back — in that order, in under two screens.
- ADRs in `docs/adr/NNN-title.md`: context, decision, alternatives, consequences. Six short ones beat one long design doc.

**For the final demo**
Open on the incident walkthrough, not the architecture slide. Push a commit live → watch it build, scan, deploy, smoke-test → fire bad traffic → error rate spikes in Grafana → one click into Loki → the exact failing payload. Then explain the design. Ten minutes, rehearsed, no live debugging.
