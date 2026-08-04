# ADR-0001: Self-hosted Gitea + Gitea Actions for SCM and CI

## Status

Accepted — 2026-07-27. Partly superseded by
[ADR-0004](0004-github-for-review-gitea-for-execution.md): GitHub is the origin
and owns review, Gitea owns execution. The self-hosted runner, registry and
Docker socket decided here are unchanged.

## Context

The project needs source control and a CI system. The brief emphasises a
fully-owned, self-hosted pipeline: the value being demonstrated is
understanding the whole delivery chain — runner, registry, Docker socket —
not just wiring up a hosted service. At the same time the skills learned
should transfer to the tooling used in industry, and the work should stay
visible as a portfolio piece.

The realistic options were a hosted forge (GitHub with GitHub-hosted
Actions runners) or a self-hosted forge with its own runner.

## Decision

Self-host **Gitea** with the **`act_runner`** executor, writing pipelines in
Gitea Actions' **GitHub-Actions-compatible YAML**. The runner is registered
to the local Docker host and builds/pushes images through the mounted Docker
socket. The repository is mirrored out to a public GitHub repo for portfolio
visibility.

## Consequences

**Positive**

- Full ownership of the entire pipeline — Gitea, the runner, the local
  registry, and the Docker daemon all sit on infrastructure I control and
  can explain end to end.
- The workflow syntax is GitHub-Actions-compatible, so the `ci.yml` I write
  here transfers almost verbatim to GitHub Actions.
- Self-hosting is what makes the "immutable artifact to a local registry"
  and "deploy via the same host" story possible (see ADR-0002).

**Negative / trade-offs**

- I own the maintenance: keeping Gitea, the runner, and the registry
  running is on me, not a managed service.
- Not every GitHub Marketplace action is guaranteed to run under
  `act_runner`; some assume GitHub-hosted specifics, so third-party actions
  must be verified rather than trusted blindly.
- Mounting the Docker socket into the runner is a privilege-escalation path
  in a real environment — acceptable for a single-owner local setup, but in
  production the answer would be rootless Docker / BuildKit-in-container.

## Alternatives considered

- **GitHub with GitHub-hosted runners.** Zero infra to maintain, but it
  hides exactly the parts of the pipeline the project is meant to
  demonstrate (runner, registry, daemon), and weakens the ownership story.
  Kept as the *mirror* target for visibility instead.
