"""
Reproducible validation runner for TradeIQ.

Usage:
    python -m research.validation_runner --output validation_reports/research_run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.pipeline import fetch_and_analyze


ASSETS = {
    "SPY": "SPY",
    "QQQ": "QQQ",
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "BTC-USD": "BTC-USD",
    "ETH-USD": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "NVDA": "NVDA",
}

TIMEFRAME_PERIODS = {
    "5m": "60d",
    "15m": "60d",
    "1h": "2y",
    "4h": "2y",
    "1d": "10y",
}


def summarize(asset: str, ticker: str, timeframe: str, split: str, df: pd.DataFrame, metrics: dict) -> dict:
    signals = df[df["signal"].notna()]
    trades = [t for t in metrics.get("trade_history", []) if t.get("status") == "taken"]
    if len(trades) > 2:
        confidence = np.array([float(t.get("confidence_pct", 0)) for t in trades])
        pnl = np.array([float(t.get("pnl_r", 0)) for t in trades])
        corr = float(np.corrcoef(confidence, pnl)[0, 1]) if confidence.std() > 0 and pnl.std() > 0 else 0.0
    else:
        corr = 0.0

    return {
        "asset": asset,
        "ticker": ticker,
        "timeframe": timeframe,
        "split": split,
        "bars": len(df),
        "signals": int(len(signals)),
        "trades_taken": int(metrics.get("trades_taken", 0)),
        "trades_rejected": int(metrics.get("trades_rejected", 0)),
        "win_rate": float(metrics.get("win_rate", 0) or 0),
        "profit_factor": metrics.get("profit_factor", 0),
        "sharpe_ratio": float(metrics.get("sharpe_ratio", 0) or 0),
        "max_drawdown_r": float(metrics.get("max_drawdown_r", 0) or 0),
        "total_pnl_r": float(metrics.get("total_pnl_r", 0) or 0),
        "signal_rate_pct": float(len(signals) / max(len(df), 1) * 100),
        "confidence_pnl_corr": corr,
    }


def split_frame(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    if df.index.max() >= pd.Timestamp("2025-01-01") and df.index.min() <= pd.Timestamp("2024-12-31"):
        return [
            ("in_sample", df[df.index < pd.Timestamp("2025-01-01")]),
            ("out_of_sample", df[df.index >= pd.Timestamp("2025-01-01")]),
        ]
    cut = int(len(df) * 0.7)
    return [("in_sample", df.iloc[:cut]), ("out_of_sample", df.iloc[cut:])]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation_reports/research_run")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    failures: list[dict] = []
    for asset, ticker in ASSETS.items():
        for timeframe, period in TIMEFRAME_PERIODS.items():
            try:
                analyzed, metrics = fetch_and_analyze(ticker, timeframe, period)
                rows.append(summarize(asset, ticker, timeframe, "full", analyzed, metrics))
                for split_name, split_df in split_frame(analyzed):
                    from engines import backtest_engine

                    rows.append(summarize(asset, ticker, timeframe, split_name, split_df, backtest_engine.run_backtest(split_df)))
            except Exception as exc:
                failures.append({"asset": asset, "timeframe": timeframe, "error": str(exc)})

    matrix = pd.DataFrame(rows)
    matrix.to_csv(output / "validation_matrix.csv", index=False)

    full = matrix[matrix["split"] == "full"] if not matrix.empty else pd.DataFrame()
    summary = {
        "runs": int(len(full)),
        "failures": failures,
        "total_trades": int(full["trades_taken"].sum()) if not full.empty else 0,
        "avg_win_rate": float(full["win_rate"].mean()) if not full.empty else 0.0,
        "avg_sharpe": float(full["sharpe_ratio"].mean()) if not full.empty else 0.0,
        "avg_signal_rate_pct": float(full["signal_rate_pct"].mean()) if not full.empty else 0.0,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
