import time
from collections import deque
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
        # Get historical data for initial VWAP calculation
        allData = getHistoricalData(currency, TimeInterval.THIRTY_MINUTE.value, days_ago=3)[-101:-1]
        highs = deque(float(x['high']) for x in allData)
        lows = deque(float(x['low']) for x in allData)
        closes = deque(float(x['close']) for x in allData)
        volumes = deque(float(x['volume']) for x in allData)

        # Define algorithm configuration specific to VWAP trading strategy
        config = AlgorithmConfiguration(
            vwapBuy=True,
            vwapSell=True,
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
    print("Setting up websocket/data stream")

    lastSeenCandles = {}
    users = {}

    # Configure intervals
    data_check_interval = 60  # seconds
    error_retry_interval = 2  # seconds

    while True:
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - 10000  # Example offset for candle data
        
        for currency in CURRENCY_TICKER_PAIRS:
            # Initialize User if not already done
            if currency not in users:
                users[currency] = User(TRADE_VALUE, currency)

            # Attempt to fetch the latest candle data
            while True:
                try:
                    candles = users[currency].client.get_public_candles(
                        currency, str(start_timestamp), str(end_timestamp), 'THIRTY_MINUTE'
                    )['candles']
                    latest_candle = candles[1]  # Assuming 1 is the latest relevant candle index
                    break
                except Exception as e:
                    print(f"Failed to fetch latest candle for {currency}: {e}. Retrying...")
                    time.sleep(error_retry_interval)

            # Check for new data and invoke callback if needed
            if currency not in lastSeenCandles:
                lastSeenCandles[currency] = latest_candle['start']

            if lastSeenCandles[currency] != latest_candle['start']:
                lastSeenCandles[currency] = latest_candle['start']
                webSocketCallbacks.on_message(latest_candle, users[currency], currency)

        # Wait before the next data fetch round
        time.sleep(data_check_interval)

if __name__ == "__main__":
    main()
