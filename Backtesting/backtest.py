import sys
sys.path.append('../')
from configBackTest import *
import time
from algorithm import Algorithm, AlgorithmConfiguration
from Backtesting.configBackTest import *
import json
import multiprocessing


class TestUser:
    def __init__(self, balance, tradeAmount):
        self.balance = balance
        self.tradeAmount = tradeAmount
        self.shares = 0
        self.holding = False
        self.purchasePrice = 0
        self.totalTrades = 0
        self.totalWins = 0
        self.totalLoss = 0

    def buyShares(self, price):
        if not self.holding:
            # print("BOUGHT", price)
            if PAUSE_ON_TRADE:
                time.sleep(5)
            self.purchasePrice = price
            tradeAmountAfterFees = self.tradeAmount - self.tradeAmount * MAKER_FEES
            self.shares += tradeAmountAfterFees / price
            self.balance -= self.tradeAmount
            self.holding = True
            self.totalTrades += 1
            return True
        return False

    def sellShares(self, price):
        if self.holding:
            if PAUSE_ON_TRADE:
                time.sleep(5)
            self.balance += self.shares * price
            self.shares = 0
            self.holding = False
            if self.purchasePrice >= price:
                self.totalLoss += 1
            elif self.purchasePrice < price:
                self.totalWins += 1
            return True
        return False

    def portfolioValue(self, price):
        return self.balance + price * self.shares


def main():
    with open('XRP.json', 'r') as json_file:
        allData = json.load(json_file)
        highs = [float(x['high']) for x in allData]
        lows = [float(x['low']) for x in allData]
        closes = [float(x['close']) for x in allData]
        volumes = [float(x['volume']) for x in allData]
        start_time = time.time()
        beginTest(highs, lows, closes, volumes)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Elapsed time: {elapsed_time} seconds")

def vwap_buy_analysis(center_value, count):
    value = [round(center_value + 0.01 * i, 2) for i in range(0, count + 1)]
    return value

def vwap_sell_analysis(center_value, count):
    value = [round(center_value - 0.01 * i, 2) for i in range(0, count + 1)]
    return value

