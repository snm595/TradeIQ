"""
TradeIQ — Market Regime Engine

Classifies each bar into one of 7 market regimes:
  - TRENDING_UP
  - TRENDING_DOWN
  - SIDEWAYS (choppy)
  - HIGH_VOLATILITY
  - LOW_VOLATILITY
  - EXPANSION
  - COMPRESSION

Also detects anti-chop signals:
  - Candle overlap chop detection
  - Failed breakout tracking
  - Combined chop flag

This layer is the primary quality filter — it prevents trading in
unfavorable conditions before any signal is generated.
"""

import pandas as pd
import numpy as np
from enum import Enum
import config


class MarketRegime(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    EXPANSION = "expansion"
    COMPRESSION = "compression"


def classify_regime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each bar into a market regime and add chop detection flags.

    Adds columns:
      - regime: MarketRegime enum value
      - is_choppy: bool — strong chop detected
      - failed_breakout_count: int — number of failed breakouts in lookback

    Args:
        df: DataFrame with indicator columns already computed.

    Returns:
        DataFrame with regime columns appended.
    """
    df = df.copy()

    # Step 1: Detect failed breakouts (anti-chop)
    df = _detect_failed_breakouts(df)
    df = _compute_directional_efficiency(df)
    df = _compute_wick_rejection_rate(df)
    df = _compute_vwap_flatness(df)
    df = _compute_trend_stability(df)
    df = _compute_breakout_follow_through(df)
    df = _compute_chop_score(df)

    # Step 2: Build chop flag
    overlap_chop = df["candle_overlap_pct"].fillna(0) > config.OVERLAP_CHOP_THRESHOLD
    breakout_chop = df["failed_breakout_count"].fillna(0) >= config.FAILED_BREAKOUT_MIN_COUNT
    weak_efficiency = df["directional_efficiency"].fillna(1.0) < config.MIN_DIRECTIONAL_EFFICIENCY
    flat_vwap = df["vwap_slope_norm"].abs().fillna(0.0) < config.VWAP_FLAT_SLOPE_THRESHOLD
    unstable_trend = df["trend_stability"].fillna(1.0) < config.MIN_TREND_STABILITY
    high_wick_rejection = df["wick_rejection_rate"].fillna(0.0) > config.MAX_WICK_REJECTION_RATE
    high_chop_score = df["chop_score"].fillna(0.0) >= config.CHOP_SCORE_BLOCK_THRESHOLD

    df["is_choppy"] = (
        overlap_chop
        | breakout_chop
        | weak_efficiency
        | (flat_vwap & unstable_trend)
        | high_wick_rejection
        | high_chop_score
    )

    # Step 3: Classify regime using clear priority-based decision tree
    df["regime"] = df.apply(_classify_row, axis=1)

    return df


def _classify_row(row) -> str:
    """
    Classify a single row into a market regime.

    Priority order (highest to lowest):
      1. Extreme volatility overrides everything
      2. Sideways/chop detection
      3. Expansion/compression (volatility direction)
      4. Trending up/down (directional)
    """
    atr_ratio = row.get("atr_ratio", 1.0)
    ema_slope = row.get("ema_slope", 0.0)
    close = row.get("close", 0.0)
    ema_200 = row.get("ema_200", 0.0)
    is_choppy = row.get("is_choppy", False)
    candle_overlap = row.get("candle_overlap_pct", 0.0)

    # Handle NaN values
    if pd.isna(atr_ratio):
        atr_ratio = 1.0
    if pd.isna(ema_slope):
        ema_slope = 0.0
    if pd.isna(candle_overlap):
        candle_overlap = 0.0

    # Priority 1: Extreme volatility
    if atr_ratio >= config.ATR_HIGH_VOL_RATIO:
        return MarketRegime.HIGH_VOLATILITY.value

    if atr_ratio <= config.ATR_LOW_VOL_RATIO:
        return MarketRegime.LOW_VOLATILITY.value

    # Priority 2: Sideways / choppy
    if is_choppy:
        return MarketRegime.SIDEWAYS.value

    # Priority 3: Expansion / Compression
    # Expansion: ATR growing + directional move
    is_expanding = atr_ratio >= config.ATR_EXPANSION_RATIO
    is_directional = abs(ema_slope) > config.REGIME_SLOPE_THRESHOLD * 0.5

    if is_expanding and is_directional:
        return MarketRegime.EXPANSION.value

    # Compression: ATR shrinking + range-bound
    is_compressing = atr_ratio <= config.ATR_COMPRESSION_RATIO
    is_flat = abs(ema_slope) < config.REGIME_SLOPE_THRESHOLD * 0.5

    if is_compressing and is_flat:
        return MarketRegime.COMPRESSION.value

    # Priority 4: Trending
    if ema_slope > config.REGIME_SLOPE_THRESHOLD and close > ema_200:
        return MarketRegime.TRENDING_UP.value

    if ema_slope < -config.REGIME_SLOPE_THRESHOLD and close < ema_200:
        return MarketRegime.TRENDING_DOWN.value

    # Default: if nothing clear, call it sideways
    return MarketRegime.SIDEWAYS.value


def _detect_failed_breakouts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect failed breakouts — price breaks above/below recent range then re‑enters within the configured
    number of bars (`FAILED_BREAKOUT_REENTRY_BARS`).

    The function marks a breakout as *failed* if the price does not re‑enter the prior range within the
    allowed window. It then computes a rolling count of failed breakouts over `FAILED_BREAKOUT_LOOKBACK`.
    """
    lookback = config.FAILED_BREAKOUT_LOOKBACK
    reentry = config.FAILED_BREAKOUT_REENTRY_BARS

    # Rolling high/low over lookback period
    high_rolling = df["high"].rolling(window=lookback).max()
    low_rolling = df["low"].rolling(window=lookback).min()

    # Detect breakout events based on prior bar's high/low (shift(1) gives the previous bar's range)
    breakout_high = df["close"] > high_rolling.shift(1)
    breakout_low = df["close"] < low_rolling.shift(1)

    # Initialise re‑entry trackers
    reentered_high = pd.Series(False, index=df.index)
    reentered_low = pd.Series(False, index=df.index)

    # Look ahead up to `reentry` bars to see if price re‑enters the range
    for i in range(1, reentry + 1):
        reentered_high |= (df["close"].shift(-i) <= high_rolling.shift(1))
        reentered_low |= (df["close"].shift(-i) >= low_rolling.shift(1))

    # Failed breakout = breakout event without any re‑entry within the window
    failed_high = breakout_high & ~reentered_high
    failed_low = breakout_low & ~reentered_low
    failed_breakout = (failed_high | failed_low).astype(float)

    # Rolling count of failed breakouts over the lookback window
    df["failed_breakout_count"] = (
        failed_breakout.rolling(window=lookback).sum().fillna(0).astype(int)
    )
    return df


def _compute_directional_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    lookback = max(config.CANDLE_OVERLAP_LOOKBACK, 10)
    net_move = (df["close"] - df["close"].shift(lookback)).abs()
    step_move = df["close"].diff().abs().rolling(lookback).sum()
    df["directional_efficiency"] = np.where(step_move > 0, net_move / step_move, 0.0)
    return df


def _compute_wick_rejection_rate(df: pd.DataFrame) -> pd.DataFrame:
    full_range = (df["high"] - df["low"]).replace(0, np.nan)
    body = (df["close"] - df["open"]).abs()
    wick_ratio = ((full_range - body) / full_range).clip(lower=0, upper=1).fillna(0)
    df["wick_rejection_rate"] = wick_ratio.rolling(config.CANDLE_OVERLAP_LOOKBACK).mean().fillna(0)
    return df


def _compute_vwap_flatness(df: pd.DataFrame) -> pd.DataFrame:
    lookback = max(5, config.EMA_SLOPE_LOOKBACK)
    denom = (df["atr"] * lookback).replace(0, np.nan)
    df["vwap_slope_norm"] = ((df["vwap"] - df["vwap"].shift(lookback)) / denom).replace([np.inf, -np.inf], np.nan).fillna(0)
    return df


def _compute_trend_stability(df: pd.DataFrame) -> pd.DataFrame:
    lookback = max(8, config.EMA_SLOPE_LOOKBACK)
    candle_dir = np.sign(df["close"] - df["open"])
    ema_dir = np.sign(df["ema_slope"])
    aligned = (candle_dir == ema_dir).astype(float)
    df["trend_stability"] = aligned.rolling(lookback).mean().fillna(0.5)
    return df


def _compute_breakout_follow_through(df: pd.DataFrame) -> pd.DataFrame:
    lookback = config.FAILED_BREAKOUT_LOOKBACK
    prior_high = df["high"].rolling(lookback).max().shift(1)
    prior_low = df["low"].rolling(lookback).min().shift(1)
    broke_high = df["close"] > prior_high
    broke_low = df["close"] < prior_low
    follow_up = df["close"].shift(-1)
    buy_follow = broke_high & (follow_up > df["close"])
    sell_follow = broke_low & (follow_up < df["close"])
    any_break = broke_high | broke_low
    success = (buy_follow | sell_follow).astype(float)
    denom = any_break.astype(float).rolling(lookback).sum()
    num = success.rolling(lookback).sum()
    df["breakout_follow_through"] = np.where(denom > 0, num / denom, 0.5)
    return df


def _compute_chop_score(df: pd.DataFrame) -> pd.DataFrame:
    overlap = df["candle_overlap_pct"].fillna(0)
    fail_bo = (df["failed_breakout_count"].fillna(0) / max(config.FAILED_BREAKOUT_MIN_COUNT * 2, 1)).clip(0, 1)
    ineff = (1 - df["directional_efficiency"].fillna(0)).clip(0, 1)
    wick = df["wick_rejection_rate"].fillna(0).clip(0, 1)
    flat_vwap = (1 - (df["vwap_slope_norm"].abs() / max(config.VWAP_FLAT_SLOPE_THRESHOLD * 4, 1e-6))).clip(0, 1)
    weak_follow = (1 - df["breakout_follow_through"].fillna(0.5)).clip(0, 1)

    df["chop_score"] = (
        0.24 * overlap
        + 0.20 * fail_bo
        + 0.18 * ineff
        + 0.14 * wick
        + 0.12 * flat_vwap
        + 0.12 * weak_follow
    ).clip(0, 1)
    return df


def get_regime_description(regime: str) -> str:
    """Return a human-readable description of the regime."""
    descriptions = {
        MarketRegime.TRENDING_UP.value: "Strong uptrend — EMA200 sloping up, price above EMA200",
        MarketRegime.TRENDING_DOWN.value: "Strong downtrend — EMA200 sloping down, price below EMA200",
        MarketRegime.SIDEWAYS.value: "Choppy/sideways — high candle overlap or repeated failed breakouts",
        MarketRegime.HIGH_VOLATILITY.value: "Extreme volatility — ATR well above average, proceed with caution",
        MarketRegime.LOW_VOLATILITY.value: "Low volatility — ATR well below average, limited opportunity",
        MarketRegime.EXPANSION.value: "Volatility expanding with direction — potential breakout move",
        MarketRegime.COMPRESSION.value: "Volatility contracting — coiling, potential breakout ahead",
    }
    return descriptions.get(regime, "Unknown regime")


def compute_transition_matrix(df: pd.DataFrame) -> dict:
    """
    Compute Markov transition probability matrix between the 7 market states.
    """
    regimes = df["regime"].dropna()
    states = [r.value for r in MarketRegime]
    
    if len(regimes) < 2:
        return {s1: {s2: 1.0 if s1 == s2 else 0.0 for s2 in states} for s1 in states}

    current = regimes[:-1].values
    next_ = regimes[1:].values

    matrix = {s1: {s2: 0.0 for s2 in states} for s1 in states}
    row_totals = {s: 0 for s in states}

    for c, n in zip(current, next_):
        if c in matrix and n in matrix[c]:
            matrix[c][n] += 1
            row_totals[c] += 1

    normalized_matrix = {}
    for s1 in states:
        total = row_totals[s1]
        normalized_matrix[s1] = {}
        for s2 in states:
            if total > 0:
                normalized_matrix[s1][s2] = round(float(matrix[s1][s2] / total), 3)
            else:
                normalized_matrix[s1][s2] = 1.0 if s1 == s2 else 0.0

    return normalized_matrix


def compute_veto_analytics(df: pd.DataFrame) -> dict:
    """
    Compute veto contributions and veto interaction matrix for rejected signals.
    """
    idx = df.index
    
    # Extract series with standard fallbacks
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
    regime = df.get("regime", pd.Series("unknown", index=idx))

    regime_allowed = regime.isin({"trending_up", "trending_down", "expansion"})

    # Veto rules (True means vetoed)
    vetoes = {
        "regime_not_allowed": (~regime_allowed).astype(int),
        "is_choppy": is_choppy.astype(int),
        "low_efficiency": (directional_efficiency < config.EXEC_MIN_DIRECTIONAL_EFFICIENCY).astype(int),
        "high_overlap": (candle_overlap > config.EXEC_MAX_OVERLAP_DENSITY).astype(int),
        "weak_follow_through": (breakout_follow < config.EXEC_MIN_BREAKOUT_FOLLOW_THROUGH).astype(int),
        "flat_vwap": (vwap_slope < config.EXEC_MIN_ABS_VWAP_SLOPE).astype(int),
        "flat_ema": (ema_slope < config.EXEC_MIN_ABS_EMA_SLOPE).astype(int),
        "unstable_trend": (trend_stability < config.EXEC_MIN_TREND_STABILITY).astype(int),
        "low_continuation_quality": (continuation_quality < config.EXEC_MIN_CONTINUATION_QUALITY).astype(int),
        "failed_breakouts": (failed_breakouts > config.EXEC_MAX_FAILED_BREAKOUTS).astype(int),
        "high_chop_score": (chop_score > config.EXEC_MAX_CHOP_SCORE).astype(int),
    }

    veto_keys = list(vetoes.keys())
    veto_df = pd.DataFrame(vetoes, index=idx)
    
    # Calculate marginal veto contributions (times each filter vetoed a signal)
    # We only care about signal bars (BUY or SELL signals from signal_engine)
    raw_signals = (df["close"] > df["vwap"]) & (df["close"] > df["ema_200"]) | (df["close"] < df["vwap"]) & (df["close"] < df["ema_200"])
    signal_bars = df.index[raw_signals]
    
    if len(signal_bars) == 0:
        return {
            "contributions": {k: 0 for k in veto_keys},
            "interaction_matrix": {k1: {k2: 0.0 for k2 in veto_keys} for k1 in veto_keys},
            "total_rejected": 0
        }

    veto_signals = veto_df.loc[signal_bars]
    contributions = veto_signals.sum().to_dict()

    # Calculate veto co-occurrence interaction matrix
    interaction = {k1: {k2: 0.0 for k2 in veto_keys} for k1 in veto_keys}
    for k1 in veto_keys:
        for k2 in veto_keys:
            # How often do k1 and k2 veto together on signal bars?
            both = (veto_signals[k1] & veto_signals[k2]).sum()
            total_k1 = veto_signals[k1].sum()
            if total_k1 > 0:
                interaction[k1][k2] = round(float(both / total_k1), 3)
            else:
                interaction[k1][k2] = 0.0

    return {
        "contributions": contributions,
        "interaction_matrix": interaction,
        "total_rejected": int((veto_signals.sum(axis=1) > 0).sum())
    }
