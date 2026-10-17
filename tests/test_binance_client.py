import hashlib
import hmac
import io
import json
import urllib.parse

from bot.binance_client import TESTNET_URL, LIVE_URL, Client, sign


def test_sign_binance_doc_example():
    # Example from Binance API docs (HMAC-SHA256)
    secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    q = ("symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1"
         "&recvWindow=5000&timestamp=1499827319559")
    assert sign(q, secret) == "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"


class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass


def test_signed_order_request():
    seen = {}

    def opener(req, timeout):
        seen["req"] = req
        return Resp(json.dumps({"orderId": 7}).encode())

    c = Client("KEY", "SECRET", testnet=True, opener=opener)
    assert c.order_market_buy(symbol="BTCUSDT", quoteOrderQty="20.00")["orderId"] == 7
    r = seen["req"]
    assert r.get_method() == "POST" and r.full_url == TESTNET_URL + "/v3/order"
    assert r.get_header("X-mbx-apikey") == "KEY"
    body = r.data.decode()
    query, sig = body.rsplit("&signature=", 1)
    assert sig == hmac.new(b"SECRET", query.encode(), hashlib.sha256).hexdigest()
    p = dict(urllib.parse.parse_qsl(query))
    assert p["side"] == "BUY" and p["type"] == "MARKET" and p["quoteOrderQty"] == "20.00"
    assert "timestamp" in p


def test_public_without_keys_and_live_url():
    seen = {}

    def opener(req, timeout):
        seen["req"] = req
        return Resp(b"[[0,0,0,0,\"1.5\",0]]")

    c = Client(testnet=False, opener=opener)
    assert c.get_klines(symbol="BTCUSDT", interval="15m", limit=5)[0][4] == "1.5"
    r = seen["req"]
    assert r.full_url.startswith(LIVE_URL + "/v3/klines?") and "signature" not in r.full_url
    assert r.get_header("X-mbx-apikey") is None


def test_symbol_info_filters():
    data = {"symbols": [{"symbol": "BTCUSDT", "filters": [{"filterType": "LOT_SIZE", "stepSize": "0.00001"}]}]}
    c = Client(opener=lambda req, timeout: Resp(json.dumps(data).encode()))
    assert c.get_symbol_info("BTCUSDT")["filters"][0]["stepSize"] == "0.00001"
