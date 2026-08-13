"""Structured logging — one JSON object per line, on stdout.

Twelve-factor: the application does not know where its logs go. It writes to
stdout and the platform decides. Here the platform is Alloy, which tails the
container's stdout via the Docker API and ships it to Loki
(`platform/observability/alloy/config.alloy`).

The format is JSON because the alternative is a regex. Loki can parse a text
line with `pattern` or `regexp`, but then the log format becomes an interface
that two repositories have to agree on, and it breaks silently — a changed
message produces empty labels, not an error. `| json` in a LogQL query cannot
break that way.

**`request_id` on every line, not just the access line.** `RequestIdFilter`
pulls it out of Flask's request context and attaches it to every record emitted
while a request is being served, including ones from libraries that know
nothing about it. That is what makes the demo work: click from a spike in the
error rate to the logs, and the failing request's own id is on the line that
explains it — not on a summary line you then have to correlate by timestamp.

`request_id` is a log field and never a Prometheus label. The reasoning is in
[ADR-0007](../docs/adr/0007-metric-cardinality.md) and it is the sentence worth
saying out loud at review.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone

# Every attribute the stdlib puts on a LogRecord. Anything on a record that is
# not in here arrived through `extra=` and is caller-supplied structure worth
# emitting, so the formatter passes it through rather than requiring each field
# to be declared twice.
_STDLIB_RECORD_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

# An inbound X-Request-ID is caller-controlled input and ends up in a log line,
# a Loki label filter and a Grafana URL. Newlines would forge log records,
# quotes would break the JSON consumer's assumptions, and unbounded length is a
# cheap way to fill a disk. Anything outside this alphabet is discarded and a
# fresh id is generated — rejecting the request would punish a caller for a
# header they may not control.
_REQUEST_ID_RE = re.compile(r"\A[A-Za-z0-9._-]{1,64}\Z")

REQUEST_ID_HEADER = "X-Request-ID"


def sanitise_request_id(candidate: str | None) -> str:
    """Return a safe request id: the caller's if it is sane, else a new one."""
    if candidate and _REQUEST_ID_RE.match(candidate):
        return candidate
    return uuid.uuid4().hex


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            # RFC 3339 in UTC with an explicit offset. Loki assigns its own
            # ingestion timestamp; this one is the application's, and the two
            # disagreeing is itself a useful signal.
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["error_type"] = getattr(exc_type, "__name__", str(exc_type))
            payload["error_message"] = str(exc_value)
            # The traceback is a multi-line string inside a single JSON string,
            # so it stays one Loki entry. A traceback split across ten lines is
            # ten entries that arrive interleaved with everyone else's.
            payload["stack"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _STDLIB_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = value

        # default=str rather than letting a stray object raise. A logging call
        # must not be able to fail the request it is describing.
        return json.dumps(payload, default=str, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """Attach the current request's id to every record emitted while serving.

    A filter rather than a formatter concern: filters run for every handler on
    every logger, so a library that logs through its own logger still gets the
    id without knowing this application exists.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Imported lazily so this module stays importable outside an app
        # context — it is also loaded by gunicorn's own logging setup.
        from flask import g, has_request_context

        if has_request_context():
            record.request_id = getattr(g, "request_id", None)
        return True


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger. Only the root logger.

    **One owner per logger, and getting there took three attempts.** The first
    version of this function also re-pointed `gunicorn.error` and
    `gunicorn.access`, and the story of why it no longer does is worth more
    than the code:

    1. It could not work for `gunicorn.error`. This runs when `app.app` is
       imported, which happens in each worker, after the arbiter has already
       printed "Starting gunicorn 23.0.0" through a logger this call never
       sees. Fixed by `logconfig_dict` in `gunicorn.conf.py`, which gunicorn
       applies in the arbiter before the first line.
    2. Defining `logconfig_dict` re-enabled gunicorn's access log, because
       `Logger.access()` returns early only when *none* of `accesslog`,
       `logconfig` and `logconfig_dict` is set. Fixed with a `NullHandler` on
       `gunicorn.access`.
    3. That NullHandler was then overwritten — by this function, in the worker,
       putting the console handler back on the logger `gunicorn.conf.py` had
       just silenced. Every request logged twice again.

    Each fix was correct and each was defeated by the other configuration path.
    The defect was never any one of them; it was that two files configured the
    same loggers and the last writer won, in an order that depends on process
    lifecycle. So the ownership is now split with no overlap: `gunicorn.conf.py`
    owns everything named `gunicorn.*`, this function owns the root logger, and
    neither reaches into the other.

    The consequence to know about: `gunicorn app.app:app` **without**
    `--config gunicorn.conf.py` produces plain-text gunicorn lines. The
    Dockerfile always passes it, and nothing in `DEVELOPMENT.md` invokes
    gunicorn any other way, so this is stated rather than guarded.

    Gunicorn's access log is switched off in `gunicorn.conf.py` rather than
    reformatted, because `after_request` in `app.py` already emits a richer
    record for the same event. The tradeoff, stated rather than buried: a
    request malformed enough that gunicorn rejects it before Flask sees it is
    now logged by neither. That is a real gap. It is accepted because the
    alternative is two access records per request, which makes every rate
    computed from logs wrong by a factor of two.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    # Replace rather than append: basicConfig may already have run (Flask's
    # development server does it), and two handlers means two identical lines.
    root.handlers = [handler]
    root.setLevel(level)
