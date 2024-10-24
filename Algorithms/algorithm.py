import numpy

class AlgorithmConfiguration:
    def __init__(self, 
                vwapBuy=False, 
                vwapSell=False,
                stopLoss=False,
                waitAfterLoss=0,
                vwapWindow=60,
                ):   
        self.vwapBuy=vwapBuy
        self.vwapSell=vwapSell
        self.stopLoss=stopLoss
        self.waitAfterLoss=waitAfterLoss
        self.vwapWindow=vwapWindow

class Algorithm:
    def __init__(self, first100Highs, first100Lows, first100Closes, first100Volumes, configuration): 
        self.highs = first100Highs
        self.lows = first100Lows
        self.closes = first100Closes
        self.volumes = first100Volumes
        self.timeSinceLoss = 0
        self.typicals = [(high + low + close) / 3 for high, low, close in zip(self.highs, self.lows, self.closes)]
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, configuration.vwapWindow)
        self.configuration = configuration
    
    def inform(self, newHigh, newLow, newClose, newVolume):
        self.highs = numpy.append(self.highs, newHigh)
        self.highs = self.highs[1:]
        self.lows = numpy.append(self.lows, newLow)
        self.lows = self.lows[1:]
        self.closes = numpy.append(self.closes, newClose)
        self.closes = self.closes[1:]
        self.volumes = numpy.append(self.volumes, newVolume)
        self.volumes = self.volumes[1:]
        self.typicals = [(high + low + close) / 3 for high, low, close in zip(self.highs, self.lows, self.closes)]
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, self.configuration.vwapWindow)
        if self.timeSinceLoss:
            self.timeSinceLoss += 1

    def shouldBuy(self):
        # Buy when the current close sinks 1% below the VWAP
        vwapCheck = self.vwap >= (1 - 0.01) * self.closes[-1]

        waitAfterLossCheck = not self.timeSinceLoss or self.timeSinceLoss >= self.configuration.waitAfterLoss
        if waitAfterLossCheck:
            self.timeSinceLoss = 0

        if vwapCheck and waitAfterLossCheck:
            return True
        else:
            return False
        
    def shouldSell(self, purchasePrice):
        # Sell when the current close is 1% above the VWAP
        vwapCheck = self.vwap * (1 + 0.01) <= self.closes[-1]

        if vwapCheck:
            return True
        elif self.configuration.stopLoss and self.closes[-1] <= purchasePrice * self.configuration.stopLoss:
            return True
        else:
            return False

    def calculate_vwap(self, volumes, typicals, window):
        return numpy.sum(numpy.multiply(typicals[-(window):], volumes[-(window):]))/ numpy.sum(volumes[-(window):])
    