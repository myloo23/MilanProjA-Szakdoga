import json

import pytest
from flask import Request

from app.app import MAX_REQUEST_BODY_BYTES, app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

def test_home_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200

def test_health_returns_up(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "UP"}

def test_echo_valid_json(client):
    payload = {"name": "Milan"}

    response = client.post("/echo", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {
        "received": payload
    }

def test_echo_invalid_json_returns_400(client):
    invalid_json = '{"name":"Milan"'

    response = client.post(
        "/echo",
        data=invalid_json,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid JSON payload"
    }

def test_echo_without_content_type_returns_400(client):
    response = client.post("/echo", data='{"name":"Milan"}')

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid JSON payload"
    }

def test_echo_wrong_content_type_returns_400(client):
    response = client.post(
        "/echo",
        data='{"name":"Milan"}',
        content_type="text/plain",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid JSON payload"
    }

def test_echo_returns_400_when_the_stack_runs_out(client, monkeypatch):
    # Regression guard. Deeply nested JSON recurses once per level, and
    # RecursionError is not a ValueError, so Flask never turned it into the
    # BadRequest the handler catches and this returned 500 — unauthenticated,
    # and a 500 moves the error rate the alert rule watches.
    #
    # The exception is injected rather than provoked with a real payload. On
    # CPython 3.12 the depth at which the parser gives way is a function of the
    # actual C stack, so it moves with the platform, the interpreter build and
    # the size of the thread's stack — and gunicorn serves this on worker
    # threads. A test that sent 16,000 brackets would be asserting a property
    # of the machine it happens to run on, and would go green for the wrong
    # reason the first time a runner had more stack. This asserts the handler,
    # which is the part this repository owns; the contract test below covers
    # what a real payload does.
    def out_of_stack(*_args, **_kwargs):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(Request, "get_json", out_of_stack)

    response = client.post("/echo", json={"depth": "irrelevant"})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid JSON payload"
    }

def test_echo_never_returns_5xx_for_a_body_inside_the_limit(client):
    # The contract, stated as the contract: a body the size limit lets through
    # is the client's problem or it is fine, and it is never the server's
    # fault. Deliberately not asserting 400 — at this depth the parser may
    # succeed or may run out of stack depending on the host, and both answers
    # are correct. Only a 5xx is a bug, which is exactly the thing that was
    # wrong before.
    #
    # Sized to the deepest nesting that fits under the size limit, so the two
    # limits are tested where they meet rather than somewhere comfortable.
    nesting = (MAX_REQUEST_BODY_BYTES // 2) - 768
    payload = "[" * nesting + "]" * nesting

    assert len(payload) < MAX_REQUEST_BODY_BYTES

    response = client.post(
        "/echo",
        data=payload,
        content_type="application/json",
    )

    assert response.status_code < 500

def test_echo_oversized_body_returns_413(client):
    # The body is well-formed JSON and the only thing wrong with it is its
    # size, so this exercises MAX_CONTENT_LENGTH rather than any parse path.
    oversized = json.dumps({"pad": "x" * MAX_REQUEST_BODY_BYTES})

    response = client.post(
        "/echo",
        data=oversized,
        content_type="application/json",
    )

    assert response.status_code == 413
    assert response.get_json() == {
        "error": "Request body too large"
    }

def test_a_body_at_the_limit_is_still_accepted(client):
    # The limit has to be a ceiling rather than an approximation: a fix that
    # rejected legitimate traffic would pass the test above and still break the
    # smoke test. Sized to land just inside the limit once JSON quoting and the
    # key are counted.
    payload = {"pad": "x" * (MAX_REQUEST_BODY_BYTES - 128)}

    assert len(json.dumps(payload)) < MAX_REQUEST_BODY_BYTES

    response = client.post("/echo", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {"received": payload}

def test_ready_returns_ready(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "READY"}