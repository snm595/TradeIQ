"""
Shared research pipeline.

All validation and paper-trading tools call this module so research results use
the same deterministic engine sequence as the live API.
"""

from __future__ import annotations

import pandas as pd

from engines import (
    backtest_engine,
    confidence_engine,
    continuation_engine,
    data_engine,
    indicator_engine,
    regime_engine,
    signal_engine,
)


def analyze_frame(df: pd.DataFrame, ticker: str, htf_period: str = "2y") -> tuple[pd.DataFrame, dict]:
    htf_df = data_engine.fetch_higher_timeframe(ticker, period=htf_period)
    analyzed = indicator_engine.compute_all(df)
    analyzed = regime_engine.classify_regime(analyzed)
    analyzed = continuation_engine.compute_continuation_quality(analyzed)
    analyzed = signal_engine.generate_signals(analyzed)
    analyzed = confidence_engine.score_signals(analyzed, htf_df)
    metrics = backtest_engine.run_backtest(analyzed)
    return analyzed, metrics


def fetch_and_analyze(ticker: str, timeframe: str, period: str) -> tuple[pd.DataFrame, dict]:
    df = data_engine.fetch_ohlcv(ticker, timeframe=timeframe, period=period, use_cache=False)
    return analyze_frame(df, ticker)
