import json
import math
import uuid
from enum import Enum
from TradingBot.config import *

class OrderType(Enum):
    BUY = 1
    SELL = 2

def fetchBalance(client, currency):
    # Assumes currency is in the format "BTC-USD"
    target_currency = currency.split('-')[0]
    accounts = client.get_accounts()
    for account in accounts['accounts']:
        if account['currency'] == target_currency:
            return float(account['available_balance']['value'])
    return 0.0

def order(client, order_type, currency, quantity=0):
    order_id = str(uuid.uuid4())

    if order_type == OrderType.BUY:
        order = client.market_order_buy(
            client_order_id=order_id,
            product_id=currency,
            quote_size=quantity
        )
    elif order_type == OrderType.SELL:
        balance = fetchBalance(client, currency)
        order = client.market_order_sell(
            client_order_id=order_id,
            product_id=currency,
            base_size=str(truncate(balance, 2))
        )
    else:
        print("Invalid OrderType!")
        return False
    
    if not order.get('success', False):
        print(f"Order failed: {order}")
        return False

    return True

def on_open(user):
    print('Opened Connection')

def on_close(user):
    print('Closed Connection')

def on_message(message, user, currency):
    print('Received Message')
    candle = message

    # Update the algorithm with new candle data
    algo = user.algorithm
    algo.inform(
        newHigh=float(candle['high']),
        newLow=float(candle['low']),
        newClose=float(candle['close']),
        newVolume=float(candle['volume'])
    )

    # Buy if conditions met and not currently holding
    if not user.holding and algo.shouldBuy():
        if order(user.client, OrderType.BUY, currency, TRADE_VALUE):
            print("BUY")
            user.buy(float(candle['close']))

    # Sell if conditions met and currently holding
    elif user.holding and algo.shouldSell(user.purchasePrice):
        if order(user.client, OrderType.SELL, currency):
            print("SELL")
            user.sell()

def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper
