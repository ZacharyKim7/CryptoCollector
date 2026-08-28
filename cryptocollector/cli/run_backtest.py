import csv
import os
import time

from cryptocollector import config
from cryptocollector.backtest.engine import SEED_LENGTH
from cryptocollector.backtest.grid_search import run_grid_search
from cryptocollector.data.cache import CandleCache
from cryptocollector.data.coinbase_client import make_client
from cryptocollector.strategy.regime import RegimeConfig, RegimeDetector

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backtest_results")


def current_regime_snapshot(candles) -> dict:
    """Diagnostic independent of any specific trading config: is this coin
    range-bound RIGHT NOW, using the default regime thresholds?"""
    if len(candles) <= SEED_LENGTH:
        return {"is_active": None, "atr_pct": None, "adx": None}

    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()
    closes = candles["close"].to_numpy()

    regimeConfig = RegimeConfig()
    regime = RegimeDetector(highs[:SEED_LENGTH], lows[:SEED_LENGTH], closes[:SEED_LENGTH], regimeConfig)
    for i in range(SEED_LENGTH, len(closes)):
        regime.inform(highs[i], lows[i], closes[i])

    return {"is_active": regime.is_active(), "atr_pct": round(regime.atr_pct * 100, 2), "adx": round(regime.adx, 2)}


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    client = make_client()
    cache = CandleCache()

    all_rows = []
    snapshots = {}

    for symbol in config.WATCHLIST:
        print(f"--- {symbol} ---")
        cache.fetch_and_update(symbol, client)
        candles = cache.get_candles(symbol)

        if len(candles) <= SEED_LENGTH:
            print(f"  Not enough {config.TARGET_TIMEFRAME} candles ({len(candles)}) to backtest, skipping.")
            continue

        snapshot = current_regime_snapshot(candles)
        snapshots[symbol] = snapshot
        print(f"  Current regime: active={snapshot['is_active']} atr%={snapshot['atr_pct']} adx={snapshot['adx']}")

        results = run_grid_search(symbol, candles)
        print(f"  Ran {len(results)} configs. Best return: {results[0]['total_return_pct']:.2f}%" if results else "  No valid configs.")
        all_rows.extend(results)

    if not all_rows:
        print("No results to write.")
        return

    timestamp = int(time.time())
    out_path = os.path.join(RESULTS_DIR, f"backtest_{timestamp}.csv")
    fieldnames = [k for k in all_rows[0].keys() if k not in ("algoConfig", "regimeConfig")]
    fieldnames += ["vwapBuy", "rsiBuy", "vwapSell", "rsiSell", "vwapWindow", "stopLoss", "waitAfterLoss", "minAtrPct", "maxAdx"]

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            algoConfig = row["algoConfig"]
            regimeConfig = row["regimeConfig"]
            flat = {k: v for k, v in row.items() if k not in ("algoConfig", "regimeConfig")}
            flat.update(
                {
                    "vwapBuy": algoConfig.vwapBuy,
                    "rsiBuy": algoConfig.rsiBuy,
                    "vwapSell": algoConfig.vwapSell,
                    "rsiSell": algoConfig.rsiSell,
                    "vwapWindow": algoConfig.vwapWindow,
                    "stopLoss": algoConfig.stopLoss,
                    "waitAfterLoss": algoConfig.waitAfterLoss,
                    "minAtrPct": regimeConfig.minAtrPct,
                    "maxAdx": regimeConfig.maxAdx,
                }
            )
            writer.writerow(flat)

    print(f"\nWrote {len(all_rows)} results to {out_path}")


if __name__ == "__main__":
    main()
