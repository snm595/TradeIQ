"""
TradeIQ — Backtest Engine

Simple, honest backtesting with no overfitting tricks.

Rules:
  - Entry on signal bar's close
  - Exit on opposite signal OR stop-loss/take-profit hit
  - Stop loss: 2× ATR from entry
  - Take profit: 3× ATR from entry (1.5:1 R:R)
  - Only trades that pass confidence filter are taken

Reports metrics honestly, including both taken and rejected signals.
"""

import pandas as pd
import numpy as np
from typing import Optional
import config


def run_backtest(df: pd.DataFrame) -> dict:
    """
    Run a full backtest on the analyzed DataFrame.

    Args:
        df: DataFrame with signals, confidence, and indicators.

    Returns:
        dict with performance metrics and trade history.
    """
    trades = _simulate_trades(df)
    metrics = _compute_metrics(trades, df)
    return metrics


def _simulate_trades(df: pd.DataFrame) -> list[dict]:
    """
    Walk through the data and simulate trades.

    Only signals with decision == "TRADE" are taken.
    Rejected signals are tracked separately.
    """
    trades = []
    active_trade = None
    consecutive_losses = 0

    for i in range(len(df)):
        row = df.iloc[i]
        idx = df.index[i]

        # Check if active trade hits SL or TP
        if active_trade is not None:
            trade_closed, result = _check_exit(active_trade, row, idx)
            if trade_closed:
                trades.append(result)
                active_trade = None

        # Check for new signal
        signal = row.get("signal")
        if pd.notna(signal):
            decision = row.get("decision", "REJECT")
            confidence = row.get("confidence_pct", 0)

            # Close any active trade on opposite signal
            if active_trade is not None:
                closed = _force_close(active_trade, row, idx, "opposite_signal")
                trades.append(closed)
                active_trade = None
                if closed.get("pnl_r", 0) <= 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0

            # Record trade (taken or rejected)
            atr = row.get("atr", 0)
            if pd.isna(atr) or atr <= 0:
                atr = abs(row["high"] - row["low"])

            entry_price = row["close"]
            is_buy = signal == "BUY"

            trade_record = {
                "entry_time": str(idx),
                "signal": signal,
                "entry_price": float(entry_price),
                "atr_at_entry": float(atr),
                "confidence_pct": float(confidence) if not pd.isna(confidence) else 0,
                "grade": row.get("grade", "N/A"),
                "decision": decision,
                "regime": row.get("regime", "unknown"),
            }

            if decision == "TRADE":
                risk_scale = config.RISK_REDUCTION_FACTOR if consecutive_losses >= config.MAX_CONSECUTIVE_LOSS_GUARD else 1.0
                # Set SL and TP
                sl_distance = atr * config.STOP_LOSS_ATR_MULT * risk_scale
                tp_distance = atr * config.TAKE_PROFIT_ATR_MULT * risk_scale

                if is_buy:
                    sl = entry_price - sl_distance
                    tp = entry_price + tp_distance
                else:
                    sl = entry_price + sl_distance
                    tp = entry_price - tp_distance

                active_trade = {
                    **trade_record,
                    "stop_loss": float(sl),
                    "take_profit": float(tp),
                    "is_buy": is_buy,
                    "status": "taken",
                    "risk_scale": risk_scale,
                }
            else:
                # Signal was rejected — record but don't trade
                trade_record["status"] = "rejected"
                trade_record["exit_time"] = str(idx)
                trade_record["exit_price"] = float(entry_price)
                trade_record["pnl"] = 0.0
                trade_record["pnl_r"] = 0.0
                trade_record["exit_reason"] = "rejected_by_confidence"
                trades.append(trade_record)

    # Close any remaining open trade at last bar
    if active_trade is not None:
        last_row = df.iloc[-1]
        last_idx = df.index[-1]
        closed = _force_close(active_trade, last_row, last_idx, "end_of_data")
        trades.append(closed)



    return trades


def _check_exit(trade: dict, row: pd.Series, idx) -> tuple[bool, Optional[dict]]:
    """Check if a bar triggers the SL or TP of an active trade."""
    is_buy = trade["is_buy"]
    sl = trade["stop_loss"]
    tp = trade["take_profit"]
    entry_price = trade["entry_price"]

    high = row["high"]
    low = row["low"]

    # Check stop loss
    if is_buy and low <= sl:
        return True, _close_trade(trade, sl, idx, "stop_loss")
    if not is_buy and high >= sl:
        return True, _close_trade(trade, sl, idx, "stop_loss")

    # Check take profit
    if is_buy and high >= tp:
        return True, _close_trade(trade, tp, idx, "take_profit")
    if not is_buy and low <= tp:
        return True, _close_trade(trade, tp, idx, "take_profit")

    return False, None


