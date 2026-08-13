# Contributing

An entry point, not a rulebook. Everything here is a pointer — where two
documents disagree, the one linked is right and this file is stale.

## Before the first commit

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.txt
pre-commit install
```

That last line is not optional and it is not automatic. Cloning a repository
installs no hooks; without it the `gitleaks` check in
[`.pre-commit-config.yaml`](.pre-commit-config.yaml) never runs on your machine.
It is a convenience rather than a gate — the gate is the Trivy step in CI — but
it is the difference between amending a commit and rewriting history. What that
costs, measured, is in [`RUNBOOK.md § A secret reached Git`](docs/RUNBOOK.md).

Running anything else — the app, the platform stack, the deploy, the rollback
drill — is [`DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## The loop

Branch names, the two remotes, which merge strategy goes where, and why a
squash on `release/* → main` is a bug rather than a preference: all of it is
[`BRANCHING.md`](docs/BRANCHING.md). Read rule 7 before you touch the merge
button dropdown — it has been got wrong once already, in PR #31, and the
consequence is recorded in [`PLAN.md`](docs/PLAN.md) §7.

Push to `gitea` first and wait for green. GitHub has no runner, so the pull
request cannot tell a reviewer anything the Gitea run has not already proven.

## What a change has to carry

The Definition of Done is in [`PLAN.md`](docs/PLAN.md) §6 and it is short:
merged through a reviewed pull request, CI green, documentation updated in the
same change, and the claim demonstrable live.

The fourth clause is the one that bites. This repository marks anything it
cannot demonstrate with ⬜, and an unproven claim is treated as worse than a
missing one — so if a change makes something true, run it and record the result
with a date. If it makes something *nearly* true, say so in the same commit.

Commit subjects follow Conventional Commits; the body says **why**. The diff
already says what.

## Decisions

A choice with a real tradeoff gets an ADR in [`docs/adr/`](docs/adr/) at the
time it is made, not reconstructed at the end. If a decision reverses an earlier
one, record it as a reversal rather than editing the old text into agreement.
