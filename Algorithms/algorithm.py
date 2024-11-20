import numpy
import ta
import ta.momentum

class AlgorithmConfiguration:
    def __init__(self, 
                vwapBuy=False, 
                maBuy=False,
                rsiBuy=False,
                vwapSell=False,
                maSell=False,
                rsiSell=False,
                stopLoss=False,
                waitAfterLoss=0,
                vwapWindow=60,
                maWindow=60,
                rsiWindow=14,
                ):   
        self.vwapBuy=vwapBuy
        self.maBuy=maBuy
        self.rsiBuy=rsiBuy
        self.vwapSell=vwapSell
        self.maSell=maSell
        self.rsiSell=rsiSell
        self.stopLoss=stopLoss
        self.waitAfterLoss=waitAfterLoss
        self.vwapWindow=vwapWindow
        self.maWindow=maWindow
        self.rsiWindow=rsiWindow

class Algorithm:
    def __init__(self, first100Highs, first100Lows, first100Closes, first100Volumes, configuration): 
        self.highs = first100Highs
        self.lows = first100Lows
        self.closes = first100Closes
        self.volumes = first100Volumes
        self.timeSinceLoss = 0
        self.typicals = [(high + low + close) / 3 for high, low, close in zip(self.highs, self.lows, self.closes)]
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, configuration.vwapWindow)
        self.ma = self.calculate_ma(configuration.maWindow)[-1]
        self.rsi = self.calculate_rsi(configuration.rsiWindow)
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
        self.ma = self.calculate_ma(self.configuration.maWindow)[-1]
        self.rsi = self.calculate_rsi(self.configuration.rsiWindow)
        if self.timeSinceLoss:
            self.timeSinceLoss += 1

    def shouldBuy(self):
        # Buy when the current close sinks deep below the vwap

        vwapCheck = not self.configuration.vwapBuy or self.vwap >= self.configuration.vwapBuy * self.closes[-1]
        maCheck = not self.configuration.maBuy or self.ma >= self.configuration.maBuy * self.closes[-1]
        rsiCheck = not self.configuration.rsiBuy or self.rsi <= self.configuration.rsiBuy

        waitAfterLossCheck = not self.timeSinceLoss or self.timeSinceLoss >= self.configuration.waitAfterLoss
        if waitAfterLossCheck:
            self.timeSinceLoss = 0
        
        if vwapCheck and maCheck and rsiCheck and waitAfterLossCheck:
            return True
        else:
            return False
        
    def shouldSell(self, purchasePrice):
        # Sell when the current close approaches the vwap

        vwapCheck = not self.configuration.vwapSell or self.vwap * self.configuration.vwapSell <= self.closes[-1]
        maCheck = not self.configuration.maSell or self.ma * self.configuration.maSell <= self.closes[-1]
        rsiCheck = not self.configuration.rsiSell or self.rsi >= self.configuration.rsiSell

        if vwapCheck and maCheck and rsiCheck:
            return True
        elif self.configuration.stopLoss and self.closes[-1] <= purchasePrice * self.configuration.stopLoss:
            return True
        else:
            return False

    def calculate_vwap(self, volumes, typicals, window):
        return numpy.sum(numpy.multiply(typicals[-(window):], volumes[-(window):]))/ numpy.sum(volumes[-(window):])
    
    def calculate_ma(self, window):
        weights = numpy.repeat(1.0, window) / window
        ma = numpy.convolve(self.closes, weights, 'valid')
        return ma
    
    def calculate_rsi(self, window):
        delta = [self.closes[i] - self.closes[i-1] for i in range(1, len(self.closes))]
        gain = [delta[i] if delta[i] > 0 else 0 for i in range(len(delta))]
        loss = [-delta[i] if delta[i] < 0 else 0 for i in range(len(delta))]
        
        avg_gain = sum(gain[:window]) / window
        avg_loss = sum(loss[:window]) / window
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi