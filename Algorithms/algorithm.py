import numpy
from collections import deque

class AlgorithmConfiguration:
    def __init__(self, 
                 vwapBuy=False, 
                 vwapSell=False,
                 stopLoss=False,
                 waitAfterLoss=0,
                 vwapWindow=60,
                 buyThreshold=0.01,
                 sellThreshold=0.01
                 ):
        self.vwapBuy = vwapBuy
        self.vwapSell = vwapSell
        self.stopLoss = stopLoss
        self.waitAfterLoss = waitAfterLoss
        self.vwapWindow = vwapWindow
        self.buyThreshold = buyThreshold
        self.sellThreshold = sellThreshold

class Algorithm:
    def __init__(self, first100Highs, first100Lows, first100Closes, first100Volumes, configuration): 
        self.highs = deque(first100Highs, maxlen=100)
        self.lows = deque(first100Lows, maxlen=100)
        self.closes = deque(first100Closes, maxlen=100)
        self.volumes = deque(first100Volumes, maxlen=100)
        self.timeSinceLoss = 0
        self.typicals = [(high + low + close) / 3 for high, low, close in zip(self.highs, self.lows, self.closes)]
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, configuration.vwapWindow)
        self.configuration = configuration
    
    def inform(self, newHigh, newLow, newClose, newVolume):
        self.highs.append(newHigh)
        self.lows.append(newLow)
        self.closes.append(newClose)
        self.volumes.append(newVolume)
        self.typicals = [(high + low + close) / 3 for high, low, close in zip(self.highs, self.lows, self.closes)]
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, self.configuration.vwapWindow)
        if self.timeSinceLoss:
            self.timeSinceLoss += 1

    def shouldBuy(self):
        # Check if price is below VWAP threshold and if wait period after a loss has passed
        if (self.vwap >= (1 - self.configuration.buyThreshold) * self.closes[-1] and 
                (not self.timeSinceLoss or self.timeSinceLoss >= self.configuration.waitAfterLoss)):
            self.timeSinceLoss = 0
            return True
        return False

    def shouldSell(self, purchasePrice):
        # Check if price is above VWAP threshold or if it hits stop loss
        if (self.vwap * (1 + self.configuration.sellThreshold) <= self.closes[-1] or
                (self.configuration.stopLoss and self.closes[-1] <= purchasePrice * self.configuration.stopLoss)):
            return True
        return False

    def calculate_vwap(self, volumes, typicals, window):
        total_volume = numpy.sum(volumes[-window:])
        if total_volume == 0:
            return 0
        return numpy.sum(numpy.multiply(typicals[-window:], volumes[-window:])) / total_volume

        