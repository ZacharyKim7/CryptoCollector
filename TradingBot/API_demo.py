from config import API_KEY, API_SECRET
from coinbase.rest import RESTClient
from json import dumps
import math

api_key = API_KEY
api_secret = API_SECRET

client = RESTClient(api_key=api_key, api_secret=api_secret)

# Display accounts and their balances.
# accounts_response = client.get_accounts()
# accounts = accounts_response.accounts
# accounts_data = [account.__dict__ for account in accounts]
# print(dumps(accounts_data, indent=2))

product = client.get_product("BTC-USD")
btc_usd_price = float(product["price"])
adjusted_btc_usd_price = str(math.floor(btc_usd_price - (btc_usd_price * 0.05)))

order = client.limit_order_gtc_buy(
    client_order_id="clientOrderId",
    product_id="ADA-USD",
    base_size="0.0002",
    limit_price=adjusted_btc_usd_price
)

if "success_response" in order:
    order_id = order["success_response"]["order_id"]
    client.cancel_orders(order_ids=[order_id])
elif "error_response" in order:
    error_response = order["error_response"]
    print(error_response)