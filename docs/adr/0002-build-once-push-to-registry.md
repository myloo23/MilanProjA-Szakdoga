# ADR-0002: Build the image once and push to a local registry (immutable artifact)

## Status

Accepted — 2026-07-27

## Context

CI produces a Docker image; something then has to run it. There are two
broad ways to get from "image built" to "container running":

1. **Build and run on the same host** — the CI job builds the image and
   immediately `docker run`s it on the same machine.
2. **Build once, push, deploy from the artifact** — CI builds the image,
   pushes it to a registry under an immutable tag, and a separate deploy
   step pulls that exact image and runs it.

The distinction matters because it decides whether the thing being deployed
is *traceable and reproducible* or just *whatever was on the build machine
at the time*.

## Decision

Build the image once in CI and **push it to a local registry
(`localhost:5001`) tagged by the git commit SHA**. Deployment (Ansible, in a
later phase) pulls that exact SHA-tagged image — it never rebuilds. The tag
is the git SHA, never `latest`.

## Consequences

**Positive**

- **Immutable and traceable:** a running container maps to exactly one
  commit. There is no ambiguity about what code is in production.
- **Rollback is trivial:** deploy the previous SHA. No rebuild, no guessing.
- **CI and CD are cleanly separated:** CD deploys the artifact CI produced,
  which is what makes "no rebuild in CD" possible.
- Forces the discipline of immutable artifacts, which is the whole point of
  a real pipeline versus a demo.

**Negative / trade-offs**

- Requires running and maintaining a registry component.
- Introduces the `localhost:5001` (host-published) vs `registry:5000`
  (in-network container name) resolution nuance: the runner pushes to
  `localhost:5001`, but a container on the shared network resolves the
  registry as `registry:5000`. This has to be understood or pushes/pulls
  fail confusingly.

## Alternatives considered

- **Build-and-run on the same host (option 1).** Simpler, no registry — but
  it produces no stored, versioned artifact, has no provenance, and no clean
  rollback path. It demonstrates that an image *can* run, not that a
  *pipeline* delivers a traceable release. Rejected as a demo, not a
  pipeline.
