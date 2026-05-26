"""
TradeIQ - Continuation Quality Engine

Computes behavior-quality features for continuation setups without adding
indicator clutter. This layer measures whether price is actually persisting
after structure shifts, or merely producing noisy impulse/reversal behavior.
"""

import numpy as np
import pandas as pd


def compute_continuation_quality(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add continuation diagnostics used by signal gating, confidence calibration,
    and research reports.

    Required inputs are produced by indicator_engine and regime_engine.
    """
    df = df.copy()

    follow = df.get("breakout_follow_through", pd.Series(0.5, index=df.index)).fillna(0.5).clip(0, 1)
    efficiency = df.get("directional_efficiency", pd.Series(0.0, index=df.index)).fillna(0.0).clip(0, 1)
    stability = df.get("trend_stability", pd.Series(0.5, index=df.index)).fillna(0.5).clip(0, 1)
    overlap = df.get("candle_overlap_pct", pd.Series(1.0, index=df.index)).fillna(1.0).clip(0, 1)
    wick = df.get("wick_rejection_rate", pd.Series(1.0, index=df.index)).fillna(1.0).clip(0, 1)
    chop = df.get("chop_score", pd.Series(1.0, index=df.index)).fillna(1.0).clip(0, 1)

    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    volume_ema = df.get("volume_ema", pd.Series(1.0, index=df.index)).fillna(1.0)
    atr = df.get("atr", pd.Series(1.0, index=df.index)).replace(0, np.nan)

    # 1. Post-Breakout Persistence
    prior_high = high.rolling(20).max().shift(1)
    prior_low = low.rolling(20).min().shift(1)
    broke_high = (close > prior_high).astype(int)
    broke_low = (close < prior_low).astype(int)
    broke_any = (broke_high | broke_low).astype(int)
    post_breakout_persistence = broke_any.groupby((broke_any == 0).cumsum()).cumsum()
    df["post_breakout_persistence"] = (post_breakout_persistence / 5.0).clip(0, 1).fillna(0.0)

    # 2. Continuation Survival Probability
    ema_slope = df.get("ema_slope", pd.Series(0.0, index=df.index)).fillna(0.0)
    ema_dir = np.sign(ema_slope)
    aligned_candle = ((np.sign(close - close.shift(1)) == ema_dir) & (ema_dir != 0)).astype(float)
    df["continuation_survival_probability"] = aligned_candle.rolling(8).mean().fillna(0.5)

    # 3. Directional Persistence Decay
    candle_dir = np.sign(close - open_).fillna(0.0)
    decay_persistence = (
        1.0 * candle_dir
        + 0.8 * candle_dir.shift(1)
        + 0.6 * candle_dir.shift(2)
        + 0.4 * candle_dir.shift(3)
        + 0.2 * candle_dir.shift(4)
    ) / 3.0
    df["directional_persistence_decay"] = decay_persistence.abs().clip(0, 1).fillna(0.0)

    # 4. Reversal Probability
    pullback_raw = (close.rolling(5).max() - close) / atr
    pullback_integrity = (1 - pullback_raw.clip(0, 1)).fillna(0.5)
    reversal_prob = (0.5 * (pullback_raw / 2.0).clip(0, 1) + 0.5 * wick).clip(0, 1)
    df["reversal_probability"] = reversal_prob.fillna(0.0)
    df["pullback_integrity"] = pullback_integrity.clip(0, 1)

    # 5. Acceptance Above/Below VWAP
    vwap = df.get("vwap", close)
    above_vwap = (close > vwap).astype(int)
    below_vwap = (close < vwap).astype(int)
    consecutive_above = above_vwap.groupby((above_vwap == 0).cumsum()).cumsum()
    consecutive_below = below_vwap.groupby((below_vwap == 0).cumsum()).cumsum()
    vwap_acceptance_bars = np.maximum(consecutive_above, consecutive_below)
    df["vwap_acceptance_score"] = (vwap_acceptance_bars / 5.0).clip(0, 1).fillna(0.0)

    # 6. Breakout Volume-Price Exhaustion
    vol_ratio = volume / volume_ema.replace(0, np.nan)
    candle_spread = (high - low) / atr
    exhaustion = (vol_ratio > 1.5) & ((candle_spread < 0.6) | (wick > 0.5))
    df["breakout_exhaustion"] = exhaustion.astype(float).fillna(0.0)

    # Composite Continuation Quality Score
    df["continuation_quality_score"] = (
        100
        * (
            0.15 * follow
            + 0.12 * efficiency
            + 0.10 * stability
            + 0.10 * df["post_breakout_persistence"]
            + 0.10 * df["continuation_survival_probability"]
            + 0.12 * df["directional_persistence_decay"]
            + 0.10 * df["pullback_integrity"]
            + 0.08 * (1.0 - df["reversal_probability"])
            + 0.08 * df["vwap_acceptance_score"]
            + 0.05 * (1.0 - df["breakout_exhaustion"])
        )
    ).clip(0, 100)

    df["continuation_state"] = np.select(
        [
            df["continuation_quality_score"] >= 70,
            df["continuation_quality_score"] >= 55,
            df["continuation_quality_score"] >= 40,
        ],
        ["institutional", "qualified", "fragile"],
        default="no_trade",
    )
    return df
