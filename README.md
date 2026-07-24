# Project A — Classic CI/CD Pipeline

> Commit → build → test → containerize → deploy → observe. On a plain Docker host, no Kubernetes.
> **TCS DevOps Internship** · Owner: **Milán Takács**

![Status](https://img.shields.io/badge/status-in%20progress-yellow)
![CI](https://img.shields.io/badge/CI-Gitea%20Actions-609926?logo=gitea&logoColor=white)
![Deploy](https://img.shields.io/badge/deploy-Ansible-EE0000?logo=ansible&logoColor=white)
![App](https://img.shields.io/badge/app-Flask%203.1-000000?logo=flask&logoColor=white)
![Runtime](https://img.shields.io/badge/runtime-Gunicorn-499848?logo=gunicorn&logoColor=white)
![Container](https://img.shields.io/badge/container-Docker-2496ED?logo=docker&logoColor=white)
![Metrics](https://img.shields.io/badge/metrics-Prometheus-E6522C?logo=prometheus&logoColor=white)
![Dashboards](https://img.shields.io/badge/dashboards-Grafana-F46800?logo=grafana&logoColor=white)
![Logs](https://img.shields.io/badge/logs-Loki-F5A800?logo=grafana&logoColor=white)

---

## What it does

Automates the full path from a Git commit to a running, monitored container — the classic build-artifact-deploy loop that real pipelines run every day.

```
push  →  CI (lint · test · build · scan · push)  →  CD (Ansible deploy)  →  observe (metrics + logs)
```

## Architecture

```mermaid
flowchart LR
    Dev([Developer]) -->|git push| Gitea[Gitea + Actions]
    Gitea -->|ci.yml| CI{{lint · test · build · scan}}
    CI -->|push image| Reg[(Local Registry<br/>localhost:5000)]
    Gitea -->|cd.yml on main| Ansible[Ansible<br/>community.docker]
    Reg -->|pull by SHA| Ansible
    Ansible -->|run container| App[Flask App<br/>Gunicorn :8000]
    App -->|/metrics| Prom[(Prometheus)]
    App -->|stdout JSON| Alloy[Grafana Alloy]
    Alloy --> Loki[(Loki)]
    Prom --> Graf[Grafana]
    Loki --> Graf
    Graf -->|metric → log pivot| Dev
```

## Pipeline flow

```mermaid
flowchart LR
    A[Commit] --> B[Lint<br/>ruff]
    B --> C[Unit tests<br/>pytest + coverage]
    C --> D[Build image<br/>multi-stage]
    D --> E[Scan<br/>trivy]
    E --> F[Push<br/>SHA tag]
    F -->|main only| G[Ansible deploy]
    G --> H[Smoke test<br/>/health]
    H --> I[Live + monitored]
    C -.fail.-> X[Stop]
    E -.HIGH/CRITICAL.-> X
    H -.unhealthy.-> R[Rollback<br/>prev SHA]
```

## Roadmap — 3 sprints

```mermaid
gantt
    title Project A — 3 Sprint Plan (~18 working days)
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Sprint 1 · Foundation & App
    Repo + tooling setup        :done,    s1a, 2026-07-14, 2d
    App hardening (logs/tests)  :done,    s1b, after s1a, 3d
    Containerization (Docker)   :done,    s1c, after s1b, 2d

    section Sprint 2 · Pipeline
    CI (Gitea Actions)          :active,  s2a, after s1c, 3d
    CD (Ansible deploy)         :         s2b, after s2a, 3d

    section Sprint 3 · Observability & Demo
    Metrics + logs stack        :         s3a, after s2b, 4d
    Hardening, docs, demo       :         s3b, after s3a, 3d
```

### Sprint breakdown

| Sprint | Phases | Focus | Exit criteria | Status |
|--------|--------|-------|---------------|:------:|
| **1 · Foundation & App** | 0–2 | Repo, production-grade Flask app, hardened container | `make test lint` green; `docker run` serves all routes | ✅ Done |
| **2 · Pipeline** | 3–4 | Gitea Actions CI + Ansible CD, immutable SHA-tagged artifact | Merge to `main` → new container, smoke test passes, zero manual steps | 🟡 In progress |
| **3 · Observability & Demo** | 5–6 | Prometheus + Grafana + Loki, ADRs, runbook, live demo | Incident walkthrough runs end-to-end in < 60s | ⬜ Planned |

## Progress

```mermaid
pie showData
    title Sprint completion
    "Done" : 1
    "In progress" : 1
    "Planned" : 1
```

| Area | State |
|------|:-----:|
| Flask app: JSON error handling, `/echo` 400, tests | ✅ |
| Hardened Dockerfile (non-root, digest-pinned, healthcheck) | ✅ |
| Dependency locking (pip-tools, hashes) | ✅ |
| Gunicorn WSGI runtime | ✅ |
| CI pipeline (lint → test → build → scan → push) | 🟡 |
| CD with Ansible + smoke test + rollback | ⬜ |
| Prometheus / Grafana / Loki observability | ⬜ |
| ADRs, runbook, demo script | ⬜ |

## Stack

| Layer | Tool |
|-------|------|
| App | Flask 3.1 · Gunicorn |
| SCM + CI | Gitea + Gitea Actions (`act_runner`) |
| Artifact | Docker image → local registry (`localhost:5000`), tagged by git SHA |
| Deploy | Ansible + `community.docker` (idempotent) |
| Metrics | `prometheus_client` · cAdvisor · node_exporter |
| Logs | JSON stdout → Grafana Alloy → Loki |
| Dashboards | Grafana (provisioned as code) |

## Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Hello / build info |
| `/health` | GET | Liveness probe |
| `/echo` | POST | Echo JSON · returns `400` on invalid payload |
| `/metrics` | GET | Prometheus metrics *(planned)* |

## Quick start

```bash
# Run tests
pytest

# Build & run the container
docker build -t flaskapp:dev .
docker run -p 8000:8000 flaskapp:dev

# Verify
curl localhost:8000/health        # {"status":"UP"}
curl -X POST localhost:8000/echo -H 'Content-Type: application/json' -d '{"hi":"there"}'
```

## Docs

| Document | Contents |
|----------|----------|
| [`docs/ProjectA.md`](docs/ProjectA.md) | Original assignment brief |
| [`docs/EXECUTION-PLAN.md`](docs/EXECUTION-PLAN.md) | Full phase plan, ADR summary, risks, TODO |
| [`docs/PROJECT-WORKFLOW.md`](docs/PROJECT-WORKFLOW.md) | Branch & commit workflow |
| [`docs/MANUAL-WALKTHROUGH.md`](docs/MANUAL-WALKTHROUGH.md) | Step-by-step manual run |
| [`docs/DevCheatSheet.md`](docs/DevCheatSheet.md) | Command reference |

---

<sub>Deploy target: local Docker host · No Kubernetes (that's Project C) · Every stage runnable via <code>make</code>.</sub>

