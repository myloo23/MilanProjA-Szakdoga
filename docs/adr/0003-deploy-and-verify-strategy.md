# ADR-0003: Ansible deploys the artifact, and verification gates the deploy

## Status

Accepted — 2026-07-30

## Context

[ADR-0002](0002-build-once-push-to-registry.md) settled *what* gets deployed.
Two questions were still open, and both had a tempting cheap answer.

**What drives the deploy?** A shell script in the CI job works immediately, but
it describes actions rather than desired state, so it cannot be idempotent, and
it exists only inside the pipeline, so a deploy cannot be reproduced locally.

**How does the pipeline know it worked?** `docker run` exiting 0 means the
container *started*, not that the application *works*. A container that starts
and fails every request is a successful `docker run` and a failed deploy.

Underneath both: waiting. You can sleep a fixed number of seconds and hope, or
poll a signal the application emits. The Ansible smoke test used `uri` with
`retries`/`until` from day one. CI used `sleep 5`. Both were "waiting for the
app"; only one made a claim about it. The `sleep` passed consistently, which is
exactly what made it dangerous — a timing bet that has not lost yet looks
identical to a correct wait.

## Decision

**Ansible drives the deploy.** The `deploy_app` role declares desired container
state and `community.docker` reconciles it. The same playbook runs from CI and
from a laptop; only the vantage point differs.

**Verification fails the deploy, it does not warn.** The smoke tasks run inside
the deploy play and every one is a gate: health, readiness, an `/echo` round
trip asserted on both wrapper and content, and a negative case asserting a bad
`Content-Type` still returns 400 rather than 500. On failure the `rescue` block
reports the previously running version and prints the exact rollback command.

**Every wait is gated on a signal, never a timer.** The deploy waits with `uri`
+ `retries`/`until`. CI polls `docker inspect` until the container's own
`HEALTHCHECK` reports healthy. Both are bounded and both fail with diagnostics.

**Health checks and network checks are different assertions, so both stay.**
`HEALTHCHECK` probes `localhost` from inside the container: it proves the app is
up and structurally cannot detect an app that is healthy but unreachable. CI
therefore keeps a `curl` across the network *after* the health gate passes.

## Consequences

**Positive**

- Re-running with an unchanged SHA reports `changed=0`; a new SHA redeploys.
  Reruns are safe by construction, not by convention.
- One definition of "healthy", used by the pipeline and by hand, so the two
  cannot quietly disagree.
- Failures are attributable: health gate red means it never came up, network
  check red means it came up but is unreachable.
- The rollback command is printed at the moment it is needed, not reconstructed
  under pressure.

**Negative / trade-offs**

- Ansible is heavier than a shell script: collections and control-node packages
  must be present on the runner, and their absence is its own failure class.
- The `host` vs `network` vantage split is real complexity that has to be
  understood before reading smoke output.
- Gating on health was expected to cost ~5s per run versus `sleep 5`. Measured,
  it cost nothing: both runs took 23s, because Docker probes during the
  `HEALTHCHECK` start period. The prediction was wrong and the measurement
  decided — noted here rather than quietly dropped.

## Alternatives considered

- **Shell script deploy in the CI job.** Cannot express desired state, so it
  cannot be idempotent, and it cannot be reproduced locally. Rejected.
- **Verification as a non-blocking warning.** Keeps the pipeline green while the
  app stabilises, and trains everyone to ignore it. Rejected.
- **A hand-rolled `curl` retry loop instead of reading the container's health
  state.** Functionally close, but it duplicates the definition of "healthy" in
  a second place. Two definitions drift, and the drift surfaces as a pipeline
  that passes while production fails. Rejected.
