import logging
import sys

from bot.config import Config
from bot.trader import Trader


def main():
    cfg = Config.from_env()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(cfg.log_file)])
    if not cfg.dry_run and not (cfg.api_key and cfg.api_secret):
        sys.exit("BINANCE_API_KEY/BINANCE_API_SECRET required when DRY_RUN=false")
    if not cfg.use_testnet and not cfg.dry_run:
        logging.warning("LIVE TRADING WITH REAL FUNDS ENABLED")
    from binance.client import Client
    client = Client(cfg.api_key or None, cfg.api_secret or None, testnet=cfg.use_testnet)
    try:
        Trader(client, cfg).run()
    except KeyboardInterrupt:
        logging.info("Stopped by user")


if __name__ == "__main__":
    main()
