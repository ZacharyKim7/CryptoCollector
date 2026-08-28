import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Coins to monitor/backtest. User-curated, not auto-scanned.
WATCHLIST = ["ADA-USD", "XRP-USD"]

# Coinbase's public candles endpoint does not offer a native FOUR_HOUR
# granularity (valid values are ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE,
# THIRTY_MINUTE, ONE_HOUR, TWO_HOUR, SIX_HOUR, ONE_DAY). We fetch/cache the
# native granularity below and resample pairs of candles into synthetic
# 4-hour bars (see data/cache.py::get_candles) to get the coarser signal the
# strategy wants without losing precision or making extra API calls.
NATIVE_GRANULARITY = "TWO_HOUR"
TARGET_TIMEFRAME = "4h"  # pandas resample rule

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cryptocollector.db")
DEFAULT_BACKFILL_DAYS = 180

# Simulated trading costs, carried over from the original backtester.
MAKER_FEES = 0.005
SLIPPAGE_PCT = 0.0

# Paper trader polling cadence. Candles are 4h, so this only needs to be
# frequent enough to catch a new candle close promptly, not real-time.
POLL_INTERVAL_SECONDS = 300

# --- Regime detector defaults (tuned via backtest grid search, not by hand) ---
REGIME_ATR_WINDOW = 14
REGIME_MIN_ATR_PCT = 0.02
REGIME_ADX_WINDOW = 14
REGIME_MAX_ADX = 20

# --- Mean-reversion strategy defaults ---
ALGO_VWAP_WINDOW = 60
ALGO_MA_WINDOW = 60
ALGO_RSI_WINDOW = 14
ALGO_VWAP_BUY = 1.03
ALGO_VWAP_SELL = 1.03
ALGO_STOP_LOSS = 0.99
ALGO_WAIT_AFTER_LOSS = 0

STARTING_BALANCE = 10000
TRADE_AMOUNT = 1000
