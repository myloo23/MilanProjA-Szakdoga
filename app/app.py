# app.py
import os
import time

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import (
    BadRequest,
    RequestEntityTooLarge,
    UnsupportedMediaType,
)

from app import db, metrics, notes
from app.logging_config import (
    REQUEST_ID_HEADER,
    configure_logging,
    sanitise_request_id,
)

configure_logging()

app = Flask(__name__)

# The largest request body this application will read. Flask's default is no
# limit at all, and `/echo` returns what it was sent — so one request costs
# roughly three copies of itself: the buffered body, the parsed structure and
# the serialised response. The deploy role gives this container 256 MB
# (`deploy_app_memory`) and gunicorn runs two workers of four threads, so eight
# concurrent multi-megabyte posts is an out-of-memory kill, not a slow request.
#
# 64 KiB is chosen from both ends. The largest body anything in this project
# sends is `smoke.yml`'s `{"smoke": "<40-char sha>"}`, so the limit is three
# orders of magnitude above legitimate traffic; and a body this size cannot
# exhaust the container no matter how many arrive at once, because the memory
# limit bounds the workers before the bodies do.
#
# Werkzeug enforces this when the body is read and raises 413. The handler
# below is what stops that arriving as an HTML error page from a JSON API.
MAX_REQUEST_BODY_BYTES = 64 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BODY_BYTES

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
    # Readiness answers "can this pod serve traffic", and without the database
    # it cannot. A pod that fails this check is removed from the Service's
    # endpoints and stops receiving requests without being restarted, which is
    # what makes a rolling update safe: the new pod takes traffic only once it
    # can actually answer.
    #
    # /health deliberately does NOT check the database. Liveness failures cause
    # restarts, so tying it to an external dependency would turn a database
    # outage into a restart loop across every replica.
    try:
        db.ping()
    except Exception:
        app.logger.warning(
            "database unreachable, reporting not ready",
            extra={"event": "not_ready", "dependency": "postgres"},
        )
        return jsonify(status="NOT_READY", dependency="postgres"), 503

    return jsonify(status="READY")


@app.route("/metrics")
def prometheus_metrics():
    body, content_type = metrics.render()
    return Response(body, mimetype=content_type)

@app.get("/version")
def version():
    return jsonify({"version": os.environ.get("APP_VERSION", "dev")})


def _json_body() -> dict:
    """The request body as a dict, or an empty dict for anything unusable.

    `silent=True` keeps a malformed body from raising: the endpoints below
    validate what they need and answer 400 themselves, so a bad request can
    never reach the generic 500 handler. Same contract as /echo — bad input is
    a client error, never a server error.
    """
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


@app.get("/notes")
def list_notes():
    return jsonify(notes=notes.list_notes())


@app.post("/notes")
def create_note():
    payload = _json_body()
    title = str(payload.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400

    created = notes.create_note(title, str(payload.get("body") or ""))
    return jsonify(created), 201


@app.put("/notes/<int:note_id>")
def update_note(note_id: int):
    payload = _json_body()
    title = str(payload.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400

    updated = notes.update_note(note_id, title, str(payload.get("body") or ""))
    if updated is None:
        return jsonify(error="note not found"), 404

    return jsonify(updated)


@app.delete("/notes/<int:note_id>")
def delete_note(note_id: int):
    if not notes.delete_note(note_id):
        return jsonify(error="note not found"), 404

    return "", 204


@app.errorhandler(RequestEntityTooLarge)
def _payload_too_large(_error: RequestEntityTooLarge) -> tuple[Response, int]:
    """Return the 413 as JSON rather than as Werkzeug's HTML page.

    Registered application-wide rather than on `/echo`, because the limit is a
    property of the server and a future endpoint that reads a body should not
    have to remember to opt in.

    The rejected body is not logged, for the same reason `/echo` does not log
    an invalid payload: it is attacker-controlled and, by definition, large.
    `content_length` is the useful field and it is one integer. Logged at
    warning because a client that sends this is doing something wrong, and
    because a burst of them is a signal worth alerting on later.
    """
    app.logger.warning(
        "request body over the limit",
        extra={
            "event": "payload_too_large",
            "content_length": request.content_length,
            "limit_bytes": MAX_REQUEST_BODY_BYTES,
        },
    )
    return jsonify(error="Request body too large"), 413


@app.route("/echo", methods=["POST"])
def echo():
    # The parse and the response are inside one `try` on purpose, and it is not
    # a stylistic choice. `/echo` reflects what it was sent, so a document deep
    # enough to exhaust the C stack does it once on the way in, in
    # `json.loads`, and again on the way out, in `jsonify`. The decoder and the
    # encoder do not fail at the same depth — a body can parse and then blow up
    # being serialised — and which one gives way first depends on the platform,
    # the interpreter version and how much stack the thread was given. Guarding
    # only the parse would have left a 500 reachable by exactly the payload the
    # guard was written for.
    try:
        return jsonify(received=request.get_json())
    except RecursionError:
        # Deeply nested JSON — `[[[[...]]]]` — recurses once per level, and
        # `RecursionError` is not a `ValueError`, so Flask never converts it
        # into the `BadRequest` the clause below catches. It reached the
        # generic 500 handler instead.
        #
        # Caught separately rather than added to the tuple below. Those two are
        # Werkzeug's way of saying "the client sent something unusable"; this is
        # the interpreter saying it ran out of stack, and folding them together
        # would hide that the fix came from a different direction.
        #
        # `MAX_CONTENT_LENGTH` does not subsume this. On CPython 3.12 the
        # decoder gives way somewhere between 8,000 and 16,000 levels, and
        # 16,000 levels is 32,000 bytes — half the 64 KiB ceiling. The two
        # limits guard different things and both are needed.
        #
        # **The depth is not a constant and must not be treated as one.** 3.12
        # replaced the old fixed recursion limit for C-level calls with a check
        # against the real C stack, so the threshold now moves with the
        # platform and with the stack the thread was given — and gunicorn
        # serves this on worker threads, not the main one. That is why nothing
        # here, in the tests or in `smoke.yml` asserts a particular depth
        # fails: the contract is that no body inside the size limit produces a
        # 5xx, and the depth at which the interpreter agrees is its business.
        #
        # 400 rather than 413: the body is inside the size limit and
        # well-formed, it is the shape that is hostile, and `/echo`'s contract
        # — bad input is a client error, never a server error — is what
        # `smoke.yml` asserts on every deploy.
        app.logger.warning(
            "JSON payload nested too deeply to process",
            extra={
                "event": "bad_request",
                "content_type": request.content_type,
                "content_length": request.content_length,
            },
        )
        return jsonify(error="Invalid JSON payload"), 400
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

# meres-jelolo: 203
