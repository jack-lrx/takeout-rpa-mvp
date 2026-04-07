from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.core.config import BASE_DIR
from app.models.order import NormalizedOrder, OrderItem
from app.models.status import NormalizedStatus
from app.services.dedup import WriteResult, insert_or_ignore


class SQLiteStore:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.schema_path = BASE_DIR / "app" / "db" / "schema.sql"

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize_database(self) -> None:
        schema = self.schema_path.read_text(encoding="utf-8")
        with self.connection() as connection:
            connection.executescript(schema)

    def insert_order(self, order: NormalizedOrder) -> WriteResult:
        sql = """
        INSERT OR IGNORE INTO orders (
            platform, order_id, items, amount, expected_income, raw_payload, pushed_to_erp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            order.platform,
            order.order_id,
            self._json_dumps([item.model_dump(mode="json") for item in order.items]),
            order.amount,
            order.expected_income,
            self._json_dumps(order.raw_payload),
            order.pushed_to_erp,
        )
        with self.connection() as connection:
            return insert_or_ignore(connection, sql, params)

    def insert_status(self, status: NormalizedStatus) -> WriteResult:
        sql = """
        INSERT OR IGNORE INTO status (
            platform, order_id, status, rider_status_text, event_time, raw_payload, pushed_to_erp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            status.platform,
            status.order_id,
            status.status,
            status.rider_status_text,
            status.event_time,
            self._json_dumps(status.raw_payload),
            status.pushed_to_erp,
        )
        with self.connection() as connection:
            return insert_or_ignore(connection, sql, params)

    def mark_order_pushed(self, platform: str, order_id: str, pushed: bool = True) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE orders
                SET pushed_to_erp = ?, updated_at = CURRENT_TIMESTAMP
                WHERE platform = ? AND order_id = ?
                """,
                (1 if pushed else 0, platform, order_id),
            )

    def mark_status_pushed(
        self,
        platform: str,
        order_id: str,
        status: str,
        event_time: str,
        pushed: bool = True,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE status
                SET pushed_to_erp = ?
                WHERE platform = ? AND order_id = ? AND status = ? AND event_time = ?
                """,
                (1 if pushed else 0, platform, order_id, status, event_time),
            )

    def log_push(
        self,
        *,
        platform: str,
        order_id: str,
        data_type: str,
        target_url: str,
        request_payload: dict[str, Any] | list[Any] | str,
        response_status: int | None,
        response_body: str | None,
        success: bool,
        error_message: str | None,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO push_logs (
                    platform, order_id, data_type, target_url, request_payload,
                    response_status, response_body, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    platform,
                    order_id,
                    data_type,
                    target_url,
                    self._json_dumps(request_payload),
                    response_status,
                    response_body,
                    1 if success else 0,
                    error_message,
                ),
            )

    def get_pending_orders(self, limit: int = 100) -> list[NormalizedOrder]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT platform, order_id, items, amount, expected_income, raw_payload, pushed_to_erp
                FROM orders
                WHERE pushed_to_erp = 0
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_order(row) for row in rows]

    def get_pending_statuses(self, limit: int = 100) -> list[NormalizedStatus]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT platform, order_id, status, rider_status_text, event_time, raw_payload, pushed_to_erp
                FROM status
                WHERE pushed_to_erp = 0
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_status(row) for row in rows]

    def list_push_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT platform, order_id, data_type, target_url, response_status, response_body,
                       success, error_message, created_at
                FROM push_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _row_to_order(self, row: sqlite3.Row) -> NormalizedOrder:
        items = self._json_loads(row["items"], default=[])
        return NormalizedOrder(
            platform=row["platform"],
            order_id=row["order_id"],
            items=[OrderItem.model_validate(item) for item in items],
            amount=row["amount"],
            expected_income=row["expected_income"],
            raw_payload=self._json_loads(row["raw_payload"], default={}),
            pushed_to_erp=row["pushed_to_erp"],
        )

    def _row_to_status(self, row: sqlite3.Row) -> NormalizedStatus:
        return NormalizedStatus(
            platform=row["platform"],
            order_id=row["order_id"],
            status=row["status"],
            rider_status_text=row["rider_status_text"],
            event_time=row["event_time"],
            raw_payload=self._json_loads(row["raw_payload"], default={}),
            pushed_to_erp=row["pushed_to_erp"],
        )

    @staticmethod
    def _json_dumps(payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _json_loads(payload: str, default: Any) -> Any:
        try:
            return json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return default