def _close_trade(trade: dict, exit_price: float, exit_time, reason: str) -> dict:
    """Close a trade with the given exit details."""
    entry = trade["entry_price"]
    is_buy = trade["is_buy"]
    atr = trade["atr_at_entry"]

    # Execution realism: apply spread + slippage bps to both sides.
    spread_cost = (config.SPREAD_BPS / 10000.0) * entry
    slippage_cost = (config.SLIPPAGE_BPS / 10000.0) * entry
    total_cost = spread_cost + slippage_cost

    if is_buy:
        pnl = (exit_price - entry) - total_cost
    else:
        pnl = (entry - exit_price) - total_cost

    # P&L in R multiples (risk units)
    risk = atr * config.STOP_LOSS_ATR_MULT
    pnl_r = pnl / risk if risk > 0 else 0

    return {
        "entry_time": trade["entry_time"],
        "exit_time": str(exit_time),
        "signal": trade["signal"],
        "entry_price": entry,
        "exit_price": float(exit_price),
        "stop_loss": trade["stop_loss"],
        "take_profit": trade["take_profit"],
        "atr_at_entry": atr,
        "confidence_pct": trade["confidence_pct"],
        "grade": trade["grade"],
        "decision": trade["decision"],
        "regime": trade.get("regime", "unknown"),
        "status": "taken",
        "pnl": round(float(pnl), 4),
        "pnl_r": round(float(pnl_r), 2),
        "exit_reason": reason,
        "risk_scale": trade.get("risk_scale", 1.0),
    }


def _force_close(trade: dict, row: pd.Series, idx, reason: str) -> dict:
    """Force close a trade at the current bar's close."""
    return _close_trade(trade, row["close"], idx, reason)


def _compute_metrics(trades: list[dict], df: pd.DataFrame) -> dict:
    """
    Compute performance metrics from the trade list.

    Returns honest, unbiased statistics.
    """
    taken_trades = [t for t in trades if t.get("status") == "taken"]
    rejected_trades = [t for t in trades if t.get("status") == "rejected"]

    if not taken_trades:
        return {
            "total_signals": len(trades),
            "trades_taken": 0,
            "trades_rejected": len(rejected_trades),
            "win_rate": 0,
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0,
            "avg_rr": 0,
            "total_pnl_r": 0,
            "trade_history": trades,
            "regime_performance": {},
            "confidence_bucket_performance": {},
            "equity_curve_r": [],
        }

    # Basic counts
    wins = [t for t in taken_trades if t["pnl"] > 0]
    losses = [t for t in taken_trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(taken_trades) * 100

    # Profit factor
    gross_profit = sum(t["pnl_r"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl_r"] for t in losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0
    )

    # Average R:R
    avg_rr = np.mean([t["pnl_r"] for t in taken_trades])

    # Total P&L in R
    total_pnl_r = sum(t["pnl_r"] for t in taken_trades)

    # Max drawdown (equity curve based)
    equity_curve = []
    running = 0
    for t in taken_trades:
        running += t["pnl_r"]
        equity_curve.append(running)

    peak = 0
    max_dd = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (using R multiples as returns)
    returns = [t["pnl_r"] for t in taken_trades]
    if len(returns) > 1:
        mean_r = np.mean(returns)
        std_r = np.std(returns, ddof=1)
        sharpe = mean_r / std_r if std_r > 0 else 0
    else:
        sharpe = 0

    # Exit reason breakdown
    exit_reasons = {}
    for t in taken_trades:
        reason = t.get("exit_reason", "unknown")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    regime_performance = {}
    for t in taken_trades:
        reg = t.get("regime", "unknown")
        if reg not in regime_performance:
            regime_performance[reg] = {"trades": 0, "pnl_r": 0.0, "wins": 0}
        regime_performance[reg]["trades"] += 1
        regime_performance[reg]["pnl_r"] += t["pnl_r"]
        if t["pnl_r"] > 0:
            regime_performance[reg]["wins"] += 1
    for reg, stats in regime_performance.items():
        trades_n = max(stats["trades"], 1)
        stats["win_rate"] = round(stats["wins"] / trades_n * 100, 1)
        stats["pnl_r"] = round(float(stats["pnl_r"]), 2)

    confidence_bucket_performance = {"A+": [], "A": [], "B": [], "Avoid": []}
    for t in taken_trades:
        grade = t.get("grade", "Avoid")
        if grade not in confidence_bucket_performance:
            confidence_bucket_performance[grade] = []
        confidence_bucket_performance[grade].append(t["pnl_r"])
    confidence_bucket_performance = {
        k: {
            "trades": len(v),
            "avg_pnl_r": round(float(np.mean(v)), 2) if v else 0.0,
            "total_pnl_r": round(float(np.sum(v)), 2) if v else 0.0,
        }
        for k, v in confidence_bucket_performance.items()
    }

    return {
        "total_signals": len(trades),
        "trades_taken": len(taken_trades),
        "trades_rejected": len(rejected_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(float(profit_factor), 2) if profit_factor != float("inf") else "∞",
        "max_drawdown_r": round(float(max_dd), 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "avg_rr": round(float(avg_rr), 2),
        "total_pnl_r": round(float(total_pnl_r), 2),
        "exit_reasons": exit_reasons,
        "regime_performance": regime_performance,
        "confidence_bucket_performance": confidence_bucket_performance,
        "equity_curve_r": [round(float(x), 2) for x in equity_curve],
        "trade_history": trades,
    }
