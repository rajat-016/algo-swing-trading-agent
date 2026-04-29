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
                context = await browser.new_context(viewport={"width": 1920, "height": 1080})

                for name, value in self.cookies.items():
                    await context.add_cookies([{"name": name, "value": value, "domain": ".chartink.com"}])

                page = await context.new_page()
                await page.goto(self.screener_url)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(8000)

                symbols = []
                
                SYMBOL_BLOCKLIST = {
                    "NAME", "SYMBOL", "LTP", "CHANGE", "VOLUME", "SCAN", "PRICE", "HIGH", "LOW", "OPEN", "CLOSE", "PREV", 
                    "CO", "PCS", "RS", "AVG", "MEDIAN", "VALUE", "AT", "52W", "52W_LOW", "52W_HIGH",
                    "BETA", "MCAP", "OID", "DOCTYPE", "NREUM", "LICENSE", "HTML", "HEAD", "BODY",
                    "META", "LINK", "SCRIPT", "STYLE", "DIV", "SPAN", "TABLE", "THEAD", "TBODY",
                    "TR", "TH", "TD", "A", "P", "BR", "IMG", "INPUT", "FONT", "B", "I",
                }

                link_selectors = [
                    "table tbody tr td a[href*='/stocks/']",
                    "table tbody tr td a[href*='/charts/']",
                    "a[href*='/stocks/']",
                    "a[href*='/charts/']",
                    "[class*='stock'] a",
                    "[data-symbol]",
                    ".symbol-cell a",
                    ".stock-symbol a",
                ]
                
                for selector in link_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.debug(f"ChartInk: Found {len(elements)} elements with selector '{selector}'")
                        for el in elements[:40]:
                            try:
                                text = (await el.inner_text()).strip()
                                href = await el.get_attribute("href") or ""
                                
                                if text and 2 <= len(text) <= 10 and text.replace("_", "").replace("-", "").isalpha():
                                    if text.upper() not in SYMBOL_BLOCKLIST and text.upper() not in symbols:
                                        symbols.append(text.upper())
                                        logger.debug(f"ChartInk: Found symbol from link: {text}")
                            except Exception:
                                continue
                        
                        if len(symbols) >= 5:
                            break

                if not symbols:
                    rows = await page.query_selector_all("table tbody tr")
                    for row in rows[:50]:
                        try:
                            cells = await row.query_selector_all("td")
                            if cells and len(cells) > 0:
                                first_cell_text = (await cells[0].inner_text()).strip()
                                
                                if first_cell_text and 2 <= len(first_cell_text) <= 10:
                                    if first_cell_text.upper() not in SYMBOL_BLOCKLIST:
                                        anchors = await row.query_selector_all("a")
                                        if anchors:
                                            text = (await anchors[0].inner_text()).strip()
                                            if text and text.upper() not in SYMBOL_BLOCKLIST and text.upper() not in symbols:
                                                symbols.append(text.upper())
                                                logger.debug(f"ChartInk: Found symbol from row: {text}")
                        except Exception:
                            continue

                if not symbols:
                    content = await page.content()
                    import re
                    patterns = [
                        r'/stocks/([A-Z]{2,10})["\'/]',
                        r'/charts/([A-Z]{2,10})["\'/]',
                        r'"symbol"\s*:\s*"([A-Z]{2,10})"',
                        r'data-symbol=["\']([A-Z]{2,10})["\']',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for m in matches:
                            if m.upper() not in SYMBOL_BLOCKLIST and m.upper() not in symbols:
                                symbols.append(m.upper())
                    
                    if len(symbols) >= 5:
                        logger.debug(f"ChartInk: Found {len(symbols)} symbols from regex patterns")

                await browser.close()

                symbols = [s for s in symbols if s.isupper() and s.isalpha() and 2 <= len(s) <= 10 and s not in SYMBOL_BLOCKLIST]
                symbols = list(dict.fromkeys(symbols))[:30]
                self._symbols = symbols
                self._last_fetch = asyncio.get_event_loop().time()
                logger.info(f"ChartInk: Fetched {len(symbols)} stocks: {symbols[:10]}")
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