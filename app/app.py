# app.py
import time

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from app import metrics
from app.logging_config import (
    REQUEST_ID_HEADER,
    configure_logging,
    sanitise_request_id,
)

configure_logging()

app = Flask(__name__)

# Endpoints whose successful traffic is machinery, not usage: Docker's
# HEALTHCHECK hits /health every 10s and Prometheus scrapes /metrics every 15s.
# Logged at DEBUG so the default INFO level does not bury a day of real requests
# under fifteen thousand lines of self-inspection. A failure on one of these is
# still logged loudly — the level is chosen from the status code below, so the
# first health check to return 500 is at ERROR like anything else.
_QUIET_ENDPOINTS = frozenset({"/health", "/ready", "/metrics"})


@app.before_request
def _start_request() -> None:
    # perf_counter, not time(): a monotonic clock cannot be dragged backwards
    # by an NTP correction mid-request and report a negative duration.
    g.started = time.perf_counter()
    g.request_id = sanitise_request_id(request.headers.get(REQUEST_ID_HEADER))


@app.after_request
def _finish_request(response: Response) -> Response:
    # url_rule is None when nothing matched — a 404. Passing that through as
    # None is deliberate: metrics.observe() maps it to a single bucket, and the
    # log line records the real path, which is where you actually want to see
    # what was requested.
    endpoint = request.url_rule.rule if request.url_rule else None
    duration = time.perf_counter() - getattr(g, "started", time.perf_counter())

    metrics.observe(request.method, endpoint, response.status_code, duration)

    # Returned so a caller can quote the id from a failed call without having
    # to be given access to the logs first.
    response.headers[REQUEST_ID_HEADER] = g.get("request_id", "")

    if response.status_code >= 500:
        level = "error"
    elif response.status_code >= 400:
        level = "warning"
    elif endpoint in _QUIET_ENDPOINTS:
        level = "debug"
    else:
        level = "info"

    getattr(app.logger, level)(
        "request",
        extra={
            "event": "http_request",
            "method": request.method,
            "path": request.path,
            "endpoint": endpoint or metrics.UNMATCHED,
            "status": response.status_code,
            # Rounded at emission, not in the query. Sub-microsecond precision
            # on a network request is noise that costs bytes on every line.
            "duration_ms": round(duration * 1000, 2),
            "remote_addr": request.remote_addr,
        },
    )
    return response


@app.route("/")
def home():
    return "Hello from Flask!"


@app.route("/health")
def health():
    return jsonify(status="UP")


@app.route("/ready")
def ready():
    # no external deps yet; when you add one (DB/registry),
    # check it here and return 503 if it's unreachable
    return jsonify(status="READY")


@app.route("/metrics")
def prometheus_metrics():
    body, content_type = metrics.render()
    return Response(body, mimetype=content_type)


@app.route("/echo", methods=["POST"])
def echo():
    try:
        data = request.get_json()
    except (BadRequest, UnsupportedMediaType):
        # The payload is deliberately not logged. It is attacker-controlled
        # input of arbitrary size, and this is the endpoint the incident demo
        # floods — echoing it into the log stream turns a burst of bad requests
        # into a burst of unbounded log lines. The request_id on this line is
        # the handle; the caller has it too, from the response header.
        app.logger.warning(
            "invalid JSON payload",
            extra={"event": "bad_request", "content_type": request.content_type},
        )
        return jsonify(error="Invalid JSON payload"), 400

    return jsonify(received=data)
