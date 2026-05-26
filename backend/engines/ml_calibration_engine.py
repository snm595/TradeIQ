"""
TradeIQ — Explainable ML Calibration Engine

Utilizes scikit-learn's RandomForestClassifier to calibrate trade confidence scores.
Constructs walk-forward out-of-sample calibration models, feature importance maps,
and transparent tree-path feature contribution metrics (lightweight SHAP-like explanations).
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from typing import Optional


FEATURES = [
    "breakout_follow_through",
    "directional_efficiency",
    "trend_stability",
    "candle_overlap_pct",
    "wick_rejection_rate",
    "chop_score",
    "post_breakout_persistence",
    "continuation_survival_probability",
    "directional_persistence_decay",
    "reversal_probability",
    "vwap_acceptance_score",
    "breakout_exhaustion",
    "atr_ratio",
    "ema_slope"
]


def calibrate_confidence_with_ml(
    df: pd.DataFrame,
    htf_df: Optional[pd.DataFrame] = None
) -> dict:
    """
    Train a RandomForest calibration model on all historical signal bars,
    predict the calibrated win probability for the latest signal bar,
    and output explainability contributions and feature importances.
    """
    df = df.copy()
    
    # 1. Isolate historical signal bars (where a BUY/SELL was generated)
    signal_mask = df["signal"].notna()
    df_signals = df[signal_mask].copy()
    
    # We need resolved outcomes to train our model.
    # A signal outcome is determined by the backtester's simulated trades.
    # Let's simulate a fast standard label resolution:
    # For every signal, did close rise or fall by 1.5x ATR relative to the other side within 10 bars?
    # Or, to be 100% aligned with backtest_engine, we can run a quick trade simulation to obtain true labels.
    from engines import backtest_engine
    metrics = backtest_engine.run_backtest(df)
    trades = [t for t in metrics.get("trade_history", []) if t.get("status") == "taken"]
    
    if len(trades) < 10:
        # Insufficient sample size for ML training
        return {
            "enabled": False,
            "message": "Insufficient trades sample size (< 10) to train ML calibration model.",
            "win_probability": None,
            "feature_importances": {},
            "feature_contributions": {},
            "oos_accuracy": 0.0
        }

    # Map trades to df_signals by entry time
    trade_outcomes = {t["entry_time"]: (1.0 if t["pnl_r"] > 0 else 0.0) for t in trades}
    
    df_signals["target"] = df_signals.index.map(lambda idx: trade_outcomes.get(str(idx), np.nan))
    df_signals = df_signals.dropna(subset=["target"] + FEATURES)
    
    if len(df_signals) < 10:
        return {
            "enabled": False,
            "message": "Insufficient resolved signal outcomes to calibrate model.",
            "win_probability": None,
            "feature_importances": {},
            "feature_contributions": {},
            "oos_accuracy": 0.0
        }

    X = df_signals[FEATURES].values
    y = df_signals["target"].values

    # 2. Walk-forward / Out-of-Sample Validation
    # Split into 70% Train, 30% Test for validation scoring
    split_idx = int(len(X) * 0.7)
    
    if split_idx >= 5:
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        val_model = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42)
        val_model.fit(X_train, y_train)
        val_preds = val_model.predict(X_val)
        oos_acc = float((val_preds == y_val).mean())
    else:
        oos_acc = 0.5

    # 3. Train final model on all historical data
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X, y)

    # 4. Predict latest signal bar
    latest_bar = df.iloc[-1]
    latest_features = latest_bar[FEATURES].fillna(0.0).values.reshape(1, -1)
    
    win_prob = float(model.predict_proba(latest_features)[0, 1])

    # 5. Extract Feature Importances
    importances = model.feature_importances_
    feature_imp_dict = {FEATURES[i]: round(float(importances[i]), 3) for i in range(len(FEATURES))}
    
    # Sort importances
    feature_imp_dict = dict(sorted(feature_imp_dict.items(), key=lambda item: item[1], reverse=True))

    # 6. Tree-path Explainer Approximation (SHAP-like)
    # base_rate (average win rate of historical signals)
    base_rate = float(y.mean())
    prediction_diff = win_prob - base_rate
    
    # Compute relative contributions using importances and feature standard deviations
    contributions = {}
    feature_means = X.mean(axis=0)
    feature_stds = X.std(axis=0) + 1e-6
    
    raw_contribs = []
    for i, col in enumerate(FEATURES):
        val = float(latest_bar[col])
        if pd.isna(val):
            val = float(feature_means[i])
        
        # Directional impact based on deviation from mean
        dev = (val - feature_means[i]) / feature_stds[i]
        
        # Check sign of correlation between feature and target to orient direction
        corr = float(np.corrcoef(X[:, i], y)[0, 1]) if X[:, i].std() > 0 and y.std() > 0 else 1.0
        corr_sign = np.sign(corr)
        
        raw_contrib = importances[i] * dev * corr_sign
        raw_contribs.append(raw_contrib)
        
    # Scale contributions so they sum up exactly to (win_prob - base_rate)
    sum_raw = sum(abs(rc) for rc in raw_contribs) + 1e-6
    for i, col in enumerate(FEATURES):
        share = abs(raw_contribs[i]) / sum_raw
        contributions[col] = round(prediction_diff * share, 3)

    # Sort contributions by magnitude
    contributions = dict(sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True))

    return {
        "enabled": True,
        "base_rate": round(base_rate * 100, 1),
        "win_probability": round(win_prob * 100, 1),
        "feature_importances": feature_imp_dict,
        "feature_contributions": contributions,
        "oos_accuracy": round(oos_acc * 100, 1),
        "sample_size": len(df_signals)
    }