def beginTest(highs, lows, closes, volumes):

    vwapBuys = [1.0, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07]
    rsiBuys = [15,25,35,False]
    maBuys = [False]

    vwapSells = [1.06,1.05,1.04,1.03,1.02,1.01,1.00,0.99,0.98,0.97]
    rsiSells = [65,75,85,False]
    maSells = [False]

    vwapWindows = [14, 20, 30, 45, 60, 75, 90]
    
    stopLosses = [0.99]

    waitAfterLoss = [0, 12, 48, 96]


    #hardcode settting

    vwapBuys = [1.03]
    vwapSells = [1.03]
    rsiBuys = [False]
    rsiSells = [False]
    vwapWindows = [75]
    stopLosses = [0.99]
    waitAfterLoss = [0]

    configurations = []
    for vwap_buy in vwapBuys:
        for rsi_buy in rsiBuys:
            for ma_buy in maBuys:
                for vwap_sell in vwapSells:
                    for rsi_sell in rsiSells:
                        for ma_sell in maSells:
                            for vwap_window in vwapWindows:
                                for stop_loss in stopLosses:
                                    for wait_after_loss in waitAfterLoss:
                                        # You may want to add conditions to skip combinations that are not valid
                                        # For example, if rsi_buy or rsi_sell is False, skip the iteration
                                        if vwap_sell == False and rsi_sell == False and ma_sell == False:
                                            continue
                                        
                                        configurations.append(AlgorithmConfiguration(
                                            vwapBuy=vwap_buy,
                                            rsiBuy=rsi_buy,
                                            maBuy=ma_buy,
                                            vwapSell=vwap_sell,
                                            rsiSell=rsi_sell,
                                            maSell=ma_sell,
                                            stopLoss=stop_loss,
                                            vwapWindow=vwap_window,
                                            waitAfterLoss=wait_after_loss
                                        ))
    chunk_size = len(configurations)
    chunks = [configurations[i:i+chunk_size] for i in range(0, len(configurations), chunk_size)]
    # Create a ThreadPoolExecutor
    manager = multiprocessing.Manager()
    results_list = manager.list()
    processes = [multiprocessing.Process(target=thread_function, args=(chunk, highs, lows, closes, volumes, results_list)) for chunk in chunks]

    for process in processes:
        process.start()

    for process in processes:
        process.join()
        print("1")
    print("runn")
    # for algoConfig in configurations:
    #     percentage_complete = round((float(counter) / (len(configurations))) * 100, 2)
    #     print(f"Percentage Complete: {percentage_complete}%")
    #     testUser = TestUser(10000, 10000)
    #     algorithm = Algorithm(first100Highs=highs[:100], first100Lows=lows[:100], first100Closes=closes[:100], first100Volumes=volumes[:100], configuration=algoConfig)
    #     for interval in range(100, len(closes)):
    #         algorithm.inform(highs[interval], lows[interval], closes[interval], volumes[interval])
    #         if algorithm.shouldBuy():
    #             testUser.buyShares(closes[interval])
    #         elif algorithm.shouldSell(testUser.purchasePrice):
    #             testUser.sellShares(closes[interval])

    #     counter += 1
        
    #     if((testUser.portfolioValue(closes[-1]) / 10000 - 1) * 100 >= 0.0):
    #         tradeResult = {
    #             "Total Percentage": (testUser.portfolioValue(closes[-1]) / 10000 - 1) * 100,
    #             "Total Trades": testUser.totalTrades,
    #             "Total Wins": testUser.totalWins,
    #             "Total Loss": testUser.totalLoss,
    #             "Vwap Buy": algoConfig.vwapBuy,
    #             "Vwap Sell": algoConfig.vwapSell,
    #             "Ma Buy": algoConfig.maBuy,
    #             "Ma Sell": algoConfig.maSell,
    #             "Rsi Buy": algoConfig.rsiBuy,
    #             "Rsi Sell": algoConfig.rsiSell,
    #         }
    #         tradeList.append(tradeResult)
    results_list = list(results_list)
    results_list.sort(key=lambda x:x["Total Percentage"])
    print("232434")
    for eachTrade in results_list:
        print('=' * 20)
        print(f"Vwap Buy: {eachTrade["Vwap Buy"]}")
        print(f"Vwap Sell: {eachTrade["Vwap Sell"]}")
        print(f"Ma Buy: {eachTrade["Ma Buy"]}")
        print(f"Ma Sell: {eachTrade["Ma Sell"]}")
        print(f"Rsi Buy: {eachTrade["Rsi Buy"]}")
        print(f"Rsi Sell: {eachTrade["Rsi Sell"]}")
        print(f"Stop Loss: {eachTrade["Stop Loss"]}")
        print(f"Wait After Loss: {eachTrade["Wait After Loss"]}")
        print(f"Vwap Window: {eachTrade["Vwap Window"]}")
        print(f"Percentage Gain: {eachTrade["Total Percentage"]}%")
        print(f"Total trades: {eachTrade["Total Trades"]}")
        print(f"Total Wins: {eachTrade["Total Wins"]}")
        print(f"Total Loss: {eachTrade["Total Loss"]}")
        print('*' * 20)

def thread_function(configurations, highs, lows, closes, volumes, results_list):
    tradeList = []
    counter = 0
    for algoConfig in configurations:
        percentage_complete = round((float(counter) / (len(configurations))) * 100, 2)
        print(f"Percentage Complete: {percentage_complete}%")
        counter += 1
        testUser = TestUser(10000, 10000)
        algorithm = Algorithm(first100Highs=highs[:100], first100Lows=lows[:100], first100Closes=closes[:100], first100Volumes=volumes[:100], configuration=algoConfig)
        for interval in range(100, len(closes)):
            algorithm.inform(highs[interval], lows[interval], closes[interval], volumes[interval])
            if algorithm.shouldBuy():
                order = testUser.buyShares(closes[interval])
            elif algorithm.shouldSell(testUser.purchasePrice):
                order = testUser.sellShares(closes[interval])
                if order:
                    if closes[interval] < testUser.purchasePrice * algorithm.configuration.stopLoss:
                        algorithm.timeSinceLoss += 1
        if((testUser.portfolioValue(closes[-1]) / 10000 - 1) * 100 >= -100.0):
            tradeResult = {
                "Total Percentage": (testUser.portfolioValue(closes[-1]) / 10000 - 1) * 100,
                "Total Trades": testUser.totalTrades,
                "Total Wins": testUser.totalWins,
                "Total Loss": testUser.totalLoss,
                "Vwap Buy": algoConfig.vwapBuy,
                "Vwap Sell": algoConfig.vwapSell,
                "Ma Buy": algoConfig.maBuy,
                "Ma Sell": algoConfig.maSell,
                "Rsi Buy": algoConfig.rsiBuy,
                "Rsi Sell": algoConfig.rsiSell,
                "Stop Loss": algoConfig.stopLoss,
                "Wait After Loss": algoConfig.waitAfterLoss,
                "Vwap Window": algoConfig.vwapWindow
            }
            tradeList.append(tradeResult)
    results_list.extend(tradeList)
    print("Chunk complete")


if __name__ == "__main__":
    main()
