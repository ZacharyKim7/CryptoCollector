import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

CURRENCY_TICKER='XRP-USD'
LIMIT=1000
TEST_PERIOD_DAYS=5
VWAP_WINDOW=60
PAUSE_ON_TRADE=False
MAKER_FEES=0.005
