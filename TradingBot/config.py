import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

TRADE_VALUE = "100"
CURRENCY_TICKER_PAIRS = ["ADA-USD"]