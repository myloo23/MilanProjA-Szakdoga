# ADR-0006: Loki for logs, not Elasticsearch

## Status

Accepted — 2026-08-06

## Context

The brief asks for centralised logs that can be searched from one place during
an incident. The default answer in most organisations is still the ELK stack —
Elasticsearch, Logstash, Kibana — and a reviewer who has run one will ask why
this project did not.

The requirement it has to serve is narrow and specific. During the demo, an
error rate spikes on a Grafana panel and the next action is to read the log
lines behind that spike, identified by `request_id`, without leaving the browser
or opening a shell. The volume is one application on one laptop. The retention
that matters is a sprint.

Two things already constrain the answer. Grafana is being run regardless,
because the metrics half of Sprint 3 needs it — so one of the two candidates
comes with a query UI already paid for. And PLAN.md §5 budgets roughly 3–4 GB
for the entire stack on a machine that is simultaneously running Docker Desktop,
Gitea, a registry, an `act_runner` job container and the deployed application.

## Decision

**Loki, with Grafana Alloy as the collector.**

The argument is not that Loki is better. It is that the two systems are built
around different bets, and only one of those bets pays here.

**Elasticsearch indexes the contents of every log line.** That is what makes it
extraordinary at questions you did not anticipate — full-text search across
unstructured logs, aggregations over arbitrary fields, ad-hoc forensics. It is
also what makes it expensive: the inverted index is frequently larger than the
logs themselves, and Elasticsearch's floor for a usable single node is around
2 GB of heap before Logstash and Kibana are counted. That is most of this
project's entire budget, spent on a capability the demo does not use.

**Loki indexes only labels and stores the line bodies compressed.** Queries work
by selecting a small set of streams by label and then scanning them. That is
slower for a needle-in-a-haystack search across everything, and irrelevant here,
because every query this project makes already knows which container it wants
and roughly when. `{container="projecta-flask"} | json | request_id="…"` selects
one stream and scans a few minutes of it.

**The pivot is the real reason.** The requirement is not "search logs", it is
"get from a metric to the logs behind it in one click". In Grafana that is a
datasource-level feature: a data link on the Prometheus panel opens an Explore
pane on the Loki datasource with the time range carried across, and Loki's
`derivedFields` turns `request_id` in the log line into a link that queries for
that request. Both are configured in
`platform/observability/grafana/provisioning/datasources/datasources.yaml`, in
about twelve lines. With Kibana the metrics and the logs live in two different
applications with two different time pickers, and the pivot becomes a
copy-paste of a timestamp — which is exactly the manual correlation step this
sprint exists to remove.

**Alloy rather than Promtail** for collection. Promtail reached end of life and
its own documentation points at Alloy; adopting a component that is already
retired would be a finding against the project rather than for it. Alloy reads
container stdout through the Docker API, so the application keeps writing to
stdout and knowing nothing about any of this.

**JSON at the source, parsed at query time.** The application emits structured
JSON (`app/logging_config.py`) and Alloy extracts a small number of fields. The
alternative — plain text plus a regex in the collector — makes the log format an
undocumented interface between two repositories, and it fails silently: a
reworded message produces empty fields rather than an error.

## Consequences

**Good.** One UI for metrics and logs, which is what makes the one-click pivot
possible at all. Roughly 512 MB for Loki against several gigabytes for an ELK
node, on a budget where that difference is the difference between the stack
running and the laptop swapping during a demo. Configuration is three files in
this repository rather than an index template, a pipeline definition and a
Kibana saved object.

**Bad, and worth saying before being asked.** Loki cannot answer questions that
require full-text search across every service at once — "find every occurrence
of this stack trace anywhere in the last month" is an Elasticsearch question and
Loki will scan for a long time before answering it. This project has no such
question today. If it acquires one, the answer is not to bolt full-text search
onto Loki; it is to reconsider this decision, which is why it is written down.

**The cardinality trap moves rather than disappears.** Loki labels behave like
Prometheus labels — every distinct combination is a separate stream, and a
high-cardinality label such as `request_id` would produce one stream per request
and degrade Loki far faster than the equivalent mistake degrades Elasticsearch.
The mitigation is the same discipline in both halves of the stack, and it is
[ADR-0007](0007-metric-cardinality.md).

**Measured, 2026-08-06.** The cost argument holds, by a wider margin than this
record claimed. All six observability services idle at **350 MiB**, and the
whole stack — Gitea, the registry, the runner and the application included — at
**769 MiB**, against the 3–4 GB [`PLAN.md`](../PLAN.md) §5 budgeted and against
the "roughly 512 MB for Loki" estimated above. The contingency of dropping
node-exporter if memory got tight was never needed. Alloy has the least headroom
at 73 MiB of its 256 MiB limit, and it is the component whose cost scales with
log volume, so it is the one to watch under a burst rather than Loki. Section
3.6 of [`sprint3-verification.md`](../sprint3-verification.md).

The single-UI claim — the whole reason for this decision — is verified end to
end in section 7. A spike on the error rate panel, a derived-field link, and the
failing request's own `request_id` on screen, without leaving Grafana and
without copy-pasting a timestamp between two applications.

**What is still an argument from documentation.** Loki's query latency under
load has not been measured, and section 7 still carries the wall-clock time from
the first malformed request to reading the `request_id` off the screen as a
blank. That this stack is *cheap*, and that the pivot *works*, are now numbers.
That it answers *fast* is not one yet.
