import logging
import time

import pandas as pd

from cryptocollector import config
from cryptocollector.backtest.engine import SEED_LENGTH
from cryptocollector.data.cache import CandleCache
from cryptocollector.data.coinbase_client import make_client
from cryptocollector.live.state_store import StateStore
from cryptocollector.strategy.algorithm import Algorithm, AlgorithmConfiguration
from cryptocollector.strategy.decision import evaluate
from cryptocollector.strategy.regime import RegimeConfig, RegimeDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _completed_candles(candles: pd.DataFrame, timeframe: str, buffer_seconds: int = 300) -> pd.DataFrame:
    """Drop the trailing resampled bar(s) that haven't fully closed yet, so
    the trader never acts on a still-forming 4h candle."""
    if candles.empty:
        return candles
    bin_seconds = pd.Timedelta(timeframe).total_seconds()
    now = time.time()
    cutoff = now - buffer_seconds
    return candles[candles["start_ts"] + bin_seconds <= cutoff]


class PaperTraderSymbol:
    def __init__(
        self,
        symbol: str,
        client,
        cache: CandleCache,
        state_store: StateStore,
        algoConfig: AlgorithmConfiguration,
        regimeConfig: RegimeConfig,
        tradeAmount: float = config.TRADE_AMOUNT,
    ):
        self.symbol = symbol
        self.client = client
        self.cache = cache
        self.state_store = state_store
        self.algoConfig = algoConfig
        self.tradeAmount = tradeAmount
        self.last_seen_ts: int | None = None

        cache.fetch_and_update(symbol, client)
        seed_candles = _completed_candles(cache.get_candles(symbol), config.TARGET_TIMEFRAME)
        if len(seed_candles) < SEED_LENGTH:
            raise ValueError(f"Not enough completed {config.TARGET_TIMEFRAME} candles cached for {symbol} to seed the strategy")

        seed = seed_candles.iloc[-SEED_LENGTH:]
        highs, lows, closes, volumes = seed["high"].to_numpy(), seed["low"].to_numpy(), seed["close"].to_numpy(), seed["volume"].to_numpy()

        self.algorithm = Algorithm(highs, lows, closes, volumes, algoConfig)
        self.regime = RegimeDetector(highs, lows, closes, regimeConfig)
        self.last_seen_ts = int(seed["start_ts"].iloc[-1])

        position = state_store.load_position(symbol)
        if position:
            self.holding = position["holding"]
            self.purchasePrice = position["purchase_price"]
            self.quantity = position["quantity"]
            logger.info(f"{symbol}: restored state - holding={self.holding} purchasePrice={self.purchasePrice}")
        else:
            self.holding = False
            self.purchasePrice = 0.0
            self.quantity = 0.0

    def poll_once(self) -> None:
        self.cache.fetch_and_update(self.symbol, self.client)
        candles = _completed_candles(self.cache.get_candles(self.symbol), config.TARGET_TIMEFRAME)
        new_candles = candles[candles["start_ts"] > self.last_seen_ts]

        for _, candle in new_candles.iterrows():
            self._on_new_candle(candle)
            self.last_seen_ts = int(candle["start_ts"])

    def _on_new_candle(self, candle) -> None:
        high, low, close, volume = candle["high"], candle["low"], candle["close"], candle["volume"]
        self.algorithm.inform(high, low, close, volume)
        self.regime.inform(high, low, close)

        decision = evaluate(self.regime, self.algorithm, self.holding, self.purchasePrice)
        ts = int(candle["start_ts"])

        if decision == "BUY":
            fee = self.tradeAmount * config.MAKER_FEES
            self.quantity = (self.tradeAmount - fee) / close
            self.purchasePrice = close
            self.holding = True
            self.state_store.record_trade(self.symbol, "BUY", close, self.quantity, fee, ts)
            self.state_store.save_position(self.symbol, self.holding, self.purchasePrice, self.quantity)
            logger.info(f"{self.symbol}: SIMULATED BUY at {close}")

        elif decision == "SELL":
            fee = self.quantity * close * config.MAKER_FEES
            self.state_store.record_trade(self.symbol, "SELL", close, self.quantity, fee, ts)
            logger.info(f"{self.symbol}: SIMULATED SELL at {close} (bought at {self.purchasePrice})")
            self.holding = False
            self.quantity = 0.0
            self.purchasePrice = 0.0
            self.state_store.save_position(self.symbol, self.holding, self.purchasePrice, self.quantity)


def run(algo_configs: dict[str, AlgorithmConfiguration], regime_configs: dict[str, RegimeConfig]) -> None:
    """Poll each symbol in the watchlist on an interval and paper-trade it.
    algo_configs/regime_configs map symbol -> config (e.g. the winning
    result from cli/run_backtest.py's grid search for that symbol)."""
    client = make_client()
    cache = CandleCache()
    state_store = StateStore()

    traders = {
        symbol: PaperTraderSymbol(symbol, client, cache, state_store, algo_configs[symbol], regime_configs[symbol])
        for symbol in config.WATCHLIST
    }
    logger.info(f"Paper trader started for {list(traders.keys())}")

    while True:
        for symbol, trader in traders.items():
            try:
                trader.poll_once()
            except Exception:
                logger.exception(f"Error polling {symbol}")
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    from cryptocollector.strategy.algorithm import AlgorithmConfiguration as _AlgoCfg
    from cryptocollector.strategy.regime import RegimeConfig as _RegimeCfg

    default_algo = _AlgoCfg(
        vwapBuy=config.ALGO_VWAP_BUY,
        vwapSell=config.ALGO_VWAP_SELL,
        stopLoss=config.ALGO_STOP_LOSS,
        vwapWindow=config.ALGO_VWAP_WINDOW,
        waitAfterLoss=config.ALGO_WAIT_AFTER_LOSS,
    )
    default_regime = _RegimeCfg()
    run({s: default_algo for s in config.WATCHLIST}, {s: default_regime for s in config.WATCHLIST})
