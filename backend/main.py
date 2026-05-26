from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import math
import numpy as np
import logging
from typing import Any

import config
from engines import data_engine, indicator_engine, regime_engine, signal_engine, confidence_engine, backtest_engine, continuation_engine
from models import schemas

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="TradeIQ API", description="Institutional Trade Intelligence Engine")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_data_for_json(df):
    """Convert NaN/Inf values to None for JSON serialization."""
    df_clean = df.replace([np.inf, -np.inf], np.nan)
    # Cast to object so None is preserved instead of coerced back to NaN in float columns.
    df_clean = df_clean.astype(object).where(pd.notnull(df_clean), None)
    return df_clean.reset_index()

import pandas as pd # Needed for notnull inside clean_data_for_json

def sanitize_for_json(value: Any) -> Any:
    """Recursively replace NaN/Inf values with None so JSON encoding is always compliant."""
    if isinstance(value, dict):
        return {k: sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_json(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize_for_json(v) for v in value]
    if isinstance(value, (np.floating, float)):
        if not math.isfinite(float(value)):
            return None
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if value is None:
        return None
    return value

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "TradeIQ Engine is running"}

@app.get("/api/analyze", response_model=schemas.AnalysisResponse)
def analyze(
    ticker: str = Query(config.DEFAULT_TICKER, description="Stock ticker symbol"),
    timeframe: str = Query(config.DEFAULT_TIMEFRAME, description="Timeframe (e.g., 1m, 5m, 1h, 1d)"),
    period: str = Query(config.DEFAULT_PERIOD, description="Data period (e.g., 1mo, 1y)")
):
    try:
        # 1. Fetch Data
        df = data_engine.fetch_ohlcv(ticker, timeframe, period)
        htf_df = data_engine.fetch_higher_timeframe(ticker, period="2y") # Fixed period for HTF to ensure enough data

        # 2. Compute Indicators
        df = indicator_engine.compute_all(df)

        # 3. Classify Regime
        df = regime_engine.classify_regime(df)

        # 4. Compute continuation quality
        df = continuation_engine.compute_continuation_quality(df)

        # 5. Generate Raw Signals
        df = signal_engine.generate_signals(df)

        # 6. Score Signals (Confidence)
        df = confidence_engine.score_signals(df, htf_df)

        # Build Response
        current_price = df.iloc[-1]["close"]
        current_regime = df.iloc[-1]["regime"]
        is_choppy = df.iloc[-1]["is_choppy"]

        regime_analysis = schemas.RegimeAnalysis(
            current_regime=current_regime,
            description=regime_engine.get_regime_description(current_regime),
            is_choppy=bool(is_choppy)
        )

        signal_summary = signal_engine.get_signal_summary(df)
        latest_signal_dict = confidence_engine.get_latest_signal_explanation(df)
        latest_signal = schemas.SignalAnalysis(**latest_signal_dict)

        # Prepare chart data (OHLCV + key indicators)
        chart_df = clean_data_for_json(df)
        # Rename 'Date' or 'Datetime' column to 'time' for lightweight-charts
        time_col = chart_df.columns[0]
        chart_df = chart_df.rename(columns={time_col: 'time'})
        # Convert timestamp to string ISO format
        chart_df['time'] = chart_df['time'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Select columns to send to frontend to reduce payload size
        cols_to_keep = ['time', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'ema_200', 'signal', 'confidence_pct', 'decision']
        chart_data = chart_df[cols_to_keep].to_dict(orient="records")


        response = schemas.AnalysisResponse(
            ticker=ticker,
            timeframe=timeframe,
            period=period,
            current_price=float(current_price),
            signal_summary=signal_summary,
            regime=regime_analysis,
            latest_signal=latest_signal,
            chart_data=chart_data
        )
        return sanitize_for_json(response.model_dump())

    except ValueError as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Internal server error during analysis")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/backtest", response_model=schemas.BacktestResponse)
def backtest(
    ticker: str = Query(config.DEFAULT_TICKER, description="Stock ticker symbol"),
    timeframe: str = Query(config.DEFAULT_TIMEFRAME, description="Timeframe (e.g., 1m, 5m, 1h, 1d)"),
    period: str = Query(config.DEFAULT_PERIOD, description="Data period (e.g., 1mo, 1y)")
):
    try:
        # Need the full pipeline before backtesting
        df = data_engine.fetch_ohlcv(ticker, timeframe, period)
        htf_df = data_engine.fetch_higher_timeframe(ticker, period="2y")
        df = indicator_engine.compute_all(df)
        df = regime_engine.classify_regime(df)
        df = continuation_engine.compute_continuation_quality(df)
        df = signal_engine.generate_signals(df)
        df = confidence_engine.score_signals(df, htf_df)

        metrics = backtest_engine.run_backtest(df)

        response = schemas.BacktestResponse(
            ticker=ticker,
            timeframe=timeframe,
            period=period,
            metrics=metrics
        )
        return sanitize_for_json(response.model_dump())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Internal server error during backtest")
        raise HTTPException(status_code=500, detail="Internal server error")


# ─── Quant Labs Research API Endpoints ────────────────────────────────────────

