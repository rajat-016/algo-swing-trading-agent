import requests
import hashlib
from typing import Optional, Dict, List, Any
from datetime import datetime
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException, OrderException, NetworkException
from core.config import get_settings
from core.enums import OrderSide, OrderType, ProductType
from core.logging import logger
from core.exceptions import (
    ZerodhaError, IPRestrictionError, AuthenticationError, 
    RateLimitError, OrderError, InsufficientFundsError, DataFetchError
)
import os


class OrderResponse:
    def __init__(self, order_id: str, status: str, message: str = ""):
        self.order_id = order_id
        self.status = status
        self.message = message


class KiteBroker:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.zerodha.api_key
        self.api_secret = self.settings.zerodha.api_secret
        self.access_token = self.settings.zerodha.access_token
        self.kite_url = self.settings.zerodha.kite_url
        self.target_pct = self.settings.target_profit_pct
        self.sl_pct = self.settings.stop_loss_pct
        self.kite: Optional[KiteConnect] = None
        self._connected = False
        self._instruments_cache: Dict[str, Any] = {}
        self._name_to_symbol_cache: Dict[str, str] = {}
        self._symbol_to_token_cache: Dict[str, str] = {}
        self._ltp_cache: Dict[str, float] = {}
        
    def _init_kite(self):
        if not self.kite:
            self.kite = KiteConnect(self.api_key, root=self.kite_url)
            if self.access_token:
                self.kite.set_access_token(self.access_token)

    def _map_chartink_to_zerodha(self, chartink_symbol: str) -> str:
        from services.broker.symbol_mapper import SymbolMapper

        symbol_mapper = SymbolMapper.get_instance()
        kite_symbol = symbol_mapper.get_kite_symbol(chartink_symbol)
        if kite_symbol:
            logger.debug(f"SymbolMapper: Mapped '{chartink_symbol}' -> '{kite_symbol}'")
            return kite_symbol

        logger.warning(f"SymbolMapper: '{chartink_symbol}' not in mapping table, falling back to Zerodha instruments")

        if not self._name_to_symbol_cache:
            self._load_name_mapping()

        clean = chartink_symbol.upper().replace(" ", "")
        
        if clean in self._symbol_to_token_cache:
            return clean
        
        if clean in self._name_to_symbol_cache:
            return self._name_to_symbol_cache[clean]
        
        for key, value in self._name_to_symbol_cache.items():
            key_clean = key.replace(" ", "").replace("LIMITED", "").replace("LTD", "")
            if key_clean == clean or clean.startswith(key_clean[:len(key_clean)//2+1]):
                return value

        logger.warning(f"SymbolMapper: No mapping found for '{chartink_symbol}', using raw symbol")
        return clean

    def _load_name_mapping(self):
        try:
            self._init_kite()
            instruments = self.kite.instruments("NSE")
            for inst in instruments:
                name = inst.get("name", "")
                symbol = inst.get("tradingsymbol", "")
                token = str(inst.get("instrument_token", ""))
                if name and symbol and token:
                    self._name_to_symbol_cache[name.upper()] = symbol
                    self._symbol_to_token_cache[symbol] = token
        except Exception as e:
            logger.error(f"Error loading name mapping: {e}")

    def connect(self) -> bool:
        try:
            self._init_kite()
            
            if self.access_token and self._validate_connection():
                self._connected = True
                return True

            if self.settings.zerodha.request_token:
                logger.info("Zerodha: Generating access token from request token...")
                if self._generate_session_from_request_token():
                    self._save_access_token()
                    if self._validate_connection():
                        self._connected = True
                        return True
                else:
                    logger.warning("Zerodha: Request token is invalid/expired")
                    self._clear_tokens()

            logger.error(
                "Zerodha: Could not connect. Get a fresh request token:\n"
                f"  1. Open: https://kite.zerodha.com/connect/login?v=3&api_key={self.api_key}\n"
                "  2. Login with your Zerodha credentials\n"
                "  3. Copy the request_token from the redirect URL\n"
                "  4. Set it as ZERODHA__REQUEST_TOKEN in backend/.env\n"
                "  5. Restart the application"
            )
            return False

        except TokenException as e:
            error_msg = str(e)
            if "IP" in error_msg or "403" in error_msg:
                logger.critical(f"Zerodha: IP restriction detected - {e}")
                raise IPRestrictionError(f"IP not allowed: {e}", ip_address=self.settings.zerodha.api_key)
            else:
                logger.error(f"Zerodha: Token error - {e}")
                raise AuthenticationError(f"Token error: {e}")
        except NetworkException as e:
            logger.error(f"Zerodha: Network error - {e}")
            raise ZerodhaError(f"Network error: {e}", error_type="NETWORK_ERROR")
        except Exception as e:
            error_msg = str(e)
            if "IP" in error_msg or "403" in error_msg:
                logger.critical(f"Zerodha: IP restriction detected - {e}")
                raise IPRestrictionError(f"IP not allowed: {e}")
            elif "403" in error_msg or "unauthorized" in error_msg.lower():
                logger.error(f"Zerodha: Authentication failed - {e}")
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                logger.error(f"Zerodha: Connection error - {e}")
                return False

    def _validate_connection(self) -> bool:
        if not self.kite:
            return False
        try:
            profile = self.kite.profile()
            if profile:
                logger.info(f"Zerodha: Connected (user: {profile.get('user_name', 'unknown')})")
                self._connected = True
                return True
        except Exception:
            self._connected = False
        return False

    def _generate_session_from_request_token(self) -> bool:
        try:
            request_token = self.settings.zerodha.request_token
            api_secret = self.settings.zerodha.api_secret
            
            logger.info("Generating session from request token...")
            
            data = self.kite.generate_session(
                request_token,
                api_secret=api_secret,
            )
            
            self.access_token = data.get("access_token")
            self.kite.set_access_token(self.access_token)
            
            logger.info("Session generated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Session generation failed: {e}")
            return False

    def _clear_tokens(self) -> None:
        """Clear stale access_token and request_token from .env."""
        try:
            env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
            with open(env_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                if line.startswith("ZERODHA__ACCESS_TOKEN="):
                    new_lines.append("ZERODHA__ACCESS_TOKEN=\n")
                elif line.startswith("ZERODHA__REQUEST_TOKEN="):
                    new_lines.append("ZERODHA__REQUEST_TOKEN=\n")
                else:
                    new_lines.append(line)

            with open(env_path, "w") as f:
                f.writelines(new_lines)
            logger.info("Stale tokens cleared from .env")
        except Exception as e:
            logger.warning(f"Could not clear tokens: {e}")

    def _save_access_token(self) -> None:
        if not self.access_token:
            return
        try:
            env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
            lines = []
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                if line.startswith("ZERODHA__ACCESS_TOKEN="):
                    new_lines.append(f"ZERODHA__ACCESS_TOKEN={self.access_token}\n")
                elif line.startswith("ZERODHA__REQUEST_TOKEN="):
                    new_lines.append("ZERODHA__REQUEST_TOKEN=\n")
                else:
                    new_lines.append(line)
            
            with open(env_path, "w") as f:
                f.writelines(new_lines)
            logger.info("Access token saved to .env")
        except Exception as e:
            logger.warning(f"Could not save access token: {e}")

    def _login_via_browser(self) -> bool:
        """Open browser for manual login and capture request_token."""
        try:
            from playwright.sync_api import sync_playwright
            import time
            from urllib.parse import urlparse, parse_qs
            
            login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={self.api_key}"
            
            logger.info("Opening browser for Zerodha login...")
            logger.info(f"URL: {login_url}")
            logger.info("Please login manually in the browser...")
            
            request_token = None
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                
                page.goto(login_url)
                
                max_wait = 300
                waited = 0
                while waited < max_wait:
                    time.sleep(2)
                    waited += 2
                    try:
                        url = page.url
                        if "request_token=" in url:
                            parsed = urlparse(url)
                            params = parse_qs(parsed.query)
                            request_token = params.get("request_token", [None])[0]
                            if request_token:
                                logger.info(f"Got request_token: {request_token[:10]}...")
                                break
                        
                        if "login_failed" in url:
                            logger.error("Login failed in browser")
                            break
                    except Exception:
                        pass
                
                browser.close()
            
            if not request_token:
                logger.error("Failed to get request_token - user may have cancelled")
                return False
            
            self.settings.zerodha.request_token = request_token
            
            data = self.kite.generate_session(
                request_token,
                api_secret=self.api_secret,
            )
            
            self.access_token = data.get("access_token")
            self.kite.set_access_token(self.access_token)
            
            logger.info("Successfully generated access_token via browser login")
            self._save_access_token()
            return True
            
        except Exception as e:
            logger.error(f"Browser login failed: {e}")
            return False

    def is_connected(self) -> bool:
        return self._connected

    def get_ltp(self, trading_symbol: str) -> Optional[float]:
        try:
            self._init_kite()
            instrument_token = self._get_instrument_token(trading_symbol)
            if not instrument_token:
                return None
            
            ltp = self.kite.ltp(f"NSE:{trading_symbol}")
            return float(ltp.get(f"NSE:{trading_symbol}", {}).get("last_price", 0))
        except TokenException as e:
            logger.error(f"Zerodha: Authentication error getting LTP for {trading_symbol} - {e}")
            raise AuthenticationError(f"Auth error: {e}")
        except NetworkException as e:
            logger.error(f"Zerodha: Network error getting LTP for {trading_symbol} - {e}")
            return None
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.error(f"Zerodha: Rate limit getting LTP for {trading_symbol}")
                raise RateLimitError("Rate limit exceeded")
            else:
                logger.error(f"Zerodha: Error getting LTP for {trading_symbol} - {e}")
            return None

    def get_historical_data(
        self,
        trading_symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = "15minute",
    ) -> List[Dict]:
        try:
            self._init_kite()
            zerodha_symbol = self._map_chartink_to_zerodha(trading_symbol)
            instrument_token = self._get_instrument_token(zerodha_symbol)
            if not instrument_token:
                return []
            
            candles = self.kite.historical_data(
                instrument_token=int(instrument_token),
                from_date=from_date.strftime("%Y-%m-%d %H:%M:%S"),
                to_date=to_date.strftime("%Y-%m-%d %H:%M:%S"),
                interval=interval,
            )
            
            return [
                {
                    "date": c["date"],
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c["volume"],
                }
                for c in candles
            ]
        except TokenException as e:
            logger.error(f"Zerodha: Authentication error getting historical data for {trading_symbol} - {e}")
            raise AuthenticationError(f"Auth error: {e}")
        except NetworkException as e:
            logger.error(f"Zerodha: Network error getting historical data for {trading_symbol} - {e}")
            raise DataFetchError(f"Network error: {e}")
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.error(f"Zerodha: Rate limit getting historical data for {trading_symbol}")
                raise RateLimitError("Rate limit exceeded")
            else:
                logger.error(f"Zerodha: Error getting historical data for {trading_symbol} - {e}")
            return []

    def get_nifty_data(
        self,
        from_date: datetime,
        to_date: datetime,
        interval: str = "60minute",
    ) -> List[Dict]:
        """Get NIFTY 50 historical data for relative strength calculation"""
        try:
            self._init_kite()
            instrument_token = self._get_instrument_token("NIFTY 50")
            if not instrument_token:
                instrument_token = self._get_instrument_token("NIFTY")
            if not instrument_token:
                logger.warning("NIFTY instrument token not found")
                return []

            candles = self.kite.historical_data(
                instrument_token=int(instrument_token),
                from_date=from_date.strftime("%Y-%m-%d %H:%M:%S"),
                to_date=to_date.strftime("%Y-%m-%d %H:%M:%S"),
                interval=interval,
            )

            return [
                {
                    "date": c["date"],
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c["volume"],
                }
                for c in candles
            ]
        except Exception as e:
            logger.error(f"Zerodha: Error getting NIFTY data - {e}")
            return []

    def get_weekly_data(
        self,
        trading_symbol: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[Dict]:
        """Get weekly data for multi-timeframe analysis"""
        return self.get_historical_data(trading_symbol, from_date, to_date, "weekly")

    def get_positions(self) -> List[Dict]:
        try:
            self._init_kite()
            positions = self.kite.positions()
            return positions.get("net", [])
        except Exception as e:
            logger.error(f"Zerodha: Error getting positions - {e}")
            return []

    def get_holdings(self) -> List[Dict]:
        try:
            self._init_kite()
            holdings = self.kite.holdings()
            return holdings
        except Exception as e:
            logger.error(f"Zerodha: Error getting holdings - {e}")
            return []

    def get_margins(self) -> Optional[Dict]:
        try:
            self._init_kite()
            margins = self.kite.margins()
            return margins.get("equity", {})
        except Exception as e:
            logger.error(f"Zerodha: Error getting margins - {e}")
            return None

    def place_order(
        self,
        trading_symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.LIMIT,
        price: float = 0,
        product_type: ProductType = ProductType.CNC,
        use_market_protection: bool = False,
        market_protection_pct: float = 0.5,
    ) -> Optional[OrderResponse]:
        try:
            self._init_kite()
            
            exchange = "NSE"
            
            kite_product = product_type.value
            
            if order_type == OrderType.MARKET:
                kite_order_type = "MARKET"
                kite_trigger_price = 0
            elif order_type in [OrderType.SL, OrderType.SL_M]:
                kite_order_type = order_type.value
                kite_trigger_price = price
                price = 0
            elif order_type == OrderType.LIMIT:
                kite_order_type = "LIMIT"
                kite_trigger_price = 0
            else:
                kite_order_type = order_type.value
                kite_trigger_price = 0
            
            market_protection_val = 0
            if use_market_protection and kite_order_type in ["MARKET", "SL-M"]:
                market_protection_val = int(market_protection_pct)
            
            order_id = self.kite.place_order(
                variety="regular",
                exchange=exchange,
                tradingsymbol=trading_symbol,
                transaction_type=side.value,
                quantity=quantity,
                order_type=kite_order_type,
                product=kite_product,
                price=price if price else 0,
                trigger_price=kite_trigger_price,
                market_protection=market_protection_val,
            )

            logger.info(f"Zerodha: Order placed - {order_id} | {trading_symbol} | {side.value} | Qty: {quantity} @ Rs.{price} | Type: {kite_order_type}")
            return OrderResponse(order_id=str(order_id), status="SUCCESS")
            
        except TokenException as e:
            error_msg = str(e)
            if "IP" in error_msg or "403" in error_msg:
                logger.critical(f"Zerodha: IP restriction detected - {e}")
                raise IPRestrictionError(f"IP not allowed to place orders: {e}", ip_address=self.settings.zerodha.api_key)
            else:
                logger.error(f"Zerodha: Authentication error - {e}")
                raise AuthenticationError(f"Authentication failed: {e}")
        except OrderException as e:
            error_msg = str(e)
            if "insufficient" in error_msg.lower() or "funds" in error_msg.lower():
                logger.error(f"Zerodha: Insufficient funds - {e}")
                raise InsufficientFundsError(f"Insufficient funds: {e}")
            else:
                logger.error(f"Zerodha: Order rejected - {e}")
                raise OrderError(f"Order rejected: {e}", trading_symbol, rejection_reason=str(e))
        except NetworkException as e:
            logger.error(f"Zerodha: Network error placing order - {e}")
            raise ZerodhaError(f"Network error: {e}", error_type="NETWORK_ERROR")
        except Exception as e:
            error_msg = str(e)
            if "IP" in error_msg or "not allowed" in error_msg:
                logger.critical(f"Zerodha: IP restriction detected - {e}")
                raise IPRestrictionError(f"IP not allowed: {e}")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                logger.error(f"Zerodha: Rate limit exceeded - {e}")
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
                logger.error(f"Zerodha: Order error - {e}")
                return None

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._init_kite()
            self.kite.cancel_order(order_id)
            logger.info(f"Zerodha: Order cancelled - {order_id}")
            return True
        except Exception as e:
            logger.error(f"Zerodha: Error cancelling order - {e}")
            return False

    def get_order_history(self) -> List[Dict]:
        try:
            self._init_kite()
            orders = self.kite.orders()
            return orders
        except Exception as e:
            logger.error(f"Zerodha: Error getting order history - {e}")
            return []

    def _get_instrument_token(self, trading_symbol: str) -> Optional[int]:
        if trading_symbol in self._instruments_cache:
            return self._instruments_cache[trading_symbol]

        try:
            self._init_kite()
            instruments = self.kite.instruments("NSE")

            for inst in instruments:
                if inst.get("tradingsymbol") == trading_symbol:
                    token = inst.get("instrument_token")
                    self._instruments_cache[trading_symbol] = token
                    logger.debug(f"Token for {trading_symbol}: {token}")
                    return token

            logger.warning(f"No instrument found for {trading_symbol}")
            return None
        except Exception as e:
            logger.error(f"Zerodha: Error getting instrument token - {e}")
            return None

    def sync_holdings_to_db(self, db) -> dict:
        """
        Sync holdings from Zerodha to database.
        Captures existing holdings (bought manually or by algo).
        
        Logic:
        - Check quantity + t1_quantity + t2_quantity (T1, T2, TQ)
        - If total < 1: don't count as holding, mark as EXITED if exists
        - If any >= 1: count as holding, mark as ENTERED
        """
        from models.stock import Stock, StockStatus

        try:
            holdings = self.get_holdings()
            logger.info(f"Syncing {len(holdings)} holdings from Zerodha")

            from models.stock import Stock, StockStatus

            synced = 0
            marked_exited = 0
            skipped = 0
            
            h_by_symbol = {h.get("tradingsymbol"): h for h in holdings if h.get("tradingsymbol")}
            
            all_symbols = db.query(Stock.symbol).all()
            all_symbols = [s[0] for s in all_symbols]
            
            for symbol in all_symbols:
                h = h_by_symbol.get(symbol)
                if not h:
                    existing = db.query(Stock).filter(Stock.symbol == symbol).first()
                    if existing and existing.status == StockStatus.ENTERED:
                        existing.status = StockStatus.EXITED
                        existing.broker_status = "NOT_HOLDING"
                        marked_exited += 1
                        logger.info(f"Marked as EXITED: {symbol} (no holdings from broker)")
            
            for h in holdings:
                qty = h.get("quantity", 0)
                t1_qty = h.get("t1_quantity", 0)
                t2_qty = h.get("t2_quantity", 0)
                total_qty = qty + t1_qty + t2_qty
                
                if total_qty < 1:
                    skipped += 1
                    logger.debug(f"Skipping {h.get('tradingsymbol')}: total_qty={total_qty} (qty={qty}, t1={t1_qty}, t2={t2_qty})")
                    continue
                
                exchange = h.get("exchange", "")
                if exchange not in ["NSE", "BSE"]:
                    skipped += 1
                    logger.debug(f"Skipping {h.get('tradingsymbol')}: exchange={exchange} (not NSE/BSE)")
                    continue

                exchange = h.get("exchange", "NSE")
                symbol = h.get("tradingsymbol", "")
                if not symbol:
                    skipped += 1
                    continue
                    
                token = str(h.get("instrument_token", ""))
                avg_price = h.get("average_price", 0.0)
                current_price = h.get("current_price", 0.0)
                pnl = h.get("pnl", 0.0)
                pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0

                existing = db.query(Stock).filter(Stock.symbol == symbol).first()

                if existing:
                    existing.status = StockStatus.ENTERED
                    existing.exchange = exchange
                    existing.entry_quantity = total_qty
                    existing.average_price = avg_price
                    existing.current_price = current_price
                    existing.pnl = pnl
                    existing.pnl_percentage = pnl_pct
                    existing.instrument_token = token
                    existing.broker_status = "HOLDING"
                    if not existing.target_price:
                        existing.target_price = avg_price * (1 + self.target_pct / 100)
                    if not existing.stop_loss:
                        existing.stop_loss = avg_price * (1 - self.sl_pct / 100)
                    logger.debug(f"Updated holding: {symbol} qty={total_qty}")
                else:
                    target = avg_price * (1 + self.target_pct / 100)
                    stop_loss = avg_price * (1 - self.sl_pct / 100)
                    stock = Stock(
                        symbol=symbol,
                        instrument_token=token,
                        exchange=exchange,
                        status=StockStatus.ENTERED,
                        entry_quantity=total_qty,
                        average_price=avg_price,
                        current_price=current_price,
                        entry_price=avg_price,
                        target_price=target,
                        stop_loss=stop_loss,
                        pnl=pnl,
                        pnl_percentage=pnl_pct,
                        broker_status="HOLDING",
                    )
                    db.add(stock)
                    logger.info(f"Added holding: {symbol} qty={total_qty} on {exchange}")

                synced += 1

            db.commit()
            logger.info(f"Holdings sync complete: {synced} synced, {marked_exited} marked EXITED, {skipped} skipped (total_qty < 1)")
            return {"status": "success", "synced": synced, "marked_exited": marked_exited}

        except Exception as e:
            logger.error(f"Holdings sync failed: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}

    def sync_positions_to_db(self, db) -> dict:
        """
        Sync open positions from Zerodha to database.
        Tracks all open intraday/MIS positions.
        
        Logic:
        - If qty < 0: mark as EXITED (sold/short closed)
        - If qty > 0: mark as ENTERED
        - Also marks existing ENTERED positions as EXITED if no longer in positions
          BUT only if not in holdings with qty >= 1
        """
        from models.stock import Stock, StockStatus

        try:
            positions = self.get_positions()
            holdings = self.get_holdings()
            
            holding_symbols = set()
            for h in holdings:
                sym = h.get("tradingsymbol")
                if sym:
                    qty = h.get("quantity", 0)
                    t1 = h.get("t1_quantity", 0)
                    t2 = h.get("t2_quantity", 0)
                    if qty + t1 + t2 >= 1:
                        holding_symbols.add(sym)
            
            logger.info(f"Syncing {len(positions)} positions from Zerodha")
            logger.debug(f"Holdings symbols (skip if EXITED): {holding_symbols}")

            synced = 0
            marked_exited = 0
            
            pos_by_symbol = {p.get("tradingsymbol"): p for p in positions if p.get("tradingsymbol")}
            
            all_entered = db.query(Stock).filter(Stock.status == StockStatus.ENTERED).all()
            for stock in all_entered:
                if stock.symbol not in pos_by_symbol and stock.symbol not in holding_symbols:
                    stock.status = StockStatus.EXITED
                    stock.broker_status = "POSITION_CLOSED"
                    marked_exited += 1
                    logger.info(f"Marked as EXITED: {stock.symbol} (not in positions)")
            
            for p in positions:
                qty = p.get("quantity", 0)
                if qty == 0:
                    continue

                symbol = p.get("tradingsymbol", "")
                exchange = p.get("exchange", "NSE")
                token = str(p.get("instrument_token", ""))
                avg_price = p.get("average_price", 0.0)
                current_price = p.get("current_price", 0.0)
                pnl = p.get("pnl", 0.0)

                existing = db.query(Stock).filter(Stock.symbol == symbol).first()

                if existing:
                    existing.exchange = exchange
                    existing.entry_quantity = abs(qty)
                    existing.average_price = avg_price
                    existing.current_price = current_price
                    existing.pnl = pnl
                    existing.instrument_token = token
                    existing.status = StockStatus.ENTERED if qty > 0 else StockStatus.EXITED
                    existing.broker_status = "OPEN"
                    logger.debug(f"Updated position: {symbol} qty={qty}")
                else:
                    target = avg_price * (1 + self.target_pct / 100)
                    stop_loss = avg_price * (1 - self.sl_pct / 100)
                    stock = Stock(
                        symbol=symbol,
                        instrument_token=token,
                        exchange=exchange,
                        status=StockStatus.ENTERED if qty > 0 else StockStatus.EXITED,
                        entry_quantity=abs(qty),
                        average_price=avg_price,
                        current_price=current_price,
                        entry_price=avg_price,
                        target_price=target,
                        stop_loss=stop_loss,
                        pnl=pnl,
                        broker_status="OPEN",
                    )
                    db.add(stock)
                    logger.info(f"Added position: {symbol} qty={qty} on {exchange}")

                synced += 1

            db.commit()
            logger.info(f"Positions sync complete: {synced} synced, {marked_exited} marked EXITED")
            return {"status": "success", "synced": synced, "marked_exited": marked_exited}

        except Exception as e:
            logger.error(f"Positions sync failed: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}

    def sync_order_status_to_db(self, db) -> dict:
        """
        Sync order status from Zerodha to database.
        Updates broker_status for orders: OPEN, TRIGGER_PENDING, REJECTED, COMPLETE
        
        Note: Stock status (ENTERED/EXITED) is determined by holdings/positions sync ONLY.
        This updates broker_status and order tracking, not stock status.
        """
        from models.stock import Stock, StockStatus

        try:
            orders = self.get_order_history()
            logger.info(f"Syncing order status for {len(orders)} orders")

            updated = 0
            for order in orders:
                order_id = str(order.get("order_id", ""))
                symbol = order.get("tradingsymbol", "")
                status = order.get("status", "")
                filled_qty = order.get("filled_quantity", 0)
                pending_qty = order.get("pending_quantity", 0)

                if not order_id or not symbol:
                    continue

                stock = db.query(Stock).filter(Stock.broker_order_id == order_id).first()
                
                # Don't match exited records by symbol (loose fallback)
                if not stock:
                    stock = db.query(Stock).filter(
                        Stock.symbol == symbol,
                        Stock.status != StockStatus.EXITED
                    ).first()
                
                if stock:
                    # Don't overwrite broker_status for already-exited positions
                    if stock.status == StockStatus.EXITED:
                        logger.debug(f"Skipping order sync for exited position: {symbol} (exit_order_id: {stock.exit_order_id})")
                        continue
                    
                    stock.broker_status = status
                    stock.broker_order_id = order_id
                    
                    if status == "COMPLETE":
                        stock.broker_status = "COMPLETE"
                        stock.entry_quantity = filled_qty if filled_qty > 0 else stock.entry_quantity
                        stock.entry_date = datetime.utcnow()
                        
                        holdings = self.get_holdings()
                        positions = self.get_positions()
                        
                        h_found = False
                        for h in holdings:
                            if h.get("tradingsymbol") == symbol:
                                qty = h.get("quantity", 0)
                                t1 = h.get("t1_quantity", 0)
                                t2 = h.get("t2_quantity", 0)
                                if qty + t1 + t2 >= 1:
                                    h_found = True
                                    stock.status = StockStatus.ENTERED
                                    break
                        
                        if not h_found:
                            for p in positions:
                                if p.get("tradingsymbol") == symbol:
                                    p_qty = p.get("quantity", 0)
                                    if p_qty < 0:
                                        stock.status = StockStatus.EXITED
                                        stock.exit_date = datetime.utcnow()
                                    elif p_qty > 0:
                                        stock.status = StockStatus.ENTERED
                                    break
                    elif status == "REJECTED":
                        stock.broker_status = "REJECTED"
                        reason = order.get("rejection_reason") or order.get("order_comment", "ORDER_REJECTED")
                        stock.exit_reason = reason
                        stock.exit_date = datetime.utcnow()
                    elif status == "TRIGGER_PENDING":
                        pass
                    elif status == "OPEN" and pending_qty > 0:
                        pass

                    updated += 1
                    logger.info(f"Order {symbol}: broker_status={status}")

                    updated += 1
                    logger.info(f"Order {symbol}: broker_status={status}")

            db.commit()
            logger.info(f"Order status sync complete: {updated} updated")
            return {"status": "success", "updated": updated}

        except Exception as e:
            logger.error(f"Order status sync failed: {e}")
            return {"status": "error", "message": str(e)}

    def sync_all_to_db(self, db) -> dict:
        """
        Sync all broker data to database: holdings, positions, order status.
        
        Sync order:
        1. Holdings: qty + t1 + t2 >= 1 = ENTERED
        2. Positions: qty > 0 = ENTERED, qty < 0 = EXITED  
        3. Orders: Only updates broker_status (not stock status)
        """
        holdings_result = self.sync_holdings_to_db(db)
        positions_result = self.sync_positions_to_db(db)
        orders_result = self.sync_order_status_to_db(db)

        return {
            "status": "success",
            "holdings": holdings_result,
            "positions": positions_result,
            "orders": orders_result,
        }


kite_broker = KiteBroker()


def get_broker() -> KiteBroker:
    return kite_broker
