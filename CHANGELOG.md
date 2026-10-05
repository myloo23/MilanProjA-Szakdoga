# Changelog

What shipped, per sprint checkpoint. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are sprint
tags rather than semver, because this project releases on the sprint boundary
the mentors validate, not on a compatibility promise it does not make.

**This file absorbs the deployment record.** The mentors' Git strategy training
asks for a separate `DEPLOYMENTS.md`. Two files would have to be kept true
about the same events, and the second one to fall behind would be the one
nobody reads — so what was deployed is recorded here, against the tag it was
deployed from.

**Deploys are traceable by SHA regardless of this file.** Every image is tagged
by git SHA and the running container carries a `version` label; that is the
authority. This is the human-readable index over it.

## [szakdolgozat] — `release/meres`, 2026-09-17 … 2026-10-05

The thesis rebuild: same pipeline and evidence discipline, new target. Detail
and reasoning per step: [`szakdolgozat/naplo.md`](szakdolgozat/naplo.md).

### Added

- Terraform for the Azure VM (resource group, network, NSG, static IP, VM);
  cloud-init installs k3s, so the cluster comes up with no manual step
  ([`terraform/`](terraform/), ADR-0008)
- Helm chart: backend ×2, frontend ×2, PostgreSQL with a PVC and schema,
  Traefik ingress ([`chart/`](chart/))
- Frontend: Vite + React + TypeScript, served by unprivileged nginx, `/api`
  proxied to the backend
- Backend: notes CRUD on PostgreSQL, `/version` (build SHA — the measurement's
  acceptance criterion), readiness that checks the database, multiprocess-safe
  metrics under Gunicorn
- Platform on the VM: Gitea, act_runner, registry via `compose.azure.yaml`
- Observability on k3s: Prometheus discovers the backend pods through the k3s
  API with a read-only ServiceAccount, Alloy ships pod logs to Loki (ADR-0010)
- Measurement: 10 manual and 10 automated deploys, 3 + 3 recoveries, with
  transcripts, job logs and CSVs ([`szakdolgozat/bizonyitek/meres/`](szakdolgozat/bizonyitek/meres/));
  figures generated from them by `scripts/abrak-6-fejezet.py`
- Third SBOM generation, built on the VM from the measured release `e4da1d9`:
  seven SBOMs, 771 components, frontend image included ([`docs/sbom/`](docs/sbom/))
- Frontend image gates: hadolint and Trivy, same pins and threshold as the
  backend (added after the measurement closed)
- `scripts/pin-base-images.sh` — re-pins base-image digests only after they pass
  the pipeline's Trivy gate

### Changed

- **Deploy: Helm on k3s replaces Ansible on the Docker host** (ADR-0009). The
  deploy job records the running revision, runs `helm upgrade --wait`, verifies
  with the existing `verify` play, and on failure runs `helm rollback --wait`
  and verifies the previous SHA
- Both images are built and pushed under one SHA tag
- VM `lifecycle { ignore_changes = [custom_data] }` — a cloud-init edit no
  longer replaces the machine

### Fixed

- `requirements-dev.txt` was not recompiled after `psycopg` entered
  `requirements.in`; only the test environment broke, and only the pipeline
  noticed
- Pipeline images built without `GIT_SHA` reported `dev` on `/version`

### Deployed

- `e4da1d9` — the last run of the automated measurement series; the release the
  SBOMs describe

### Known issue

- Backend base image carries a fixed-upstream HIGH (`libpcre2-8-0`,
  CVE-2026-103111) not yet in a published `python:3.12-slim`; the pipeline stays
  red until `scripts/pin-base-images.sh` finds a clean digest. The gate is not
  relaxed

## [sprint-3, not tagged] — `release/sprint3`

### Added

- `gitleaks` pre-commit hook, pinned at v8.30.1
  ([`.pre-commit-config.yaml`](.pre-commit-config.yaml))
- Trivy `fs --scanners secret` step in CI — the gate the hook is not. Closes F6
  of [the 2026-08-10 security review](docs/security-review-2026-08-10.md)
- Leaked-secret incident procedure, rehearsed 2026-08-10, in
  [`RUNBOOK.md`](docs/RUNBOOK.md)
- `CONTRIBUTING.md`, and this file

### Notes

