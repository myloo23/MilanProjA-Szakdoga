"""The note entity: every statement that touches the `note` table.

Separated from the view functions so the endpoints can be tested without a
database — the tests replace these four functions. It also keeps SQL out of
`app.py`, which is already the largest module in the project.
"""

from app.db import connection

_COLUMNS = "id, title, body, created_at"


def list_notes() -> list[dict]:
    with connection() as conn:
        return conn.execute(
            f"SELECT {_COLUMNS} FROM note ORDER BY id"
        ).fetchall()


def create_note(title: str, body: str) -> dict:
    with connection() as conn:
        return conn.execute(
            f"INSERT INTO note (title, body) VALUES (%s, %s) RETURNING {_COLUMNS}",
            (title, body),
        ).fetchone()


def update_note(note_id: int, title: str, body: str) -> dict | None:
    """Return the updated row, or None when no note has that id."""
    with connection() as conn:
        return conn.execute(
            f"UPDATE note SET title = %s, body = %s WHERE id = %s RETURNING {_COLUMNS}",
            (title, body, note_id),
        ).fetchone()


def delete_note(note_id: int) -> bool:
    """Return True when a row was removed, False when the id did not exist."""
    with connection() as conn:
        return conn.execute(
            "DELETE FROM note WHERE id = %s", (note_id,)
        ).rowcount > 0
