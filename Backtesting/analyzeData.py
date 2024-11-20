from Algorithms.algorithm import Algorithm
from configBackTest import *
from Algorithms.getHistoricalKlines import get_historical_klines
from Algorithms.grabTestData import *
from binance.client import Client

class GoodTrade:
    def __init__(self, buyPrice, vwapBuy, maBuy):
        self.buyPrice = buyPrice
        self.vwapBuy = vwapBuy
        self.maBuy = maBuy
        self.sellPrice = None
        self.vwapSell = None
        self.maSell = None
    
    def addBuyInfo(self, buyPrice, vwapBuy, maBuy):
        self.buyPrice = buyPrice
        self.vwapBuy = vwapBuy
        self.maBuy = maBuy

    def addSellInfo(self, sellPrice, vwapSell, maSell):
        self.sellPrice = sellPrice
        self.vwapSell = vwapSell
        self.maSell = maSell

    def buyVwapDifference(self):
        return round((self.vwapBuy - self.buyPrice) / self.buyPrice * 100,2)
    
    def buyMaDifference(self):
        return round((self.maBuy - self.buyPrice) / self.buyPrice * 100,2)


def main():
    allData = get_historical_klines(CURRENCY_TICKER, Client.KLINE_INTERVAL_30MINUTE, TEST_PERIOD_DAYS + " day ago UTC")
    highs = getHighsFromKLINE(allData)
    lows = getLowsFromKLINE(allData)
    closes = getClosesFromKLINE(allData)
    volumes = getVolumesFromKLINE(allData)

    goodTrades = getGoodTrades(highs, lows, closes, volumes)
    for trade in goodTrades:
        print(trade.buyPrice, trade.sellPrice)

    print("Average VWAP diff:", sum([trade.buyVwapDifference() for trade in goodTrades]) / len(goodTrades))
    print("Average MA diff:", sum([trade.buyMaDifference() for trade in goodTrades]) / len(goodTrades))

def getGoodTrades(highs, lows, closes, volumes):
    goodTrades = []
    algorithm = Algorithm(first100Highs=highs[:100], first100Lows=lows[:100], first100Closes=closes[:100], first100Volumes=volumes[:100])
    currentTrade = None
    for interval in range(100, len(closes)):
        algorithm.inform(highs[interval], lows[interval], closes[interval], volumes[interval])
        if not currentTrade:
            currentTrade = GoodTrade(closes[interval], algorithm.vwap, algorithm.ma)
        elif currentTrade.buyPrice * 1.05 <= closes[interval]:
            currentTrade.addSellInfo(closes[interval], algorithm.vwap, algorithm.ma)
            goodTrades.append(currentTrade)
            currentTrade = None
        elif currentTrade.buyPrice >= closes[interval]:
            currentTrade.addBuyInfo(closes[interval], algorithm.vwap, algorithm.ma)
            
    return goodTrades

if __name__ == "__main__":
    main()