import requests, time, json

PAIRS = ["BNBUSDT", "LTCUSDT", "LINKUSDT", "DOGEUSDT"]
ENTER_APR, EXIT_APR = 0.50, 0.12
BUFFER_H, MAX_HOLD_H, LEV, DEP = 2, 72, 2, 50.0
FEE_RT = 0.002  # round-trip both legs, both exchanges


def get(url, **kw):
    for _ in range(3):
        try:
            r = requests.get(url, timeout=20, **kw)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(2)
    return None


def binance_hist(pair):
    d = get("https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": pair, "limit": 1000}) or []
    out = {}
    for x in d:
        out[int(x["fundingTime"])] = float(x["fundingRate"])
    return out


def bitget_hist(pair):
    out = {}
    for page in range(10):
        d = get("https://api.bitget.com/api/v2/mix/market/history-fund-rate",
                params={"symbol": pair, "productType": "USDT-FUTURES",
                        "pageSize": 100, "pageNo": page + 1})
        rows = (d or {}).get("data") or []
        if not rows:
            break
        for x in rows:
            out[int(x["fundingTime"])] = float(x["fundingRate"])
        if len(rows) < 100:
            break
        time.sleep(0.3)
    return out


def run(pair):
    b, g = binance_hist(pair), bitget_hist(pair)
    ts = sorted(set(b) & set(g))
    if len(ts) < 10:
        print(pair, "aligned points:", len(ts))
        return
    trades, pos, buf = [], None, 0
    for t in ts:
        spr = abs(b[t]) + abs(g[t]) if b[t] * g[t] < 0 else 0.0
        apr = spr * 3 * 365
        if pos is None:
            buf = buf + 8 if apr >= ENTER_APR else 0
            if buf >= BUFFER_H * 3600 * 1000:
                pos = {"t": t, "apr": apr, "leg": "long" if b[t] < 0 else "short"}
                buf = 0
        else:
            held = (t - pos["t"]) / 3600000
            if apr <= EXIT_APR or held >= MAX_HOLD_H:
                hrs = held
                fund = DEP * LEV * (pos["apr"] / 365) * (hrs / 24)
                pnl = fund - DEP * LEV * FEE_RT
                trades.append((pair, hrs, pos["apr"], pnl))
                pos = None
    if trades:
        n = len(trades)
        w = sum(1 for x in trades if x[3] > 0)
        print(f"{pair}: trades={n} win={w / n * 100:.0f}% "
              f"total=${sum(x[3] for x in trades):+.2f} "
              f"avgHold={sum(x[1] for x in trades) / n:.1f}h "
              f"avgAPR={sum(x[2] for x in trades) / n * 100:.0f}%")
        for tr in trades[:5]:
            print("   ", tr)
    else:
        print(pair, "no trades above 50% APR in window")


if __name__ == "__main__":
    for p in PAIRS:
        run(p)
