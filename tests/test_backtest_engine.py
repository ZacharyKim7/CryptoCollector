import numpy as np
import pandas as pd

from cryptocollector.backtest.engine import BacktestEngine
from cryptocollector.backtest.metrics import compute_metrics
from cryptocollector.strategy.algorithm import AlgorithmConfiguration
from cryptocollector.strategy.regime import RegimeConfig


def _candles_df():
    # 100 flat "seed" candles, then a sharp drop (should trigger a buy),
    # then a sharp rise well above the rolling vwap (should trigger a sell).
    n_seed = 100
    seed = 100.0 + np.sin(np.linspace(0, 10 * np.pi, n_seed))
    dip = np.full(20, 50.0)
    spike = np.full(20, 150.0)
    closes = np.concatenate([seed, dip, spike])
    highs = closes + 0.5
    lows = closes - 0.5
    volumes = np.full(len(closes), 1000.0)
    start_ts = np.arange(len(closes)) * 7200

    return pd.DataFrame({"open": closes, "high": highs, "low": lows, "close": closes, "volume": volumes, "start_ts": start_ts})


def test_engine_executes_a_full_buy_sell_round_trip():
    candles = _candles_df()
    algoConfig = AlgorithmConfiguration(vwapBuy=1.2, vwapSell=1.0, vwapWindow=60, stopLoss=False, waitAfterLoss=0)
    regimeConfig = RegimeConfig(minAtrPct=0.0, maxAdx=1000)  # always active, isolates the strategy logic

    engine = BacktestEngine(algoConfig, regimeConfig, symbol="TEST-USD")
    result = engine.run(candles, seed_length=100)

    assert len(result.equity_curve) == len(candles) - 100
    assert all(result.regime_active_flags)  # regime thresholds are trivially satisfied

    sides = [t.side for t in result.trades]
    assert "BUY" in sides
    assert "SELL" in sides
    assert sides.index("BUY") < sides.index("SELL")

    assert result.portfolio.totalWins >= 1  # bought at ~50, sold at ~150


def test_metrics_reflect_a_profitable_round_trip():
    candles = _candles_df()
    algoConfig = AlgorithmConfiguration(vwapBuy=1.2, vwapSell=1.0, vwapWindow=60, stopLoss=False, waitAfterLoss=0)
    regimeConfig = RegimeConfig(minAtrPct=0.0, maxAdx=1000)

    engine = BacktestEngine(algoConfig, regimeConfig, symbol="TEST-USD")
    result = engine.run(candles, seed_length=100)
    metrics = compute_metrics(result)

    assert metrics["total_return_pct"] > 0
    assert metrics["num_completed_trades"] >= 1
    assert metrics["win_rate_pct"] == 100.0


def test_engine_raises_on_insufficient_candles():
    candles = _candles_df().iloc[:50]
    engine = BacktestEngine(AlgorithmConfiguration(), RegimeConfig())
    try:
        engine.run(candles, seed_length=100)
        assert False, "expected ValueError"
    except ValueError:
        pass
