# ADR-0009: Helm replaces Ansible as the deployment step

## Status

Accepted — 2026-09-21

## Context

[ADR-0003](0003-deploy-and-verify-strategy.md) chose Ansible to drive the deploy
and made verification a gate rather than a warning. Both halves of that decision
were about a Docker host: `community.docker` reconciled container state, and the
smoke tasks decided whether the deploy stood.

[ADR-0008](0008-k3s-over-managed-kubernetes.md) moves the target to Kubernetes,
which reopens only the first half. Kubernetes already reconciles desired state —
that is what it is — so the question is no longer "what makes the change happen"
but "what hands Kubernetes the desired state, with the image tag substituted, and
what can put the previous state back".

Three answers were available: keep Ansible and use its `kubernetes.core`
modules; apply plain manifests with `kubectl apply` and substitute the tag with
`sed` or `envsubst`; or template the manifests with Helm and install them as one
release.

The measurement makes this more than a taste question. Recovery time after a
broken deployment is one of the three recorded quantities, so the mechanism that
restores the previous version has to be a single, timeable, repeatable operation
— not a sequence of steps whose duration depends on how quickly the operator
reconstructs what the previous state was.

## Decision

**The deployment step is `helm upgrade --install`, and the unit of deployment is
one release.** `chart/` holds the three components — backend, frontend,
PostgreSQL — and the only value the pipeline sets is the image tag:
`--set image.tag=<commit-sha>`. Both images are built from the same commit and
share that tag, so one switch moves the whole application to a new version.

**`helm rollback` is the recovery mechanism.** Helm keeps the previous release
revisions, so restoring the last working version is one command with a known
target, and its duration is a number the measurement can record.

**Helm owns the cluster objects; nothing else writes them.** No `kubectl apply`
against objects the chart manages, and no Ansible modules touching the cluster.

**Verification stays exactly where ADR-0003 put it: in front of the gate.** The
pipeline waits with `kubectl rollout status` (a signal, not a timer, as ADR-0003
requires), then asserts `/version` returns the deployed commit SHA and runs the
smoke test. A failing assertion triggers the rollback.

**Ansible is not deleted.** It stays in the repository as the previous
generation of the deployment step, because the thesis compares the chain before
and after, and a deleted baseline cannot be described accurately.

## Consequences

**Positive**

- One command deploys, one command restores, and both are reproducible by hand
  and from the pipeline — the property ADR-0003 valued in Ansible survives the
  move.
- Revision history is kept by the tool, so "the previous working version" is an
  identifier rather than something reconstructed under pressure.
- The pipeline's deploy step loses the control-node dependency chain (Ansible,
  collections, their locks) and gains one binary.

**Negative / trade-offs**

- Go templating over YAML is its own failure class: a template can produce
  valid-looking YAML that means something else. `helm template` before install
  is the mitigation, and it belongs in the runbook.
- Mixing owners corrupts the release. Revision 6 of the local release on
  2026-09-18 failed with `conflicts with "kubectl-client-side-apply"` on the
  `postgres` Deployment, because the same object had earlier been created with
  `kubectl apply` during the learning phase. That is the concrete cost of the
  "Helm owns the objects" rule being broken once, and it is worth citing in the
  thesis rather than hiding.
- `helm rollback` restores Kubernetes objects, not data. A rollback that follows
  a schema change does not undo the schema change; the current schema is additive
  (`CREATE TABLE IF NOT EXISTS`), so this is not a live problem, but the limit
  has to be stated where recovery is measured.
- The database PVC carries `helm.sh/resource-policy: keep`, so `helm uninstall`
  leaves the volume behind. That is deliberate — it is what keeps an uninstall
  from silently destroying data — but it means a truly clean reinstall needs an
  explicit `kubectl delete pvc`.

## Alternatives considered

- **Ansible with `kubernetes.core`.** Keeps one tool for deployment across both
  generations of the project. Rejected: it would wrap Kubernetes' own
  reconciliation in a second reconciliation loop, and Ansible has no equivalent
  of a release revision — rollback would become "re-run the playbook with the old
  tag", which is a redeploy, not a restore, and measures something else.
