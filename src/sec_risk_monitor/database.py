"""PostgreSQL transaction and migration helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg import Connection

from .config import PROJECT_ROOT


@contextmanager
def connect(database_url: str) -> Iterator[Connection]:
    """Open a transaction-scoped database connection."""

    with psycopg.connect(database_url) as connection:
        yield connection


def apply_sql_file(connection: Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        cursor.execute(sql)
    connection.commit()


def migrate(connection: Connection) -> None:
    """Apply ordered idempotent SQL migrations."""

    for path in sorted((PROJECT_ROOT / "sql").glob("[0-9][0-9][0-9]_*.sql")):
        apply_sql_file(connection, path)

