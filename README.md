# my-first-project — RSI-бот для Binance Spot

Простой торговый бот на Python: покупает, когда RSI(14) < 30, и продаёт, когда RSI > 70.
Держит не больше одной позиции, на каждую сделку тратит фиксированную сумму в USDT.

## ⚠️ Риски
- Торговля криптовалютой может привести к **потере всех вложенных средств**.
- Простая RSI-стратегия **не гарантирует прибыль** и часто убыточна на трендовом рынке.
- Это учебный проект, а не финансовый совет. Начинайте с **Testnet** и `DRY_RUN=true`.
- Никогда не публикуйте файл `.env` и не давайте API-ключам права на вывод средств.

## Установка
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # затем впишите свои ключи в .env
```

## Ключи Binance Testnet
1. Откройте https://testnet.binance.vision/ и войдите через GitHub.
2. Нажмите **Generate HMAC_SHA256 Key**, задайте имя.
3. Скопируйте API Key и Secret Key в `.env` (`BINANCE_API_KEY`, `BINANCE_API_SECRET`).
4. Оставьте `USE_TESTNET=true`. На тестовом счёте уже есть виртуальные средства.

## Настройки (`.env`)
| Переменная | По умолчанию | Описание |
|---|---|---|
| `USE_TESTNET` | `true` | Тестовая сеть Binance |
| `DRY_RUN` | `true` | Только логировать сигналы, без ордеров |
| `SYMBOL` | `BTCUSDT` | Торговая пара |
| `INTERVAL` | `15m` | Таймфрейм свечей |
| `RSI_PERIOD` | `14` | Период RSI |
| `RSI_BUY` / `RSI_SELL` | `30` / `70` | Пороги покупки и продажи |
| `QUOTE_AMOUNT` | `20` | Сумма покупки в USDT |
| `POLL_SECONDS` | `60` | Пауза между проверками |

## Запуск
```bash
python main.py
```
Логи пишутся в консоль и в `bot.log`, состояние позиции в `state.json`.
Остановка: `Ctrl+C`. Чтобы ставить реальные ордера на Testnet, задайте `DRY_RUN=false`.

## Тесты
```bash
pytest -v
```
Тесты проверяют расчёт RSI и логику сигналов с имитацией биржи, без сети и ключей.
