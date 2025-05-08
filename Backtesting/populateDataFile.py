import json
from historicalDataHelpers import getHistoricalData, TimeInterval
from configBackTest import *

def extract_candle_data(candle):
    # Extract the relevant data from the candle dictionary
    return {
        'start': candle['start'],
        'low': candle['low'],
        'high': candle['high'],
        'open': candle['open'],
        'close': candle['close'],
        'volume': candle['volume']
    }

with open('XRP.json', 'w') as json_file:
    data = getHistoricalData(CURRENCY_TICKER, TimeInterval.THIRTY_MINUTE.value, days_ago=TEST_PERIOD_DAYS)
    # Extract data from each candle
    json_data = [extract_candle_data(candle['candles']) for candle in data]
    json.dump(json_data, json_file)

    # json.dump(getHistoricalData(CURRENCY_TICKER, TimeInterval.THIRTY_MINUTE.value, start=1709596360, end=1715813560), json_file)
    