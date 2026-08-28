import os

from cryptocollector.data.cache import CandleCache


def _candle(start_ts, open_, high, low, close, volume):
    return {"start": str(start_ts), "open": str(open_), "high": str(high), "low": str(low), "close": str(close), "volume": str(volume)}


def test_upsert_and_latest_timestamp(tmp_path):
    cache = CandleCache(db_path=os.path.join(tmp_path, "test.db"))
    candles = [_candle(0, 1, 2, 0.5, 1.5, 10), _candle(7200, 1.5, 2.5, 1, 2, 20)]

    inserted = cache.upsert_candles("ADA-USD", "TWO_HOUR", candles)
    assert inserted == 2
    assert cache.get_latest_timestamp("ADA-USD", "TWO_HOUR") == 7200
    assert cache.get_latest_timestamp("ADA-USD", "ONE_HOUR") is None


def test_upsert_is_idempotent(tmp_path):
    cache = CandleCache(db_path=os.path.join(tmp_path, "test.db"))
    candles = [_candle(0, 1, 2, 0.5, 1.5, 10)]

    cache.upsert_candles("ADA-USD", "TWO_HOUR", candles)
    cache.upsert_candles("ADA-USD", "TWO_HOUR", candles)

    df = cache.get_raw_candles("ADA-USD", "TWO_HOUR")
    assert len(df) == 1


def test_resample_aggregates_pairs_of_two_hour_candles_into_four_hour_bars(tmp_path):
    cache = CandleCache(db_path=os.path.join(tmp_path, "test.db"))
    # Two TWO_HOUR candles starting at t=0 and t=7200 should merge into one 4h bar.
    candles = [
        _candle(0, open_=1, high=3, low=0.5, close=2, volume=10),
        _candle(7200, open_=2, high=4, low=1.5, close=3, volume=15),
    ]
    cache.upsert_candles("ADA-USD", "TWO_HOUR", candles)

    resampled = cache.get_candles("ADA-USD", timeframe="4h", granularity="TWO_HOUR")
    assert len(resampled) == 1
    bar = resampled.iloc[0]
    assert bar["open"] == 1
    assert bar["close"] == 3
    assert bar["high"] == 4
    assert bar["low"] == 0.5
    assert bar["volume"] == 25
    assert int(bar["start_ts"]) == 0
