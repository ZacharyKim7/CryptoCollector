from cryptocollector import config


class RegimeConfig:
    def __init__(
        self,
        atrWindow=config.REGIME_ATR_WINDOW,
        minAtrPct=config.REGIME_MIN_ATR_PCT,
        adxWindow=config.REGIME_ADX_WINDOW,
        maxAdx=config.REGIME_MAX_ADX,
    ):
        self.atrWindow = atrWindow
        self.minAtrPct = minAtrPct
        self.adxWindow = adxWindow
        self.maxAdx = maxAdx


class RegimeDetector:
    """Flags whether a coin is currently in the target trading regime: both
    volatile (ATR% above a floor) and range-bound/sideways (ADX below a
    ceiling). Mirrors Algorithm's rolling-window inform() pattern so it can
    be driven candle-by-candle alongside the strategy in both the backtest
    engine and the live paper trader.

    ATR and ADX are maintained as true Wilder-smoothed running values (O(1)
    per candle after a one-time seed from the initial window) rather than
    recomputed from scratch each step - this is what makes grid-searching
    thousands of configs across a full history tractable.
    """

    def __init__(self, firstHighs, firstLows, firstCloses, configuration: RegimeConfig):
        self.highs = list(map(float, firstHighs))
        self.lows = list(map(float, firstLows))
        self.closes = list(map(float, firstCloses))
        self.configuration = configuration

        self._atr = self._seed_atr(configuration.atrWindow)
        self.atr_pct = self._atr / self.closes[-1]

        self._smoothedTR, self._smoothedPlusDM, self._smoothedMinusDM, self.adx = self._seed_adx(configuration.adxWindow)

    def inform(self, newHigh, newLow, newClose):
        prevHigh, prevLow, prevClose = self.highs[-1], self.lows[-1], self.closes[-1]

        self._update_atr(prevClose, newHigh, newLow, newClose)
        self._update_adx(prevHigh, prevLow, prevClose, newHigh, newLow, newClose)

        window = max(self.configuration.atrWindow, self.configuration.adxWindow) + 1
        self.highs = (self.highs + [newHigh])[-window:]
        self.lows = (self.lows + [newLow])[-window:]
        self.closes = (self.closes + [newClose])[-window:]

    def is_volatile(self) -> bool:
        return bool(self.atr_pct >= self.configuration.minAtrPct)

    def is_sideways(self) -> bool:
        return bool(self.adx <= self.configuration.maxAdx)

    def is_active(self) -> bool:
        return self.is_volatile() and self.is_sideways()

    @staticmethod
    def _true_range(high, low, prevClose):
        return max(high - low, abs(high - prevClose), abs(low - prevClose))

    def _true_ranges(self):
        return [self._true_range(self.highs[i], self.lows[i], self.closes[i - 1]) for i in range(1, len(self.closes))]

    def _seed_atr(self, window):
        trs = self._true_ranges()[-window:]
        return sum(trs) / window

    def _update_atr(self, prevClose, newHigh, newLow, newClose):
        window = self.configuration.atrWindow
        tr = self._true_range(newHigh, newLow, prevClose)
        self._atr = (self._atr * (window - 1) + tr) / window
        self.atr_pct = self._atr / newClose

    def _directional_moves(self):
        trs, plusDMs, minusDMs = [], [], []
        for i in range(1, len(self.closes)):
            trs.append(self._true_range(self.highs[i], self.lows[i], self.closes[i - 1]))
            up = self.highs[i] - self.highs[i - 1]
            down = self.lows[i - 1] - self.lows[i]
            plusDMs.append(up if (up > down and up > 0) else 0.0)
            minusDMs.append(down if (down > up and down > 0) else 0.0)
        return trs, plusDMs, minusDMs

    def _seed_adx(self, window):
        trs, plusDMs, minusDMs = self._directional_moves()

        smoothedTR = sum(trs[:window])
        smoothedPlusDM = sum(plusDMs[:window])
        smoothedMinusDM = sum(minusDMs[:window])

        dxValues = []
        for i in range(window, len(trs)):
            smoothedTR = smoothedTR - smoothedTR / window + trs[i]
            smoothedPlusDM = smoothedPlusDM - smoothedPlusDM / window + plusDMs[i]
            smoothedMinusDM = smoothedMinusDM - smoothedMinusDM / window + minusDMs[i]
            dxValues.append(self._dx(smoothedPlusDM, smoothedMinusDM, smoothedTR))

        if dxValues:
            initialCount = min(window, len(dxValues))
            adx = sum(dxValues[:initialCount]) / initialCount
            for dx in dxValues[initialCount:]:
                adx = (adx * (window - 1) + dx) / window
        else:
            adx = 0.0

        return smoothedTR, smoothedPlusDM, smoothedMinusDM, adx

    def _update_adx(self, prevHigh, prevLow, prevClose, newHigh, newLow, newClose):
        window = self.configuration.adxWindow
        tr = self._true_range(newHigh, newLow, prevClose)
        up = newHigh - prevHigh
        down = prevLow - newLow
        plusDM = up if (up > down and up > 0) else 0.0
        minusDM = down if (down > up and down > 0) else 0.0

        self._smoothedTR = self._smoothedTR - self._smoothedTR / window + tr
        self._smoothedPlusDM = self._smoothedPlusDM - self._smoothedPlusDM / window + plusDM
        self._smoothedMinusDM = self._smoothedMinusDM - self._smoothedMinusDM / window + minusDM

        dx = self._dx(self._smoothedPlusDM, self._smoothedMinusDM, self._smoothedTR)
        self.adx = (self.adx * (window - 1) + dx) / window

    @staticmethod
    def _dx(smoothedPlusDM, smoothedMinusDM, smoothedTR):
        plusDI = 100 * smoothedPlusDM / smoothedTR if smoothedTR else 0.0
        minusDI = 100 * smoothedMinusDM / smoothedTR if smoothedTR else 0.0
        diSum = plusDI + minusDI
        return 100 * abs(plusDI - minusDI) / diSum if diSum else 0.0
