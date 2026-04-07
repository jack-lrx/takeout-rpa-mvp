from __future__ import annotations

import asyncio

from playwright.async_api import Page, Response, WebSocket

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.erp_client import ERPDispatcher
from app.services.parser import parse_network_payload
from app.services.store import SQLiteStore
from rpa.extractors import CapturedEvent, build_response_event, build_websocket_event

logger = get_logger(__name__)


class NetworkEventProcessor:
    def __init__(self, *, platform: str, store: SQLiteStore, dispatcher: ERPDispatcher):
        settings = get_settings()
        self.platform = platform
        self.store = store
        self.dispatcher = dispatcher
        self.truncate_length = settings.network_log_truncate
        self._tasks: set[asyncio.Task] = set()

    def schedule(self, coro: asyncio.Future) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait_for_pending(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def handle_response(self, response: Response) -> None:
        event = await build_response_event(
            response,
            platform=self.platform,
            truncate_length=self.truncate_length,
        )
        if event:
            self.process_event(event)

    async def handle_websocket_frame(self, url: str, payload_text: str | bytes) -> None:
        event = build_websocket_event(
            url=url,
            payload_text=payload_text,
            platform=self.platform,
            truncate_length=self.truncate_length,
        )
        if event:
            self.process_event(event)

    def process_event(self, event: CapturedEvent) -> None:
        logger.info(
            "captured_event source=%s url=%s status=%s body=%s",
            event.source,
            event.url,
            event.http_status,
            event.body_preview,
        )
        parsed = parse_network_payload(platform=event.platform, url=event.url, payload=event.payload)
        for order in parsed.orders:
            write_result = self.store.insert_order(order)
            logger.info("order_persisted order_id=%s created=%s", order.order_id, write_result.created)
            if write_result.created:
                self.dispatcher.push_order(order)
        for status in parsed.statuses:
            write_result = self.store.insert_status(status)
            logger.info(
                "status_persisted order_id=%s status=%s created=%s",
                status.order_id,
                status.status,
                write_result.created,
            )
            if write_result.created:
                self.dispatcher.push_status(status)


def attach_page_listeners(page: Page, processor: NetworkEventProcessor) -> None:
    def on_response(response: Response) -> None:
        processor.schedule(processor.handle_response(response))

    def on_websocket(websocket: WebSocket) -> None:
        logger.info("websocket_connected url=%s", websocket.url)

        def on_frame_received(payload: str | bytes) -> None:
            processor.schedule(processor.handle_websocket_frame(websocket.url, payload))

        websocket.on("framereceived", on_frame_received)

    page.on("response", on_response)
    page.on("websocket", on_websocket)
