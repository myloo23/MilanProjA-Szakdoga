# ADR-0003: Ansible deploys the artifact, and verification gates the deploy

## Status

Accepted — 2026-07-30

## Context

ADR-0002 established that CI produces one immutable, SHA-tagged image. That
settles *what* gets deployed. It says nothing about *who* deploys it, or how
the pipeline decides the deploy worked.

Two questions were still open, and both had a tempting cheap answer:

1. **What drives the deploy?** A shell script in the CI job (`docker stop`,
   `docker rm`, `docker run`) is a few lines and works immediately. The cost
   is that it is not idempotent, describes actions rather than desired state,
   and cannot be run from a laptop against the same host without drifting
   from what the pipeline does.

2. **How does the pipeline know the deploy succeeded?** The cheap answer is
   that the deploy command exited 0. But `docker run` exiting 0 means the
   container *started*, not that the application *works*. A container that
   starts and immediately fails every request is a successful `docker run`
   and a failed deploy.

Underneath both sits a third question that this project got wrong once and
in exactly one place. Waiting for an application to become available can be
done two ways: sleep a fixed number of seconds and hope, or poll a signal the
application itself emits until it says ready. The Ansible smoke test used
`uri` with `retries`/`until` from the day it was written. The CI job used
`sleep 5`. Both were "waiting for the app"; only one of them was making a
claim about the app. The `sleep 5` passed consistently, which is precisely
what makes it dangerous — a timing bet that has not yet lost looks identical
to a correct wait.

## Decision

**Ansible drives the deploy.** The `deploy_app` role declares the desired
container state — image by SHA, restart policy, resource limits, log driver —
and `community.docker` reconciles it. The same playbook runs from CI and from
a laptop; the vantage point differs (`deploy_app_smoke_vantage`), the
definition of the deploy does not.

**Verification fails the deploy, it does not warn.** The smoke tasks run
inside the deploy play, and every one of them is a gate: health, readiness,
an `/echo` round trip asserted on both wrapper and content, and a negative
case asserting a bad `Content-Type` still returns 400 rather than 500. A
deploy that cannot prove the application works is a failed deploy. On failure
the role's `rescue` block reports the previously running version and prints
the exact rollback command.

**Every wait is gated on a signal, never on a timer.** Concretely:

- The **deploy** waits with `uri` + `retries`/`until` against `/health`.
- **CI** polls `docker inspect`'s health state until the container's own
  `HEALTHCHECK` reports `healthy`.

Both are bounded, and both fail loudly with diagnostics rather than
continuing on an assumption.

**Health checks and network checks are different assertions and both are
kept.** `HEALTHCHECK` probes `localhost` from inside the container: it proves
the application is up, and it structurally cannot detect an application that
is healthy but unreachable from another container on the shared network. CI
therefore keeps a `curl` across `projecta-platform` *after* the health gate
has passed — no longer racing startup, and now failing for exactly one
reason.

## Consequences

**Positive**

- Deploys are idempotent: re-running with an unchanged SHA reports
  `changed=0`, while a new SHA redeploys. Reruns are safe by construction,
  not by convention.
- One definition of "healthy", exercised identically by the pipeline and by
  hand, so the two cannot quietly disagree.
- A green pipeline is a statement about the application, not about the
  runner's timing. Failures are attributable: health gate red means the app
  never came up, network check red means it came up but is unreachable.
- Rollback is a documented one-liner printed at the moment it is needed,
  rather than something to be reconstructed under pressure.

**Negative / trade-offs**

- Ansible is a heavier dependency than a shell script: collections and
  control-node Python packages must be installed on the runner, and their
  absence is its own class of failure (see #20).
- Gating on health is *slower* than `sleep 5` in the happy case. The image's
  `HEALTHCHECK` has a 10s interval, so CI typically learns the container is
  healthy at ~10s rather than assuming it at 5s. This is the correct trade:
  five seconds of wall clock bought with a guess is not a saving.
- The vantage-point split (`host` vs `network`) is real complexity that has
  to be understood before reading the smoke output, because the application
  answers at two different addresses depending on who is asking.

## Alternatives considered

- **Shell script deploy in the CI job.** Fastest to write, and the reason it
  was rejected is not aesthetic: it cannot express desired state, so it
  cannot be idempotent, and it exists only inside the pipeline, so there is
  no way to reproduce a deploy locally. Rejected.
- **Verification as a non-blocking warning.** Tempting because it keeps the
  pipeline green while the app is still being stabilised. Rejected: a check
  that cannot fail the build is a log line, and it trains the team to ignore
  it.
- **A hand-rolled `curl` retry loop in CI instead of reading the container's
  health state.** Functionally close, and rejected because it duplicates the
  definition of "healthy" in a second place. The image already declares it;
  two definitions drift, and the drift surfaces as a pipeline that passes
  while production fails.
