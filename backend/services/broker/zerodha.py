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

    def connect(self) -> bool:
        try:
            if not self.access_token:
                logger.warning("Zerodha: No access token configured")
                return False

            self.session.headers.update({
                "Authorization": f"token {self.api_key}:{self.access_token}",
                "X-Kite-Version": "3",
            })

            profile = self.session.get(f"{self.kite_url}/api/v3/profile")
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

            url = f"{self.kite_url}/api/v3/quote"
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
            instrument = self._get_instrument_token(trading_symbol)
            if not instrument:
                return []

            url = f"{self.kite_url}/api/v3/instruments/historical"
            params = {
                "instrument_token": instrument,
                "from": from_date.strftime("%Y-%m-%d %H:%M:%S"),
                "to": to_date.strftime("%Y-%m-%d %H:%M:%S"),
                "interval": interval,
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
            url = f"{self.kite_url}/api/v3/positions"
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
            url = f"{self.kite_url}/api/v3/holdings"
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
            url = f"{self.kite_url}/api/v3/margins"
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

            url = f"{self.kite_url}/api/v3/orders"
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
            url = f"{self.kite_url}/api/v3/orders/{order_id}"
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
            url = f"{self.kite_url}/api/v3/orders"
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
            url = f"{self.kite_url}/api/v3/instruments"
            response = self.session.get(url)

            if response.status_code == 200:
                lines = response.text.strip().split("\n")
                for line in lines[1:]:
                    parts = line.split(",")
                    if len(parts) >= 3:
                        symbol = parts[2].strip('"')
                        if symbol == trading_symbol:
                            instrument_token = parts[0].strip('"')
                            self._instruments_cache[trading_symbol] = instrument_token
                            return instrument_token
            return None
        except Exception as e:
            logger.error(f"Zerodha: Error getting instrument token - {e}")
            return None


zerodha_broker = ZerodhaBroker()


def get_broker() -> ZerodhaBroker:
    return zerodha_broker
