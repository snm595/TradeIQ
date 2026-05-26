from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class SignalAnalysis(BaseModel):
    timestamp: Optional[str] = None
    signal: str
    confidence_pct: float
    grade: str
    risk_level: str
    decision: str
    reasons: List[str]
    warnings: List[str]
    confidence_breakdown: Optional[str] = None
    confidence_momentum: Optional[float] = None
    market_narrative: Optional[str] = None

class RegimeAnalysis(BaseModel):
    current_regime: str
    description: str
    is_choppy: bool

class AnalysisResponse(BaseModel):
    ticker: str
    timeframe: str
    period: str
    current_price: float
    signal_summary: Dict[str, Any]
    regime: RegimeAnalysis
    latest_signal: SignalAnalysis
    chart_data: List[Dict[str, Any]]  # OHLCV + Indicators

class BacktestResponse(BaseModel):
    ticker: str
    timeframe: str
    period: str
    metrics: Dict[str, Any]
