from cryptocollector import config
from cryptocollector.data.cache import CandleCache
from cryptocollector.data.coinbase_client import make_client


def main():
    client = make_client()
    cache = CandleCache()

    for symbol in config.WATCHLIST:
        fetched = cache.fetch_and_update(symbol, client)
        print(f"{symbol}: fetched {fetched} new native ({config.NATIVE_GRANULARITY}) candles")


if __name__ == "__main__":
    main()
