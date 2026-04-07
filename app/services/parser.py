from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from app.core.logging import get_logger
from app.models.order import NormalizedOrder, OrderItem
from app.models.status import NormalizedStatus

logger = get_logger(__name__)

ORDER_ID_KEYS = {
    "orderid",
    "order_id",
    "bizorderid",
    "wmorderid",
    "orderno",
    "serialnumber",
    "tradeid",
}
ORDER_LIST_KEYS = {"orders", "orderlist", "list", "records", "rows", "result"}
ITEM_KEYS = {"items", "itemlist", "products", "productlist", "goods", "goodslist", "skulist", "cartitems"}
AMOUNT_KEYS = {"amount", "totalamount", "orderamount", "payamount", "actualamount", "totalprice", "price"}
EXPECTED_INCOME_KEYS = {"expectedincome", "merchantincome", "settleamount", "estimateincome", "receivableamount"}
STATUS_KEYS = {"status", "orderstatus", "deliverystatus", "dispatchstatus", "state"}
RIDER_KEYS = {"riderstatustext", "riderstatus", "deliverystatustext", "dispatchtext", "courierstatus"}
EVENT_TIME_KEYS = {"eventtime", "updatetime", "statusat", "timestamp", "updatedat", "time", "mtime"}
ITEM_NAME_KEYS = {"name", "itemname", "productname", "goodsname", "title", "sku", "skuname"}
ITEM_QUANTITY_KEYS = {"quantity", "qty", "count", "num", "amount"}
ITEM_PRICE_KEYS = {"unitprice", "price", "saleprice", "originprice", "amount"}

SAMPLE_ORDER_PAYLOAD: dict[str, Any] = {
    "data": {
        "orders": [
            {
                "bizOrderId": "MT202604070001",
                "productList": [
                    {"skuName": "宫保鸡丁", "quantity": 1, "price": 28},
                    {"skuName": "米饭", "quantity": 2, "price": 3},
                ],
                "payAmount": 34,
                "merchantIncome": 30,
            }
        ]
    }
}

SAMPLE_STATUS_PAYLOAD: dict[str, Any] = {
    "delivery": {
        "orderId": "MT202604070001",
        "deliveryStatus": "delivering",
        "riderStatusText": "骑手已取餐，正在配送",
        "updateTime": "2026-04-07T00:00:00+08:00",
    }
}


@dataclass(slots=True)
class ParsedPayload:
    orders: list[NormalizedOrder] = field(default_factory=list)
    statuses: list[NormalizedStatus] = field(default_factory=list)
    unparsed: bool = False


def parse_network_payload(
    *,
    platform: str,
    url: str,
    payload: dict[str, Any] | list[Any] | str | int | float | bool | None,
) -> ParsedPayload:
    normalized_payload = _ensure_json_payload(payload)
    parsed = ParsedPayload()
    for candidate in _candidate_order_nodes(normalized_payload):
        order = _adapt_order(candidate, platform=platform, raw_payload=normalized_payload)
        if order and not _order_exists(parsed.orders, order.order_id):
            parsed.orders.append(order)
    for candidate in _candidate_status_nodes(normalized_payload):
        status = _adapt_status(candidate, platform=platform, raw_payload=normalized_payload)
        if status and not _status_exists(parsed.statuses, status):
            parsed.statuses.append(status)
    if not parsed.orders and not parsed.statuses:
        parsed.unparsed = True
        logger.warning("parser_unparsed_payload url=%s payload=%s", url, _truncate_text(normalized_payload))
    return parsed


def _ensure_json_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return payload
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return payload
    return payload


