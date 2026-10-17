import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

from .strategy import BUY, SELL, calculate_rsi, get_signal

log = logging.getLogger("rsi_bot")


def retry(fn, attempts=3, delay=2.0, backoff=2.0, sleep=time.sleep):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # network / API errors
            last = exc
            log.warning("Attempt %d/%d failed: %s", i + 1, attempts, exc)
            if i < attempts - 1:
                sleep(delay)
                delay *= backoff
    raise last


class Trader:
    """Single-position RSI trader. `client` is a python-binance Client (or mock)."""

    def __init__(self, client, config, sleep=time.sleep):
        self.client = client
        self.cfg = config
        self.sleep = sleep
        self.state = self._load_state()
        self.state.setdefault("trades", [])
        self.stop_event = threading.Event()
        self.running = False
        self.lock = threading.Lock()
        self.last = {"price": None, "rsi": {}, "signal": None, "updated": None, "error": None}

    # ---- state ----
    def _load_state(self):
        if os.path.exists(self.cfg.state_file):
            try:
                with open(self.cfg.state_file) as f:
                    return json.load(f)
            except (OSError, ValueError) as exc:
                log.error("Cannot read state file: %s", exc)
        return {"in_position": False, "qty": 0.0, "entry_price": 0.0, "trades": []}

    def _record(self, side, qty, price):
        t = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "side": side,
             "qty": qty, "price": price, "dry_run": self.cfg.dry_run}
        self.state["trades"] = (self.state.get("trades", []) + [t])[-50:]

    def _save_state(self):
        with open(self.cfg.state_file, "w") as f:
            json.dump(self.state, f)

    # ---- exchange helpers ----
    def _call(self, fn, *a, **kw):
        return retry(lambda: fn(*a, **kw), sleep=self.sleep)

    def fetch_closes(self):
        limit = max(self.cfg.rsi_period * 10, 100)
        kl = self._call(self.client.get_klines, symbol=self.cfg.symbol,
                        interval=self.cfg.interval, limit=limit)
        return [float(k[4]) for k in kl[:-1]]  # drop the still-open candle

    def _step_size(self):
        info = self._call(self.client.get_symbol_info, self.cfg.symbol) or {}
        for f in info.get("filters", []):
            if f.get("filterType") == "LOT_SIZE":
                return Decimal(f["stepSize"])
        return Decimal("0.000001")

    def _round_qty(self, qty):
        step = self._step_size()
        return float((Decimal(str(qty)) / step).to_integral_value(ROUND_DOWN) * step)

    # ---- actions ----
    def buy(self, price):
        if self.cfg.dry_run:
            qty = self.cfg.quote_amount / price
            log.info("[DRY-RUN] BUY %.8f %s @ %.2f", qty, self.cfg.symbol, price)
        else:
            order = self._call(self.client.order_market_buy, symbol=self.cfg.symbol,
                               quoteOrderQty=f"{self.cfg.quote_amount:.2f}")
            qty = float(order.get("executedQty", 0))
            quote = float(order.get("cummulativeQuoteQty", 0))
            price = quote / qty if qty else price
            log.info("BUY filled: %s qty=%s avg=%.2f", order.get("orderId"), qty, price)
        self.state.update({"in_position": True, "qty": qty, "entry_price": price})
        self._record(BUY, qty, price)
        self._save_state()

    def sell(self, price):
        qty = self.state["qty"]
        if self.cfg.dry_run:
            log.info("[DRY-RUN] SELL %.8f %s @ %.2f", qty, self.cfg.symbol, price)
        else:
            q = self._round_qty(qty)
            order = self._call(self.client.order_market_sell,
                               symbol=self.cfg.symbol, quantity=q)
            log.info("SELL filled: %s qty=%s", order.get("orderId"), q)
        pnl = (price - self.state["entry_price"]) * qty
        log.info("Position closed, approx PnL: %.4f", pnl)
        self._record(SELL, qty, price)
        self.state.update({"in_position": False, "qty": 0.0, "entry_price": 0.0})
        self._save_state()

    def step(self):
        closes = self.fetch_closes()
        rsi = calculate_rsi(closes, self.cfg.rsi_period)
        signal = get_signal(rsi, self.state["in_position"],
                            self.cfg.rsi_buy, self.cfg.rsi_sell)
        price = closes[-1] if closes else 0.0
        rsis = {p: calculate_rsi(closes, p) for p in sorted({6, 12, 14, 24, self.cfg.rsi_period})}
        with self.lock:
            self.last.update(price=price, rsi=rsis, signal=signal, error=None,
                             updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        log.info("%s price=%.2f RSI=%s signal=%s in_position=%s", self.cfg.symbol,
                 price, f"{rsi:.2f}" if rsi is not None else "n/a",
                 signal, self.state["in_position"])
        if signal == BUY:
            self.buy(price)
        elif signal == SELL:
            self.sell(price)
        return signal

    def stop(self):
        log.info("Stop requested")
        self.stop_event.set()

    def status(self, log_lines=()):
        with self.lock:
            last = dict(self.last)
        if self.running:
            mode = "dry_run" if self.cfg.dry_run else "trading"
        else:
            mode = "stopped"
        return {
            "status": mode,
            "testnet": self.cfg.use_testnet, "dry_run": self.cfg.dry_run,
            "symbol": self.cfg.symbol, "interval": self.cfg.interval,
            "strategy_period": self.cfg.rsi_period,
            "price": last["price"],
            "rsi": {str(k): (round(v, 2) if v is not None else None) for k, v in last["rsi"].items()},
            "signal": last["signal"], "error": last["error"],
            "position": ({"qty": self.state["qty"], "entry_price": self.state["entry_price"]}
                         if self.state.get("in_position") else None),
            "trades": self.state.get("trades", [])[-10:][::-1],
            "logs": list(log_lines)[-20:],
            "updated": last["updated"],
        }

    def run(self):
        log.info("Starting bot: testnet=%s dry_run=%s", self.cfg.use_testnet, self.cfg.dry_run)
        self.running = True
        try:
            while not self.stop_event.is_set():
                try:
                    self.step()
                except Exception as exc:
                    log.exception("Step failed: %s", exc)
                    with self.lock:
                        self.last["error"] = str(exc)
                self.stop_event.wait(self.cfg.poll_seconds)
        finally:
            self.running = False
            log.info("Bot stopped")
