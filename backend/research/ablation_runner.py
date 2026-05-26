"""
Controlled factor ablation runner.

Each variant modifies one gate at a time and records the portfolio-level change.
This is research tooling, not live strategy logic.
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

import config
from research.validation_runner import ASSETS, TIMEFRAME_PERIODS
from research.pipeline import fetch_and_analyze


VARIANTS = {
    "baseline": {},
    "remove_directional_efficiency": {"EXEC_MIN_DIRECTIONAL_EFFICIENCY": 0.0},
    "remove_overlap_density": {"EXEC_MAX_OVERLAP_DENSITY": 1.0},
    "remove_follow_through": {"EXEC_MIN_BREAKOUT_FOLLOW_THROUGH": 0.0},
    "remove_continuation_quality": {"EXEC_MIN_CONTINUATION_QUALITY": 0.0},
    "remove_vwap_flatness": {"EXEC_MIN_ABS_VWAP_SLOPE": 0.0},
    "remove_trend_stability": {"EXEC_MIN_TREND_STABILITY": 0.0},
    "remove_failed_breakout_veto": {"EXEC_MAX_FAILED_BREAKOUTS": 999},
    "remove_chop_score_veto": {"EXEC_MAX_CHOP_SCORE": 1.0},
}


@contextmanager
def patched(values: dict):
    old_values = {key: getattr(config, key) for key in values}
    for key, value in values.items():
        setattr(config, key, value)
    try:
        yield
    finally:
        for key, value in old_values.items():
            setattr(config, key, value)


def run_variant(values: dict) -> dict:
    rows = []
    with patched(values):
        for asset, ticker in ASSETS.items():
            for timeframe, period in TIMEFRAME_PERIODS.items():
                try:
                    analyzed, metrics = fetch_and_analyze(ticker, timeframe, period)
                    sideways_trades = sum(
                        1
                        for trade in metrics.get("trade_history", [])
                        if trade.get("status") == "taken" and trade.get("regime") == "sideways"
                    )
                    rows.append(
                        {
                            "asset": asset,
                            "timeframe": timeframe,
                            "signals": int(analyzed["signal"].notna().sum()),
                            "trades": int(metrics.get("trades_taken", 0)),
                            "pnl_r": float(metrics.get("total_pnl_r", 0) or 0),
                            "drawdown_r": float(metrics.get("max_drawdown_r", 0) or 0),
                            "sharpe": float(metrics.get("sharpe_ratio", 0) or 0),
                            "sideways_trades": sideways_trades,
                        }
                    )
                except Exception as exc:
                    rows.append({"asset": asset, "timeframe": timeframe, "error": str(exc)})

    frame = pd.DataFrame(rows)
    valid = frame[frame["error"].isna()] if "error" in frame.columns else frame
    return {
        "runs": int(len(valid)),
        "trades": int(valid["trades"].sum()) if not valid.empty else 0,
        "pnl_r": float(valid["pnl_r"].sum()) if not valid.empty else 0.0,
        "avg_drawdown_r": float(valid["drawdown_r"].mean()) if not valid.empty else 0.0,
        "avg_sharpe": float(valid["sharpe"].mean()) if not valid.empty else 0.0,
        "sideways_trades": int(valid["sideways_trades"].sum()) if not valid.empty else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation_reports/ablation_research.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    results = {name: run_variant(values) for name, values in VARIANTS.items()}
    output.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
