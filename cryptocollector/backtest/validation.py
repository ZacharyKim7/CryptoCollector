import pandas as pd

from cryptocollector.backtest.engine import BacktestEngine
from cryptocollector.backtest.grid_search import run_grid_search
from cryptocollector.backtest.metrics import compute_metrics
from cryptocollector.strategy.algorithm import AlgorithmConfiguration
from cryptocollector.strategy.regime import RegimeConfig

DEFAULT_TOP_N = 20
DEFAULT_TEST_FRACTION = 0.2


def train_test_split(candles: pd.DataFrame, test_fraction: float = DEFAULT_TEST_FRACTION) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological (not random) split, since shuffling time-series candles
    would let the model 'see the future' during training."""
    split_idx = int(len(candles) * (1 - test_fraction))
    return candles.iloc[:split_idx].reset_index(drop=True), candles.iloc[split_idx:].reset_index(drop=True)


def evaluate_on(symbol: str, algoConfig: AlgorithmConfiguration, regimeConfig: RegimeConfig, candles: pd.DataFrame) -> dict | None:
    engine = BacktestEngine(algoConfig, regimeConfig, symbol=symbol)
    try:
        result = engine.run(candles)
    except ValueError:
        return None
    return compute_metrics(result)


def run_validated_grid_search(
    symbol: str,
    candles: pd.DataFrame,
    algo_grid: list[AlgorithmConfiguration] | None = None,
    regime_grid: list[RegimeConfig] | None = None,
    top_n: int = DEFAULT_TOP_N,
    test_fraction: float = DEFAULT_TEST_FRACTION,
) -> list[dict]:
    """Grid-search on the training slice only, then re-evaluate the top N
    training winners on a held-out test slice they never saw. A config that
    was genuinely finding an edge should hold up reasonably well out of
    sample; a config that was just curve-fit to training noise will
    typically collapse toward (or below) zero on the test slice. Ranks the
    combined results by TEST return, not train return, so an overfit
    training winner can't silently outrank a config that actually
    generalizes.
    """
    train_candles, test_candles = train_test_split(candles, test_fraction)

    train_results = run_grid_search(symbol, train_candles, algo_grid=algo_grid, regime_grid=regime_grid)
    top_candidates = train_results[:top_n]

    combined = []
    for train_metrics in top_candidates:
        algoConfig = train_metrics["algoConfig"]
        regimeConfig = train_metrics["regimeConfig"]

        test_metrics = evaluate_on(symbol, algoConfig, regimeConfig, test_candles)
        if test_metrics is None:
            continue

        row = {"symbol": symbol, "algoConfig": algoConfig, "regimeConfig": regimeConfig}
        row.update({f"train_{k}": v for k, v in train_metrics.items() if k not in ("symbol", "algoConfig", "regimeConfig")})
        row.update({f"test_{k}": v for k, v in test_metrics.items() if k not in ("symbol", "algoConfig", "regimeConfig")})
        combined.append(row)

    combined.sort(key=lambda r: r["test_total_return_pct"], reverse=True)
    return combined
