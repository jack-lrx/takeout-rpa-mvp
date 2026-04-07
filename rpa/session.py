from __future__ import annotations

from contextlib import asynccontextmanager

from playwright.async_api import BrowserContext, Page, async_playwright

from app.core.config import get_settings


@asynccontextmanager
async def persistent_browser_session(headless: bool = False) -> tuple[BrowserContext, Page]:
    settings = get_settings()
    settings.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(settings.browser_user_data_dir),
        headless=headless,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        yield context, page
    finally:
        await context.close()
        await playwright.stop()
