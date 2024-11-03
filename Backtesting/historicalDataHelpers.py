from datetime import datetime, timedelta
from coinbase.rest import RESTClient
from TradingBot.config import *
from enum import Enum
import time

class TimeInterval(Enum):
    ONE_MINUTE = "ONE_MINUTE"
    FIVE_MINUTE = "FIVE_MINUTE"
    FIFTEEN_MINUTE = "FIFTEEN_MINUTE"
    THIRTY_MINUTE = "THIRTY_MINUTE"
    ONE_HOUR = "ONE_HOUR"
    ONE_DAY = "ONE_DAY"

# Function to convert days ago to Unix timestamp
def days_ago_to_unix(days):
    return str(int((datetime.utcnow() - timedelta(days=days)).timestamp()))

# Get current Unix timestamp
def current_unix_timestamp():
    return str(int(datetime.utcnow().timestamp()))

def getHistoricalData(currency_pair, interval, start=0, end=0, days_ago=None):

    if days_ago:
        start_timestamp = int(days_ago_to_unix(days_ago))
        end_timestamp = int(current_unix_timestamp())
    else:
        start_timestamp = start
        end_timestamp = end

    client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
    # Define the maximum number of candlesticks per request
    max_candles_per_request = 300

    # Calculate the interval in seconds
    if interval == TimeInterval.ONE_MINUTE.value:
        interval_seconds = 60
    elif interval == TimeInterval.FIVE_MINUTE.value:
        interval_seconds = 300
    elif interval == TimeInterval.FIFTEEN_MINUTE.value:
        interval_seconds = 900
    elif interval == TimeInterval.THIRTY_MINUTE.value:
        interval_seconds = 1800
    elif interval == TimeInterval.ONE_HOUR.value:
        interval_seconds = 3600
    elif interval == TimeInterval.ONE_DAY.value:
        interval_seconds = 86400
    else:
        raise ValueError("Invalid interval")

    # Calculate the number of seconds between start and end timestamps
    time_diff_seconds = end_timestamp - start_timestamp

    # Calculate the number of requests needed
    num_requests = (time_diff_seconds // interval_seconds) // max_candles_per_request + 1

    # Initialize list to store candlesticks
    all_candles = []

    # Make requests for each chunk of data
    for i in range(num_requests):
        # Calculate the start and end timestamps for the current chunk
        chunk_start_timestamp = start_timestamp + (i * max_candles_per_request * interval_seconds)
        chunk_end_timestamp = min(start_timestamp + ((i + 1) * max_candles_per_request * interval_seconds), end_timestamp)

        # Fetch candles for the current chunk
        candles = client.get_public_candles(currency_pair, str(chunk_start_timestamp), str(chunk_end_timestamp), interval)
        # Append the candles to the list
        all_candles[:0] = candles['candles']
        time.sleep(2) 
        
    return all_candles[::-1]