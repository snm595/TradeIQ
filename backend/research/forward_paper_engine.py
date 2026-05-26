"""
TradeIQ — Forward Paper-Trading Simulator

Records live signal observations and simulates a realistic latency-aware paper-trading journal.
Tracks trade lifecycles, Maximum Adverse Excursion (MAE), Maximum Favorable Excursion (MFE),
slippage models, and regime transition sequences.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import json
from datetime import datetime, timezone
from pathlib import Path
import config
from research.pipeline import fetch_and_analyze


JOURNAL_PATH = Path("validation_reports/forward_paper_journal.jsonl")


def latest_observation(ticker: str, timeframe: str, period: str) -> dict:
    """
    Run analysis and generate a comprehensive paper-trading observation object.
    Includes simulated latency execution, slippage models, and MAE/MFE tracking.
    """
    analyzed, metrics = fetch_and_analyze(ticker, timeframe, period)
    
    last = analyzed.iloc[-1]
    signal_rows = analyzed[analyzed["signal"].notna()]
    latest_signal = signal_rows.iloc[-1] if not signal_rows.empty else None

    # Track MAE/MFE for all simulated trades in the backtest
    trade_history = metrics.get("trade_history", [])
    taken_trades = [t for t in trade_history if t.get("status") == "taken"]

    mae_mfe_trades = []
    for trade in taken_trades:
        try:
            entry_time = pd.Timestamp(trade["entry_time"])
            exit_time = pd.Timestamp(trade["exit_time"])
            trade_bars = analyzed.loc[entry_time:exit_time]
            
            if not trade_bars.empty:
                prices = trade_bars["close"].values
                entry_price = trade["entry_price"]
                atr = trade["atr_at_entry"]
                is_buy = trade["signal"] == "BUY"
                
                if is_buy:
                    worst_price = min(prices)
                    best_price = max(prices)
                    # MAE = entry - worst (expressed in R)
                    mae_r = (entry_price - worst_price) / (atr * config.STOP_LOSS_ATR_MULT)
                    # MFE = best - entry (expressed in R)
                    mfe_r = (best_price - entry_price) / (atr * config.STOP_LOSS_ATR_MULT)
                else:
                    worst_price = max(prices)
                    best_price = min(prices)
                    # MAE = worst - entry (expressed in R)
                    mae_r = (worst_price - entry_price) / (atr * config.STOP_LOSS_ATR_MULT)
                    # MFE = entry - best (expressed in R)
                    mfe_r = (entry_price - best_price) / (atr * config.STOP_LOSS_ATR_MULT)
                
                trade["mae_r"] = round(float(max(0.0, mae_r)), 2)
                trade["mfe_r"] = round(float(max(0.0, mfe_r)), 2)
            else:
                trade["mae_r"] = 0.0
                trade["mfe_r"] = 0.0
        except Exception:
            trade["mae_r"] = 0.0
            trade["mfe_r"] = 0.0
            
        mae_mfe_trades.append(trade)

    # 1. Latency-Aware Execution Simulation (Slippage Model)
    # Simulate a 150ms-400ms network execution latency
    simulated_latency_ms = int(np.random.randint(150, 450))
    # Slippage adjustment based on ATR (e.g. 5% of ATR added as latency penalty)
    atr_val = last.get("atr", 0.0)
    if pd.isna(atr_val) or atr_val <= 0:
        atr_val = last["close"] * 0.001
        
    simulated_slippage = float(0.05 * atr_val)

    latest_signal_data = {}
    if latest_signal is not None:
        raw_price = float(latest_signal["close"])
        is_buy = latest_signal.get("signal") == "BUY"
        # Worse price due to execution latency
        slippage_price = raw_price + simulated_slippage if is_buy else raw_price - simulated_slippage
        
        latest_signal_data = {
            "time": str(latest_signal.name),
            "signal": latest_signal.get("signal"),
            "decision": latest_signal.get("decision"),
            "confidence_pct": float(latest_signal.get("confidence_pct", 0.0)),
            "grade": latest_signal.get("grade", "N/A"),
            "raw_price": round(raw_price, 4),
            "executed_price": round(slippage_price, 4),
            "slippage_bps": round((simulated_slippage / raw_price) * 10000, 2),
            "latency_ms": simulated_latency_ms,
            "reasons": str(latest_signal.get("reasons", "")).split("|") if latest_signal.get("reasons") else [],
            "warnings": str(latest_signal.get("warnings", "")).split("|") if latest_signal.get("warnings") else []
        }

    # 2. Regime Transition sequence
    regime_sequence = analyzed["regime"].dropna().tail(5).tolist()

    return {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker,
        "timeframe": timeframe,
        "period": period,
        "bar_time": str(last.name),
        "close": float(last["close"]),
        "regime": last.get("regime"),
        "is_choppy": bool(last.get("is_choppy", False)),
        "chop_score": _num(last.get("chop_score")),
        "directional_efficiency": _num(last.get("directional_efficiency")),
        "breakout_follow_through": _num(last.get("breakout_follow_through")),
        "continuation_quality_score": _num(last.get("continuation_quality_score")),
        "latest_signal": latest_signal_data,
        "regime_sequence": regime_sequence,
        "backtest_metrics": {
            "total_trades": int(metrics.get("trades_taken", 0)),
            "win_rate": float(metrics.get("win_rate", 0.0)),
            "total_pnl_r": float(metrics.get("total_pnl_r", 0.0)),
            "max_drawdown_r": float(metrics.get("max_drawdown_r", 0.0)),
            "trades_list": mae_mfe_trades[-10:] # Keep last 10 for dashboard replay
        }
    }


def append_observation(path: Path, observation: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(observation, sort_keys=True) + "\n")


def get_journal_history(limit: int = 50) -> list[dict]:
    """Read the persistent JSONL paper journal file."""
    if not JOURNAL_PATH.exists():
        return []
    
    observations = []
    with JOURNAL_PATH.open("r") as fh:
        for line in fh:
            try:
                observations.append(json.loads(line.strip()))
            except Exception:
                continue
    return observations[-limit:]


def _num(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
