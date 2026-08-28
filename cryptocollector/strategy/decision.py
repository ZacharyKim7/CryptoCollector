from cryptocollector.strategy.algorithm import Algorithm
from cryptocollector.strategy.regime import RegimeDetector


def evaluate(regime: RegimeDetector, algorithm: Algorithm, holding: bool, purchasePrice: float) -> str:
    """Single BUY/SELL/HOLD decision shared by the backtest engine and the
    live paper trader, so both run the exact same logic.

    Buys only fire while the regime is active (volatile + sideways).
    Sells/stop-losses are NEVER gated by regime state: if a held coin breaks
    out of its range, the strategy must still be able to exit.
    """
    if holding:
        if algorithm.shouldSell(purchasePrice):
            return "SELL"
        return "HOLD"

    if regime.is_active() and algorithm.shouldBuy():
        return "BUY"
    return "HOLD"
