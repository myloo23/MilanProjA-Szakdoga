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

## [Unreleased] — `release/sprint3`

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
- Sprint 3 workstreams A (observability) and B (pipeline control flow) are in
  progress — see [`PLAN.md`](docs/PLAN.md)

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
