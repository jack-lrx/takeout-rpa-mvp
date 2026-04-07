from __future__ import annotations

from threading import Lock
from typing import Any

from fastapi import APIRouter

from app.models.order import NormalizedOrder
from app.models.status import NormalizedStatus

router = APIRouter(prefix="/mock", tags=["erp-mock"])

_order_lock = Lock()
_status_lock = Lock()
_received_orders: list[dict[str, Any]] = []
_received_statuses: list[dict[str, Any]] = []


@router.post("/orders")
async def receive_order(order: NormalizedOrder) -> dict[str, Any]:
    payload = order.model_dump(mode="json")
    with _order_lock:
        _received_orders.append(payload)
        count = len(_received_orders)
    return {"accepted": True, "message": "order received", "count": count, "data": payload}


@router.post("/order-status")
async def receive_order_status(status: NormalizedStatus) -> dict[str, Any]:
    payload = status.model_dump(mode="json")
    with _status_lock:
        _received_statuses.append(payload)
        count = len(_received_statuses)
    return {"accepted": True, "message": "order status received", "count": count, "data": payload}


@router.get("/orders")
async def list_orders() -> dict[str, Any]:
    with _order_lock:
        items = list(_received_orders)
    return {"count": len(items), "items": items}


@router.get("/order-status")
async def list_order_status() -> dict[str, Any]:
    with _status_lock:
        items = list(_received_statuses)
    return {"count": len(items), "items": items}
