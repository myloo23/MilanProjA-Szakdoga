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
`ruff → hadolint → pytest (80% gate) → ansible-lint → build → health gate →
network check → trivy → push → reclaim`. Fail-fast in cost order — `ansible-lint`
sits after the checks that need no installation and before the build. Every tool
is pinned exactly, Trivy included since `a6a4d33`; a scanner on a floating tag
turns a build nobody touched red. `reclaim` removes the SHA-tagged image after
the push, so the runner's disk does not grow by one image per run.
⬜ Remaining: build metadata via `--build-arg`, surfaced on a `/version` endpoint.

**Phase 4 — CD with Ansible** ✅

- ✅ `ansible/` scaffold with an inventory-driven `docker_host`, so a remote
  target costs an inventory edit and no role change
- ✅ `deploy_app` role: pull by SHA, run with limits and log rotation, then a
  smoke test that fails the play. On failure it dumps the last 50 log lines and
  prints the rollback command with the previous SHA already filled in
- ✅ `deploy` job gated on `needs: build-test-push` and a ref check. **No rebuild
  in CD** — it deploys the artifact CI tested
- ✅ **Rollback rehearsed** end to end on 2026-07-31: a deliberately broken image
  deployed, the smoke test failed the deploy and printed its own rollback
  command, that command restored service in **7s**. Evidence in
  `docs/RUNBOOK.md`; full transcript in commit `eac8fe5`;
  repeatable via `scripts/rollback-drill.sh`
- ⬜ **Zero-downtime swap.** The drill measured what replace-then-verify costs:
  the broken container was live for **27s** before the smoke test gave up, so the
  real outage window is ~34s, not 7s. Known P2 item, now a number instead of a
  note
- ⬜ `ansible-vault` — deliberately not built. Nothing here is secret yet, and
  vault before a secret is ceremony, not security

**Phase 5 — Observability** ⬜ *Next*
Prometheus (app, cAdvisor, node_exporter), Grafana provisioned as code with two
dashboards, Alloy → Loki with JSON parsing, a data link from error rate to the
filtered log query, one alert rule.

**Phase 6 — Pipeline control flow** ⬜
Conditional stage and job execution, `timeout-minutes`, `continue-on-error`,
retry on the steps that fail for reasons unrelated to the change, and dynamic
fan-out to a matrix built at runtime. Added after the Sprint 2 review on
2026-08-05 at the mentor's request; the pipeline currently runs every step
unconditionally except the ref gate, which is a defensible default and not a
demonstration of knowing the alternatives. Bounded by what `act_runner`
actually supports — see Sprint 3, workstream B.

---

## 3. Milestones

| Milestone | Complete when | Status |
|---|---|:--:|
| **M1 — Pipeline Foundation** | A commit triggers lint, test, build, scan, push of an immutably tagged image | ✅ |
| **M2 — Automated Delivery** | A reviewed merge deploys that exact image, with a smoke test that can fail the deploy | ✅ ¹ |
| **M3 — Observability** | Metric spike → one click to the matching logs; dashboards as code | ⬜ |
| **M4 — Production Readiness** | Rollback rehearsed, ADRs written, clean-machine reproducible, demo scripted | 🟡 |

¹ The deploy, the smoke gate and the rollback are all demonstrated. "Reviewed"
is followed by hand rather than enforced — rulesets and `CODEOWNERS` do not
apply to private repositories on this plan. Marked ✅ because the delivery
mechanism is complete and the gap is a billing tier, not missing work; the
qualification is stated rather than buried.

### Sprint 1 — "Commit to Artifact" ✅

Platform stack via compose, app hardening, coverage gate, hardened Dockerfile,
`ci.yml` through to the registry push, ADR-0001 and ADR-0002.

### Sprint 2 — "Artifact to Running Container" ✅

*Goal: a reviewed merge deploys the exact image CI built, verifies it, and can be
rolled back in under a minute.*

Delivered: the `deploy_app` role; the in-role smoke test; the `deploy` job;
health-gated waits replacing a fixed `sleep`; `hadolint`; ADR-0003 and ADR-0004.

Unplanned but delivered: the review model changed mid-sprint. GitHub became the
source of truth for review, Gitea kept execution. Protection and CODEOWNERS are
configured but not enforced — that needs a public repository on this plan, and
the work stays private.

Also delivered: `ansible-lint` at the `production` profile; the rollback
rehearsal, executed rather than asserted — 7s to recover, with the ~34s total
outage window measured and recorded rather than quietly averaged away
(`docs/RUNBOOK.md`).

