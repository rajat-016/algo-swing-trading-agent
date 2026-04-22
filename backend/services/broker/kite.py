import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
from kiteconnect import KiteConnect
from core.config import get_settings
from core.enums import OrderSide, OrderType, ProductType
from core.logging import logger


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
            if not self.access_token:
                logger.warning("Zerodha: No access token configured")
                return False

            self._init_kite()
            profile = self.kite.profile()
            if profile:
                self._connected = True
                logger.info(f"Zerodha: Connected (user: {profile.get('user_name', 'unknown')})")
                return True
            else:
                logger.error("Zerodha: Connection failed")
                return False
        except Exception as e:
            logger.error(f"Zerodha: Connection error - {e}")
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
        except Exception as e:
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
        except Exception as e:
            logger.error(f"Zerodha: Error getting historical data for {trading_symbol} - {e}")
            return []

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
            elif use_market_protection or side == OrderSide.SELL:
                kite_order_type = "SL-M"
            else:
                kite_order_type = order_type.value

            order_id = self.kite.place_order(
                variety="regular",
                exchange=exchange,
                tradingsymbol=trading_symbol,
                transaction_type=side.value,
                quantity=quantity,
                order_type=kite_order_type,
                product=kite_product,
                price=price if price else 0,
            )

            logger.info(f"Zerodha: Order placed - {order_id} | {trading_symbol} | {side.value} | Qty: {quantity} @ ₹{price}")
            return OrderResponse(order_id=str(order_id), status="SUCCESS")
            
        except Exception as e:
            logger.error(f"Zerodha: Order error - {e}")
            return None
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


kite_broker = KiteBroker()


def get_broker() -> KiteBroker:
    return kite_broker
