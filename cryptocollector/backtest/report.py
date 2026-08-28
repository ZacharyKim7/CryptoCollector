import pandas as pd

from cryptocollector.backtest.engine import BacktestResult


def trade_quality_report(result: BacktestResult) -> pd.DataFrame:
    """Per-round-trip trade diagnostics: how far price had deviated from
    vwap/ma at the actual entry/exit points. Ports the GoodTrade concept
    from the original Backtesting/analyzeData.py, computed against the new
    engine's trade log instead of a standalone script.
    """
    rows = []
    open_trade = None
    for trade in result.trades:
        if trade.side == "BUY":
            open_trade = trade
        elif trade.side == "SELL" and open_trade is not None:
            rows.append(
                {
                    "symbol": result.symbol,
                    "buy_index": open_trade.index,
                    "sell_index": trade.index,
                    "buy_price": open_trade.price,
                    "sell_price": trade.price,
                    "return_pct": round((trade.price - open_trade.price) / open_trade.price * 100, 2),
                    "buy_vwap_diff_pct": round((open_trade.vwap - open_trade.price) / open_trade.price * 100, 2) if open_trade.vwap else None,
                    "buy_ma_diff_pct": round((open_trade.ma - open_trade.price) / open_trade.price * 100, 2) if open_trade.ma else None,
                    "buy_rsi": round(open_trade.rsi, 2) if open_trade.rsi is not None else None,
                    "sell_vwap_diff_pct": round((trade.price - trade.vwap) / trade.vwap * 100, 2) if trade.vwap else None,
                    "sell_ma_diff_pct": round((trade.price - trade.ma) / trade.ma * 100, 2) if trade.ma else None,
                    "sell_rsi": round(trade.rsi, 2) if trade.rsi is not None else None,
                }
            )
            open_trade = None

    return pd.DataFrame(rows)