**After the sprint closed (2026-08-03), a hardening pass.** Recorded here rather
than folded into the sprint above, because the sprint goal was met at PR #25 and
a board that quietly absorbs later work stops telling the truth about what was
planned versus what was found.

- **Software inventory / SBOM** — six CycloneDX SBOMs, 621 components, every
  command reproducible (`docs/sbom/`). Bonus scope, and it paid for itself: it
  found the gunicorn drift below
- **gunicorn production/CI drift, fixed** (#28). `requirements.txt` shipped
  `23.0.0` while `requirements-dev.txt` installed `26.0.0`; both compiled from a
  `requirements.in` that left them unpinned. `DEVELOPMENT.md` also documented a
  `pip-compile` command missing `--allow-unsafe`, which would have regenerated
  the dev lock without its `pip`/`setuptools`/`wheel` pins — the drift had two
  sources and both are closed
- **Two Dependabot alerts on `requests`, closed** (#29). Control-node only —
  `community.docker` imports it to reach the Docker daemon; it is absent from
  the shipped image
- **Trivy pinned to `0.72.0`.** It was the one tool in the pipeline still on
  `latest`, against the argument this repo already makes for `hadolint`. The
  scanner that gates the build is now the scanner that produced the SBOM
- **CI reclaims its own disk.** Every run built a SHA-tagged image that nothing
  ever removed; on a host also carrying Gitea, the registry and the deployed
  container, that ends as a full disk during a demo
- **SBOM regenerated** against `a6a4d33` after its own staleness guard fired —
  see `docs/sbom/README.md`, "Guard history"

Nothing open. The sprint goal is met with one honest qualification: "a
**reviewed** merge" is a process the repository follows by hand, not one it
enforces, because rulesets and `CODEOWNERS` do not apply to private
repositories on this plan. Configured, documented, unenforced — see
[`BRANCHING.md`](BRANCHING.md).

**Review demo**

1. Open a pull request and show the ruleset and `CODEOWNERS` config. **Do not
   claim the merge is blocked — it is not.** Rulesets and `CODEOWNERS` are
   inert on a private repository on this plan, so the Reviewers field stays
   empty and the merge button stays green. Say that before anyone clicks it:
   the rules exist, the plan does not enforce them, and the process compensates
   by hand ([`BRANCHING.md`](BRANCHING.md)). Naming the limitation is stronger
   than demonstrating a block that will not happen.
2. Merge → CD runs → the new container is live and the smoke test passes.
3. The container's `version` label matches the merge commit:
   `docker inspect --format '{{index .Config.Labels "version"}}' projecta-flask`
   against `git rev-parse HEAD`.
4. Run the deploy a second time → `changed=0`. Verified 2026-07-31 against
   `fbc1254e`: `ok=11 changed=0`, every smoke check re-run and passing.
   Idempotence shown, not claimed.
5. Deploy a broken image → the smoke test fails the deploy and prints its own
   rollback command → roll back with one line. Rehearsed 2026-07-31: 27s to
   detect, 7s to recover. Quote the ~34s outage window, not the 7s — replace
   -then-verify means the smoke test bounds downtime rather than preventing it,
   and saying so first is stronger than being asked. Repeat with
   `scripts/rollback-drill.sh`.

### Sprint 3 — "See What's Happening, and Control What Runs" ⬜ *Next*

Two workstreams, deliberately named separately. **A** is the observability work
this roadmap always planned. **B** came from the Sprint 2 review with
G. Kovalcsik on 2026-08-05 and is unrelated to it — folding B into A would make
the sprint goal describe half of what the sprint contains.

**A — Observability**

Prometheus, Grafana as code, Alloy → Loki, the metric-to-log data link, one
alert rule, a load-generation script, ADRs for Loki-over-ELK and for metric
cardinality. Depends on the two open Phase 1 items: structured JSON logging with
`request_id`, and `/metrics`.

**B — Pipeline control flow**

The mentor's framing: the point is to *try* the conditional mechanisms, not to
need them. A pipeline whose behaviour is obvious from reading it is the goal;
these are the tools that make it non-obvious if used without cause.

- ⬜ **Conditional stage and job execution.** Deliberate experiments with
  `if:`, job-level conditions and reusable outputs, on branches that are
  allowed to fail. What passes goes in `ci.yml`; what does not goes in the ADR
- ⬜ **`timeout-minutes`** on the steps that can hang. Today nothing bounds the
  Trivy download, the health wait or the deploy — a hung step holds a runner
  with capacity 1 until someone notices
- ⬜ **`continue-on-error`** where a failure should be reported and passed over
  rather than stopping the run. Every gate in this pipeline currently fails
  hard, by the rule in §6. Anything given this treatment has to be argued for
  in the same commit — the rule stays, the exception gets a name
- ⬜ **Retry** on the steps that fail for reasons unrelated to the change:
  registry pulls, the Galaxy collection install, the Trivy DB fetch. Actions
  has no native step retry, so this is an action dependency or a shell loop
- ⬜ **Dynamic fan-out to N parallel jobs** — a matrix built from a previous
  job's output via `fromJSON()`. The least likely of the five to work here;
  see the spike below
- ⬜ **ADR — when a second workflow beats a nested conditional.** Kovalcsik's
  actual warning: developers over-complicate a single file with `if`/`else`/`and`
  until nobody can say why a stage was skipped, and at that point two plain YAML
  files are the simpler artefact. Write the threshold down before the pipeline
  reaches it

**Already satisfied, do not rebuild.** He also said feature branches should not
push containers. `ci.yml` has done this since `fbc1254`: the `ref_gate` step
computes `ships` once from `github.ref` and both the push step and the `deploy`
job consume it, so only `main` and `release/*` reach the registry. Show him the
step rather than writing a new one.

**Spike first — `act_runner` capability.** Timeboxed to half a day, before any
of B is planned in detail. Retry, `timeout-minutes`, `continue-on-error` and a
`fromJSON()` matrix each get a throwaway branch and a recorded result. The
precedent is in `ci.yml` itself: the ref gate is a shell `case` rather than
`startsWith()` because expression support under `act_runner` was not worth
betting a release gate on. Kovalcsik explicitly said it is fine if the tool
does not support these. So a documented limitation is a deliverable here, not
a miss — and by §6, an unproven claim is worse than a missing one.

**Review demo** — the deck, not the pipeline. Kovalcsik reviewed the Sprint 2
demo and said the HTML worked as it was, that there is rarely time for a live
pipeline run and it carries risk anyway, and that a recorded-and-sped-up run is
worse than a screenshot. He is not a fan of live demos even after a hundred
rehearsals.

So the incident from the brief gets *captured*, not performed: malformed
requests fired at `/echo`, the error rate spiking, the alert firing, the click
through to the filtered logs, and the failing payload with its `request_id` —
each a still, in the `PROJECT-GUIDE.html` format that worked last time, with the
environment left warm in case someone asks to see it live.

This reverses what this section said until 2026-08-05, and the reversal is the
point: the live walkthrough was planned against an assumption about what
reviewers want, and the reviewer has now said otherwise. Recorded rather than
quietly edited, because the next sprint will face the same temptation.

The sentence that still has to be said out loud: why `request_id` is a log
field and not a Prometheus label. That one is worth more than another
dashboard, and it does not need a live pipeline to land.

### Hardening week ⬜

No new features. Remaining ADRs, `CHANGELOG.md`, the clean-machine test,
`DEMO.md`, two timed rehearsals on a cold machine — the cold run is what turns
today's warm-host rollback number into a defensible one.

---

## 4. Open work

**P0 — must exist or the project fails**

- [x] Platform stack, registry, CI through to push, Ansible deploy, deploy job
- [x] A README a stranger can follow to a running stack
- [ ] Prometheus scraping `/metrics`; a dashboard with rate, errors, latency
- [ ] Alloy → Loki, logs queryable by `level` and `path`

**P1 — the difference between "works" and "senior"**

- [x] `/echo` 400 handling, coverage gate, Trivy scan, Gunicorn, secrets out of Git
- [x] **`/echo` answers every hostile body with a client error, not a 500.** The
      original 400 handling caught the two exceptions Werkzeug raises and missed
      the one the interpreter does: deeply nested JSON raised `RecursionError`,
      which is not a `ValueError`, so it reached the generic 500 handler.
      Unauthenticated, and a 500 moves the error rate the alert rule watches.
      Fixed alongside `MAX_CONTENT_LENGTH`, which was unset — a 5 MB body was
      read and reflected in full. F1 and F2 in
      [`security-review-2026-08-10.md`](security-review-2026-08-10.md); both
      reproduced before the fix and guarded by pytest and by `smoke.yml`
      afterwards. Two corrections are recorded against F1 in that document: the
      recursion depth is a property of the host rather than a constant since
      CPython 3.12, so nothing asserts a depth — only that no body inside the
      size limit yields a 5xx; and `/echo` reflects its input, so the response
      path recurses as well and the first fix guarded only half of it
- [x] Post-deploy smoke test that fails the deploy
- [x] `hadolint` in CI
- [x] `ansible-lint` in CI — `production` profile, gated in `build-test-push`
- [x] **Rollback rehearsed**, not just documented — 7s, `docs/RUNBOOK.md`
- [ ] Structured JSON logging with `request_id`
- [ ] Grafana provisioned as code, cAdvisor and node_exporter
- [x] Runbook — `docs/RUNBOOK.md`, Deploy and Rollback sections
- [ ] Remaining ADRs
- [ ] **`timeout-minutes` on the steps that can hang.** Nothing bounds the Trivy
      download, the health wait or the deploy today. On a runner with capacity
      1, one hung step is an outage of the whole pipeline
- [ ] **Conditional execution, tried on purpose** — `if:`, job conditions,
      `continue-on-error`, retry. Mentor request, 2026-08-05
- [x] **Nothing in the stack listens beyond this host.** Every published port
      bound `0.0.0.0`, so the registry — which has no authentication and which
      CD deploys from by tag — was reachable by anyone on whatever network the
      laptop had joined, as were Prometheus's lifecycle endpoint and Loki. Now
      `127.0.0.1`, in `compose.yaml` and in the deploy role, at no cost to the
      pipeline: containers address each other by name and never through a
      published port. F4 in
      [`security-review-2026-08-10.md`](security-review-2026-08-10.md)
- [x] **The build context carries only what the Dockerfile copies.**
      `.dockerignore` was a deny-list whose `.env` entry matched the context
      root and therefore not `platform/.env`, which was sent to the daemon on
      every build. Inverted to an allow-list, so the next secret to land in
      this repository is excluded by default rather than by memory. F5, same
      document. Also F9: `docker image prune --force` took no filter and
      deleted every dangling image on the host, which is only harmless while
      the host is certainly yours — and risk B1 has not answered that

**P2 — only after P0 and P1**

- [x] **SBOM** — six CycloneDX files, 621 components, `docs/sbom/`. Point-in-time
      and committed, so it goes stale by design; the staleness guard in its
      README is the compensating control, and it has fired once already
- [ ] Alert routing, zero-downtime swap, auto-changelog
- [ ] **Dynamic fan-out to N parallel jobs** — a matrix built from a previous
      job's output. P2 because this pipeline has nothing to parallelise: one
      image, one target. Carried as a capability to demonstrate rather than a
      problem to solve, and honest about which it is
- [ ] **Automated dependency updates.** Dependabot alerts are being acted on by
      hand (two closed in #29). Nothing regenerates the SBOM or opens the bump
      automatically — a `schedule:` job in `ci.yml` is the obvious next step and
      is deliberately not built yet
- [x] **Hash-lock the Ansible requirements.** Both control-node locks are now
      `pip-compile --generate-hashes` output, installed with `--require-hashes`
      in CI — the same standard as the application locks. `requirements.yml`
      stays version-pinned only: Galaxy collections have no hash-locking
      equivalent, which is an ecosystem limitation rather than a gap

### From the mentors' Git strategy training

Reference material lives outside the repo (see `.gitignore`); what it asks for
that is not already done is tracked here, because a reviewer should find open
work in one place rather than two.

Most of it is already satisfied: branch protection, CODEOWNERS, conventional
commits, squash for `feature/*` and a merge commit for `release/* → main` are
all configured and reasoned about in [`BRANCHING.md`](BRANCHING.md). Genuinely
outstanding:

- [x] Pre-commit hooks with `gitleaks`, pinned at v8.30.1 in
      `.pre-commit-config.yaml`. The review's point in F6 stands and is now
      acted on: a hook is client-side and `--no-verify` skips it, so the
      enforcing check is a Trivy `fs --scanners secret` step in `ci.yml`, placed
      immediately after Ruff on the fail-fast cost order. The hook is the
      two-second warning, the CI step is the gate. **Both halves proven on
      2026-08-10** — the hook blocked a commit locally, and the CI step failed a
      build on a branch that used `--no-verify` to get past the hook. Evidence
      in [`RUNBOOK.md`](RUNBOOK.md)
- [x] Watched the hook block a commit, 2026-08-10. Output recorded in
      [`RUNBOOK.md`](RUNBOOK.md). It fired as `generic-api-key` on entropy 3.55
      rather than as `aws-access-token` on format, and reported `0 commits
      scanned` — so what is proven is that the hook stops *this* secret in the
      staged diff, not that it recognises credential formats or looks at
      history. History is the CI step's job
- [x] Rehearse the leaked-secret drill. Done 2026-08-10 against a throwaway
      clone at 50 commits, all three cases, written up in
      [`RUNBOOK.md`](RUNBOOK.md). The finding worth carrying: **`git revert -m 1`
      does not remove a secret** — the working tree is clean afterwards and the
      credential is still readable by SHA. It looks like it worked, which is
      what makes it dangerous. `filter-repo` cleared 74 commits in 500ms
- [x] Release tags and `CHANGELOG.md`. Seeded from the `sprint-2` tag, with the
      training's `DEPLOYMENTS.md` folded in rather than kept as a second file.
      Pre-`sprint-2` sprints are deliberately not backfilled — a record
      reconstructed from `git log` afterwards is written to look tidy rather
      than kept as things happened
- [x] `CONTRIBUTING.md` — thin entry point pointing at `BRANCHING.md`,
      `DEVELOPMENT.md` and the Definition of Done, not a restatement of them

Opened by this work rather than closed by it:

- [ ] Nothing scans git *history* for secrets. Both new checks read the working
      tree: the hook sees the staged diff, Trivy `fs` sees the checkout. A
      secret committed and later deleted is invisible to both. `gitleaks detect`
      over the full history would cover it, and the honest reason it is not
      wired in yet is that it needs a decision about what to do on a hit —
      a red pipeline on a commit nobody can change is a gate that gets disabled
- [ ] Trivy `fs --scanners misconfig` over the compose file and the Dockerfile.
      The security review recommends it alongside the secret scanner and expects
      it red on first run. Kept out of the same change on purpose: triaging IaC
      misconfiguration is real work and is not secret scanning, and bundling it
      would have meant landing both half-done
- [ ] `BRANCHING.md` still says `release/sprint2` throughout, including in rules
      1, 2, 5, 6 and 7 and the everyday loop. The rules are right; the branch
      name is one sprint out of date — cheap to fix, and worth fixing before it
      reads as an instruction to branch off a retired branch

**Deliberate divergence.** The training recommends `main` + `dev`. This project
runs `main` + a per-sprint `release/*` branch — `release/sprint3` today, and
`release/sprint2` before it, now retired to the `sprint-2` tag — because the
sprint checkpoint *is* the thing demonstrated to mentors, and a long-lived
`dev` alongside it would be a third branch with no distinct job. The branch is
short-lived by design, which is the substantive difference from `dev`, not just
a naming one. Documented in
[`BRANCHING.md`](BRANCHING.md) and [ADR-0004](adr/0004-github-for-review-gitea-for-execution.md).
Expect this to be asked about; the answer is that the strategy was chosen, not
inherited.

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

1. Structured JSON logging with `request_id`, then `/metrics`. Sprint 3
   workstream A depends on both and cannot start without them.
2. The `act_runner` capability spike — half a day, four throwaway branches,
   one recorded result each. It decides how much of workstream B is buildable
   and should happen before B is planned in detail.
3. Trivy `fs --scanners misconfig` over the compose file and the Dockerfile —
   the half of F6 this change deliberately left open. Expect it red on the
   first run; the triage is the work.
4. `/version` endpoint via `--build-arg` — the demo currently proves the running
   SHA with the container's `version` label, which works; the endpoint would
   make it provable without Docker access.

**Done since the last revision (2026-08-05).** Sprint 2 closed and merged to
`main` as PR #31; `release/sprint2` deleted from both forges and preserved as
the annotated tag `sprint-2`; `release/sprint3` cut from `main`; the Sprint 2
demo evidence committed under `docs/demo-assets-sprint2/`.

One thing to carry rather than bury: **PR #31 was squash-merged.** §6 and
[`BRANCHING.md`](BRANCHING.md) rule 7 both say `release/*` → `main` takes a
merge commit, and the rule states the exact consequence that followed — `main`
and `release/sprint2` ended with identical trees and no shared history. The
damage is bounded, because Sprint 3 branches from `main` and the sprint2 branch
is now a tag. The cause was the merge button remembering the previous choice,
which is squash for every `feature/*`. Worth naming out loud at the next
review: the rule was written, correct, and clicked past anyway.
