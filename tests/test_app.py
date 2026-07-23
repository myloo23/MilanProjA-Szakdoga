import pytest

from app.app import app


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