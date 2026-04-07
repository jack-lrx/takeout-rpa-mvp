from __future__ import annotations

import argparse
import asyncio
import json

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.erp_client import ERPDispatcher
from app.services.parser import SAMPLE_ORDER_PAYLOAD, SAMPLE_STATUS_PAYLOAD
from app.services.store import SQLiteStore
from rpa.listeners import NetworkEventProcessor, attach_page_listeners
from rpa.session import persistent_browser_session

logger = get_logger(__name__)


async def run_live(platform: str, merchant_url: str, headless: bool) -> None:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.initialize_database()
    processor = NetworkEventProcessor(
        platform=platform,
        store=store,
        dispatcher=ERPDispatcher(store),
    )

    async with persistent_browser_session(headless=headless) as (_, page):
        attach_page_listeners(page, processor)
        await page.goto(merchant_url, wait_until="domcontentloaded")
        print(f"浏览器已打开：{merchant_url}")
        print("请在浏览器中完成商家后台扫码登录。")
        print("登录完成后，保持页面打开。程序将持续监听 XHR 和 WebSocket 网络事件。")
        await asyncio.to_thread(input, "扫码完成后按 Enter 开始正式监听，按 Ctrl+C 退出：")
        while True:
            await asyncio.sleep(1)


async def run_demo(platform: str) -> None:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)
    store.initialize_database()
    processor = NetworkEventProcessor(
        platform=platform,
        store=store,
        dispatcher=ERPDispatcher(store),
    )
    processor.process_event(
        event=_build_demo_event(
            platform=platform,
            url="https://demo.local/api/order/query",
            http_status="200",
            payload=SAMPLE_ORDER_PAYLOAD,
        )
    )
    processor.process_event(
        event=_build_demo_event(
            platform=platform,
            url="wss://demo.local/ws/delivery/status",
            http_status="WS",
            payload=SAMPLE_STATUS_PAYLOAD,
        )
    )
    print("Demo payloads processed successfully.")


def _build_demo_event(*, platform: str, url: str, http_status: str, payload: dict) -> object:
    from rpa.extractors import CapturedEvent

    return CapturedEvent(
        source="demo",
        platform=platform,
        url=url,
        http_status=http_status,
        body_preview=json.dumps(payload, ensure_ascii=False)[:200],
        payload=payload,
        captured_at="demo",
    )


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Login merchant backend and listen for order events.")
    parser.add_argument("--platform", default="meituan", help="Platform identifier, e.g. meituan or eleme")
    parser.add_argument("--merchant-url", default=settings.merchant_backend_url, help="Merchant backend URL")
    parser.add_argument("--headless", action="store_true", help="Run Playwright in headless mode")
    parser.add_argument("--demo", action="store_true", help="Use sample payloads instead of opening a browser")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    if args.demo:
        await run_demo(args.platform)
    else:
        await run_live(args.platform, args.merchant_url, args.headless)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("rpa_listener_stopped")