def _candidate_order_nodes(payload: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in _walk_nodes(payload):
        if not isinstance(node, dict):
            continue
        if id(node) in seen:
            continue
        keys = {_norm_key(key) for key in node.keys()}
        if ITEM_KEYS & keys or ((ORDER_ID_KEYS & keys) and ((AMOUNT_KEYS & keys) or (EXPECTED_INCOME_KEYS & keys))):
            nodes.append(node)
            seen.add(id(node))
        for list_value in _iter_matching_values(node, ORDER_LIST_KEYS):
            if isinstance(list_value, list):
                for item in list_value:
                    if isinstance(item, dict) and id(item) not in seen:
                        nodes.append(item)
                        seen.add(id(item))
    return nodes


def _candidate_status_nodes(payload: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in _walk_nodes(payload):
        if not isinstance(node, dict):
            continue
        if id(node) in seen:
            continue
        keys = {_norm_key(key) for key in node.keys()}
        if ORDER_ID_KEYS & keys and (STATUS_KEYS & keys or RIDER_KEYS & keys):
            nodes.append(node)
            seen.add(id(node))
    return nodes


def _adapt_order(node: dict[str, Any], *, platform: str, raw_payload: Any) -> NormalizedOrder | None:
    order_id = _find_first_scalar(node, ORDER_ID_KEYS)
    if order_id in (None, ""):
        return None
    items = _extract_items(node)
    amount = _find_first_number(node, AMOUNT_KEYS)
    expected_income = _find_first_number(node, EXPECTED_INCOME_KEYS)
    if expected_income == 0.0 and amount:
        expected_income = amount
    return NormalizedOrder(
        platform=platform,
        order_id=str(order_id),
        items=items,
        amount=amount,
        expected_income=expected_income,
        raw_payload=raw_payload,
    )


def _adapt_status(node: dict[str, Any], *, platform: str, raw_payload: Any) -> NormalizedStatus | None:
    order_id = _find_first_scalar(node, ORDER_ID_KEYS)
    status = _find_first_scalar(node, STATUS_KEYS)
    if order_id in (None, "") or status in (None, ""):
        return None
    rider_text = _find_first_scalar(node, RIDER_KEYS) or ""
    event_time = _find_first_scalar(node, EVENT_TIME_KEYS) or datetime.now(timezone.utc).isoformat()
    return NormalizedStatus(
        platform=platform,
        order_id=str(order_id),
        status=str(status),
        rider_status_text=str(rider_text),
        event_time=event_time,
        raw_payload=raw_payload,
    )


def _extract_items(node: dict[str, Any]) -> list[OrderItem]:
    items_payload = _find_first_list(node, ITEM_KEYS)
    if not items_payload:
        return []
    items: list[OrderItem] = []
    for item in items_payload:
        if isinstance(item, dict):
            items.append(
                OrderItem(
                    name=str(_find_first_scalar(item, ITEM_NAME_KEYS) or ""),
                    quantity=_find_first_number(item, ITEM_QUANTITY_KEYS, default=1.0),
                    unit_price=_find_first_number(item, ITEM_PRICE_KEYS, default=None),
                    raw_item=item,
                )
            )
        else:
            items.append(OrderItem(name=str(item), raw_item={"value": item}))
    return items


def _walk_nodes(payload: Any) -> Iterable[Any]:
    yield payload
    if isinstance(payload, dict):
        for value in payload.values():
            yield from _walk_nodes(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk_nodes(item)


def _iter_matching_values(node: dict[str, Any], keyset: set[str]) -> Iterable[Any]:
    for key, value in node.items():
        if _norm_key(key) in keyset:
            yield value


def _find_first_scalar(payload: Any, keyset: set[str]) -> Any:
    for node in _walk_nodes(payload):
        if isinstance(node, dict):
            for key, value in node.items():
                if _norm_key(key) in keyset and not isinstance(value, (dict, list)):
                    return value
    return None


def _find_first_list(payload: Any, keyset: set[str]) -> list[Any]:
    for node in _walk_nodes(payload):
        if isinstance(node, dict):
            for key, value in node.items():
                if _norm_key(key) in keyset and isinstance(value, list):
                    return value
    return []


def _find_first_number(payload: Any, keyset: set[str], default: float | None = 0.0) -> float | None:
    for value in _iter_scalar_values(payload, keyset):
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _iter_scalar_values(payload: Any, keyset: set[str]) -> Iterable[Any]:
    for node in _walk_nodes(payload):
        if isinstance(node, dict):
            for key, value in node.items():
                if _norm_key(key) in keyset and not isinstance(value, (dict, list)):
                    yield value


def _norm_key(key: Any) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum() or ch == "_")


def _order_exists(orders: list[NormalizedOrder], order_id: str) -> bool:
    return any(item.order_id == order_id for item in orders)


def _status_exists(statuses: list[NormalizedStatus], status: NormalizedStatus) -> bool:
    return any(
        item.order_id == status.order_id and item.status == status.status and item.event_time == status.event_time
        for item in statuses
    )


def _truncate_text(payload: Any, limit: int = 300) -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
