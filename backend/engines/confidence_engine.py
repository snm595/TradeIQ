"""
TradeIQ — Confidence Engine

Assigns a weighted confidence score to every potential trade setup.
Each signal gets a detailed breakdown of why it scores high or low,
plus a clear TRADE/REJECT decision.

Scoring philosophy: every factor either adds conviction or removes it.
The system is biased toward rejection — it's better to miss a trade
than to take a bad one.

Inspired by:
  - AMC composite scoring with weighted axes
  - Viprasol confluence minimum threshold
  - Pullback Sniper quality grading (A+/A/B/Avoid)
  - AGPro shift quality scoring
"""

import pandas as pd
import numpy as np
from typing import Optional
import config
from engines.regime_engine import MarketRegime


def score_signals(
    df: pd.DataFrame,
    htf_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Score every signal bar with a confidence percentage.

    Adds columns:
      - confidence_pct: 0-100 score
      - grade: "A+", "A", "B", "Avoid"
      - risk_level: "low", "moderate", "high"
      - decision: "TRADE" or "REJECT"
      - reasons: list of positive factors (as string)
      - warnings: list of negative factors (as string)

    Args:
        df: DataFrame with signals and indicators.
        htf_df: Optional higher-timeframe DataFrame for HTF alignment.

    Returns:
        DataFrame with confidence columns on signal bars.
    """
    df = df.copy()

    # Initialize columns
    df["confidence_pct"] = np.nan
    df["grade"] = None
    df["risk_level"] = None
    df["decision"] = None
    df["reasons"] = None
    df["warnings"] = None
    df["confidence_breakdown"] = None
    df["confidence_momentum"] = np.nan
    df["market_narrative"] = None

    # Pre-compute HTF EMA for alignment check
    htf_ema = None
    if htf_df is not None and len(htf_df) > config.EMA_LONG_PERIOD:
        htf_ema = htf_df["close"].ewm(span=config.EMA_LONG_PERIOD, adjust=False).mean()

    # Score each signal bar
    signal_mask = df["signal"].notna()
    for idx in df.index[signal_mask]:
        row = df.loc[idx]
        result = _score_single(row, df, idx, htf_ema)

        df.at[idx, "confidence_pct"] = result["confidence_pct"]
        df.at[idx, "grade"] = result["grade"]
        df.at[idx, "risk_level"] = result["risk_level"]
        df.at[idx, "decision"] = result["decision"]
        df.at[idx, "reasons"] = "|".join(result["reasons"])
        df.at[idx, "warnings"] = "|".join(result["warnings"])
        df.at[idx, "confidence_breakdown"] = result["breakdown_text"]
        df.at[idx, "market_narrative"] = result["market_narrative"]

    # Confidence momentum helps identify improving/decaying setup quality.
    df["confidence_momentum"] = df["confidence_pct"].diff(config.CONFIDENCE_MOMENTUM_LOOKBACK)

    # Apply optional ML confidence calibration to the latest signal bar
    if getattr(config, "USE_ML_CALIBRATION", False):
        try:
            from engines import ml_calibration_engine
            ml_results = ml_calibration_engine.calibrate_confidence_with_ml(df, htf_df)
            if ml_results.get("enabled") and ml_results.get("win_probability") is not None:
                signal_indices = df.index[df["signal"].notna()]
                if len(signal_indices) > 0:
                    latest_idx = signal_indices[-1]
                    ml_prob = ml_results["win_probability"]
                    df.at[latest_idx, "confidence_pct"] = ml_prob
                    
                    # Recompute grade & decision based on ML calibrated confidence
                    if ml_prob >= config.GRADE_APLUS_MIN:
                        new_grade = "A+"
                    elif ml_prob >= config.GRADE_A_MIN:
                        new_grade = "A"
                    elif ml_prob >= config.GRADE_B_MIN:
                        new_grade = "B"
                    else:
                        new_grade = "Avoid"
                        
                    df.at[latest_idx, "grade"] = new_grade
                    # Do not override hard blocks from reliability engine
                    if df.at[latest_idx, "decision"] != "REJECT":
                        df.at[latest_idx, "decision"] = "TRADE" if ml_prob >= config.CONFIDENCE_TRADE_MIN else "REJECT"
                    df.at[latest_idx, "confidence_breakdown"] = f"ML Calibrated Confidence: {ml_prob:.1f}% | OOS Accuracy: {ml_results.get('oos_accuracy')}%"
        except Exception:
            pass

    return df


def _score_single(
    row: pd.Series,
    df: pd.DataFrame,
    idx,
    htf_ema: Optional[pd.Series],
) -> dict:
    """
    Score a single signal bar.

    Returns a dict with confidence_pct, grade, risk_level, decision,
    reasons (list), and warnings (list).
    """
    signal = row["signal"]
    is_buy = signal == "BUY"
    score = 0
    max_positive = 14  # Maximum possible positive points
    max_negative = 9   # Maximum possible negative points
    reasons = []
    warnings = []
    regime = row.get("regime", "")
    weights = _get_adaptive_weights(regime, row)
    breakdown = {
        "trend_quality": {"score": 0.0, "max": 25.0},
        "vwap_control": {"score": 0.0, "max": 20.0},
        "volume_confirmation": {"score": 0.0, "max": 20.0},
        "structure_quality": {"score": 0.0, "max": 15.0},
        "continuation_quality": {"score": 0.0, "max": 20.0},
        "htf_alignment": {"score": 0.0, "max": 10.0},
        "chop_penalty": {"score": 0.0, "max": 10.0},
    }

    # ── POSITIVE FACTORS ─────────────────────────────────────────────────────

    # Factor 1: EMA trend alignment (+2)
    ema_slope = row.get("ema_slope", 0)
    close = row.get("close", 0)
    ema_200 = row.get("ema_200", 0)

    if is_buy and close > ema_200 and ema_slope > config.REGIME_SLOPE_THRESHOLD:
        gain = weights["ema_trend"]
        score += gain
        breakdown["trend_quality"]["score"] += gain * 6.0
        reasons.append("EMA200 bullish with strong positive slope")
    elif not is_buy and close < ema_200 and ema_slope < -config.REGIME_SLOPE_THRESHOLD:
        gain = weights["ema_trend"]
        score += gain
        breakdown["trend_quality"]["score"] += gain * 6.0
        reasons.append("EMA200 bearish with strong negative slope")
    elif (is_buy and close > ema_200) or (not is_buy and close < ema_200):
        score += 1 * weights["ema_partial"]
        breakdown["trend_quality"]["score"] += 4.0
        reasons.append("Price on correct side of EMA200")

    # Factor 2: VWAP control / acceptance (+2)
    vwap = row.get("vwap", 0)
    if not pd.isna(vwap):
        # Check sustained VWAP position (look back acceptance_bars)
        try:
            loc = df.index.get_loc(idx)
            if loc >= config.VWAP_ACCEPTANCE_BARS:
                recent_closes = df["close"].iloc[loc - config.VWAP_ACCEPTANCE_BARS + 1: loc + 1]
                recent_vwap = df["vwap"].iloc[loc - config.VWAP_ACCEPTANCE_BARS + 1: loc + 1]

                if is_buy and (recent_closes > recent_vwap).all():
                    gain = weights["vwap_control"]
                    score += gain
                    breakdown["vwap_control"]["score"] += gain * 7.0
                    reasons.append(f"Above VWAP for {config.VWAP_ACCEPTANCE_BARS} consecutive bars")
                elif not is_buy and (recent_closes < recent_vwap).all():
                    gain = weights["vwap_control"]
                    score += gain
                    breakdown["vwap_control"]["score"] += gain * 7.0
                    reasons.append(f"Below VWAP for {config.VWAP_ACCEPTANCE_BARS} consecutive bars")
                else:
                    if (is_buy and close > vwap) or (not is_buy and close < vwap):
                        score += 1 * weights["vwap_partial"]
                        breakdown["vwap_control"]["score"] += 4.0
                        reasons.append("Currently on correct side of VWAP")
        except (KeyError, IndexError):
            pass

    # Factor 3: Volume confirmation (+2)
    volume = row.get("volume", 0)
    vol_ema = row.get("volume_ema", 0)
    if vol_ema > 0:
        vol_ratio = volume / vol_ema
        if vol_ratio >= 1.5:
            gain = weights["volume"]
            score += gain
            breakdown["volume_confirmation"]["score"] += gain * 7.0
            reasons.append(f"Strong volume expansion ({vol_ratio:.1f}× average)")
        elif vol_ratio >= config.VOLUME_EXPANSION_MULT:
            score += 1 * weights["volume_partial"]
            breakdown["volume_confirmation"]["score"] += 4.0
            reasons.append(f"Volume above average ({vol_ratio:.1f}× average)")

    # Factor 4: Clean candle structure (+1)
    body = abs(close - row.get("open", close))
    full_range = row.get("high", close) - row.get("low", close)
    if full_range > 0:
        body_ratio = body / full_range
        if body_ratio >= 0.5:
            gain = weights["candle_quality"]
            score += gain
            breakdown["structure_quality"]["score"] += gain * 5.0
            reasons.append("Clean candle structure (strong body)")

    # Factor 5: Trend consistency (+2)
    try:
        loc = df.index.get_loc(idx)
        if loc >= 4:
            recent_4 = df.iloc[loc - 3: loc + 1]
            if is_buy:
                consecutive_up = (recent_4["close"] > recent_4["open"]).sum()
                if consecutive_up >= 3:
                    gain = weights["trend_consistency"]
                    score += gain
                    breakdown["trend_quality"]["score"] += gain * 4.5
                    reasons.append(f"{consecutive_up}/4 consecutive bullish bars")
            else:
                consecutive_down = (recent_4["close"] < recent_4["open"]).sum()
                if consecutive_down >= 3:
                    gain = weights["trend_consistency"]
                    score += gain
                    breakdown["trend_quality"]["score"] += gain * 4.5
                    reasons.append(f"{consecutive_down}/4 consecutive bearish bars")
    except (KeyError, IndexError):
        pass

    # Factor 6: ATR expansion (+1)
    atr_ratio = row.get("atr_ratio", 1.0)
    if not pd.isna(atr_ratio) and atr_ratio >= 1.2:
        gain = weights["atr_expansion"]
        score += gain
        breakdown["structure_quality"]["score"] += gain * 3.5
        reasons.append(f"Volatility expanding (ATR ratio: {atr_ratio:.2f})")

    # Factor 7: Higher timeframe alignment (+2)
    if htf_ema is not None and len(htf_ema) > 0:
        try:
            # Find closest HTF bar to current timestamp
            htf_val = htf_ema.iloc[-1]
            if is_buy and close > htf_val:
                gain = weights["htf_alignment"]
                score += gain
                breakdown["htf_alignment"]["score"] += gain * 5.0
                reasons.append("Daily EMA200 confirms bullish direction")
            elif not is_buy and close < htf_val:
                gain = weights["htf_alignment"]
                score += gain
                breakdown["htf_alignment"]["score"] += gain * 5.0
                reasons.append("Daily EMA200 confirms bearish direction")
            else:
                warnings.append("Higher timeframe does not confirm direction")
        except (IndexError, KeyError):
            pass

    # Factor 8: Breakout quality (+2)
    try:
        loc = df.index.get_loc(idx)
        lookback = 20
        if loc >= lookback:
            recent = df.iloc[loc - lookback: loc]
            if is_buy and close > recent["high"].max():
                gain = weights["breakout_quality"]
                score += gain
                breakdown["structure_quality"]["score"] += gain * 4.0
                reasons.append("Clean breakout above prior 20-bar high")
            elif not is_buy and close < recent["low"].min():
                gain = weights["breakout_quality"]
                score += gain
                breakdown["structure_quality"]["score"] += gain * 4.0
                reasons.append("Clean breakdown below prior 20-bar low")
    except (KeyError, IndexError):
        pass

    # ── NEGATIVE FACTORS ─────────────────────────────────────────────────────

    # Penalty 1: Sideways market (-3)
    if regime == MarketRegime.SIDEWAYS.value:
        penalty = abs(config.PENALTY_SIDEWAYS) * weights["penalty_scale"]
        score -= penalty
        breakdown["chop_penalty"]["score"] += penalty * 2.0
        warnings.append("Choppy/sideways market detected")

    # Penalty 2: Low volatility (-2)
    if regime == MarketRegime.LOW_VOLATILITY.value:
        penalty = abs(config.PENALTY_LOW_VOL) * weights["penalty_scale"]
        score -= penalty
        breakdown["chop_penalty"]["score"] += penalty * 1.5
        warnings.append("Low volatility regime — limited opportunity")

    # Penalty 3: Conflicting structure (-2)
    if not pd.isna(vwap) and not pd.isna(ema_200):
        vwap_says_buy = close > vwap
        ema_says_buy = close > ema_200
        if vwap_says_buy != ema_says_buy:
            penalty = abs(config.PENALTY_CONFLICTING) * weights["penalty_scale"]
            score -= penalty
            breakdown["chop_penalty"]["score"] += penalty * 1.5
            warnings.append("VWAP and EMA200 disagree on direction")

    # Penalty 4: Repeated rejections (-2)
    failed_breakouts = row.get("failed_breakout_count", 0)
    if not pd.isna(failed_breakouts) and failed_breakouts >= config.FAILED_BREAKOUT_MIN_COUNT:
        penalty = abs(config.PENALTY_REJECTION) * weights["penalty_scale"]
        score -= penalty
        breakdown["chop_penalty"]["score"] += penalty * 1.5
        warnings.append(f"{int(failed_breakouts)} failed breakouts in lookback — rejection zone")
    if row.get("chop_score", 0) >= config.CHOP_SCORE_BLOCK_THRESHOLD:
        penalty = 2.0 * weights["penalty_scale"]
        score -= penalty
        breakdown["chop_penalty"]["score"] += penalty * 2.0
        warnings.append("Composite anti-chop filter detects rotational trap risk")

    # ── NORMALIZE SCORE ──────────────────────────────────────────────────────
    # Map from [-max_negative, +max_positive] → [0, 100]
    raw_min = -max_negative
    raw_max = max_positive
    legacy_confidence = ((score - raw_min) / (raw_max - raw_min)) * 100
    reliability = _compute_reliability_score(row)
    confidence_pct = (0.35 * legacy_confidence) + (0.65 * reliability["score"])
    confidence_pct = max(0, min(100, round(confidence_pct, 1)))

    if reliability["score"] >= 70:
        reasons.append("Continuation quality passes reliability screen")
    else:
        warnings.append("Continuation reliability remains below institutional threshold")
    continuation_quality = float(row.get("continuation_quality_score", 0) or 0)
    breakdown["continuation_quality"]["score"] = min(20.0, continuation_quality / 5.0)
    if reliability["hard_block"]:
        warnings.append(reliability["block_reason"])

    # ── GRADE ────────────────────────────────────────────────────────────────
    if confidence_pct >= config.GRADE_APLUS_MIN:
        grade = "A+"
    elif confidence_pct >= config.GRADE_A_MIN:
        grade = "A"
    elif confidence_pct >= config.GRADE_B_MIN:
        grade = "B"
    else:
        grade = "Avoid"

    # ── RISK LEVEL ───────────────────────────────────────────────────────────
    if confidence_pct >= 80:
        risk_level = "low"
    elif confidence_pct >= 60:
        risk_level = "moderate"
    else:
        risk_level = "high"

    # ── DECISION ─────────────────────────────────────────────────────────────
    decision = "TRADE" if confidence_pct >= config.CONFIDENCE_TRADE_MIN and not reliability["hard_block"] else "REJECT"

    # If rejected, add explicit reason
    if decision == "REJECT" and not warnings:
        warnings.append("Insufficient confluence — confidence below threshold")

    if not reasons:
        reasons.append("Minimal alignment detected")

    # Clamp and format breakdown output
    for part in breakdown.values():
        part["score"] = round(float(max(0, min(part["max"], part["score"]))), 1)
    chop_penalty = -round(float(breakdown["chop_penalty"]["score"]), 1)
    breakdown_text = (
        f"Trend Quality: {breakdown['trend_quality']['score']:.1f}/25 | "
        f"VWAP Control: {breakdown['vwap_control']['score']:.1f}/20 | "
        f"Volume Confirmation: {breakdown['volume_confirmation']['score']:.1f}/20 | "
        f"Structure Quality: {breakdown['structure_quality']['score']:.1f}/15 | "
        f"Continuation Quality: {breakdown['continuation_quality']['score']:.1f}/20 | "
        f"Reliability: {reliability['score']:.1f}/100 | "
        f"Chop Penalty: {chop_penalty:.1f} | "
        f"Final Confidence: {confidence_pct:.1f}%"
    )
    market_narrative = _build_market_narrative(signal, regime, reasons, warnings)

    return {
        "confidence_pct": confidence_pct,
        "grade": grade,
        "risk_level": risk_level,
        "decision": decision,
        "reasons": reasons,
        "warnings": warnings,
        "breakdown": {
            "trend_quality": breakdown["trend_quality"]["score"],
            "vwap_control": breakdown["vwap_control"]["score"],
            "volume_confirmation": breakdown["volume_confirmation"]["score"],
            "structure_quality": breakdown["structure_quality"]["score"],
            "continuation_quality": breakdown["continuation_quality"]["score"],
            "htf_alignment": breakdown["htf_alignment"]["score"],
            "chop_penalty": chop_penalty,
        },
        "breakdown_text": breakdown_text,
        "market_narrative": market_narrative,
    }


def get_latest_signal_explanation(df: pd.DataFrame) -> Optional[dict]:
    """
    Get a full explanation of the most recent signal.

    Returns a dict suitable for the dashboard's SignalExplainer component.
    """
    signal_rows = df[df["signal"].notna()]
    if signal_rows.empty:
        return {
            "signal": "NO SIGNAL",
            "confidence_pct": 0,
            "grade": "N/A",
            "risk_level": "N/A",
            "decision": "WAIT",
            "reasons": ["No signal conditions met"],
            "warnings": ["Waiting for clean setup"],
            "timestamp": None,
            "confidence_breakdown": "Trend Quality: 0/25 | VWAP Control: 0/20 | Volume Confirmation: 0/20 | Structure Quality: 0/15 | Chop Penalty: 0 | Final Confidence: 0%",
            "market_narrative": "Market conditions remain observational. No directional trigger has achieved institutional confluence.",
        }

    last = signal_rows.iloc[-1]
    reasons_str = last.get("reasons", "")
    warnings_str = last.get("warnings", "")

    return {
        "signal": last["signal"],
        "confidence_pct": float(last.get("confidence_pct", 0)),
        "grade": last.get("grade", "N/A"),
        "risk_level": last.get("risk_level", "N/A"),
        "decision": last.get("decision", "REJECT"),
        "reasons": reasons_str.split("|") if reasons_str else [],
        "warnings": warnings_str.split("|") if warnings_str else [],
        "timestamp": str(last.name) if hasattr(last, "name") else None,
        "confidence_breakdown": last.get("confidence_breakdown", ""),
        "market_narrative": last.get("market_narrative", ""),
        "confidence_momentum": float(last.get("confidence_momentum", 0) or 0),
    }


def _get_adaptive_weights(regime: str, row: pd.Series) -> dict:
    trend_regimes = {MarketRegime.TRENDING_UP.value, MarketRegime.TRENDING_DOWN.value}
    expansion_regimes = {MarketRegime.EXPANSION.value, MarketRegime.HIGH_VOLATILITY.value}
    compression_regimes = {MarketRegime.SIDEWAYS.value, MarketRegime.COMPRESSION.value, MarketRegime.LOW_VOLATILITY.value}

    weights = {
        "ema_trend": float(config.WEIGHT_EMA_TREND),
        "ema_partial": 1.0,
        "vwap_control": float(config.WEIGHT_VWAP_CONTROL),
        "vwap_partial": 1.0,
        "volume": float(config.WEIGHT_VOLUME),
        "volume_partial": 1.0,
        "candle_quality": float(config.WEIGHT_CANDLE_QUALITY),
        "trend_consistency": float(config.WEIGHT_TREND_CONSISTENCY),
        "atr_expansion": float(config.WEIGHT_ATR_EXPANSION),
        "htf_alignment": float(config.WEIGHT_HTF_ALIGNMENT),
        "breakout_quality": float(config.WEIGHT_BREAKOUT_QUALITY),
        "penalty_scale": 1.0,
    }

    slope = abs(float(row.get("ema_slope", 0) or 0))
    atr_ratio = float(row.get("atr_ratio", 1) or 1)

    if regime in trend_regimes:
        weights["ema_trend"] *= 1.2
        weights["trend_consistency"] *= 1.2
        weights["breakout_quality"] *= 1.1
    if regime in expansion_regimes:
        weights["volume"] *= 1.25
        weights["atr_expansion"] *= 1.3
    if regime in compression_regimes:
        weights["vwap_control"] *= 1.15
        weights["breakout_quality"] *= 1.25
        weights["penalty_scale"] *= 1.35

    if slope < config.REGIME_SLOPE_THRESHOLD:
        weights["penalty_scale"] *= 1.15
    if atr_ratio < 1.0:
        weights["penalty_scale"] *= 1.1
    return weights


def _compute_reliability_score(row: pd.Series) -> dict:
    continuation_quality = float(row.get("continuation_quality_score", 0) or 0)
    follow = _clip01(row.get("breakout_follow_through", 0.0))
    efficiency = _clip01(row.get("directional_efficiency", 0.0))
    stability = _clip01(row.get("trend_stability", 0.0))
    overlap = _clip01(row.get("candle_overlap_pct", 1.0))
    chop = _clip01(row.get("chop_score", 1.0))
    vwap_slope = abs(float(row.get("vwap_slope_norm", 0.0) or 0.0))
    ema_slope = abs(float(row.get("ema_slope", 0.0) or 0.0))
    failed_breakouts_raw = row.get("failed_breakout_count", 999)
    failed_breakouts = 999.0 if pd.isna(failed_breakouts_raw) else float(failed_breakouts_raw)
    regime = row.get("regime", "")

    vwap_quality = min(1.0, vwap_slope / max(config.EXEC_MIN_ABS_VWAP_SLOPE * 4, 1e-6))
    ema_quality = min(1.0, ema_slope / max(config.EXEC_MIN_ABS_EMA_SLOPE * 4, 1e-6))
    chop_quality = 1.0 - min(1.0, chop / max(config.EXEC_MAX_CHOP_SCORE, 1e-6))
    overlap_quality = 1.0 - min(1.0, overlap / max(config.EXEC_MAX_OVERLAP_DENSITY, 1e-6))

    score = 100 * (
        0.24 * follow
        + 0.20 * efficiency
        + 0.18 * _clip01(continuation_quality / 100)
        + 0.18 * chop_quality
        + 0.10 * stability
        + 0.08 * overlap_quality
        + 0.05 * vwap_quality
        + 0.05 * ema_quality
    )

    block_reason = ""
    hard_block = False
    if regime in {MarketRegime.SIDEWAYS.value, MarketRegime.COMPRESSION.value, MarketRegime.LOW_VOLATILITY.value}:
        hard_block = True
        block_reason = "Execution veto: regime is not eligible for continuation trades"
    elif failed_breakouts > config.EXEC_MAX_FAILED_BREAKOUTS:
        hard_block = True
        block_reason = "Execution veto: recent failed breakout memory remains elevated"
    elif follow < config.EXEC_MIN_BREAKOUT_FOLLOW_THROUGH:
        hard_block = True
        block_reason = "Execution veto: breakout follow-through is too weak"
    elif efficiency < config.EXEC_MIN_DIRECTIONAL_EFFICIENCY:
        hard_block = True
        block_reason = "Execution veto: directional efficiency is too low"
    elif chop > config.EXEC_MAX_CHOP_SCORE:
        hard_block = True
        block_reason = "Execution veto: composite chop score is too high"
    elif continuation_quality < config.EXEC_MIN_CONTINUATION_QUALITY:
        hard_block = True
        block_reason = "Execution veto: continuation quality is below threshold"

    return {"score": round(float(max(0, min(100, score))), 1), "hard_block": hard_block, "block_reason": block_reason}


def _clip01(value) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(max(0.0, min(1.0, value)))
    except (TypeError, ValueError):
        return 0.0


def _build_market_narrative(signal: str, regime: str, reasons: list[str], warnings: list[str]) -> str:
    direction = "bullish" if signal == "BUY" else "bearish"
    if warnings:
        return (
            f"Directional pressure appears {direction}, but execution quality is constrained by "
            f"{warnings[0].lower()}."
        )
    if reasons:
        return (
            f"Directional pressure remains structurally {direction} as "
            f"{reasons[0].lower()} and confluence stays intact."
        )
    return "Market state is neutral and waiting for cleaner directional acceptance."
