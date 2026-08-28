from cryptocollector import config
from cryptocollector.backtest.engine import BacktestResult


def compute_metrics(result: BacktestResult) -> dict:
    portfolio = result.portfolio
    equity_curve = result.equity_curve

    initial_value = config.STARTING_BALANCE
    final_value = equity_curve[-1] if equity_curve else initial_value
    total_return_pct = (final_value / initial_value - 1) * 100 if initial_value else 0.0

    completed_trades = portfolio.totalWins + portfolio.totalLoss
    win_rate = (portfolio.totalWins / completed_trades * 100) if completed_trades else 0.0

    return {
        "symbol": result.symbol,
        "total_return_pct": total_return_pct,
        "win_rate_pct": win_rate,
        "max_drawdown_pct": _max_drawdown(equity_curve),
        "time_in_regime_pct": _mean_pct(result.regime_active_flags),
        "time_in_market_pct": _mean_pct(result.holding_flags),
        "num_trades": portfolio.totalTrades,
        "num_completed_trades": completed_trades,
        "profit_factor": _profit_factor(result),
    }


def _mean_pct(flags: list[bool]) -> float:
    return (sum(flags) / len(flags) * 100) if flags else 0.0


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak * 100)
    return max_dd


def _profit_factor(result: BacktestResult) -> float:
    gross_profit = 0.0
    gross_loss = 0.0
    open_price = None
    for trade in result.trades:
        if trade.side == "BUY":
            open_price = trade.price
        elif trade.side == "SELL" and open_price is not None:
            pnl = trade.price - open_price
            if pnl >= 0:
                gross_profit += pnl
            else:
                gross_loss += -pnl
            open_price = None
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss
