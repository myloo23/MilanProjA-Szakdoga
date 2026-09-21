"""Database access: connection handling and the readiness check.

One connection per request rather than a pool. A pool (`psycopg_pool`) is the
production answer and belongs in the further-work chapter; at this scale the
cost of opening a connection sits below the resolution of the deployment
measurements this project exists to make, and a pool adds a lifecycle that
gunicorn's fork model would need care with.

Nothing here creates the schema. That is the deployment's job — see the
`migrate` init container in `chart/templates/backend.yaml`, which runs the statements in
the `db-schema` ConfigMap before this application starts.
"""

import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


def _dsn() -> str:
    return (
        f"host={os.environ.get('DB_HOST', 'localhost')} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'projecta')} "
        f"user={os.environ.get('POSTGRES_USER', 'projecta')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', '')}"
    )


@contextmanager
def connection():
    # Kapcsolatonként egy kérés. A kapcsolatkészlet (psycopg_pool) a
    # éles válasz, és a 7. fejezetbe tartozik: ezen a terhelésen a
    # kapcsolatnyitás költsége a mérés felbontása alatt van.
    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        yield conn


def ping() -> None:
    with connection() as conn:
        conn.execute("SELECT 1")