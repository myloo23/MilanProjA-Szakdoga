"""Endpoint tests for /notes.

The database is not touched: `app.notes` keeps every SQL statement behind four
functions, and these tests replace them. What is tested here is the HTTP
contract — status codes, validation and the JSON shape — not the SQL.
"""

import pytest

from app.app import app

NOTE = {"id": 1, "title": "Első", "body": "szöveg", "created_at": "2026-09-18T12:00:00+00:00"}


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_list_notes_returns_all(client, monkeypatch):
    monkeypatch.setattr("app.app.notes.list_notes", lambda: [NOTE])

    response = client.get("/notes")

    assert response.status_code == 200
    assert response.get_json() == {"notes": [NOTE]}


def test_create_note_returns_201(client, monkeypatch):
    calls = []

    def create(title, body):
        calls.append((title, body))
        return NOTE

    monkeypatch.setattr("app.app.notes.create_note", create)

    response = client.post("/notes", json={"title": "  Első  ", "body": "szöveg"})

    assert response.status_code == 201
    assert response.get_json() == NOTE
    assert calls == [("Első", "szöveg")]


def test_create_note_body_defaults_to_empty(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.app.notes.create_note",
        lambda title, body: calls.append((title, body)) or NOTE,
    )

    response = client.post("/notes", json={"title": "Első"})

    assert response.status_code == 201
    assert calls == [("Első", "")]


@pytest.mark.parametrize(
    "payload",
    [{}, {"title": ""}, {"title": "   "}, {"body": "csak törzs"}],
)
def test_create_note_requires_title(client, monkeypatch, payload):
    monkeypatch.setattr(
        "app.app.notes.create_note",
        lambda *_: pytest.fail("must not reach the database"),
    )

    response = client.post("/notes", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {"error": "title is required"}


@pytest.mark.parametrize("data", ['{"title":', "[1, 2]", "nem json"])
def test_create_note_malformed_body_is_400_not_500(client, data):
    response = client.post("/notes", data=data, content_type="application/json")

    assert response.status_code == 400


def test_update_note_returns_updated(client, monkeypatch):
    updated = {**NOTE, "title": "Új"}
    monkeypatch.setattr("app.app.notes.update_note", lambda note_id, title, body: updated)

    response = client.put("/notes/1", json={"title": "Új"})

    assert response.status_code == 200
    assert response.get_json() == updated


def test_update_missing_note_returns_404(client, monkeypatch):
    monkeypatch.setattr("app.app.notes.update_note", lambda *_: None)

    response = client.put("/notes/999", json={"title": "Új"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "note not found"}


def test_update_note_requires_title(client, monkeypatch):
    monkeypatch.setattr(
        "app.app.notes.update_note",
        lambda *_: pytest.fail("must not reach the database"),
    )

    response = client.put("/notes/1", json={"body": "x"})

    assert response.status_code == 400


def test_delete_note_returns_204(client, monkeypatch):
    monkeypatch.setattr("app.app.notes.delete_note", lambda note_id: True)

    response = client.delete("/notes/1")

    assert response.status_code == 204
    assert response.data == b""


def test_delete_missing_note_returns_404(client, monkeypatch):
    monkeypatch.setattr("app.app.notes.delete_note", lambda note_id: False)

    response = client.delete("/notes/999")

    assert response.status_code == 404
