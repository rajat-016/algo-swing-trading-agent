import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
from core.config import get_settings
from core.enums import OrderSide, OrderType, ProductType
from core.logging import logger


class OrderResponse:
    def __init__(self, order_id: str, status: str, message: str = ""):
        self.order_id = order_id
        self.status = status
        self.message = message


class ZerodhaBroker:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.zerodha.api_key
        self.api_secret = self.settings.zerodha.api_secret
        self.access_token = self.settings.zerodha.access_token
        self.kite_url = self.settings.zerodha.kite_url
        self.session = requests.Session()
        self._connected = False
        self._instruments_cache: Dict[str, Any] = {}
        self._name_to_symbol_cache: Dict[str, str] = {}
        self._symbol_to_token_cache: Dict[str, str] = {}

    def _map_chartink_to_zerodha(self, chartink_symbol: str) -> str:
        if not self._name_to_symbol_cache:
            self._load_name_mapping()

        if chartink_symbol in self._instruments_cache:
            return chartink_symbol

        if chartink_symbol.startswith("NSE:"):
            name = chartink_symbol[4:].upper().strip()
        else:
            name = chartink_symbol.upper().strip()

        if name in self._name_to_symbol_cache:
            zerodha_symbol = self._name_to_symbol_cache[name]
            self._instruments_cache[chartink_symbol] = zerodha_symbol
            return zerodha_symbol

        name_words = set(name.split())
        best_match = None
        best_score = 0

        for key, value in self._name_to_symbol_cache.items():
            words = set(key.split())
            common = name_words & words
            if len(common) > best_score:
                best_score = len(common)
                best_match = (key, value)

        if best_match and best_score >= 2:
            self._instruments_cache[chartink_symbol] = best_match[1]
            return best_match[1]

        self._instruments_cache[chartink_symbol] = name.replace(" ", "")
        return name.replace(" ", "")

    def _load_name_mapping(self):
        try:
            url = f"{self.kite_url}/instruments"
            response = self.session.get(url)
            if response.status_code == 200:
                for line in response.text.split("\n")[1:]:
                    parts = line.split(",")
                    if len(parts) >= 5:
                        instrument_token = parts[0]
                        symbol = parts[2].strip('"')
                        name = parts[3].strip('"')
                        exchange = parts[-1]
                        instrument_type = parts[-3] if len(parts) >= 8 else ""
                        if exchange == "NSE" and instrument_type == "EQ":
                            self._name_to_symbol_cache[name.upper()] = symbol
                            self._symbol_to_token_cache[symbol] = instrument_token
        except Exception as e:
            logger.error(f"Error loading name mapping: {e}")

    def connect(self) -> bool:
        try:
            if not self.access_token:
                logger.warning("Zerodha: No access token configured")
                return False

            self.session.headers.update({
                "Authorization": f"token {self.api_key}:{self.access_token}",
                "X-Kite-Version": "3",
            })

            profile = self.session.get(f"{self.kite_url}/user/profile")
            if profile.status_code == 200:
                self._connected = True
                logger.info("Zerodha: Connected successfully")
                return True
            else:
                logger.error(f"Zerodha: Connection failed - {profile.status_code}")
                return False
        except Exception as e:
            logger.error(f"Zerodha: Connection error - {e}")
            return False

    def is_connected(self) -> bool:
        return self._connected

    def get_ltp(self, trading_symbol: str) -> Optional[float]:
        try:
            instrument = self._get_instrument_token(trading_symbol)
            if not instrument:
                return None

            url = f"{self.kite_url}/quote"
            params = {"i": [instrument]}
            response = self.session.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                instrument_data = data.get("data", {}).get(instrument, {})
                return float(instrument_data.get("last_price", 0))
            return None
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
            zerodha_symbol = self._map_chartink_to_zerodha(trading_symbol)
            instrument = self._symbol_to_token_cache.get(zerodha_symbol)
            if not instrument:
                return []

            url = f"{self.kite_url}/instruments/historical/{instrument}/{interval}"
            params = {
                "from": from_date.strftime("%Y-%m-%d %H:%M:%S"),
                "to": to_date.strftime("%Y-%m-%d %H:%M:%S"),
            }

            response = self.session.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                candles = data.get("data", {}).get("candles", [])
                return [
                    {
                        "date": c[0],
                        "open": c[1],
                        "high": c[2],
                        "low": c[3],
                        "close": c[4],
                        "volume": c[5],
                    }
                    for c in candles
                ]
            return []
        except Exception as e:
            logger.error(f"Zerodha: Error getting historical data for {trading_symbol} - {e}")
            return []

    def get_positions(self) -> List[Dict]:
        try:
            url = f"{self.kite_url}/positions"
            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", []).get("net", [])
            return []
        except Exception as e:
            logger.error(f"Zerodha: Error getting positions - {e}")
            return []

    def get_holdings(self) -> List[Dict]:
        try:
            url = f"{self.kite_url}/holdings"
            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Zerodha: Error getting holdings - {e}")
            return []

    def get_margins(self) -> Optional[Dict]:
        try:
            url = f"{self.kite_url}/user/margins"
            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("equity", {})
            return None
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
    ) -> Optional[OrderResponse]:
        try:
            instrument = self._get_instrument_token(trading_symbol)
            if not instrument:
                return None

            order_data = {
                "exchange": "NSE",
                "tradingsymbol": trading_symbol,
                "transaction_type": side.value,
                "quantity": quantity,
                "order_type": order_type.value,
                "product": product_type.value,
            }

            if order_type in [OrderType.LIMIT, OrderType.SL]:
                order_data["price"] = price

            url = f"{self.kite_url}/orders"
            response = self.session.post(url, json=order_data)

            if response.status_code == 200:
                data = response.json()
                order_id = data.get("data", {}).get("order_id", "")
                logger.info(f"Zerodha: Order placed - {order_id} | {trading_symbol} | {side.value} | Qty: {quantity}")
                return OrderResponse(order_id=order_id, status="SUCCESS")
            else:
                logger.error(f"Zerodha: Order failed - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Zerodha: Error placing order - {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        try:
            url = f"{self.kite_url}/orders/{order_id}"
            response = self.session.delete(url)

            if response.status_code == 200:
                logger.info(f"Zerodha: Order cancelled - {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Zerodha: Error cancelling order - {e}")
            return False

    def get_order_history(self) -> List[Dict]:
        try:
            url = f"{self.kite_url}/orders"
            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Zerodha: Error getting order history - {e}")
            return []

    def _get_instrument_token(self, trading_symbol: str) -> Optional[str]:
        if trading_symbol in self._instruments_cache:
            return self._instruments_cache[trading_symbol]

        try:
            url = f"{self.kite_url}/instruments"
            response = self.session.get(url)

            if response.status_code == 200:
                for line in response.text.strip().split("\n")[1:]:
                    parts = line.split(",")
                    if len(parts) >= 5:
                        instrument_token = parts[0]
                        symbol = parts[2].strip('"')
                        exchange = parts[-1]
                        instrument_type = parts[-3] if len(parts) >= 8 else ""
                        if symbol == trading_symbol and exchange == "NSE" and instrument_type == "EQ":
                            self._instruments_cache[trading_symbol] = instrument_token
                            return instrument_token
            return None
        except Exception as e:
            logger.error(f"Zerodha: Error getting instrument token - {e}")
            return None


zerodha_broker = ZerodhaBroker()


def get_broker() -> ZerodhaBroker:
    return zerodha_broker
