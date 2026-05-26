"""
TradeIQ — Signal Engine

Generates raw BUY and SELL signals using strict conditions.
This engine only produces signals when ALL primary conditions are met.

BUY: price > VWAP, price > EMA200, volume expansion, trending/expanding, no chop
SELL: price < VWAP, price < EMA200, volume expansion, trending/expanding, no chop

Direction lock prevents consecutive same-direction signals.
"""

import pandas as pd
import numpy as np
import config
from engines.regime_engine import MarketRegime


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate raw BUY/SELL signals.

    Adds columns:
      - signal: "BUY", "SELL", or None
      - signal_bar: True on bars where a signal fires

    Args:
        df: DataFrame with indicators and regime columns.

    Returns:
        DataFrame with signal columns appended.
    """
    df = df.copy()

    # ── Core conditions ──────────────────────────────────────────────────────
    price_above_vwap = df["close"] > df["vwap"]
    price_below_vwap = df["close"] < df["vwap"]
    price_above_ema = df["close"] > df["ema_200"]
    price_below_ema = df["close"] < df["ema_200"]

    # Volume expansion: current volume > EMA × multiplier
    vol_expansion = df["volume"] > (df["volume_ema"] * config.VOLUME_EXPANSION_MULT)

    # Favorable regimes for trading
    favorable_regimes = {
        MarketRegime.TRENDING_UP.value,
        MarketRegime.TRENDING_DOWN.value,
        MarketRegime.EXPANSION.value,
    }
    regime_favorable = df["regime"].isin(favorable_regimes)

    # No chop filter
    no_chop = ~df["is_choppy"]

    # No compression
    no_compression = df["regime"] != MarketRegime.COMPRESSION.value

    # Optional secondary participation check (keeps daily charts from over-filtering)
    vol_baseline = df["volume"] > df["volume_ema"]
    atr_support = df.get("atr_ratio", pd.Series(1.0, index=df.index)) >= 1.0
    participation_ok = vol_expansion | vol_baseline | atr_support

    regime_allowed = df["regime"].isin(
        {
            MarketRegime.TRENDING_UP.value,
            MarketRegime.TRENDING_DOWN.value,
            MarketRegime.EXPANSION.value,
        }
    )
    hard_quality_gate = _build_hard_quality_gate(df, regime_allowed)

    # ── Confluence-based raw signal conditions ───────────────────────────────
    # Inspired by reference scripts: require minimum alignment score rather than
    # strict all-AND gating on every filter.
    buy_score = (
        price_above_vwap.astype(int)
        + price_above_ema.astype(int)
        + participation_ok.astype(int)
        + regime_favorable.astype(int)
        + no_chop.astype(int)
        + no_compression.astype(int)
    )

    sell_score = (
        price_below_vwap.astype(int)
        + price_below_ema.astype(int)
        + participation_ok.astype(int)
        + regime_favorable.astype(int)
        + no_chop.astype(int)
        + no_compression.astype(int)
    )

    # Maintain hard directional structure checks to avoid noisy flips.
    raw_buy = (
        price_above_vwap
        & price_above_ema
        & (buy_score >= config.MIN_SIGNAL_CONFLUENCE)
        & hard_quality_gate
    )
    raw_sell = (
        price_below_vwap
        & price_below_ema
        & (sell_score >= config.MIN_SIGNAL_CONFLUENCE)
        & hard_quality_gate
    )

    # ── Apply direction lock ─────────────────────────────────────────────────
    # Prevent consecutive same-direction signals
    if config.DIRECTION_LOCK:
        signals = _apply_direction_lock(raw_buy, raw_sell)
    else:
        signals = pd.Series(
            np.where(raw_buy, "BUY", np.where(raw_sell, "SELL", None)),
            index=df.index,
        )

    df["signal"] = signals
    df["signal_bar"] = df["signal"].notna()

    return df


def _build_hard_quality_gate(df: pd.DataFrame, regime_allowed: pd.Series) -> pd.Series:
    """
    Final execution eligibility screen.
    These are hard vetoes because forensic diagnostics showed score-only penalties
    still allowed too many low-quality sideways and failed-continuation trades.
    """
    idx = df.index
    directional_efficiency = df.get("directional_efficiency", pd.Series(0.0, index=idx)).fillna(0.0)
    candle_overlap = df.get("candle_overlap_pct", pd.Series(1.0, index=idx)).fillna(1.0)
    breakout_follow = df.get("breakout_follow_through", pd.Series(0.0, index=idx)).fillna(0.0)
    vwap_slope = df.get("vwap_slope_norm", pd.Series(0.0, index=idx)).fillna(0.0).abs()
    ema_slope = df.get("ema_slope", pd.Series(0.0, index=idx)).fillna(0.0).abs()
    trend_stability = df.get("trend_stability", pd.Series(0.0, index=idx)).fillna(0.0)
    continuation_quality = df.get("continuation_quality_score", pd.Series(0.0, index=idx)).fillna(0.0)
    failed_breakouts = df.get("failed_breakout_count", pd.Series(999, index=idx)).fillna(999)
    chop_score = df.get("chop_score", pd.Series(1.0, index=idx)).fillna(1.0)
    is_choppy = df.get("is_choppy", pd.Series(True, index=idx)).fillna(True)

    return (
        regime_allowed
        & ~is_choppy
        & (directional_efficiency >= config.EXEC_MIN_DIRECTIONAL_EFFICIENCY)
        & (candle_overlap <= config.EXEC_MAX_OVERLAP_DENSITY)
        & (breakout_follow >= config.EXEC_MIN_BREAKOUT_FOLLOW_THROUGH)
        & (vwap_slope >= config.EXEC_MIN_ABS_VWAP_SLOPE)
        & (ema_slope >= config.EXEC_MIN_ABS_EMA_SLOPE)
        & (trend_stability >= config.EXEC_MIN_TREND_STABILITY)
        & (continuation_quality >= config.EXEC_MIN_CONTINUATION_QUALITY)
        & (failed_breakouts <= config.EXEC_MAX_FAILED_BREAKOUTS)
        & (chop_score <= config.EXEC_MAX_CHOP_SCORE)
    )


def _apply_direction_lock(raw_buy: pd.Series, raw_sell: pd.Series) -> pd.Series:
    """
    Apply direction lock: a BUY can only fire after a SELL (or at start),
    and vice versa.

    This prevents signal clustering and ensures alternating signals.
    Inspired by the direction lock pattern in multiple reference scripts.
    """
    signals = pd.Series(index=raw_buy.index, dtype=object)
    last_direction = 0  # 0=none, 1=buy, -1=sell

    for i in range(len(raw_buy)):
        if raw_buy.iloc[i] and last_direction != 1:
            signals.iloc[i] = "BUY"
            last_direction = 1
        elif raw_sell.iloc[i] and last_direction != -1:
            signals.iloc[i] = "SELL"
            last_direction = -1
        else:
            signals.iloc[i] = None

    return signals


def get_signal_summary(df: pd.DataFrame) -> dict:
    """Return a summary of signals generated."""
    total_bars = len(df)
    buy_signals = (df["signal"] == "BUY").sum()
    sell_signals = (df["signal"] == "SELL").sum()
    total_signals = buy_signals + sell_signals

    return {
        "total_bars": int(total_bars),
        "buy_signals": int(buy_signals),
        "sell_signals": int(sell_signals),
        "total_signals": int(total_signals),
        "signal_rate_pct": round(total_signals / max(total_bars, 1) * 100, 2),
    }
