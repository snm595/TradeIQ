"""
TradeIQ — Confidence Calibration Research Tool

Evaluates the probabilistic validity of the confidence scoring system.
Constructs reliability diagrams (expected confidence vs. realized win rate),
expectancy-vs-confidence curves, and calibration metrics.
"""

from __future__ import annotations
import numpy as np
import pandas as pd


def analyze_confidence_calibration(trades: list[dict]) -> dict:
    """
    Construct calibration statistics and reliability metrics from backtest trade history.
    """
    taken_trades = [t for t in trades if t.get("status") == "taken"]
    
    if not taken_trades:
        return {
            "reliability_buckets": [],
            "overall_calibration_error": 0.0,
            "expectancy_by_confidence": [],
            "confidence_pnl_correlation": 0.0,
            "total_sample_size": 0
        }

    df_trades = pd.DataFrame(taken_trades)
    df_trades["is_win"] = (df_trades["pnl_r"] > 0).astype(float)
    df_trades["confidence_decimal"] = df_trades["confidence_pct"] / 100.0

    # Define standard confidence buckets
    # TradeIQ minimum threshold is 60%
    bins = [60, 70, 80, 90, 100]
    labels = ["60-70%", "70-80%", "80-90%", "90-100%"]
    
    df_trades["bucket"] = pd.cut(df_trades["confidence_pct"], bins=bins, labels=labels, include_lowest=True)

    reliability_buckets = []
    expectancy_by_confidence = []
    weighted_diff_sum = 0.0
    total_valid_trades = 0

    for label in labels:
        bucket_trades = df_trades[df_trades["bucket"] == label]
        count = len(bucket_trades)
        
        if count > 0:
            avg_expected = float(bucket_trades["confidence_decimal"].mean())
            actual_win_rate = float(bucket_trades["is_win"].mean())
            avg_pnl_r = float(bucket_trades["pnl_r"].mean())
            total_pnl_r = float(bucket_trades["pnl_r"].sum())
            
            diff = abs(avg_expected - actual_win_rate)
            weighted_diff_sum += diff * count
            total_valid_trades += count
            
            reliability_buckets.append({
                "bucket": label,
                "count": count,
                "expected_confidence": round(avg_expected * 100, 1),
                "actual_win_rate": round(actual_win_rate * 100, 1),
                "calibration_gap": round((actual_win_rate - avg_expected) * 100, 1)
            })
            
            expectancy_by_confidence.append({
                "bucket": label,
                "count": count,
                "avg_expectancy_r": round(avg_pnl_r, 3),
                "total_pnl_r": round(total_pnl_r, 2)
            })
        else:
            # Empty bucket placeholder
            reliability_buckets.append({
                "bucket": label,
                "count": 0,
                "expected_confidence": float(bins[labels.index(label)] + 5),
                "actual_win_rate": 0.0,
                "calibration_gap": 0.0
            })
            expectancy_by_confidence.append({
                "bucket": label,
                "count": 0,
                "avg_expectancy_r": 0.0,
                "total_pnl_r": 0.0
            })

    # Expected Calibration Error (ECE) approximation
    ece = (weighted_diff_sum / total_valid_trades) * 100 if total_valid_trades > 0 else 0.0

    # Confidence vs. realized PnL correlation
    if len(df_trades) > 1 and df_trades["confidence_pct"].std() > 0 and df_trades["pnl_r"].std() > 0:
        corr = float(np.corrcoef(df_trades["confidence_pct"], df_trades["pnl_r"])[0, 1])
    else:
        corr = 0.0

    return {
        "reliability_buckets": reliability_buckets,
        "overall_calibration_error": round(ece, 2),
        "expectancy_by_confidence": expectancy_by_confidence,
        "confidence_pnl_correlation": round(corr, 3),
        "total_sample_size": len(df_trades)
    }
