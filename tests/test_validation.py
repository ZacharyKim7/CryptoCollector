import numpy as np
import pandas as pd

from cryptocollector.backtest.validation import evaluate_on, run_validated_grid_search, train_test_split
from cryptocollector.strategy.algorithm import AlgorithmConfiguration
from cryptocollector.strategy.regime import RegimeConfig


def _candles_df(n=400):
    i = np.arange(n)
    closes = 100 + 10 * np.sin(2 * np.pi * i / 15)
    highs, lows = closes + 2, closes - 2
    volumes = np.full(n, 1000.0)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows, "close": closes, "volume": volumes, "start_ts": i * 7200})


def test_train_test_split_is_chronological_and_non_overlapping():
    candles = _candles_df(n=100)
    train, test = train_test_split(candles, test_fraction=0.2)

    assert len(train) == 80
    assert len(test) == 20
    assert train["start_ts"].iloc[-1] < test["start_ts"].iloc[0]


def test_evaluate_on_returns_none_for_too_short_a_slice():
    candles = _candles_df(n=400)
    _, test = train_test_split(candles, test_fraction=0.1)  # only 40 rows, below SEED_LENGTH=200

    result = evaluate_on("TEST-USD", AlgorithmConfiguration(), RegimeConfig(), test)
    assert result is None


def test_run_validated_grid_search_ranks_by_test_return_not_train_return():
    candles = _candles_df(n=1000)  # ensure both the 75% train and 25% test slices exceed SEED_LENGTH=200
    algo_grid = [AlgorithmConfiguration(vwapBuy=b, vwapSell=s, vwapWindow=30, stopLoss=0.9) for b in [1.0, 1.05] for s in [1.0, 0.95]]
    regime_grid = [RegimeConfig(minAtrPct=0.0, maxAdx=1000)]

    results = run_validated_grid_search("TEST-USD", candles, algo_grid=algo_grid, regime_grid=regime_grid, top_n=4, test_fraction=0.25)

    assert len(results) > 0
    test_returns = [r["test_total_return_pct"] for r in results]
    assert test_returns == sorted(test_returns, reverse=True)
    for row in results:
        assert "train_total_return_pct" in row
        assert "test_total_return_pct" in row
