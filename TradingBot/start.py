import time
from TradingBot.config import *
from Backtesting.historicalDataHelpers import TimeInterval, getHistoricalData
from Algorithms.algorithm import Algorithm, AlgorithmConfiguration
from coinbase.rest import RESTClient
import webSocketCallbacks

class User:
    def __init__(self, tradeValue, currency):
        self.client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
        self.holding = False
        self.purchasePrice = 0
        self.tradeValue = tradeValue
        self.algorithm = self.setupAlgorithm(currency)

    def setupAlgorithm(self, currency):
        allData = getHistoricalData(currency, TimeInterval.THIRTY_MINUTE.value, days_ago=3)[-101:-1]
        highs = [float(x['high']) for x in allData]
        lows = [float(x['low']) for x in allData]
        closes = [float(x['close']) for x in allData]
        volumes = [float(x['volume']) for x in allData]

        # MOVE TO DIFFERENT AREA
        config = AlgorithmConfiguration(
            vwapBuy=1.03,
            rsiBuy=1.03,
            maBuy=False,
            vwapSell=False,
            rsiSell=False,
            maSell=False,
            stopLoss=0.99,
            vwapWindow=75,
            waitAfterLoss=0
        )
        return Algorithm(highs, lows, closes, volumes, config)
    
    def buy(self, price):
        self.purchasePrice = price
        self.holding = True
    
    def sell(self):
        self.holding = False

def main():
    # Establish initial websocket or data-fetching setup
    webSocketSetup()

def webSocketSetup():
    print("Setting up websocket")

    lastSeenCandles = {}
    users = {}

    while True:
        # Get the current time
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - 10000
        for currency in CURRENCY_TICKER_PAIRS:

            if not currency in users:
                users[currency] = User(TRADE_VALUE, currency)

            while True:
                try:
                    last_closes = users[currency].client.get_public_candles(currency, str(start_timestamp),str(end_timestamp),'THIRTY_MINUTE')['candles']
                    candle = last_closes[1]
                    break
                except:
                    print(f"Failure to fetch latest candle for {currency}, trying again...")

            if not currency in lastSeenCandles:
                lastSeenCandles[currency] = candle['start']

            if lastSeenCandles[currency] != candle['start']:
                lastSeenCandles[currency] = candle['start']
                webSocketCallbacks.on_message(candle, users[currency], currency)
            time.sleep(2)

        # Sleep for a short duration before checking again
        time.sleep(60)  # Check every 0.1 second

if __name__ == "__main__":
    main()
