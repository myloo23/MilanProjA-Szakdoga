"""Prometheus instrumentation for the Flask app.

Two series families, deliberately: a request counter and a latency histogram.
Between them they answer rate, errors and duration — the three questions a
dashboard is for. Anything else added here has to justify the series it costs.

**The endpoint label is the route template, never the request path.**
`/echo` is one label value no matter how many requests hit it; `request.path`
would be one series per distinct URL, which for a 404-scanning bot is unbounded.
This is the whole cardinality argument, enforced in four lines rather than
asserted in a document — see [ADR-0007](../docs/adr/0007-metric-cardinality.md).

**Multiprocess is handled, not ignored.** The container runs gunicorn with two
workers. `prometheus_client`'s default registry lives in one process, so a
scrape lands on whichever worker the OS picked and returns that worker's
counters only — producing a graph that appears to go backwards. The fix is the
library's multiprocess mode: workers write to memory-mapped files in
`PROMETHEUS_MULTIPROC_DIR` and the scrape aggregates across them. It is
switched on by the environment variable being set, which the Dockerfile does
and a test run does not, so `pytest` exercises the ordinary in-process path.
"""

from __future__ import annotations

import os

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)

# Requests that matched no route. A single bucket for every unrouted URL, which
# is the point: without it, `endpoint` would grow a series per 404 and a bored
# scanner could exhaust Prometheus's memory from outside the network.
UNMATCHED = "<unmatched>"

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the application.",
    ["method", "endpoint", "status"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    # Every bucket is a time series per label combination, so this list is a
    # cardinality decision, not a display preference. Cut short at 5s: this app
    # answers in single-digit milliseconds and anything past five seconds is a
    # hang, which the `+Inf` bucket already reports.
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def observe(method: str, endpoint: str | None, status: int, duration: float) -> None:
    """Record one finished request."""
    label = endpoint or UNMATCHED
    REQUESTS.labels(method=method, endpoint=label, status=str(status)).inc()
    LATENCY.labels(method=method, endpoint=label).observe(duration)


def render() -> tuple[bytes, str]:
    """Return the exposition-format body and its content type.

    In multiprocess mode a fresh registry is built per scrape and populated
    from the shared directory. That is the documented approach and it is
    correct rather than cheap — the cost is paid once every scrape interval,
    not per request.
    """
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST

    return generate_latest(), CONTENT_TYPE_LATEST
