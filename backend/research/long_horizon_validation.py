"""
TradeIQ — Long-Horizon Validation Suite

Runs rigorous out-of-sample stress testing over multi-year periods,
walk-forward rolling window splits, rolling performance tracking,
95% confidence intervals, and year-over-year regime drift analytics.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import math
from typing import Optional
from research.pipeline import analyze_frame
from engines import data_engine


def run_long_horizon_validation(
    ticker: str = "SPY",
    timeframe: str = "1d",
    period: str = "10y"
) -> dict:
    """
    Perform long-horizon validation, walk-forward splits, rolling performance,
    confidence intervals, and regime drift analysis.
    """
    # 1. Fetch OHLCV over the specified multi-year period
    df = data_engine.fetch_ohlcv(ticker, timeframe=timeframe, period=period, use_cache=False)
    
    # 2. Run analysis pipeline
    analyzed, metrics = analyze_frame(df, ticker, htf_period="2y")
    trades = [t for t in metrics.get("trade_history", []) if t.get("status") == "taken"]

    # 3. Calculate 95% Confidence Intervals
    N = len(trades)
    win_rate_ci = (0.0, 0.0)
    expectancy_ci = (0.0, 0.0)
    
    if N > 2:
        # Win rate 95% CI (Binomial)
        p = metrics["win_rate"] / 100.0
        win_std = math.sqrt(p * (1 - p) / N)
        win_margin = 1.96 * win_std * 100.0
        win_rate_ci = (round(max(0.0, metrics["win_rate"] - win_margin), 2), 
                       round(min(100.0, metrics["win_rate"] + win_margin), 2))

        # Expectancy 95% CI (Student's t / Normal approximation)
        pnl_rs = [float(t["pnl_r"]) for t in trades]
        mean_pnl = np.mean(pnl_rs)
        std_pnl = np.std(pnl_rs, ddof=1)
        pnl_margin = 1.96 * std_pnl / math.sqrt(N)
        expectancy_ci = (round(float(mean_pnl - pnl_margin), 3), 
                         round(float(mean_pnl + pnl_margin), 3))

    # 4. Walk-Forward / Rolling Window Splits
    # Split the dataset into 5 equal sequential segments (non-overlapping / contiguous)
    segment_size = len(analyzed) // 5
    walk_forward_runs = []
    
    for idx in range(5):
        start_idx = idx * segment_size
        # Allow the final segment to capture any trailing bars
        end_idx = (idx + 1) * segment_size if idx < 4 else len(analyzed)
        segment_df = analyzed.iloc[start_idx:end_idx]
        
        if len(segment_df) > 50:
            from engines import backtest_engine
            segment_metrics = backtest_engine.run_backtest(segment_df)
            start_date = str(segment_df.index.min().strftime('%Y-%m-%d'))
            end_date = str(segment_df.index.max().strftime('%Y-%m-%d'))
            
            walk_forward_runs.append({
                "window": f"Period {idx + 1} ({start_date} to {end_date})",
                "trades": int(segment_metrics.get("trades_taken", 0)),
                "win_rate": float(segment_metrics.get("win_rate", 0.0)),
                "total_pnl_r": float(segment_metrics.get("total_pnl_r", 0.0)),
                "sharpe_ratio": float(segment_metrics.get("sharpe_ratio", 0.0)),
                "max_drawdown_r": float(segment_metrics.get("max_drawdown_r", 0.0))
            })

    # 5. Rolling Sharpe and Drawdown
    # Calculates a rolling 1-year window (approx. 252 trading bars for '1d', or scaled for other timeframes)
    rolling_window = 252 if timeframe == "1d" else 500
    rolling_sharpe_series = []
    rolling_drawdown_series = []
    dates_series = []
    
    if len(analyzed) > rolling_window:
        from engines import backtest_engine
        # Calculate rolling metrics at 10 intervals to avoid payload size limits
        step = max(1, (len(analyzed) - rolling_window) // 12)
        for start_pos in range(0, len(analyzed) - rolling_window, step):
            sub_df = analyzed.iloc[start_pos:start_pos + rolling_window]
            sub_metrics = backtest_engine.run_backtest(sub_df)
            date_str = str(sub_df.index.max().strftime('%Y-%m-%d'))
            
            dates_series.append(date_str)
            rolling_sharpe_series.append(float(sub_metrics.get("sharpe_ratio", 0.0)))
            rolling_drawdown_series.append(float(sub_metrics.get("max_drawdown_r", 0.0)))

    # 6. Regime Drift Analysis
    # Group by calendar year and calculate percentage distribution of regimes
    years = analyzed.index.year.unique()
    regime_drift = []
    
    for year in years:
        year_df = analyzed[analyzed.index.year == year]
        counts = year_df["regime"].value_counts(normalize=True).to_dict()
        regime_dist = {regime: round(float(counts.get(regime, 0.0)) * 100, 1) for regime in [
            "trending_up", "trending_down", "sideways", "high_volatility", 
            "low_volatility", "expansion", "compression"
        ]}
        regime_drift.append({
            "year": int(year),
            "distribution": regime_dist
        })

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "period": period,
        "sample_trades": N,
        "total_pnl_r": float(metrics.get("total_pnl_r", 0.0)),
        "win_rate": float(metrics.get("win_rate", 0.0)),
        "win_rate_ci_95": win_rate_ci,
        "expectancy_ci_95": expectancy_ci,
        "walk_forward_validation": walk_forward_runs,
        "rolling_metrics": {
            "dates": dates_series,
            "sharpe": rolling_sharpe_series,
            "drawdown": rolling_drawdown_series
        },
        "regime_drift": regime_drift
    }
