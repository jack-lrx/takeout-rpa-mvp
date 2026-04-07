from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class WriteResult:
    created: bool
    reason: str


def insert_or_ignore(connection: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> WriteResult:
    cursor = connection.execute(sql, params)
    created = cursor.rowcount > 0
    return WriteResult(created=created, reason="inserted" if created else "duplicate")
