import logging
import os
import sys

# allow running as `python my-first-project-main/main.py` from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.config import Config  # noqa: E402
from bot.dashboard import BufferHandler, start_dashboard  # noqa: E402
from bot.trader import Trader  # noqa: E402


def main():
    cfg = Config.from_env()
    buffer = BufferHandler()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(cfg.log_file), buffer])
    if not cfg.dry_run and not (cfg.api_key and cfg.api_secret):
        sys.exit("BINANCE_API_KEY/BINANCE_API_SECRET required when DRY_RUN=false")
    if not cfg.use_testnet and not cfg.dry_run:
        logging.warning("LIVE TRADING WITH REAL FUNDS ENABLED")
    from binance.client import Client
    client = Client(cfg.api_key or None, cfg.api_secret or None, testnet=cfg.use_testnet)
    trader = Trader(client, cfg)
    server = None
    if cfg.dashboard_enabled:
        try:
            server = start_dashboard(trader, buffer, cfg.dashboard_port)
        except OSError as exc:
            logging.error("Dashboard failed to start: %s", exc)
    try:
        trader.run()  # returns when /api/stop sets the stop event
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    finally:
        if server:
            server.shutdown()
            server.server_close()
    logging.info("Exiting")


if __name__ == "__main__":
    main()
