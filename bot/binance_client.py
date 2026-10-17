"""Minimal stdlib-only Binance Spot REST client (no pycryptodome / python-binance)."""
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request

LIVE_URL = "https://api.binance.com/api"
TESTNET_URL = "https://testnet.binance.vision/api"


class BinanceAPIError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"HTTP {status} code={code}: {message}")
        self.status, self.code, self.message = status, code, message


def sign(query: str, secret: str) -> str:
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


class Client:
    def __init__(self, api_key=None, api_secret=None, testnet=True, timeout=10,
                 recv_window=5000, opener=None):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.base_url = TESTNET_URL if testnet else LIVE_URL
        self.timeout = timeout
        self.recv_window = recv_window
        self.time_offset = 0
        self._open = opener or urllib.request.urlopen

    def _build(self, method, path, params=None, signed=False):
        params = {k: v for k, v in (params or {}).items() if v is not None}
        headers = {"User-Agent": "rsi-bot/1.0"}
        if signed:
            if not (self.api_key and self.api_secret):
                raise BinanceAPIError(0, -1, "API key/secret required for signed endpoint")
            params["recvWindow"] = self.recv_window
            params["timestamp"] = int(time.time() * 1000) + self.time_offset
            query = urllib.parse.urlencode(params)
            query += "&signature=" + sign(query, self.api_secret)
        else:
            query = urllib.parse.urlencode(params)
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        url = f"{self.base_url}{path}"
        data = None
        if method == "GET" or method == "DELETE":
            if query:
                url += "?" + query
        else:
            data = query.encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return urllib.request.Request(url, data=data, headers=headers, method=method)

    def _request(self, method, path, params=None, signed=False):
        req = self._build(method, path, params, signed)
        try:
            with self._open(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                j = json.loads(body)
                raise BinanceAPIError(e.code, j.get("code"), j.get("msg")) from None
            except ValueError:
                raise BinanceAPIError(e.code, None, body[:200]) from None

    # ---- public ----
    def ping(self):
        return self._request("GET", "/v3/ping")

    def get_server_time(self):
        return self._request("GET", "/v3/time")

    def sync_time(self):
        self.time_offset = self.get_server_time()["serverTime"] - int(time.time() * 1000)
        return self.time_offset

    def get_klines(self, symbol, interval, limit=500):
        return self._request("GET", "/v3/klines",
                             {"symbol": symbol, "interval": interval, "limit": limit})

    def get_symbol_info(self, symbol):
        data = self._request("GET", "/v3/exchangeInfo", {"symbol": symbol})
        for s in data.get("symbols", []):
            if s.get("symbol") == symbol:
                return s
        return None

    # ---- signed ----
    def order_market_buy(self, symbol, quoteOrderQty):
        return self._request("POST", "/v3/order", {"symbol": symbol, "side": "BUY",
                             "type": "MARKET", "quoteOrderQty": quoteOrderQty}, signed=True)

    def order_market_sell(self, symbol, quantity):
        return self._request("POST", "/v3/order", {"symbol": symbol, "side": "SELL",
                             "type": "MARKET", "quantity": f"{quantity:.8f}".rstrip("0").rstrip(".")
                             if isinstance(quantity, float) else quantity}, signed=True)