- **Plain manifests with `kubectl apply` and tag substitution.** Fewest moving
  parts, and it is what the learning phase used. Rejected: rollback means
  applying the previous manifests, which requires knowing which those were, and
  string-substituting a tag into YAML in CI is the kind of step that fails
  silently. The revision-6 conflict above is what mixing this with Helm costs.
- **Kustomize.** Overlays instead of templates, no server-side release state.
  Rejected for the same reason as plain manifests: no revision history, so no
  single-command restore.
- **An external chart for PostgreSQL (Bitnami or similar).** Fewer lines to
  write. Rejected: the database is a subject of the thesis chapter on state, and
  a twenty-line manifest that is understood is worth more here than a chart whose
  upgrade behaviour would have to be researched to be described.

## Addendum — 2026-09-22: how the pipeline reaches the cluster

This ADR was accepted a day before `ci.yml` followed it. Building the deploy,
verify and rollback stages surfaced three questions the decision above did not
answer, and each is settled here rather than left implicit in the workflow.

**Helm runs in a container on the host's network namespace.** The deploy job
runs in a container on the `projecta-platform` bridge, and the k3s API server
listens on the host's `127.0.0.1:6443`. The bridge gateway is not a way around
that: `terraform/cloud-init.yaml` starts k3s with `--tls-san <public_ip>`, so
the server certificate names `127.0.0.1`, `localhost` and the public address,
and not `172.x.0.1`. `scripts/helm-on-host.sh` therefore creates a container
through the host's Docker socket — which the job already holds, because the
build stage uses it — with `--network host` and the host's kubeconfig
bind-mounted. Inside it, `127.0.0.1:6443` is the API server and `127.0.0.1:80`
is Traefik, exactly as the operator sees them in the manual protocol.

Rejected: installing a second, host-executing runner. It gives perfect symmetry
with the manual series and costs a new platform component to register, secure
and describe. Rejected too: hairpinning to the public address, which routes an
internal deploy through the internet and the network security group.

The helm image is pinned to `alpine/helm:3.22.0` — the version
`szakdolgozat/bizonyitek/04-kezi-telepitesi-folyamat.md` records on the
measuring machine (E1). Two series deploying with two helm versions would put a
second variable next to the branch name, which is the one thing §6.4 may not
have.

**`helm upgrade --wait` replaces `kubectl rollout status`.** The manual protocol
spends one command per Deployment (steps 10 and 11); the pipeline spends one
flag. Both wait on a readiness signal rather than a timer, which is what
ADR-0003 requires, and the difference in what it costs a human is a finding for
§6.4 rather than a divergence to correct. A consequence worth stating: the
deploy job needs no `kubectl` at all, so one pinned image covers the whole
stage.

**Not `--atomic`.** Helm's built-in rollback would fire on helm's own verdict
and leave nothing to measure. The failure this project is built to catch is the
one helm cannot see — pods healthy, application broken — so recovery stays an
explicit, separately timed step.

**Ansible survives, in one role and with a narrower claim.** The consequence
above says the deploy step "loses the control-node dependency chain (Ansible,
collections, their locks)". That is now true of the collections and false of
Ansible itself: `ansible/playbooks/verify.yml` runs the `deploy_app` role's
smoke tasks as the post-deploy gate. Every task in that file is
`ansible.builtin.uri` or `ansible.builtin.assert`, so nothing there touches a
cluster object and the "Helm owns the objects" rule holds. The deploy job
installs `ansible-core` and nothing from Galaxy.

The alternative was `scripts/smoke.sh`, which cannot be a gate: it has no
`set -e` and its `check()` asserts nothing, so its exit code is always 0. Both
sides of the measurement then run the same check set with the same definition
of healthy, and the fact that only the automated side decides mechanically is
itself one of the results.

**The smoke tasks gained the acceptance criterion.** `/version` must report the
commit being deployed. Without it a deploy that quietly left the previous
version in place would pass every other check, because the previous version is
healthy. This also required wiring `GIT_SHA` through `docker build` in CI,
which had never been passed — images built before this change report `dev`.

**Open, and blocking a green run rather than a decision:** the rollback step is
conditioned on `if: failure()`, which ADR-0005 did not test on act_runner
v0.2.12. `.gitea/workflows/spike-if-failure.yml` probes it on a `spike/**`
branch; if it turns out not to work, deploy, verify and rollback collapse into
one step's shell script, which needs no expression support at all.
