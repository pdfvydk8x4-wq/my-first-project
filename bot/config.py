import os
from dataclasses import dataclass


def _bool(v, default):
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    api_key: str = ""
    api_secret: str = ""
    use_testnet: bool = True
    dry_run: bool = True
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    rsi_period: int = 14
    rsi_buy: float = 30.0
    rsi_sell: float = 70.0
    quote_amount: float = 20.0
    poll_seconds: int = 60
    state_file: str = "state.json"
    log_file: str = "bot.log"

    @classmethod
    def from_env(cls):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        e = os.environ.get
        return cls(
            api_key=e("BINANCE_API_KEY", ""),
            api_secret=e("BINANCE_API_SECRET", ""),
            use_testnet=_bool(e("USE_TESTNET"), True),
            dry_run=_bool(e("DRY_RUN"), True),
            symbol=e("SYMBOL", "BTCUSDT").upper(),
            interval=e("INTERVAL", "15m"),
            rsi_period=int(e("RSI_PERIOD", "14")),
            rsi_buy=float(e("RSI_BUY", "30")),
            rsi_sell=float(e("RSI_SELL", "70")),
            quote_amount=float(e("QUOTE_AMOUNT", "20")),
            poll_seconds=int(e("POLL_SECONDS", "60")),
            state_file=e("STATE_FILE", "state.json"),
            log_file=e("LOG_FILE", "bot.log"),
        )
