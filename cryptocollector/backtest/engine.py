from dataclasses import dataclass, field

import pandas as pd

from cryptocollector.backtest.portfolio import SimulatedPortfolio
from cryptocollector.strategy.algorithm import Algorithm, AlgorithmConfiguration
from cryptocollector.strategy.decision import evaluate
from cryptocollector.strategy.regime import RegimeConfig, RegimeDetector

SEED_LENGTH = 100


@dataclass
class Trade:
    side: str  # "BUY" or "SELL"
    price: float
    index: int
    timestamp: int | None = None
    vwap: float | None = None
    ma: float | None = None
    rsi: float | None = None


@dataclass
class BacktestResult:
    symbol: str
    algoConfig: AlgorithmConfiguration
    regimeConfig: RegimeConfig
    portfolio: SimulatedPortfolio
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    regime_active_flags: list[bool] = field(default_factory=list)
    holding_flags: list[bool] = field(default_factory=list)


class BacktestEngine:
    """Replays the regime filter + strategy over historical candles for one
    symbol/config. Mirrors the per-candle loop shape of the original
    Backtesting/backtest.py::thread_function, but delegates the buy/sell
    decision to strategy.decision.evaluate() so the exact same logic can be
    reused by the live paper trader.
    """

    def __init__(self, algoConfig: AlgorithmConfiguration, regimeConfig: RegimeConfig, symbol: str = "", portfolio_kwargs: dict | None = None):
        self.algoConfig = algoConfig
        self.regimeConfig = regimeConfig
        self.symbol = symbol
        self.portfolio_kwargs = portfolio_kwargs or {}

    def run(self, candles: pd.DataFrame, seed_length: int = SEED_LENGTH) -> BacktestResult:
        if len(candles) <= seed_length:
            raise ValueError(f"Need more than {seed_length} candles to backtest, got {len(candles)}")

        highs = candles["high"].to_numpy()
        lows = candles["low"].to_numpy()
        closes = candles["close"].to_numpy()
        volumes = candles["volume"].to_numpy()
        timestamps = candles["start_ts"].to_numpy() if "start_ts" in candles.columns else None

        algorithm = Algorithm(highs[:seed_length], lows[:seed_length], closes[:seed_length], volumes[:seed_length], self.algoConfig)
        regime = RegimeDetector(highs[:seed_length], lows[:seed_length], closes[:seed_length], self.regimeConfig)
        portfolio = SimulatedPortfolio(**self.portfolio_kwargs)

        result = BacktestResult(symbol=self.symbol, algoConfig=self.algoConfig, regimeConfig=self.regimeConfig, portfolio=portfolio)

        for i in range(seed_length, len(closes)):
            algorithm.inform(highs[i], lows[i], closes[i], volumes[i])
            regime.inform(highs[i], lows[i], closes[i])

            preSellPurchasePrice = portfolio.purchasePrice
            decision = evaluate(regime, algorithm, portfolio.holding, portfolio.purchasePrice)
            ts = int(timestamps[i]) if timestamps is not None else None

            if decision == "BUY" and portfolio.buyShares(closes[i]):
                result.trades.append(Trade("BUY", closes[i], i, ts, algorithm.vwap, algorithm.ma, algorithm.rsi))
            elif decision == "SELL" and portfolio.sellShares(closes[i]):
                result.trades.append(Trade("SELL", closes[i], i, ts, algorithm.vwap, algorithm.ma, algorithm.rsi))
                if self.algoConfig.stopLoss and closes[i] < preSellPurchasePrice * self.algoConfig.stopLoss:
                    algorithm.timeSinceLoss += 1

            result.equity_curve.append(portfolio.portfolioValue(closes[i]))
            result.regime_active_flags.append(regime.is_active())
            result.holding_flags.append(portfolio.holding)

        return result
