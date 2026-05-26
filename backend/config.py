"""
TradeIQ — Central Configuration

All tunable parameters in one place.
Philosophy: conservative defaults that prioritize precision over volume.
"""

# ─── Data Defaults ────────────────────────────────────────────────────────────
DEFAULT_TICKER = "SPY"
DEFAULT_TIMEFRAME = "1d"
DEFAULT_PERIOD = "1y"

# ─── Indicator Parameters ────────────────────────────────────────────────────
EMA_LONG_PERIOD = 200          # Trend direction filter
VWAP_PERIOD = 20               # Rolling VWAP lookback
VOLUME_EMA_PERIOD = 20         # Volume expansion baseline
ATR_PERIOD = 14                # Volatility measurement
EMA_SLOPE_LOOKBACK = 5         # Bars to measure EMA slope
ATR_AVG_PERIOD = 50            # ATR average for ratio calculation
CANDLE_OVERLAP_LOOKBACK = 14   # Bars to measure chop

# ─── Regime Detection Thresholds ──────────────────────────────────────────────
REGIME_SLOPE_THRESHOLD = 0.02       # Normalized EMA slope threshold for trending (calibrated for ATR-normalized slope)
ATR_HIGH_VOL_RATIO = 2.0            # ATR ratio above this → HIGH_VOLATILITY
ATR_LOW_VOL_RATIO = 0.5             # ATR ratio below this → LOW_VOLATILITY
ATR_EXPANSION_RATIO = 1.3           # ATR ratio above this → EXPANSION
ATR_COMPRESSION_RATIO = 0.7         # ATR ratio below this → COMPRESSION
OVERLAP_CHOP_THRESHOLD = 0.68       # Overlap % above this → SIDEWAYS
FAILED_BREAKOUT_LOOKBACK = 20       # Bars to track failed breakouts
FAILED_BREAKOUT_REENTRY_BARS = 3    # Must re-enter range within this many bars
FAILED_BREAKOUT_MIN_COUNT = 2       # Minimum failed breakouts → strong chop
VWAP_FLAT_SLOPE_THRESHOLD = 0.01    # Flat VWAP slope threshold (ATR-normalized)
MIN_DIRECTIONAL_EFFICIENCY = 0.35   # Below this indicates rotational/noisy movement
MIN_TREND_STABILITY = 0.55          # Fraction of bars aligned with trend direction
MAX_WICK_REJECTION_RATE = 0.55      # High wick rejection implies trap-prone environment
CHOP_SCORE_BLOCK_THRESHOLD = 0.62   # Composite anti-chop score threshold for NO-TRADE environment

# ─── Signal Thresholds ───────────────────────────────────────────────────────
VOLUME_EXPANSION_MULT = 1.2    # Volume must exceed EMA × this multiplier
VWAP_ACCEPTANCE_BARS = 3       # Consecutive bars above/below VWAP for acceptance
DIRECTION_LOCK = True          # Prevent consecutive same-direction signals
MIN_SIGNAL_CONFLUENCE = 3      # Minimum confluence checks that must pass to emit raw signal
EXEC_MAX_CHOP_SCORE = 0.60     # Hard execution veto above this composite chop score
EXEC_MAX_OVERLAP_DENSITY = 0.55
EXEC_MIN_DIRECTIONAL_EFFICIENCY = 0.30
EXEC_MIN_BREAKOUT_FOLLOW_THROUGH = 0.40
EXEC_MIN_TREND_STABILITY = 0.55
EXEC_MIN_ABS_VWAP_SLOPE = 0.005
EXEC_MIN_ABS_EMA_SLOPE = 0.005
EXEC_MAX_FAILED_BREAKOUTS = 1
EXEC_MIN_CONTINUATION_QUALITY = 45

# ─── Confidence Scoring Weights ──────────────────────────────────────────────
# Positive factors (max total: +14)
WEIGHT_EMA_TREND = 2           # Price on correct side + slope confirms
WEIGHT_VWAP_CONTROL = 2        # VWAP acceptance (sustained closes)
WEIGHT_VOLUME = 2              # Strong volume expansion
WEIGHT_CANDLE_QUALITY = 1      # Clean candle structure
WEIGHT_TREND_CONSISTENCY = 2   # Consecutive bars in trend
WEIGHT_ATR_EXPANSION = 1       # Expanding volatility
WEIGHT_HTF_ALIGNMENT = 2       # Higher timeframe agreement
WEIGHT_BREAKOUT_QUALITY = 2    # Clean swing break

# Negative factors (max total: -9)
PENALTY_SIDEWAYS = -3          # Market is choppy
PENALTY_LOW_VOL = -2           # Low volatility regime
PENALTY_CONFLICTING = -2       # EMA200 and VWAP disagree
PENALTY_REJECTION = -2         # Repeated failed breakouts

# ─── Confidence Thresholds ───────────────────────────────────────────────────
CONFIDENCE_TRADE_MIN = 60      # Minimum % to take a trade
GRADE_APLUS_MIN = 90           # A+ grade threshold
GRADE_A_MIN = 75               # A grade threshold
GRADE_B_MIN = 60               # B grade threshold
# Below B → Avoid
CONFIDENCE_MOMENTUM_LOOKBACK = 5
USE_ML_CALIBRATION = False     # Toggle explainable ML confidence calibration

# ─── Execution / Backtest Realism ─────────────────────────────────────────────
SLIPPAGE_BPS = 2.0             # Per side, basis points
SPREAD_BPS = 1.0               # Half-spread applied on entry and exit
MAX_CONSECUTIVE_LOSS_GUARD = 4 # Reduce risk after this many consecutive losses
RISK_REDUCTION_FACTOR = 0.6    # Risk scale after guard triggers

# ─── Backtest Parameters ─────────────────────────────────────────────────────
STOP_LOSS_ATR_MULT = 2.0       # Stop loss = entry ± ATR × this
TAKE_PROFIT_ATR_MULT = 3.0     # Take profit = entry ± ATR × this
INITIAL_CAPITAL = 100000       # Starting capital for backtest
RISK_PER_TRADE_PCT = 1.0       # % of capital risked per trade
