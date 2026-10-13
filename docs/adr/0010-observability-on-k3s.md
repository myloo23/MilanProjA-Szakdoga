# ADR-0010: Observability follows the application onto k3s — from outside the cluster

## Status

Accepted — 2026-09-30

## Context

[ADR-0006](0006-loki-over-elk.md) and [ADR-0007](0007-metric-cardinality.md)
built the Prometheus / Loki / Grafana / Alloy stack for a Docker host: the
application was one container called `projecta-flask`, Prometheus scraped it by
name on the `projecta-platform` bridge, and Alloy read its stdout through the
Docker socket.

[ADR-0008](0008-k3s-over-managed-kubernetes.md) and
[ADR-0009](0009-helm-replaces-ansible-for-deployment.md) moved the application
onto a single-node k3s cluster. The observability stack did not follow. On the
measuring VM it sat behind a compose profile (`platform/compose.azure.yaml`) and
was not started, and its configuration could not have seen the application if it
had been: the backend is now two pods in k3s's own containerd, with addresses
that change on every rollout, and neither the Docker socket nor a static target
reaches them.

That was the right order for the measurement — the ten-and-ten runs of §6 ran
with the observability layer off, so it cannot have taken memory or CPU from the
thing being timed. This is recorded, not assumed: precondition E9 of every run
(`szakdolgozat/bizonyitek/meres/README.md`) was that `docker ps` on the VM lists
exactly three containers — Gitea, the registry and the runner. But it leaves §5.6 describing a system that does not observe
the deployed application.

Three placements were available:

1. **Everything into the cluster** (kube-prometheus-stack, or hand-written
   manifests for Prometheus, Loki, Alloy and Grafana).
2. **Prometheus into the cluster, the rest in compose.**
3. **Keep the stack in compose; give it a narrow way into the cluster.**

## Decision

**Option 3.** The stack stays where it is, with its dashboards, alert rule and
datasource provisioning unchanged. Two things change, both only in the Azure
overlay:

- **Metrics.** Prometheus uses `kubernetes_sd_configs` (role `pod`, namespace
  `default`) against the k3s API at `host.docker.internal:6443`, authenticated by
  a dedicated ServiceAccount whose Role allows `get/list/watch` on pods in
  `default` and nothing else
  (`platform/observability/k8s/prometheus-sd-rbac.yaml`). It scrapes each backend
  pod directly on its pod IP, which the host routes (`cni0`) and Docker forwards.
  TLS verification stays on: the connection goes to the bridge gateway, which is
  not on the API certificate, so `tls_config.server_name` names
  `kubernetes.default.svc`, which is.
- **Logs.** Alloy tails `/var/log/pods/default_{backend,frontend}-*/…/*.log`
  (mounted read-only), strips the CRI prefix with `stage.cri`, and feeds the same
  JSON processing as before.

The job name, the `service` label and the Loki `container` label keep their
Docker-era values (`projecta-flask`), so every existing query works unchanged.

### Why not option 1

It is the conventional answer and it is written into §7 as such. Here it costs
more than it buys: kube-prometheus-stack brings the Prometheus Operator,
kube-state-metrics and Alertmanager alongside Prometheus and Grafana — components
this project has no use for, on an 8 GB node that also runs the builds and whose
current stack idles at 350 MiB (ADR-0006); it would replace provisioning that is
already reviewed and working;
and none of the questions §5.6 has to answer — can a rollout be watched, can a
failed request be traced to its log lines — need it.

### Why not option 2

It removes the ServiceAccount token from the host, which is its real advantage.
But Grafana in compose then needs a route into the cluster (a NodePort), which is
the same kind of cross-boundary hop, just pointing the other way, and the
Prometheus configuration would live in two places depending on environment.

## Consequences

**Good.** The dashboards and the alert rule are the same files on the laptop and
on the VM. The cluster-side footprint is one ServiceAccount, one Role, one
RoleBinding and one Secret. New pods become targets through the watch, without a
reload — checked by `scripts/verify-observability-k3s.sh` step 7.

**Bad, and stated before being asked.**

- **A long-lived token sits on the host**, readable only by the Prometheus user
  (0400, uid 65534). Its reach is limited to reading pod metadata in one
  namespace; revocation is deleting the Secret. In-cluster Prometheus would not
  need it.
- **No pod-level CPU/memory metrics.** cAdvisor in compose sees Docker
  containers, not k3s's containerd. The kubelet's own cAdvisor endpoint would
  answer it, but reaching it through the API needs `nodes/proxy`, which is a far
  broader permission than the rest of this design grants. Left out on purpose;
  §7.
- **One more label on application series**: `pod`. Bounded (two live pods, two
  new names per rollout, seven-day retention), and needed so the two replicas'
  series are distinguishable by something a reader can match to `kubectl get
  pods`. Loki does *not* get it — ADR-0007 holds there unchanged.
- **Log collection depends on the node's file layout.** It works because the
  cluster has one node and Alloy runs on it. A second node would need Alloy on
  that node too — which is option 1 by another name.

## Evidence

`szakdolgozat/bizonyitek/05-megfigyeles-k3s-verify.txt` — the output of
`scripts/verify-observability-k3s.sh` on the measuring VM.
