"""
TradeIQ — Factor Ablation Research Framework

Slightly modified version of the context manager to run controlled ablation testing,
analyzing Sharpe ratio shifts, drawdown increases, trade frequency impacts,
and identifying regime leakage and factor redundancies.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from contextlib import contextmanager
import config
from engines import backtest_engine
from research.pipeline import analyze_frame
from engines import data_engine


VARIANTS = {
    "baseline": {},
    "remove_directional_efficiency": {"EXEC_MIN_DIRECTIONAL_EFFICIENCY": 0.0},
    "remove_overlap_density": {"EXEC_MAX_OVERLAP_DENSITY": 1.0},
    "remove_follow_through": {"EXEC_MIN_BREAKOUT_FOLLOW_THROUGH": 0.0},
    "remove_continuation_quality": {"EXEC_MIN_CONTINUATION_QUALITY": 0.0},
    "remove_vwap_flatness": {"EXEC_MIN_ABS_VWAP_SLOPE": 0.0},
    "remove_trend_stability": {"EXEC_MIN_TREND_STABILITY": 0.0},
    "remove_failed_breakout_veto": {"EXEC_MAX_FAILED_BREAKOUTS": 999},
    "remove_chop_score_veto": {"EXEC_MAX_CHOP_SCORE": 1.0},
}


@contextmanager
def patched_config(values: dict):
    old_values = {key: getattr(config, key) for key in values}
    for key, value in values.items():
        setattr(config, key, value)
    try:
        yield
    finally:
        for key, value in old_values.items():
            setattr(config, key, value)


def run_ablation_analysis(ticker: str = "SPY", timeframe: str = "1d", period: str = "3y") -> dict:
    """
    Schedules and runs feature-by-feature ablation across the historical dataset.
    """
    df = data_engine.fetch_ohlcv(ticker, timeframe=timeframe, period=period, use_cache=False)
    
    ablation_results = {}
    baseline_analyzed = None
    
    for variant_name, values in VARIANTS.items():
        with patched_config(values):
            analyzed, metrics = analyze_frame(df, ticker, htf_period="2y")
            trades = [t for t in metrics.get("trade_history", []) if t.get("status") == "taken"]
            
            # Count regime leakage (trades taken in sideways regime)
            leakage_count = sum(1 for t in trades if t.get("regime") == "sideways")
            
            ablation_results[variant_name] = {
                "trades": int(metrics.get("trades_taken", 0)),
                "win_rate": float(metrics.get("win_rate", 0.0)),
                "total_pnl_r": float(metrics.get("total_pnl_r", 0.0)),
                "max_drawdown_r": float(metrics.get("max_drawdown_r", 0.0)),
                "sharpe_ratio": float(metrics.get("sharpe_ratio", 0.0)),
                "regime_leakage": leakage_count
            }
            
            if variant_name == "baseline":
                baseline_analyzed = analyzed

    # Format marginal differences relative to baseline
    baseline = ablation_results["baseline"]
    marginal_contributions = []

    for name, res in ablation_results.items():
        if name == "baseline":
            continue
        
        # Marginal changes
        trades_diff = res["trades"] - baseline["trades"]
        win_rate_diff = round(res["win_rate"] - baseline["win_rate"], 2)
        pnl_diff = round(res["total_pnl_r"] - baseline["total_pnl_r"], 2)
        sharpe_diff = round(res["sharpe_ratio"] - baseline["sharpe_ratio"], 3)
        dd_diff = round(res["max_drawdown_r"] - baseline["max_drawdown_r"], 2)
        leakage_diff = res["regime_leakage"] - baseline["regime_leakage"]
        
        marginal_contributions.append({
            "variant": name,
            "filter_removed": name.replace("remove_", ""),
            "trades_change": trades_diff,
            "win_rate_change": win_rate_diff,
            "pnl_change": pnl_diff,
            "sharpe_change": sharpe_diff,
            "drawdown_change": dd_diff,
            "regime_leakage_change": leakage_diff
        })

    # Redundancy Analysis: identify if multiple filters veto the same signals
    # We can measure correlation vectors between veto columns across signal bars
    from engines import regime_engine
    
    # Use baseline_analyzed which contains all indicators and classification results
    veto_df_input = baseline_analyzed if baseline_analyzed is not None else df
    veto_results = regime_engine.compute_veto_analytics(veto_df_input)
    interaction_matrix = veto_results.get("interaction_matrix", {})

    # Compute a directed factor dependency graph:
    # Identify pairs where Veto A implies Veto B (A -> B dependency score > 0.8)
    dependency_graph = []
    for k1, links in interaction_matrix.items():
        for k2, score in links.items():
            if k1 != k2 and score >= 0.7:
                dependency_graph.append({
                    "source": k1,
                    "target": k2,
                    "strength": score,
                    "relationship": "Highly Redundant" if score >= 0.85 else "Co-occurring"
                })

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "period": period,
        "ablation_variants": ablation_results,
        "marginal_contributions": marginal_contributions,
        "redundancy_matrix": interaction_matrix,
        "factor_dependency_graph": dependency_graph
    }
