"""RSI calculation (Wilder's smoothing) and signal logic."""
from typing import Optional, Sequence

BUY, SELL, HOLD = "BUY", "SELL", "HOLD"


def calculate_rsi(closes: Sequence[float], period: int = 14) -> Optional[float]:
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def get_signal(rsi: Optional[float], in_position: bool,
               buy_level: float = 30.0, sell_level: float = 70.0) -> str:
    if rsi is None:
        return HOLD
    if not in_position and rsi < buy_level:
        return BUY
    if in_position and rsi > sell_level:
        return SELL
    return HOLD
