import json
import threading
import urllib.request

from bot.dashboard import BufferHandler, start_dashboard
from tests.test_bot import make


def req(port, path, method="GET"):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method,
                               data=b"" if method == "POST" else None)
    with urllib.request.urlopen(r, timeout=5) as resp:
        return resp.status, resp.read().decode()


def test_status_and_stop(tmp_path):
    t, c = make(tmp_path, list(range(100, 60, -1)), dry=True)
    t.cfg.poll_seconds = 0.05
    buf = BufferHandler()
    buf.lines.append("hello log")
    stopped = threading.Event()
    srv = start_dashboard(t, buf, port=0, on_stop=stopped.set)
    port = srv.server_address[1]
    th = threading.Thread(target=t.run, daemon=True)
    th.start()
    try:
        for _ in range(100):
            if t.last["updated"]:
                break
            threading.Event().wait(0.02)
        code, body = req(port, "/api/status")
        d = json.loads(body)
        assert code == 200
        assert d["status"] == "dry_run" and d["dry_run"] is True and d["testnet"] is True
        assert d["symbol"] == "BTCUSDT" and d["price"] == 61.0
        assert set(d["rsi"]) == {"6", "12", "14", "24"}
        assert d["rsi"]["14"] == 0.0
        assert d["position"] is not None and d["trades"][0]["side"] == "BUY"
        assert d["trades"][0]["dry_run"] is True
        assert "hello log" in d["logs"] and d["updated"]
        code, html = req(port, "/")
        assert code == 200 and "Остановить бота" in html

        code, body = req(port, "/api/stop", "POST")
        assert code == 200 and json.loads(body)["ok"]
        th.join(timeout=3)
        assert not th.is_alive() and stopped.wait(2)
        assert json.loads(req(port, "/api/status")[1])["status"] == "stopped"
        c.order_market_buy.assert_not_called()
    finally:
        t.stop()
        srv.shutdown()
        srv.server_close()


def test_404(tmp_path):
    t, _ = make(tmp_path, [1, 2, 3])
    srv = start_dashboard(t, BufferHandler(), port=0)
    try:
        import urllib.error
        try:
            req(srv.server_address[1], "/nope")
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown()
        srv.server_close()