- The pre-commit hook was observed blocking a commit on 2026-08-10; output in
  [`RUNBOOK.md`](docs/RUNBOOK.md). It matched on entropy rather than on AWS key
  format, and reads the staged diff rather than history — so it stops the next
  mistake, and the CI step is what covers the other forty-seven commits
- `pre-commit` 4.6.1 and nine transitive dependencies enter the dev lock; the
  application lock is unchanged apart from its `pip-compile` header
- The CI gate was verified by making it fail: a key committed with `--no-verify`
  got past the hook and was stopped by the pipeline, 2026-08-10
- Trivy `fs --scanners misconfig` is deliberately **not** included and stays
  open in [`PLAN.md`](docs/PLAN.md), as is secret scanning of git *history* —
  both new checks read the working tree, not the commit log
- Sprint 3 workstream A (observability) is **complete and verified**; workstream
  B (pipeline control flow) is partial — `timeout-minutes` shipped and the
  `act_runner` spike is done, but conditional execution, `continue-on-error`
  and retry are proven rather than applied, and `fromJSON()` fan-out closes as
  an unsupported-tool limitation. See [`PLAN.md`](docs/PLAN.md)

### Fixed

- Error-rate panel drew green across a 96% spike. Its colour came from the
  classic palette instead of its thresholds, no threshold line was rendered,
  and its red step sat at `0.2` while the alert rule fires at `0.1` — so the
  dashboard and the alert disagreed about what counts as bad. `color.mode`,
  `gradientMode` and the threshold steps corrected in
  `app-golden-signals.json`; reasoning kept in the panel description

### Corrected

- **The rollback drill's numbers moved on its third run.** 2026-07-31 and
  2026-08-04 both measured 27s to detect and 7s to recover, a 34s outage.
  2026-08-11 measured 29s and 8s, a 37s outage. Documentation described the
  drill as reproducing identical numbers, which held for two runs and no longer
  does. It reproduces to within a few seconds, and **37s** is the figure now
  quoted — the worst of the three, from the freshest transcript
- **Status tables corrected on 2026-08-11.** JSON logging, `/metrics`,
  Prometheus, Grafana, Loki, the metric-to-log link and the alert rule were all
  shipped and verified between 2026-08-08 and 2026-08-10 but left marked ⬜, so
  `README.md` and `PLAN.md` understated the project for three days. The
  capability commit and the status commit are deliberately separate; the
  failure was that the second one did not follow

### Process

- **Five merges reached `origin` and never reached `gitea`**, 2026-08-08 to
  2026-08-11. CI ran on the feature branches, CD did not run at all, and the
  deployed container stayed at `ed19d73` for three days while every branch
  showed green. Reconciled 2026-08-11: run #87 green on `release/sprint3`,
  deploy verified against the container's `version` label. Recorded in
  [`BRANCHING.md`](docs/BRANCHING.md) alongside the PR #31 squash — the same
  failure shape twice, and the argument for the branch protection this plan
  cannot enable

## [sprint-2] — 2026-08-03

*Artifact to Running Container.* Content identical to `main` at `a644b91`; the
tag preserves the branch history that the squash merge in PR #31 did not carry
over.

### Added

- `deploy_app` Ansible role with an in-role smoke test, and the CD job that uses
  it
- `hadolint` on the Dockerfile and `ansible-lint` at the production profile,
  both pinned, both failing rather than warning
- SBOM inventory, 621 components ([`docs/sbom/`](docs/sbom/))
- [ADR-0003](docs/adr/) and
  [ADR-0004](docs/adr/0004-github-for-review-gitea-for-execution.md)

### Changed

- Trivy pinned to 0.72.0 — the version that produced the SBOM, so the scanner
  gating the build is the scanner that wrote the inventory
- Control-node Ansible requirements hash-locked, to the same standard as the
  application locks

### Deployed

Rollback rehearsed 2026-07-31: **~34s outage window** — 27s to detect, 7s to
roll back. The detect number leads because it is the one that matters; the swap
happens before verification, so the broken image served 500s for the whole
detection window. Full evidence in [`RUNBOOK.md`](docs/RUNBOOK.md).

---

Sprints before `sprint-2` are not written up here. They predate the tag and
reconstructing them from `git log` after the fact would produce a record written
to look tidy rather than one kept as things happened — which is the failure mode
this file exists to avoid.
