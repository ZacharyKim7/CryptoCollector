import csv
import glob
import os

from cryptocollector import config
from cryptocollector.live import paper_trader
from cryptocollector.strategy.algorithm import AlgorithmConfiguration
from cryptocollector.strategy.regime import RegimeConfig

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backtest_results")


def _load_best_configs_from_latest_backtest() -> tuple[dict, dict]:
    """Load each watchlist symbol's best (highest total_return_pct) config
    from the most recent cli/run_backtest.py CSV output, if one exists."""
    csvs = sorted(glob.glob(os.path.join(RESULTS_DIR, "backtest_*.csv")))
    if not csvs:
        return {}, {}

    best_by_symbol: dict[str, dict] = {}
    with open(csvs[-1], newline="") as f:
        for row in csv.DictReader(f):
            symbol = row["symbol"]
            return_pct = float(row["total_return_pct"])
            if symbol not in best_by_symbol or return_pct > float(best_by_symbol[symbol]["total_return_pct"]):
                best_by_symbol[symbol] = row

    algo_configs, regime_configs = {}, {}
    for symbol, row in best_by_symbol.items():
        algo_configs[symbol] = AlgorithmConfiguration(
            vwapBuy=_parse(row["vwapBuy"]),
            rsiBuy=_parse(row["rsiBuy"]),
            vwapSell=_parse(row["vwapSell"]),
            rsiSell=_parse(row["rsiSell"]),
            vwapWindow=int(float(row["vwapWindow"])),
            stopLoss=_parse(row["stopLoss"]),
            waitAfterLoss=int(float(row["waitAfterLoss"])),
        )
        regime_configs[symbol] = RegimeConfig(minAtrPct=float(row["minAtrPct"]), maxAdx=float(row["maxAdx"]))
    return algo_configs, regime_configs


def _parse(value: str):
    if value in ("False", ""):
        return False
    return float(value)


def _default_configs() -> tuple[dict, dict]:
    algo = AlgorithmConfiguration(
        vwapBuy=config.ALGO_VWAP_BUY,
        vwapSell=config.ALGO_VWAP_SELL,
        stopLoss=config.ALGO_STOP_LOSS,
        vwapWindow=config.ALGO_VWAP_WINDOW,
        waitAfterLoss=config.ALGO_WAIT_AFTER_LOSS,
    )
    regime = RegimeConfig()
    return {s: algo for s in config.WATCHLIST}, {s: regime for s in config.WATCHLIST}


def main():
    algo_configs, regime_configs = _load_best_configs_from_latest_backtest()
    default_algo, default_regime = _default_configs()

    for symbol in config.WATCHLIST:
        if symbol not in algo_configs:
            print(f"No backtest result found for {symbol}, using config.py defaults")
            algo_configs[symbol] = default_algo[symbol]
            regime_configs[symbol] = default_regime[symbol]

    paper_trader.run(algo_configs, regime_configs)


if __name__ == "__main__":
    main()
