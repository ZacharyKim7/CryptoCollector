import numpy


class AlgorithmConfiguration:
    def __init__(
        self,
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
        self.vwapBuy = vwapBuy
        self.maBuy = maBuy
        self.rsiBuy = rsiBuy
        self.vwapSell = vwapSell
        self.maSell = maSell
        self.rsiSell = rsiSell
        self.stopLoss = stopLoss
        self.waitAfterLoss = waitAfterLoss
        self.vwapWindow = vwapWindow
        self.maWindow = maWindow
        self.rsiWindow = rsiWindow


class Algorithm:
    """Stateful mean-reversion strategy driven candle-by-candle via inform().

    RSI is maintained as a true Wilder-smoothed running average (seeded once
    from the initial window, then updated in O(1) per candle) rather than
    recomputed from the whole rolling buffer on every call. The original
    version's RSI was both wrong (averaged the OLDEST window of the rolling
    buffer instead of the trailing one) and, when later ported to recompute
    via a library on every step, far too slow to grid-search across
    thousands of configs. This fixes both: correct AND O(1) per step, which
    matters because this same inform() loop drives both the backtest engine
    and the live paper trader.
    """

    def __init__(self, first100Highs, first100Lows, first100Closes, first100Volumes, configuration):
        self.highs = numpy.array(first100Highs, dtype=float)
        self.lows = numpy.array(first100Lows, dtype=float)
        self.closes = numpy.array(first100Closes, dtype=float)
        self.volumes = numpy.array(first100Volumes, dtype=float)
        self.timeSinceLoss = 0
        self.configuration = configuration
        self.typicals = self._calculate_typicals()
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, configuration.vwapWindow)
        self.ma = self.calculate_ma(configuration.maWindow)[-1]
        self._rsiAvgGain, self._rsiAvgLoss = self._seed_rsi(configuration.rsiWindow)
        self.rsi = self._rsi_from_averages(self._rsiAvgGain, self._rsiAvgLoss)

    def inform(self, newHigh, newLow, newClose, newVolume):
        prevClose = self.closes[-1]

        self.highs = numpy.append(self.highs, newHigh)[1:]
        self.lows = numpy.append(self.lows, newLow)[1:]
        self.closes = numpy.append(self.closes, newClose)[1:]
        self.volumes = numpy.append(self.volumes, newVolume)[1:]
        self.typicals = self._calculate_typicals()
        self.vwap = self.calculate_vwap(self.volumes, self.typicals, self.configuration.vwapWindow)
        self.ma = self.calculate_ma(self.configuration.maWindow)[-1]
        self._update_rsi(prevClose, newClose)

        if self.timeSinceLoss:
            self.timeSinceLoss += 1

    def shouldBuy(self):
        # Buy when the current close sinks deep below the vwap/ma, or RSI shows oversold.
        vwapCheck = not self.configuration.vwapBuy or self.vwap >= self.configuration.vwapBuy * self.closes[-1]
        maCheck = not self.configuration.maBuy or self.ma >= self.configuration.maBuy * self.closes[-1]
        rsiCheck = not self.configuration.rsiBuy or self.rsi <= self.configuration.rsiBuy

        waitAfterLossCheck = not self.timeSinceLoss or self.timeSinceLoss >= self.configuration.waitAfterLoss
        if waitAfterLossCheck:
            self.timeSinceLoss = 0

        return bool(vwapCheck and maCheck and rsiCheck and waitAfterLossCheck)

    def shouldSell(self, purchasePrice):
        # Sell when the current close approaches/exceeds the vwap/ma, RSI shows overbought, or stop loss is hit.
        vwapCheck = not self.configuration.vwapSell or self.vwap * self.configuration.vwapSell <= self.closes[-1]
        maCheck = not self.configuration.maSell or self.ma * self.configuration.maSell <= self.closes[-1]
        rsiCheck = not self.configuration.rsiSell or self.rsi >= self.configuration.rsiSell

        if vwapCheck and maCheck and rsiCheck:
            return True
        if self.configuration.stopLoss and self.closes[-1] <= purchasePrice * self.configuration.stopLoss:
            return True
        return False

    def _calculate_typicals(self):
        return (self.highs + self.lows + self.closes) / 3

    def calculate_vwap(self, volumes, typicals, window):
        return numpy.sum(numpy.multiply(typicals[-window:], volumes[-window:])) / numpy.sum(volumes[-window:])

    def calculate_ma(self, window):
        weights = numpy.repeat(1.0, window) / window
        return numpy.convolve(self.closes, weights, "valid")

    def _seed_rsi(self, window):
        deltas = numpy.diff(self.closes[-(window + 1):])
        gains = numpy.clip(deltas, 0, None)
        losses = numpy.clip(-deltas, 0, None)
        return float(gains.mean()), float(losses.mean())

    def _update_rsi(self, prevClose, newClose):
        window = self.configuration.rsiWindow
        delta = newClose - prevClose
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        self._rsiAvgGain = (self._rsiAvgGain * (window - 1) + gain) / window
        self._rsiAvgLoss = (self._rsiAvgLoss * (window - 1) + loss) / window
        self.rsi = self._rsi_from_averages(self._rsiAvgGain, self._rsiAvgLoss)

    @staticmethod
    def _rsi_from_averages(avgGain, avgLoss):
        if avgLoss == 0:
            return 100.0
        rs = avgGain / avgLoss
        return 100 - (100 / (1 + rs))
