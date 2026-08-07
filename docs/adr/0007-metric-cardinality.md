# ADR-0007: `request_id` is a log field and never a label

## Status

Accepted — 2026-08-06

## Context

The Sprint 3 demo ends by identifying one failing request out of a burst of
them, by its `request_id`. The obvious way to make that possible is to attach
`request_id` to the metrics, so the failing request can be found by querying
Prometheus directly.

That instinct is wrong, and being able to say why is the point of this decision
record. [`PLAN.md`](../PLAN.md) puts it plainly: that sentence is worth more at
review than another dashboard.

Cardinality is the number of distinct time series a metric produces, and it is
multiplicative. `http_request_duration_seconds` carries `method`, `endpoint` and
ten histogram buckets plus `+Inf`, `_sum` and `_count`. Five methods and six
routes is 5 × 6 × 13 ≈ 390 series — small, bounded, and it stays that way no
matter how much traffic arrives.

Add `request_id` and each series exists for exactly one request, forever. A
thousand requests is a thousand times the series count. Prometheus holds the
label set of every active series in memory, so this does not degrade gracefully:
it works, then it works while using more memory, then the process is OOM-killed.
On the laptop this project runs on — PLAN.md §5 budgets 3–4 GB for the whole
stack — that is minutes away, not months.

The same trap has a second entrance. `endpoint` looks safe only because of how
it is computed. Using `request.path` instead of the matched route template would
mean `/user/1` and `/user/2` are different label values, and an unmatched path
would be a new series per 404 — which makes a bored port scanner an availability
risk from outside the network.

## Decision

**`request_id` goes in the log line and nowhere else.**

Three rules, each enforced in code rather than asserted here:

**1. Prometheus labels are the route template, the method and the status code.**
`app/metrics.py` labels on `request.url_rule.rule`, never `request.path`.
Requests that match no route collapse into one label value, `<unmatched>`, so
the 404 series count is one regardless of how many distinct URLs are attempted.
The test `test_every_unmatched_path_shares_one_label_value` fails if anyone
changes this back, which is the part that survives the author forgetting why.

**2. Loki gets exactly one label from the log line: `level`.** Loki streams have
the same multiplicative behaviour as Prometheus series, so `request_id` as a
Loki label would be the identical mistake in the other half of the stack. The id
stays in the JSON body, where `| json | request_id="…"` finds it at query time —
a scan over a handful of streams, which is the operation Loki is built for.
`status` and `endpoint` are left out too, despite being bounded, because they
are already Prometheus labels and duplicating them doubles the stream count to
make one query marginally faster.

**3. Histogram buckets are a cardinality decision, not a display preference.**
Ten buckets, stopping at 5s. Every bucket is a series per label combination, so
the temptation to add "just a few more" for a smoother graph costs series in the
same multiplicative way. Five seconds is the cut-off because this application
answers in single-digit milliseconds and anything slower is a hang, which `+Inf`
already reports.

**The two systems answer different questions, and that is the design.**
Prometheus answers *how much and how bad* — rates, ratios, percentiles, over
bounded label sets, cheaply, forever. Loki answers *which one and why* — the
individual request, its payload, its traceback. The `request_id` is the join key
between them, and the metric-to-log data link ([ADR-0006](0006-loki-over-elk.md))
is what makes the join a click rather than a correlation exercise.

## Consequences

**Good.** Series count is bounded by the shape of the application rather than by
its traffic — the same 390 or so series under one request per hour and under a
thousand per second. The instrumentation cannot be made dangerous by usage. The
`<unmatched>` bucket closes a denial-of-service path that would otherwise be
reachable by anyone who can send an HTTP request.

**Bad.** Prometheus cannot answer "how long did request `abc123` take". That
question is answerable — the duration is on the log line, in `duration_ms` — but
it is a Loki query, not a PromQL one, and someone will reach for the wrong tool
first. Accepted, because the alternative is an instrumented app that dies under
the load it was instrumented to measure.

**A rule that will be tested.** The next endpoint someone adds with a path
parameter — `/user/<id>` — is the moment this decision either holds or quietly
breaks. It holds if the label stays the route template, which renders as the
literal string `/user/<id>` for every user. That is the correct behaviour and it
will look like a bug to whoever sees it first, so it is written here to be found
by the person who goes looking.

**Verified against a running system, 2026-08-06.** Rules 1 and 3 are asserted by
tests in `tests/test_observability.py` and pass. Rule 1 was then measured rather
than only asserted: 125 requests through `loadgen.sh` moved the series count
from **5 to 6**, and the one new series is `endpoint="/"` — a route nothing had
called on that container before, not a consequence of volume. Call it a million
more times and the count stays at six. Had the label been `request.path`, the
same run would have produced 5 + 125. Section 4.5 of
[`sprint3-verification.md`](../sprint3-verification.md) has the run.

Rule 2 held too. Loki's `/labels` endpoint returns `container`, `level`,
`platform`, `service` and `service_name`, and `request_id` is not among them.
The ids that do appear in a query result are `| json` unpacking the line body at
query time — not indexed, and creating no streams. Section 5.5.

**One correction to rule 2 as written above.** "Loki gets exactly one label from
the log line" describes what `config.alloy` promotes, not the finished label
set. Loki 3.x derives `service_name` on its own, and surfaces `detected_level`
alongside our `level` in query results. Both are bounded, so the decision stands
and the cardinality argument is unaffected — but the sentence overstates the
control this project has, and a reviewer comparing it against the `/labels`
output would be right to notice.
