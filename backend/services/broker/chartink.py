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

        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-web-security",
                            "--disable-features=VizDisplayCompositor",
                            "--no-sandbox",
                        ],
                    )
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    )

                    for name, value in self.cookies.items():
                        await context.add_cookies([{"name": name, "value": value, "domain": ".chartink.com"}])

                    page = await context.new_page()
                    await page.goto(self.screener_url, wait_until="commit", timeout=60000)
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(12000)

                    # Wait for table to appear (ChartInk uses DataTables)
                    try:
                        await page.wait_for_selector("table", timeout=15000)
                        await page.wait_for_timeout(3000)
                    except Exception:
                        logger.warning("ChartInk: Table not found on page, proceeding with extraction anyway")

                    symbols = []
                    
                    SYMBOL_BLOCKLIST = {
                        "NAME", "SYMBOL", "LTP", "CHANGE", "VOLUME", "SCAN", "PRICE", "HIGH", "LOW", "OPEN", "CLOSE", "PREV", 
                        "CO", "PCS", "RS", "AVG", "MEDIAN", "VALUE", "AT", "52W", "52W_LOW", "52W_HIGH",
                        "BETA", "MCAP", "OID", "DOCTYPE", "NREUM", "LICENSE", "HTML", "HEAD", "BODY",
                        "META", "LINK", "SCRIPT", "STYLE", "DIV", "SPAN", "TABLE", "THEAD", "TBODY",
                        "TR", "TH", "TD", "A", "P", "BR", "IMG", "INPUT", "FONT", "B", "I",
                        "NO", "SR", "SR.", "#",
                    }

                    link_selectors = [
                        "table tbody tr td a[href*='/stocks/']",
                        "table tbody tr td a[href*='/charts/']",
                        "table a[href*='/stocks/']",
                        "table a[href*='/charts/']",
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
                            for el in elements[:50]:
                                try:
                                    text = (await el.inner_text()).strip()
                                    href = await el.get_attribute("href") or ""
                                    
                                    if text and 2 <= len(text) <= 12 and text.replace("_", "").replace("-", "").replace("&", "").isalpha():
                                        if text.upper() not in SYMBOL_BLOCKLIST and text.upper() not in symbols:
                                            symbols.append(text.upper())
                                            logger.debug(f"ChartInk: Found symbol from link: {text}")
                                except Exception:
                                    continue
                            
                            if len(symbols) >= 5:
                                break

                    if not symbols:
                        rows = await page.query_selector_all("table tbody tr")
                        logger.debug(f"ChartInk: Found {len(rows)} table rows")
                        for row in rows[:50]:
                            try:
                                cells = await row.query_selector_all("td")
                                if cells and len(cells) > 0:
                                    first_cell_text = (await cells[0].inner_text()).strip()
                                    
                                    if first_cell_text and 2 <= len(first_cell_text) <= 12:
                                        if first_cell_text.upper() not in SYMBOL_BLOCKLIST:
                                            anchors = await row.query_selector_all("a")
                                            if anchors:
                                                text = (await anchors[0].inner_text()).strip()
                                                if text and text.upper() not in SYMBOL_BLOCKLIST and text.upper() not in symbols:
                                                    symbols.append(text.upper())
                                                    logger.debug(f"ChartInk: Found symbol from row: {text}")
                                            elif first_cell_text.replace("_", "").replace("-", "").replace("&", "").isalpha():
                                                symbols.append(first_cell_text.upper())
                                                logger.debug(f"ChartInk: Found symbol from cell text: {first_cell_text}")
                            except Exception:
                                continue

                    if not symbols:
                        # Try extracting from all text content
                        page_text = await page.inner_text("body")
                        for line in page_text.split("\n"):
                            line = line.strip()
                            if 2 <= len(line) <= 12 and line.replace("_", "").replace("-", "").replace("&", "").isalpha():
                                if line.upper() not in SYMBOL_BLOCKLIST and line.upper() not in symbols:
                                    symbols.append(line.upper())
                                    logger.debug(f"ChartInk: Found symbol from page text: {line}")

                        if not symbols:
                            content = await page.content()
                            import re
                            patterns = [
                                r'/stocks/([A-Z0-9\-]{2,12})["\'/]',
                                r'/charts/([A-Z0-9\-]{2,12})["\'/]',
                                r'"symbol"\s*:\s*"([A-Z0-9\-]{2,12})"',
                                r'data-symbol=["\']([A-Z0-9\-]{2,12})["\']',
                                r'symbol["\s:=]+["\']([A-Z0-9\-]{2,12})["\']',
                            ]
                            for pattern in patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for m in matches:
                                    clean = m.replace("&", "").strip("-")
                                    if clean and 2 <= len(clean) <= 12 and clean.replace("_", "").replace("-", "").isalpha():
                                        if clean.upper() not in SYMBOL_BLOCKLIST and clean.upper() not in symbols:
                                            symbols.append(clean.upper())
                            
                        if len(symbols) >= 1:
                            logger.debug(f"ChartInk: Found {len(symbols)} symbols from fallback methods")
                        else:
                            logger.warning("ChartInk: No symbols found after all extraction attempts. Dumping first 2000 chars of page content for debugging.")
                            content = await page.content()
                            logger.debug(f"ChartInk page content (first 2000 chars): {content[:2000]}")

                    await browser.close()

                    symbols = [s for s in symbols if s.isupper() and (s.isalpha() or s.replace("-", "").isalpha()) and 2 <= len(s) <= 12 and s not in SYMBOL_BLOCKLIST]
                    symbols = list(dict.fromkeys(symbols))[:30]
                    self._symbols = symbols
                    self._last_fetch = asyncio.get_event_loop().time()
                    logger.info(f"ChartInk: Fetched {len(symbols)} stocks: {symbols[:10]}")
                    return symbols

            except Exception as e:
                last_error = e
                if "ERR_NETWORK" in str(e) or "timeout" in str(e).lower():
                    logger.warning(f"ChartInk: Network error on attempt {attempt}/{max_retries} - {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(3 * attempt)
                else:
                    logger.error(f"ChartInk: Error fetching stocks - {e}")
                    return []

        logger.error(f"ChartInk: All {max_retries} attempts failed - {last_error}")
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