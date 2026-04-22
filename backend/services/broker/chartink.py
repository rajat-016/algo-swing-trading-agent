import asyncio
import re
from typing import List, Dict, Optional, Any
from playwright.async_api import async_playwright
from core.config import get_settings
from core.logging import logger


class ChartInkClient:
    def __init__(self, screener_url: Optional[str] = None, cookies: Optional[Dict] = None):
        self.settings = get_settings()
        self.screener_url = screener_url or self.settings.chartink_url
        self.cookies = cookies or {}
        self._symbols: List[str] = []
        self._last_fetch = None
        self._page = None
        self._browser = None

    async def fetch_stocks(self) -> List[str]:
        if not self.screener_url:
            logger.warning("ChartInk: No screener URL configured")
            return []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()

                for name, value in self.cookies.items():
                    await context.add_cookies([{"name": name, "value": value, "domain": ".chartink.com"}])

                page = await context.new_page()
                await page.goto(self.screener_url)
                await page.wait_for_timeout(5000)

                symbols = []
                rows = await page.query_selector_all("table tbody tr")
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if cells:
                        symbol_cell = cells[1] if len(cells) > 1 else None
                        if symbol_cell:
                            symbol_text = await symbol_cell.inner_text()
                            symbol = symbol_text.strip()
                            if symbol and not symbol.startswith("-"):
                                symbols.append(f"NSE:{symbol}")

                await browser.close()

                self._symbols = symbols
                self._last_fetch = asyncio.get_event_loop().time()
                logger.info(f"ChartInk: Fetched {len(symbols)} stocks")
                return symbols

        except Exception as e:
            logger.error(f"ChartInk: Error fetching stocks - {e}")
            return []

    def get_symbols(self) -> List[str]:
        return self._symbols

    def get_stocks_with_data(self) -> List[Dict[str, Any]]:
        results = []
        for symbol in self._symbols:
            results.append({"symbol": symbol})
        return results


chartink_client = ChartInkClient()


def get_chartink_client() -> ChartInkClient:
    return chartink_client