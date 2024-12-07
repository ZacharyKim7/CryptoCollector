import json
from historicalDataHelpers import getHistoricalData, TimeInterval
from configBackTest import *

with open('BONK.json', 'w') as json_file:
    json.dump(getHistoricalData(CURRENCY_TICKER, TimeInterval.THIRTY_MINUTE.value, days_ago=TEST_PERIOD_DAYS), json_file)

    # json.dump(getHistoricalData(CURRENCY_TICKER, TimeInterval.THIRTY_MINUTE.value, start=1709596360, end=1715813560), json_file)
    