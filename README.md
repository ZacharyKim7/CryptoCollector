# CryptoCollector

An automated crypto swing-trading bot for Coinbase, built around one specific, deliberately narrow idea: **only trade a coin when it's both volatile and moving sideways.**

This isn't an attempt to beat the market in all conditions. It automates a manual strategy that worked on Cardano (ADA) — buying and selling within a stable trading range (e.g. $0.18–$0.25) over several months, without trying to predict breakouts or trends. A regime filter gates an existing mean-reversion strategy: trades only fire while the coin is classified as range-bound, and exits/stop-losses are never blocked by regime state.

This round of work is **backtesting and paper trading only** — no real orders are placed.

## Architecture

```
cryptocollector/
  config.py            # API keys, watchlist, granularity, thresholds
  data/                 # Coinbase candle fetching + SQLite cache
  strategy/             # Algorithm (VWAP/MA/RSI), RegimeDetector (ATR%/ADX), shared decision logic
  backtest/             # Simulated portfolio, backtest engine, metrics, grid search
  live/                 # Persistent paper-trading loop (simulated fills only)
  cli/                   # Entry points, see below
tests/                  # pytest unit tests
```

**Regime detection** (`strategy/regime.py`): a coin is "active" when it's both volatile (ATR% above a floor) and sideways (ADX below a ceiling). Both thresholds are tuned via backtesting, not hand-set.

**Strategy** (`strategy/algorithm.py`): the original VWAP/MA/RSI mean-reversion logic — buy when price dips meaningfully below its rolling VWAP/MA or RSI shows oversold, sell on the reverse or a stop loss.

**Data**: Coinbase's public API has no native 4-hour candle granularity, so the cache stores native 2-hour candles and resamples pairs into synthetic 4-hour bars (`data/cache.py`), which is the timeframe the regime detector and strategy operate on.

## Setup

Dependencies and the virtual environment are managed with [uv](https://docs.astral.sh/uv/):

```
uv sync
```

This creates `.venv/` and installs exactly what's pinned in `uv.lock`. Requires a Coinbase API key/secret in a `.env` file at the repo root:

```
API_KEY=...
API_SECRET=...
```

Edit `cryptocollector/config.py` to set your watchlist (`WATCHLIST`) and any threshold defaults.

## Usage

```
uv run python -m cryptocollector.cli.fetch_data       # backfill/update the local candle cache for the watchlist
uv run python -m cryptocollector.cli.run_backtest     # grid-search strategy+regime configs per symbol, writes backtest_results/*.csv
uv run python -m cryptocollector.cli.run_paper_trader # run the persistent paper-trading loop (simulated fills only, no real orders)
```

`run_paper_trader` picks up each symbol's best config from the most recent `run_backtest` CSV automatically; if none exists yet, it falls back to the defaults in `config.py`.

## Tests

```
uv run pytest tests/
```

To add a new dependency: `uv add <package>` (or `uv add --dev <package>` for dev-only tools like pytest) — this updates `pyproject.toml` and `uv.lock` together.

## Out of scope (for now)

Real order execution, live account trading, walk-forward/train-test validation of grid search results, and auto-scanning beyond a manually curated watchlist are all deliberately deferred — see the project plan for the full reasoning.
