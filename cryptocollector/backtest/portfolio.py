from cryptocollector import config


class SimulatedPortfolio:
    """Single-position simulated account. Adapted from the original
    Backtesting/backtest.py::TestUser, plus optional slippage on fills."""

    def __init__(self, balance=config.STARTING_BALANCE, tradeAmount=config.TRADE_AMOUNT, slippagePct=config.SLIPPAGE_PCT):
        self.balance = balance
        self.tradeAmount = tradeAmount
        self.slippagePct = slippagePct
        self.shares = 0.0
        self.holding = False
        self.purchasePrice = 0.0
        self.totalTrades = 0
        self.totalWins = 0
        self.totalLoss = 0

    def buyShares(self, price: float) -> bool:
        if self.holding:
            return False
        fillPrice = price * (1 + self.slippagePct)
        self.purchasePrice = fillPrice
        tradeAmountAfterFees = self.tradeAmount - self.tradeAmount * config.MAKER_FEES
        self.shares += tradeAmountAfterFees / fillPrice
        self.balance -= self.tradeAmount
        self.holding = True
        self.totalTrades += 1
        return True

    def sellShares(self, price: float) -> bool:
        if not self.holding:
            return False
        fillPrice = price * (1 - self.slippagePct)
        self.balance += self.shares * fillPrice
        self.shares = 0.0
        self.holding = False
        if self.purchasePrice >= fillPrice:
            self.totalLoss += 1
        else:
            self.totalWins += 1
        return True

    def portfolioValue(self, price: float) -> float:
        return self.balance + price * self.shares
