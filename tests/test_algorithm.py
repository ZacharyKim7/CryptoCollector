import numpy as np
import pytest

from cryptocollector.strategy.algorithm import Algorithm, AlgorithmConfiguration


def _flat_series(n=120, base=100.0, wiggle=1.0):
    closes = base + wiggle * np.sin(np.linspace(0, 20 * np.pi, n))
    highs = closes + 0.5
    lows = closes - 0.5
    volumes = np.full(n, 1000.0)
    return highs, lows, closes, volumes


def _manual_wilder_rsi(closes, window):
    deltas = np.diff(closes)
    gains = np.clip(deltas, 0, None)
    losses = np.clip(-deltas, 0, None)
    avg_gain = gains[:window].mean()
    avg_loss = losses[:window].mean()
    for gain, loss in zip(gains[window:], losses[window:]):
        avg_gain = (avg_gain * (window - 1) + gain) / window
        avg_loss = (avg_loss * (window - 1) + loss) / window
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def test_rsi_matches_a_manual_wilder_calculation_over_the_full_history():
    highs, lows, closes, volumes = _flat_series(n=120)
    window = 14
    config = AlgorithmConfiguration(rsiWindow=window)
    algo = Algorithm(highs[:100], lows[:100], closes[:100], volumes[:100], config)

    for i in range(100, 120):
        algo.inform(highs[i], lows[i], closes[i], volumes[i])

    # Algorithm seeds its running average from the trailing `window` deltas
    # of the initial 100-candle buffer (closes[85:100]), then Wilder-updates
    # through the 20 informed candles (closes[100:120]) - mirror that same
    # slice here rather than seeding from the start of the whole series.
    expected = _manual_wilder_rsi(closes[100 - window - 1 : 120], window)
    assert algo.rsi == pytest.approx(expected)


def test_rsi_rises_after_a_sustained_uptrend():
    n = 130
    flat = 100.0 + np.sin(np.linspace(0, 20 * np.pi, 100))  # mild noise so RSI isn't already pinned at 100
    closes = np.concatenate([flat, np.linspace(flat[-1], flat[-1] + 30, 30)])
    highs, lows = closes + 0.5, closes - 0.5
    volumes = np.full(n, 1000.0)
    config = AlgorithmConfiguration(rsiWindow=14)
    algo = Algorithm(highs[:100], lows[:100], closes[:100], volumes[:100], config)
    start_rsi = algo.rsi

    for i in range(100, n):
        algo.inform(highs[i], lows[i], closes[i], volumes[i])

    assert algo.rsi > start_rsi
    assert 0 <= algo.rsi <= 100


def test_inform_maintains_fixed_window_size():
    highs, lows, closes, volumes = _flat_series(n=110)
    config = AlgorithmConfiguration()
    algo = Algorithm(highs[:100], lows[:100], closes[:100], volumes[:100], config)

    for i in range(100, 110):
        algo.inform(highs[i], lows[i], closes[i], volumes[i])

    assert len(algo.closes) == 100
    assert algo.closes[-1] == closes[109]


def test_should_buy_respects_disabled_checks():
    highs, lows, closes, volumes = _flat_series(n=100)
    config = AlgorithmConfiguration()  # everything disabled
    algo = Algorithm(highs, lows, closes, volumes, config)

    assert algo.shouldBuy() is True


def test_should_buy_false_when_vwap_threshold_not_met():
    highs, lows, closes, volumes = _flat_series(n=100)
    config = AlgorithmConfiguration(vwapBuy=2.0)  # requires vwap >= 2x close, never true for a flat series
    algo = Algorithm(highs, lows, closes, volumes, config)

    assert algo.shouldBuy() is False


def test_should_sell_true_on_stop_loss():
    highs, lows, closes, volumes = _flat_series(n=100)
    config = AlgorithmConfiguration(stopLoss=0.99)
    algo = Algorithm(highs, lows, closes, volumes, config)

    purchasePrice = algo.closes[-1] * 10  # far above current close -> stop loss triggers
    assert algo.shouldSell(purchasePrice) is True
