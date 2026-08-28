import numpy as np

from cryptocollector.strategy.regime import RegimeConfig, RegimeDetector

SEED = 60


def _sideways_series(n=200, base=100.0, amplitude=10.0, period=8, spread=3.0):
    i = np.arange(n)
    closes = base + amplitude * np.sin(2 * np.pi * i / period)
    highs = closes + spread
    lows = closes - spread
    return highs, lows, closes


def _trending_series(n=200, base=100.0, growth=0.02):
    i = np.arange(n)
    closes = base * (1 + growth) ** i
    highs = closes * 1.01
    lows = closes * 0.99
    return highs, lows, closes


def _run(detector: RegimeDetector, highs, lows, closes, start=SEED):
    for i in range(start, len(closes)):
        detector.inform(highs[i], lows[i], closes[i])
    return detector


def test_sideways_series_is_classified_as_sideways_and_active():
    highs, lows, closes = _sideways_series()
    config = RegimeConfig(minAtrPct=0.02, maxAdx=20)
    detector = RegimeDetector(highs[:SEED], lows[:SEED], closes[:SEED], config)
    detector = _run(detector, highs, lows, closes)

    assert detector.is_sideways() is True
    assert detector.is_volatile() is True
    assert detector.is_active() is True


def test_trending_series_is_not_sideways():
    highs, lows, closes = _trending_series()
    config = RegimeConfig(minAtrPct=0.02, maxAdx=20)
    detector = RegimeDetector(highs[:SEED], lows[:SEED], closes[:SEED], config)
    detector = _run(detector, highs, lows, closes)

    assert detector.is_sideways() is False
    assert detector.is_active() is False


def test_low_volatility_series_is_not_active_even_if_sideways():
    highs, lows, closes = _sideways_series(amplitude=0.5, spread=0.05)
    config = RegimeConfig(minAtrPct=0.02, maxAdx=20)
    detector = RegimeDetector(highs[:SEED], lows[:SEED], closes[:SEED], config)
    detector = _run(detector, highs, lows, closes)

    assert detector.is_volatile() is False
    assert detector.is_active() is False
