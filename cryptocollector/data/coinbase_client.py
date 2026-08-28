import time
from datetime import datetime, timedelta, timezone

from coinbase.rest import RESTClient

from cryptocollector import config

# Coinbase's public candles endpoint caps each response at this many candles.
MAX_CANDLES_PER_REQUEST = 300

GRANULARITY_SECONDS = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "TWO_HOUR": 7200,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}


def make_client() -> RESTClient:
    return RESTClient(api_key=config.API_KEY, api_secret=config.API_SECRET)


def days_ago_to_unix(days: float) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())


def current_unix_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def fetch_candles(client: RESTClient, product_id: str, granularity: str, start_ts: int, end_ts: int) -> list[dict]:
    """Fetch all candles for [start_ts, end_ts), paginating in
    MAX_CANDLES_PER_REQUEST-sized chunks. Returns oldest-first.

    Adapted from the original Backtesting/historicalDataHelpers.py pagination
    loop; the chunking/pacing logic is unchanged, just parameterized as a
    standalone function instead of a script-embedded routine.
    """
    if granularity not in GRANULARITY_SECONDS:
        raise ValueError(f"Invalid granularity: {granularity}")
    interval_seconds = GRANULARITY_SECONDS[granularity]

    if end_ts <= start_ts:
        return []

    all_candles = []
    time_diff_seconds = end_ts - start_ts
    num_requests = (time_diff_seconds // interval_seconds) // MAX_CANDLES_PER_REQUEST + 1

    for i in range(num_requests):
        chunk_start = start_ts + (i * MAX_CANDLES_PER_REQUEST * interval_seconds)
        chunk_end = min(start_ts + ((i + 1) * MAX_CANDLES_PER_REQUEST * interval_seconds), end_ts)
        if chunk_start >= chunk_end:
            continue

        response = client.get_public_candles(product_id, str(chunk_start), str(chunk_end), granularity)
        candles = response["candles"]
        all_candles[:0] = candles
        time.sleep(2)

    return all_candles[::-1]
