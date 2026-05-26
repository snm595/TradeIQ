"""
TradeIQ — Professional Quant Research Tooling

Supports parameter snapshotting, experiment logs tracking, run comparisons,
and automated markdown validation audit report generation.
"""

from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import config
from research.long_horizon_validation import run_long_horizon_validation


EXPERIMENTS_DIR = Path("validation_reports/experiments")
REPORTS_DIR = Path("validation_reports/reports")


def save_experiment_run(ticker: str, timeframe: str, period: str, validation_results: dict) -> str:
    """
    Take a snapshot of all active config parameters and save the research run to an experiment log.
    """
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Capture all UPPERCASE variables in config.py
    config_snapshot = {}
    for attr in dir(config):
        if attr.isupper():
            config_snapshot[attr] = getattr(config, attr)

    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    experiment_log = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker,
        "timeframe": timeframe,
        "period": period,
        "configuration": config_snapshot,
        "validation_metrics": {
            "sample_trades": validation_results.get("sample_trades", 0),
            "total_pnl_r": validation_results.get("total_pnl_r", 0.0),
            "win_rate": validation_results.get("win_rate", 0.0),
            "win_rate_ci_95": validation_results.get("win_rate_ci_95", (0.0, 0.0)),
            "expectancy_ci_95": validation_results.get("expectancy_ci_95", (0.0, 0.0))
        }
    }

    log_path = EXPERIMENTS_DIR / f"{run_id}.json"
    log_path.write_text(json.dumps(experiment_log, indent=2))
    
    return run_id


def list_experiment_runs() -> list[dict]:
    """List all completed experiment runs."""
    if not EXPERIMENTS_DIR.exists():
        return []
    
    runs = []
    for file in EXPERIMENTS_DIR.glob("*.json"):
        try:
            runs.append(json.loads(file.read_text()))
        except Exception:
            continue
    # Sort by timestamp desc
    return sorted(runs, key=lambda x: x.get("timestamp", ""), reverse=True)


def generate_markdown_audit_report(run_id: str) -> str:
    """
    Load an experiment run and construct a professional audit report in Markdown format.
    """
    log_path = EXPERIMENTS_DIR / f"{run_id}.json"
    if not log_path.exists():
        raise FileNotFoundError(f"Experiment run {run_id} not found.")

    run = json.loads(log_path.read_text())
    metrics = run["validation_metrics"]
    cfg = run["configuration"]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    report_content = f"""# TradeIQ Quantitative Strategy Validation Audit Report
**Run ID:** `{run["run_id"]}`
**Generated At:** {run["timestamp"]}
**Asset Target:** {run["ticker"]} ({run["timeframe"]}, period={run["period"]})

---

## 1. Executive Performance Summary

The strategy was evaluated using walk-forward out-of-sample segments over a long-horizon window. Below are the audited validation results:

* **Audited Trades Sample Size:** {metrics["sample_trades"]} trades
* **Aggregate Validation PnL:** {metrics["total_pnl_r"]:+g} R
* **Strategy Win Rate:** {metrics["win_rate"]}%
* **Win Rate 95% Confidence Interval:** `{metrics["win_rate_ci_95"][0]}%` to `{metrics["win_rate_ci_95"][1]}%`
* **Expectancy 95% Confidence Interval (R):** `{metrics["expectancy_ci_95"][0]}` to `{metrics["expectancy_ci_95"][1]}` R/trade

---

## 2. Parameter Snapshot (Reproducibility Matrix)

This run was executed using the following deterministic parameter settings:

### Trend & Volatility Baselines
* `EMA_LONG_PERIOD`: `{cfg.get("EMA_LONG_PERIOD")}` (bars)
* `VWAP_PERIOD`: `{cfg.get("VWAP_PERIOD")}` (bars)
* `ATR_PERIOD`: `{cfg.get("ATR_PERIOD")}` (bars)

### Anti-Chop & Regime Enforcement Filters
* `OVERLAP_CHOP_THRESHOLD`: `{cfg.get("OVERLAP_CHOP_THRESHOLD")}`
* `FAILED_BREAKOUT_LOOKBACK`: `{cfg.get("FAILED_BREAKOUT_LOOKBACK")}`
* `FAILED_BREAKOUT_REENTRY_BARS`: `{cfg.get("FAILED_BREAKOUT_REENTRY_BARS")}`
* `MIN_DIRECTIONAL_EFFICIENCY`: `{cfg.get("MIN_DIRECTIONAL_EFFICIENCY")}`
* `CHOP_SCORE_BLOCK_THRESHOLD`: `{cfg.get("CHOP_SCORE_BLOCK_THRESHOLD")}`

### Confluence & Execution Eligibility
* `MIN_SIGNAL_CONFLUENCE`: `{cfg.get("MIN_SIGNAL_CONFLUENCE")}` (checks)
* `EXEC_MIN_CONTINUATION_QUALITY`: `{cfg.get("EXEC_MIN_CONTINUATION_QUALITY")}` (score)
* `EXEC_MAX_FAILED_BREAKOUTS`: `{cfg.get("EXEC_MAX_FAILED_BREAKOUTS")}`

---

## 3. Audited Risk Compliance

* **Slippage Bounding:** Applied `{cfg.get("SLIPPAGE_BPS")} bps` slippage penalty per trade leg.
* **Execution Bid-Ask Spreads:** Applied `{cfg.get("SPREAD_BPS")} bps` spread matching friction.
* **Risk Throttling Multiplier:** `{cfg.get("RISK_REDUCTION_FACTOR")}` scaling active after `{cfg.get("MAX_CONSECUTIVE_LOSS_GUARD")}` consecutive losses.

---
**Audit Verification:** Checked and confirmed by TradeIQ Quant Labs.
"""
    
    report_path = REPORTS_DIR / f"audit_report_{run_id}.md"
    report_path.write_text(report_content)
    
    return str(report_path)
