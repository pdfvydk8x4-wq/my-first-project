from unittest.mock import MagicMock

import pytest

from bot.config import Config
from bot.strategy import BUY, HOLD, SELL, calculate_rsi, get_signal
from bot.trader import Trader, retry


def test_rsi_insufficient_data():
    assert calculate_rsi([1, 2, 3], 14) is None


def test_rsi_all_gains_is_100():
    assert calculate_rsi(list(range(1, 30)), 14) == 100.0


def test_rsi_all_losses_is_0():
    assert calculate_rsi(list(range(30, 1, -1)), 14) == 0.0


def test_rsi_flat_is_50():
    assert calculate_rsi([10.0] * 20, 14) == 50.0


def test_rsi_known_value():
    # Classic Wilder example data (StockCharts), first RSI ~70.46
    closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
              46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    assert calculate_rsi(closes, 14) == pytest.approx(70.46, abs=0.05)


def test_rsi_bad_period():
    with pytest.raises(ValueError):
        calculate_rsi([1, 2], 0)


@pytest.mark.parametrize("rsi,pos,exp", [
    (25, False, BUY), (25, True, HOLD), (75, True, SELL), (75, False, HOLD),
    (50, False, HOLD), (50, True, HOLD), (None, False, HOLD), (30, False, HOLD), (70, True, HOLD),
])
def test_signal(rsi, pos, exp):
    assert get_signal(rsi, pos) == exp


def klines(closes):
    return [[0, 0, 0, 0, str(c), 0] for c in closes] + [[0, 0, 0, 0, "1", 0]]


def make(tmp_path, closes, dry=False):
    cfg = Config(dry_run=dry, state_file=str(tmp_path / "s.json"), quote_amount=20)
    c = MagicMock()
    c.get_klines.return_value = klines(closes)
    c.get_symbol_info.return_value = {"filters": [{"filterType": "LOT_SIZE", "stepSize": "0.00001"}]}
    c.order_market_buy.return_value = {"orderId": 1, "executedQty": "0.001", "cummulativeQuoteQty": "20"}
    c.order_market_sell.return_value = {"orderId": 2}
    return Trader(c, cfg, sleep=lambda s: None), c


def test_buy_on_oversold(tmp_path):
    t, c = make(tmp_path, list(range(100, 60, -1)))
    assert t.step() == BUY
    c.order_market_buy.assert_called_once_with(symbol="BTCUSDT", quoteOrderQty="20.00")
    assert t.state["in_position"] and t.state["qty"] == 0.001
    # no second buy while in position
    assert t.step() == HOLD
    assert c.order_market_buy.call_count == 1


def test_sell_on_overbought(tmp_path):
    t, c = make(tmp_path, list(range(60, 100)))
    t.state = {"in_position": True, "qty": 0.0012345, "entry_price": 50}
    assert t.step() == SELL
    c.order_market_sell.assert_called_once_with(symbol="BTCUSDT", quantity=0.00123)
    assert not t.state["in_position"]


def test_dry_run_places_no_orders(tmp_path):
    t, c = make(tmp_path, list(range(100, 60, -1)), dry=True)
    assert t.step() == BUY
    c.order_market_buy.assert_not_called()
    assert t.state["in_position"]


def test_state_persisted(tmp_path):
    t, c = make(tmp_path, list(range(100, 60, -1)))
    t.step()
    t2 = Trader(c, t.cfg, sleep=lambda s: None)
    assert t2.state["in_position"]


def test_retry_recovers(tmp_path):
    t, c = make(tmp_path, list(range(100, 60, -1)))
    c.get_klines.side_effect = [ConnectionError("x"), klines(list(range(100, 60, -1)))]
    assert t.step() == BUY


def test_retry_gives_up():
    fn = MagicMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        retry(fn, attempts=3, sleep=lambda s: None)
    assert fn.call_count == 3
