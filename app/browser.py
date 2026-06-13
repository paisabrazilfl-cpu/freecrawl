"""
Browser-rendered page fetch via Playwright (for JS-heavy pages).
Returns raw HTML after page settle; caller passes to extractor.
"""
import asyncio
from typing import Optional


async def fetch_with_browser(url: str, wait_ms: Optional[int] = None, timeout: int = 30000) -> tuple[str, int]:
    """Returns (html, status_code). Raises on navigation failure."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (compatible; FreeCrawl/1.0; +https://github.com/freecrawl)"
        )
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            status_code = response.status if response else 0
            if wait_ms:
                await asyncio.sleep(wait_ms / 1000)
            html = await page.content()
        finally:
            await browser.close()

    return html, status_code
