# ADR-0008: A single-node k3s cluster on a self-managed VM, not managed Kubernetes

## Status

Accepted — 2026-09-21

## Context

The thesis this repository now serves asks one question: how much does an
automated deployment chain measurably improve over deploying the same change by
hand. Answering it needs a target environment that both sides of the measurement
deploy into — the manual runs and the pipeline runs — and that environment has to
be the same environment, or the difference between the two series stops being
attributable to automation.

Until now the deploy target was a plain Docker host
([ADR-0003](0003-deploy-and-verify-strategy.md)). That is no longer enough for
two reasons. A `docker run` swap has no notion of a rollout, a readiness gate or
a previous revision, so the recovery-time half of the measurement would have
nothing to measure against. And the consultant asked for the infrastructure to
be described as code and the application to run on Kubernetes, which makes the
orchestrator part of the subject, not an implementation detail.

That leaves the question of *which* Kubernetes. Three candidates were real:
a managed service (AKS/GKE/EKS), upstream Kubernetes installed by hand
(kubeadm), or a lightweight distribution on a VM the project controls.

Two constraints narrow it. The budget is zero forint: the only funding is the
Azure for Students credit (100 USD, no card, student verification), which rules
out a managed control plane running for weeks. And the deployment chain has to
be self-hosted end to end — the thesis title claims a *saját üzemeltetésű*
CI/CD environment, and Gitea, the runner and the registry already live in
`platform/compose.yaml` on a machine the project owns.

## Decision

**The measurement cluster is k3s, single node, on one Azure VM created by
Terraform.** k3s is a certified Kubernetes distribution shipped as a single
binary; the API, the objects and `kubectl` are the same as upstream. The VM and
the network around it are Terraform's scope; installing k3s happens in the VM's
cloud-init, so the cluster is a product of `terraform apply` and not of manual
work.

**One node, deliberately.** The subject is the deployment chain, not cluster
operations. Scheduling across nodes, node failure and pod anti-affinity change
nothing about the time from a change to a working deployment, which is what the
measurement records.

**Gitea, the runner, the registry and the cluster share that VM.** The cluster
has to be able to pull the image the pipeline built; a registry on a laptop at
`localhost:5001` is unreachable from a cloud cluster. One host is the smallest
arrangement that keeps the whole chain self-hosted.

**Development happens on k3d on the laptop, never on the measurement cluster.**
k3d runs k3s inside Docker: a throwaway cluster in seconds, no credit burned,
and the same chart. `scripts/verify-k3d.sh` is the acceptance check for that
local cluster — install, CRUD through the ingress, data surviving pod deletion,
version switch and rollback.

## Consequences

**Positive**

- The cluster costs nothing and can be destroyed and recreated from code, which
  is itself the evidence the Terraform chapter needs.
- Identical API surface to upstream Kubernetes, so nothing learned or written
  about the deployment is distribution-specific.
- The local k3d cluster and the measurement cluster run the same chart, so a
  chart that passes locally is unlikely to fail for chart reasons upstream.

**Negative / trade-offs**

- CI and the deployment target share one host's CPU and memory, so a pipeline
  run competes with the application it just deployed. This favours the *manual*
  side of the measurement, because the manual runs happen while the runner is
  idle. The improvement the measurement reports is therefore a lower bound, and
  the thesis has to say so where the threats to validity are discussed.
- A single node means a node failure is a total outage, and no result about
  availability can be claimed from this setup.
- k3s replaces some upstream components (Traefik as the built-in ingress
  controller, local-path as the default storage class). Anything written about
  ingress or storage has to name the k3s default rather than imply it is
  Kubernetes-wide.
- The student credit has a deadline and a balance. If the VM is left running
  past the measurement, the environment can disappear mid-thesis; it gets
  destroyed with `terraform destroy` once the series are recorded, and the
  evidence has to be in the repository before that happens.

## Alternatives considered

- **Managed Kubernetes (AKS).** Removes the control plane from the picture and
  would be the production answer. Rejected: a managed control plane plus a node
  pool consumes the student credit in weeks, and it contradicts the *self-hosted*
  claim in the title. It belongs in the further-work chapter.
- **Upstream Kubernetes via kubeadm on the same VM.** Same cost, more setup, and
  the extra setup teaches nothing the thesis needs — the deployment chain is
  identical either way. Rejected.
- **Staying on Docker Compose and measuring that.** Cheapest, and it would still
  produce two series. Rejected: without a rollout and a previous revision there
  is no honest way to measure recovery after a broken deployment, and the
  consultant asked for Kubernetes.
- **k3s in a local VM (Lima/Multipass) instead of Azure.** Kept as the fallback
  if student verification had failed; it would have weakened the Terraform
  chapter to cluster-level resources only. Not needed — the Azure account and
  the credit are in place as of 2026-09-21.
