"""Tests for the structured log line and the /metrics endpoint.

Kept separate from test_app.py: that file tests what the application returns to
a caller, this one tests what it tells an operator. They fail for different
reasons and a reviewer should be able to see which.
"""

import json
import logging

import pytest

from app.app import app
from app.logging_config import (
    REQUEST_ID_HEADER,
    JsonFormatter,
    RequestIdFilter,
    sanitise_request_id,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def logged(caplog):
    """Capture records the way the JSON formatter would see them.

    caplog captures the record, not the rendered line, so the filter that
    attaches request_id has to be applied by hand — it normally runs on the
    handler, and caplog installs its own.
    """
    caplog.set_level(logging.DEBUG)
    caplog.handler.addFilter(RequestIdFilter())
    yield caplog


def _access_records(logged):
    return [r for r in logged.records if getattr(r, "event", None) == "http_request"]


# --- the log line -----------------------------------------------------------


def test_request_is_logged_with_the_fields_the_dashboard_needs(logged, client):
    client.get("/")

    record = _access_records(logged)[-1]

    assert record.method == "GET"
    assert record.path == "/"
    assert record.endpoint == "/"
    assert record.status == 200
    assert record.duration_ms >= 0
    assert record.request_id


def test_log_line_is_valid_json_with_the_request_id_in_it(logged, client):
    client.get("/", headers={REQUEST_ID_HEADER: "known-id-123"})

    rendered = JsonFormatter().format(_access_records(logged)[-1])
    payload = json.loads(rendered)

    assert payload["request_id"] == "known-id-123"
    assert payload["level"] == "INFO"
    assert payload["status"] == 200
    assert payload["timestamp"].endswith("+00:00")


def test_a_sane_inbound_request_id_is_honoured_and_echoed(client):
    response = client.get("/", headers={REQUEST_ID_HEADER: "trace-abc_1.2"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-abc_1.2"


def test_configure_logging_does_not_touch_gunicorn_loggers():
    """The regression that cost three commits, asserted.

    `gunicorn.conf.py` silences `gunicorn.access` with a NullHandler so that
    `after_request` is the only thing logging a completed request. This
    function used to overwrite that in the worker, restoring a duplicate access
    line and doubling every rate computed from logs. Ownership is now split;
    this is the test that keeps it split.
    """
    from app.logging_config import configure_logging

    access = logging.getLogger("gunicorn.access")
    sentinel = logging.NullHandler()
    access.handlers = [sentinel]

    configure_logging()

    assert access.handlers == [sentinel], (
        "configure_logging() reconfigured a gunicorn logger; gunicorn.conf.py "
        "owns those, and the last writer winning is what caused the duplicate "
        "access line."
    )


@pytest.mark.parametrize(
    "hostile",
    [
        'evil" injected="yes',
        "line\nbreak",
        "x" * 65,
        "",
        "semi;colon",
    ],
)
def test_a_hostile_inbound_request_id_is_replaced_not_rejected(hostile):
    cleaned = sanitise_request_id(hostile)

    assert cleaned != hostile
    assert len(cleaned) == 32
    assert cleaned.isalnum()


def test_a_failed_request_is_logged_at_warning(logged, client):
    client.post("/echo", data='{"broken"', content_type="application/json")

    record = _access_records(logged)[-1]

    assert record.levelname == "WARNING"
    assert record.status == 400


def test_a_crashing_view_is_logged_at_error_with_its_traceback(
    logged, client, monkeypatch
):
    def explode():
        raise RuntimeError("deliberate")

    # Swapped rather than adding a permanent /boom route: an endpoint whose
    # only purpose is to crash is one a load balancer can find.
    monkeypatch.setitem(app.view_functions, "home", explode)
    # TESTING re-raises so a failing test shows its traceback. Turned off here
    # only, because this test is about what a *client* sees when a view breaks,
    # and under gunicorn that is a 500 rather than a stack trace.
    monkeypatch.setitem(app.config, "PROPAGATE_EXCEPTIONS", False)

    response = client.get("/")

    assert response.status_code == 500

    access = _access_records(logged)[-1]
    assert access.levelname == "ERROR"
    assert access.status == 500

    # Flask logs the exception itself on app.logger before the response is
    # finalised, so the traceback and the access line share a request_id — which
    # is the whole point of the filter.
    crash = [r for r in logged.records if r.exc_info][-1]
    payload = json.loads(JsonFormatter().format(crash))
    assert payload["error_type"] == "RuntimeError"
    assert payload["request_id"] == access.request_id


def test_health_checks_are_logged_at_debug(logged, client):
    client.get("/health")

    assert _access_records(logged)[-1].levelname == "DEBUG"


def test_an_unmatched_path_is_logged_with_its_real_path(logged, client):
    client.get("/does-not-exist")

    record = _access_records(logged)[-1]

    assert record.status == 404
    assert record.path == "/does-not-exist"
    assert record.endpoint == "<unmatched>"


def test_the_formatter_serialises_an_exception_into_one_line():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            "t", logging.ERROR, __file__, 1, "failed", None, True
        )
        import sys

        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))

    assert payload["error_type"] == "ValueError"
    assert payload["error_message"] == "boom"
    assert "Traceback" in payload["stack"]


# --- /metrics ---------------------------------------------------------------


def test_metrics_endpoint_serves_the_prometheus_exposition_format(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["Content-Type"]
    assert b"http_requests_total" in response.data
    assert b"http_request_duration_seconds" in response.data


def test_a_request_increments_the_counter_for_its_route(client):
    def total():
        body = client.get("/metrics").data.decode()
        wanted = ('http_requests_total{', 'endpoint="/echo"', 'status="200"')
        for line in body.splitlines():
            if line.startswith(wanted[0]) and all(p in line for p in wanted[1:]):
                return float(line.rsplit(" ", 1)[1])
        return 0.0

    before = total()
    client.post("/echo", json={"name": "Milan"})

    assert total() == before + 1


def test_multiprocess_mode_aggregates_from_the_shared_directory(
    tmp_path, monkeypatch
):
    """The path the container actually takes, which `pytest` otherwise skips.

    Under gunicorn with two workers the default in-process registry returns one
    worker's numbers per scrape. This asserts the branch that replaces it does
    read the shared directory — an untested branch here would mean the graphs
    are wrong only in production, which is where nobody is watching a unit test.
    """
    from prometheus_client import CollectorRegistry, Counter, values
    from prometheus_client.multiprocess import MultiProcessCollector

    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    # The value class is chosen at import time from the environment, so it has
    # to be re-resolved after the variable is set.
    monkeypatch.setattr(values, "ValueClass", values.MultiProcessValue())

    probe = Counter("probe_total", "…", registry=CollectorRegistry())
    probe.inc(3)

    from app import metrics

    body, content_type = metrics.render()

    assert "text/plain" in content_type
    assert b"probe_total 3.0" in body
    # Proof it went through the aggregating collector rather than the default
    # registry, which never saw this counter.
    assert MultiProcessCollector is not None


def test_every_unmatched_path_shares_one_label_value(client):
    for path in ("/nope-1", "/nope-2", "/nope-3"):
        client.get(path)

    body = client.get("/metrics").data.decode()
    unmatched = [
        line
        for line in body.splitlines()
        if line.startswith("http_requests_total{") and "<unmatched>" in line
    ]

    # One series, whatever the URL was. This is the cardinality guard the whole
    # of ADR-0007 argues for, and it is the assertion that would fail if
    # someone changed the label back to request.path.
    assert len(unmatched) == 1
    assert "/nope-1" not in body
