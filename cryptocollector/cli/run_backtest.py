import csv
import os
import time

from cryptocollector import config
from cryptocollector.backtest.engine import SEED_LENGTH
from cryptocollector.backtest.report import trade_quality_report
from cryptocollector.backtest.validation import evaluate_on, run_validated_grid_search, train_test_split
from cryptocollector.data.cache import CandleCache
from cryptocollector.data.coinbase_client import make_client
from cryptocollector.strategy.regime import RegimeConfig, RegimeDetector

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backtest_results")

METRIC_FIELDS = [
    "total_return_pct",
    "win_rate_pct",
    "max_drawdown_pct",
    "time_in_regime_pct",
    "time_in_market_pct",
    "num_trades",
    "num_completed_trades",
    "profit_factor",
]
CONFIG_FIELDS = ["vwapBuy", "rsiBuy", "vwapSell", "rsiSell", "vwapWindow", "stopLoss", "waitAfterLoss", "minAtrPct", "maxAdx"]


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


def print_trade_quality(symbol: str, test_candles, algoConfig, regimeConfig) -> None:
    """Trade-level detail for the top validated config, evaluated on the
    held-out TEST slice only - the same out-of-sample data used to rank it,
    not the training data it was tuned on."""
    from cryptocollector.backtest.engine import BacktestEngine

    engine = BacktestEngine(algoConfig, regimeConfig, symbol=symbol)
    result = engine.run(test_candles)
    report = trade_quality_report(result)

    if report.empty:
        print("  No completed round-trip trades on the test slice to report on.")
        return

    out_path = os.path.join(RESULTS_DIR, f"trade_quality_{symbol}_{int(time.time())}.csv")
    report.to_csv(out_path, index=False)

    print(
        f"  Test-slice trades: {len(report)} (avg return/trade: {report['return_pct'].mean():.2f}%, "
        f"avg buy vwap diff: {report['buy_vwap_diff_pct'].mean():.2f}%, "
        f"avg sell vwap diff: {report['sell_vwap_diff_pct'].mean():.2f}%)"
    )
    print(f"  Trade-level detail written to {out_path}")


def flatten_row(row: dict) -> dict:
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
    return flat


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    client = make_client()
    cache = CandleCache()

    all_rows = []

    for symbol in config.WATCHLIST:
        print(f"--- {symbol} ---")
        cache.fetch_and_update(symbol, client)
        candles = cache.get_candles(symbol)

        if len(candles) <= SEED_LENGTH:
            print(f"  Not enough {config.TARGET_TIMEFRAME} candles ({len(candles)}) to backtest, skipping.")
            continue

        snapshot = current_regime_snapshot(candles)
        print(f"  Current regime: active={snapshot['is_active']} atr%={snapshot['atr_pct']} adx={snapshot['adx']}")

        results = run_validated_grid_search(symbol, candles)
        all_rows.extend(results)

        if not results:
            print("  No valid configs.")
            continue

        best = results[0]
        print(
            f"  Top {len(results)} training configs re-evaluated out-of-sample. Best test return: "
            f"{best['test_total_return_pct']:.2f}% (train was {best['train_total_return_pct']:.2f}%)"
        )
        survivors = sum(1 for r in results if r["test_total_return_pct"] > 0)
        print(f"  {survivors}/{len(results)} of the top training configs stayed profitable on the held-out test slice.")

        _, test_candles = train_test_split(candles)
        print_trade_quality(symbol, test_candles, best["algoConfig"], best["regimeConfig"])

    if not all_rows:
        print("No results to write.")
        return

    timestamp = int(time.time())
    out_path = os.path.join(RESULTS_DIR, f"backtest_{timestamp}.csv")
    fieldnames = ["symbol"] + [f"train_{f}" for f in METRIC_FIELDS] + [f"test_{f}" for f in METRIC_FIELDS] + CONFIG_FIELDS

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(flatten_row(row))

    print(f"\nWrote {len(all_rows)} validated results to {out_path}")


if __name__ == "__main__":
    main()
