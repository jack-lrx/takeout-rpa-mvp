from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.order import NormalizedOrder
from app.models.status import NormalizedStatus
from app.services.store import SQLiteStore

logger = get_logger(__name__)


@dataclass(slots=True)
class PushResult:
    success: bool
    status_code: int | None
    response_body: str | None
    error_message: str | None


class ERPClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.erp_mock_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout_seconds

    def push_order(self, order: NormalizedOrder) -> PushResult:
        return self._post("/mock/orders", order.model_dump(mode="json"))

    def push_status(self, status: NormalizedStatus) -> PushResult:
        return self._post("/mock/order-status", status.model_dump(mode="json"))

    def _post(self, path: str, payload: dict) -> PushResult:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
            return PushResult(
                success=response.is_success,
                status_code=response.status_code,
                response_body=response.text,
                error_message=None if response.is_success else f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return PushResult(success=False, status_code=None, response_body=None, error_message=str(exc))


class ERPDispatcher:
    def __init__(self, store: SQLiteStore, client: ERPClient | None = None):
        self.store = store
        self.client = client or ERPClient()

    def push_order(self, order: NormalizedOrder) -> PushResult:
        result = self.client.push_order(order)
        self.store.log_push(
            platform=order.platform,
            order_id=order.order_id,
            data_type="order",
            target_url=f"{self.client.base_url}/mock/orders",
            request_payload=order.model_dump(mode="json"),
            response_status=result.status_code,
            response_body=result.response_body,
            success=result.success,
            error_message=result.error_message,
        )
        self.store.mark_order_pushed(order.platform, order.order_id, pushed=result.success)
        logger.info(
            "erp_push_order order_id=%s success=%s status_code=%s error=%s",
            order.order_id,
            result.success,
            result.status_code,
            result.error_message,
        )
        return result

    def push_status(self, status: NormalizedStatus) -> PushResult:
        result = self.client.push_status(status)
        self.store.log_push(
            platform=status.platform,
            order_id=status.order_id,
            data_type="status",
            target_url=f"{self.client.base_url}/mock/order-status",
            request_payload=status.model_dump(mode="json"),
            response_status=result.status_code,
            response_body=result.response_body,
            success=result.success,
            error_message=result.error_message,
        )
        self.store.mark_status_pushed(
            status.platform,
            status.order_id,
            status.status,
            status.event_time,
            pushed=result.success,
        )
        logger.info(
            "erp_push_status order_id=%s status=%s success=%s status_code=%s error=%s",
            status.order_id,
            status.status,
            result.success,
            result.status_code,
            result.error_message,
        )
        return result

    def retry_failed(self, limit: int | None = None) -> dict[str, int]:
        settings = get_settings()
        batch_limit = limit or settings.retry_batch_size
        orders = self.store.get_pending_orders(limit=batch_limit)
        statuses = self.store.get_pending_statuses(limit=batch_limit)
        order_success = 0
        status_success = 0
        for order in orders:
            if self.push_order(order).success:
                order_success += 1
        for status in statuses:
            if self.push_status(status).success:
                status_success += 1
        return {
            "pending_orders": len(orders),
            "pending_statuses": len(statuses),
            "order_success": order_success,
            "status_success": status_success,
        }