@app.get("/api/labs/long_horizon_validation")
def get_long_horizon_validation(
    ticker: str = Query("SPY"),
    timeframe: str = Query("1d"),
    period: str = Query("10y")
):
    """Run and log a 3y-10y rolling walk-forward validation run."""
    try:
        from research import long_horizon_validation, quant_tooling
        results = long_horizon_validation.run_long_horizon_validation(ticker, timeframe, period)
        
        # Save experiment run snapshot automatically
        run_id = quant_tooling.save_experiment_run(ticker, timeframe, period, results)
        results["run_id"] = run_id
        
        return sanitize_for_json(results)
    except Exception as e:
        logger.exception("Error in long horizon validation API")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/labs/forward_journal")
def get_forward_journal(
    ticker: str = Query("SPY"),
    timeframe: str = Query("15m"),
    period: str = Query("60d"),
    limit: int = Query(50)
):
    """Fetch live paper trading observations and active simulation metrics."""
    try:
        from research import forward_paper_engine
        
        # Pull latest live observation snapshot
        obs = forward_paper_engine.latest_observation(ticker, timeframe, period)
        # Log to the persistent journal automatically
        forward_paper_engine.append_observation(forward_paper_engine.JOURNAL_PATH, obs)
        
        # Get full persistent log history
        history = forward_paper_engine.get_journal_history(limit)
        
        return sanitize_for_json({
            "latest_observation": obs,
            "journal_history": history
        })
    except Exception as e:
        logger.exception("Error in forward journal API")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/labs/regime_diagnostics")
def get_regime_diagnostics(
    ticker: str = Query("SPY"),
    timeframe: str = Query("1d"),
    period: str = Query("3y")
):
    """Compute Markov regime transition matrices and veto interaction statistics."""
    try:
        df = data_engine.fetch_ohlcv(ticker, timeframe, period)
        df = indicator_engine.compute_all(df)
        df = regime_engine.classify_regime(df)
        df = continuation_engine.compute_continuation_quality(df)
        
        transition_matrix = regime_engine.compute_transition_matrix(df)
        veto_analytics = regime_engine.compute_veto_analytics(df)
        
        return sanitize_for_json({
            "ticker": ticker,
            "timeframe": timeframe,
            "transition_matrix": transition_matrix,
            "veto_analytics": veto_analytics
        })
    except Exception as e:
        logger.exception("Error in regime diagnostics API")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/labs/confidence_calibration")
def get_confidence_calibration(
    ticker: str = Query("SPY"),
    timeframe: str = Query("1d"),
    period: str = Query("3y")
):
    """Construct expectancy-vs-confidence calibration curves and ECE metrics."""
    try:
        from research import confidence_calibration
        df = data_engine.fetch_ohlcv(ticker, timeframe, period)
        htf_df = data_engine.fetch_higher_timeframe(ticker, period="2y")
        df = indicator_engine.compute_all(df)
        df = regime_engine.classify_regime(df)
        df = continuation_engine.compute_continuation_quality(df)
        df = signal_engine.generate_signals(df)
        df = confidence_engine.score_signals(df, htf_df)
        
        metrics = backtest_engine.run_backtest(df)
        calibration_stats = confidence_calibration.analyze_confidence_calibration(metrics.get("trade_history", []))
        
        # Check if ML calibration engine is active to append details
        ml_active = getattr(config, "USE_ML_CALIBRATION", False)
        ml_stats = {}
        if ml_active:
            try:
                from engines import ml_calibration_engine
                ml_stats = ml_calibration_engine.calibrate_confidence_with_ml(df, htf_df)
            except Exception:
                pass

        return sanitize_for_json({
            "ticker": ticker,
            "timeframe": timeframe,
            "calibration": calibration_stats,
            "ml_calibrator": ml_stats
        })
    except Exception as e:
        logger.exception("Error in confidence calibration API")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/labs/ablation_report")
def get_ablation_report(
    ticker: str = Query("SPY"),
    timeframe: str = Query("1d"),
    period: str = Query("3y")
):
    """Compute marginal filter contributions and factor dependency graphs."""
    try:
        from research import factor_ablation
        results = factor_ablation.run_ablation_analysis(ticker, timeframe, period)
        return sanitize_for_json(results)
    except Exception as e:
        logger.exception("Error in factor ablation API")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/labs/experiments")
def get_experiment_runs():
    """Fetch completed quant validation experiment history."""
    try:
        from research import quant_tooling
        runs = quant_tooling.list_experiment_runs()
        return sanitize_for_json({"experiment_runs": runs})
    except Exception as e:
        logger.exception("Error in experiments history API")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/labs/generate_report")
def post_generate_report(run_id: str = Query(...)):
    """Generate a markdown validation audit report for the specified run."""
    try:
        from research import quant_tooling
        report_path = quant_tooling.generate_markdown_audit_report(run_id)
        return {"status": "success", "report_path": report_path}
    except Exception as e:
        logger.exception("Error in audit report generator API")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/labs/toggle_ml")
def post_toggle_ml(enabled: bool = Query(...)):
    """Dynamically toggle explainable machine learning confidence calibration."""
    try:
        config.USE_ML_CALIBRATION = enabled
        return {"status": "success", "ml_calibration_active": config.USE_ML_CALIBRATION}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
