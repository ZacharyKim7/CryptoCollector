import sys
sys.path.append('../')
import json
import math
from TradingBot.config import *
from enum import Enum
import uuid

class OrderType(Enum):
    BUY = 1
    SELL = 2

def fetchBalance(client, currency):
    accounts = client.get_accounts()
    for account in accounts['accounts']:
        if account['currency'] == currency.split('-')[0]:
            return account['available_balance']['value']


def order(client, order_type, currency, quantity=0):

    if order_type == OrderType.BUY:
        order = client.market_order_buy(
            client_order_id=str(uuid.uuid4()),
            product_id=currency + 'C',
            quote_size=quantity
        )

    elif order_type == OrderType.SELL:
        balance = fetchBalance(client, currency)
        order = client.market_order_sell(
            client_order_id=str(uuid.uuid4()),
            product_id=currency + 'C',
            base_size=str(truncate(float(balance), 2)),
        )

    else:
        print("Invalid OrderType!")
        return False
        
    if not order['success']:
        return False

    return True


def on_open(user):
    print('Opened Connection')

def on_close(user):
    print('Closed Connection')

def on_message(message, user, currency):
    print('Received Message')
    print(message)
    candle = message
    algo = user.algorithm
    algo.inform(float(candle['high']), float(candle['low']), float(candle['close']), float(candle['volume']))
    if not user.holding and algo.shouldBuy():
        order_succeed = order(user.client, OrderType.BUY, currency, TRADE_VALUE)
        if order_succeed:
            print("BUY")
            user.buy(float(candle['close']))
    
    elif user.holding and algo.shouldSell(user.purchasePrice):
        order_succeed = order(user.client, OrderType.SELL, currency)
        if order_succeed:
            print("SELL")
            user.sell()

def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper