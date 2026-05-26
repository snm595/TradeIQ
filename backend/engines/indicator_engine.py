"""
TradeIQ — Indicator Engine

Calculates ONLY the minimal required indicators:
  - EMA 200  → trend direction
  - VWAP     → price control / value area
  - Volume EMA → volume expansion baseline
  - ATR      → volatility measurement
  - EMA slope → trend quality (ATR-normalized)
  - ATR ratio → volatility regime
  - Candle overlap % → chop detection

NO RSI, MACD, Bollinger Bands, or other indicator bloat.
"""

import pandas as pd
import numpy as np
import config


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all core indicators and add them as columns to the DataFrame.

    Args:
        df: DataFrame with columns: open, high, low, close, volume

    Returns:
        Same DataFrame with indicator columns appended.
    """
    df = df.copy()

    df = _compute_ema200(df)
    df = _compute_vwap(df)
    df = _compute_volume_ema(df)
    df = _compute_atr(df)
    df = _compute_ema_slope(df)
    df = _compute_atr_ratio(df)
    df = _compute_candle_overlap(df)

    return df


def _compute_ema200(df: pd.DataFrame) -> pd.DataFrame:
    """EMA 200 — primary trend direction filter."""
    df["ema_200"] = df["close"].ewm(span=config.EMA_LONG_PERIOD, adjust=False).mean()
    return df


def _compute_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rolling VWAP — identifies price control / value area.

    Uses a rolling window approach since we may not have session boundaries.
    VWAP = Σ(typical_price × volume) / Σ(volume) over the lookback window.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = typical_price * df["volume"]

    period = config.VWAP_PERIOD
    df["vwap"] = pv.rolling(window=period).sum() / df["volume"].rolling(window=period).sum()

    return df


def _compute_volume_ema(df: pd.DataFrame) -> pd.DataFrame:
    """Volume EMA — baseline for detecting volume expansion."""
    df["volume_ema"] = df["volume"].ewm(span=config.VOLUME_EMA_PERIOD, adjust=False).mean()
    return df


def _compute_atr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Average True Range — volatility measurement.

    TR = max(H-L, |H-prev_close|, |L-prev_close|)
    ATR = EMA(TR, period)
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df["atr"] = true_range.ewm(span=config.ATR_PERIOD, adjust=False).mean()
    return df


def _compute_ema_slope(df: pd.DataFrame) -> pd.DataFrame:
    """
    EMA slope — trend quality indicator.

    Normalized by ATR to be scale-independent (inspired by AMC reference).
    slope = (ema_now - ema_n_bars_ago) / (ATR × lookback)

    Positive slope → uptrend, negative → downtrend.
    Magnitude indicates trend strength.
    """
    lookback = config.EMA_SLOPE_LOOKBACK
    ema_diff = df["ema_200"] - df["ema_200"].shift(lookback)
    denominator = df["atr"] * lookback

    # Avoid division by zero
    df["ema_slope"] = np.where(
        denominator > 0,
        ema_diff / denominator,
        0.0,
    )
    return df


def _compute_atr_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    ATR ratio — current ATR relative to its own average.

    ratio > 1 → volatility expanding
    ratio < 1 → volatility contracting
    Used for regime detection (inspired by AMC volatility regime filter).
    """
    atr_avg = df["atr"].rolling(window=config.ATR_AVG_PERIOD).mean()

    df["atr_ratio"] = np.where(
        atr_avg > 0,
        df["atr"] / atr_avg,
        1.0,
    )
    return df


def _compute_candle_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Candle overlap percentage — chop/sideways detection metric.

    Measures what fraction of recent candles overlap with their predecessor.
    A candle "overlaps" if its body range intersects with the prior candle's body range.

    High overlap → choppy/sideways market.
    Low overlap → trending/directional market.
    """
    lookback = config.CANDLE_OVERLAP_LOOKBACK

    body_high = df[["open", "close"]].max(axis=1)
    body_low = df[["open", "close"]].min(axis=1)

    prev_body_high = body_high.shift(1)
    prev_body_low = body_low.shift(1)

    # Overlap exists when the body ranges intersect
    overlap_top = pd.concat([body_high, prev_body_high], axis=1).min(axis=1)
    overlap_bot = pd.concat([body_low, prev_body_low], axis=1).max(axis=1)
    has_overlap = (overlap_top > overlap_bot).astype(float)

    # Rolling average of overlap frequency
    df["candle_overlap_pct"] = has_overlap.rolling(window=lookback).mean()

    return df
