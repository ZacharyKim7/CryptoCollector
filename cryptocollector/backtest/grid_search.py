import multiprocessing

import pandas as pd

from cryptocollector.backtest.engine import BacktestEngine
from cryptocollector.backtest.metrics import compute_metrics
from cryptocollector.strategy.algorithm import AlgorithmConfiguration
from cryptocollector.strategy.regime import RegimeConfig


def default_algo_grid() -> list[AlgorithmConfiguration]:
    """A moderate starting grid over the mean-reversion thresholds. Narrower
    than the original Backtesting/backtest.py's full (and never actually
    run - it was hardcoded down to single values) grid, to keep a full
    watchlist x regime-grid run tractable on a personal machine. Widen if
    results all cluster at one edge of a range.
    """
    configs = []
    for vwapBuy in [1.0, 1.02, 1.04]:
        for rsiBuy in [False, 30]:
            for vwapSell in [1.0, 0.98, 0.96]:
                for rsiSell in [False, 70]:
                    for vwapWindow in [30, 60]:
                        for stopLoss in [0.95, 0.99]:
                            if vwapSell is False and rsiSell is False:
                                continue
                            configs.append(
                                AlgorithmConfiguration(
                                    vwapBuy=vwapBuy,
                                    rsiBuy=rsiBuy,
                                    vwapSell=vwapSell,
                                    rsiSell=rsiSell,
                                    vwapWindow=vwapWindow,
                                    stopLoss=stopLoss,
                                    waitAfterLoss=0,
                                )
                            )
    return configs


def default_regime_grid() -> list[RegimeConfig]:
    configs = []
    for minAtrPct in [0.01, 0.02, 0.03]:
        for maxAdx in [15, 20, 25]:
            configs.append(RegimeConfig(minAtrPct=minAtrPct, maxAdx=maxAdx))
    return configs


def _worker(combos, symbol, candles, portfolio_kwargs, results_list):
    for algoConfig, regimeConfig in combos:
        engine = BacktestEngine(algoConfig, regimeConfig, symbol=symbol, portfolio_kwargs=portfolio_kwargs)
        try:
            result = engine.run(candles)
        except ValueError:
            continue
        metrics = compute_metrics(result)
        metrics["algoConfig"] = algoConfig
        metrics["regimeConfig"] = regimeConfig
        results_list.append(metrics)


def run_grid_search(
    symbol: str,
    candles: pd.DataFrame,
    algo_grid: list[AlgorithmConfiguration] | None = None,
    regime_grid: list[RegimeConfig] | None = None,
    portfolio_kwargs: dict | None = None,
    num_processes: int = 4,
) -> list[dict]:
    algo_grid = algo_grid if algo_grid is not None else default_algo_grid()
    regime_grid = regime_grid if regime_grid is not None else default_regime_grid()

    combos = [(a, r) for a in algo_grid for r in regime_grid]
    if not combos:
        return []

    chunk_size = max(1, len(combos) // num_processes)
    chunks = [combos[i : i + chunk_size] for i in range(0, len(combos), chunk_size)]

    manager = multiprocessing.Manager()
    results_list = manager.list()
    processes = [
        multiprocessing.Process(target=_worker, args=(chunk, symbol, candles, portfolio_kwargs, results_list))
        for chunk in chunks
    ]

    for p in processes:
        p.start()
    for p in processes:
        p.join()

    results = list(results_list)
    results.sort(key=lambda r: r["total_return_pct"], reverse=True)
    return results
