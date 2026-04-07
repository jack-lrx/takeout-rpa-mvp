from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Response

FILTER_KEYWORDS = ("order", "status", "delivery", "dispatch")


@dataclass(slots=True)
class CapturedEvent:
    source: str
    platform: str
    url: str
    http_status: str
    body_preview: str
    payload: dict[str, Any] | list[Any] | str | int | float | bool | None
    captured_at: str


def should_track_url(url: str) -> bool:
    lowered = url.lower()
    return any(keyword in lowered for keyword in FILTER_KEYWORDS)


async def build_response_event(
    response: Response,
    *,
    platform: str,
    truncate_length: int,
) -> CapturedEvent | None:
    url = response.url
    if not should_track_url(url):
        return None
    try:
        body_text = await response.text()
    except Exception as exc:  # pragma: no cover - Playwright runtime edge
        body_text = f"<unable to read body: {exc}>"
    return CapturedEvent(
        source="response",
        platform=platform,
        url=url,
        http_status=str(response.status),
        body_preview=truncate_text(body_text, truncate_length),
        payload=parse_text_payload(body_text),
        captured_at=datetime.now(timezone.utc).isoformat(),
    )


def build_websocket_event(
    *,
    url: str,
    payload_text: str | bytes,
    platform: str,
    truncate_length: int,
) -> CapturedEvent | None:
    if not should_track_url(url):
        return None
    text = payload_text.decode("utf-8", errors="ignore") if isinstance(payload_text, bytes) else str(payload_text)
    return CapturedEvent(
        source="websocket",
        platform=platform,
        url=url,
        http_status="WS",
        body_preview=truncate_text(text, truncate_length),
        payload=parse_text_payload(text),
        captured_at=datetime.now(timezone.utc).isoformat(),
    )


def parse_text_payload(text: str) -> dict[str, Any] | list[Any] | str:
    stripped = text.strip()
    if not stripped:
        return text
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return text


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
