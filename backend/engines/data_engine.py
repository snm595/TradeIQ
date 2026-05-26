"""
TradeIQ — Data Engine

Fetches OHLCV data using live providers only.
Primary: Yahoo Finance v8 API (query2, then query1 host fallback).
"""

import pandas as pd
import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# In-memory cache to avoid redundant API calls within a session
_cache: dict[str, pd.DataFrame] = {}

_YAHOO_ALLOWED_RANGES = {
    "1m": {"1d", "5d", "7d"},
    "2m": {"1d", "5d", "1mo", "3mo", "6mo", "60d"},
    "5m": {"1d", "5d", "1mo", "3mo", "6mo", "60d"},
    "15m": {"1d", "5d", "1mo", "3mo", "6mo", "60d"},
    "30m": {"1d", "5d", "1mo", "3mo", "6mo", "60d"},
    "60m": {"1mo", "3mo", "6mo", "1y", "2y"},
    "90m": {"1mo", "3mo", "6mo", "1y", "2y"},
    "1h": {"1mo", "3mo", "6mo", "1y", "2y"},
    "4h": {"1mo", "3mo", "6mo", "1y", "2y"},
    "1d": {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"},
}


def _cache_key(ticker: str, timeframe: str, period: str) -> str:
    """Generate a unique cache key."""
    return f"{ticker}|{timeframe}|{period}"


def _normalize_yahoo_request(timeframe: str, period: str) -> tuple[str, str]:
    """
    Normalize unsupported Yahoo interval/range combinations.
    Prevents 422 errors for intraday ranges like 15m + 1y.
    """
    allowed = _YAHOO_ALLOWED_RANGES.get(timeframe)
    if not allowed:
        return timeframe, period
    if period in allowed:
        return timeframe, period

    fallback_by_tf = {
        "1m": "7d",
        "2m": "60d",
        "5m": "60d",
        "15m": "60d",
        "30m": "60d",
        "60m": "1y",
        "90m": "1y",
        "1h": "1y",
        "4h": "2y",
        "1d": "1y",
    }
    return timeframe, fallback_by_tf.get(timeframe, period)


def _yahoo_interval_for_timeframe(timeframe: str) -> str:
    if timeframe == "1h":
        return "60m"
    if timeframe == "4h":
        return "60m"
    return timeframe


def _normalize_ohlcv(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Standardize and validate OHLCV frame."""
    if df.empty:
        raise ValueError(f"No data returned for {ticker}")

    df = df.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' for {ticker}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(subset=["open", "high", "low", "close"], inplace=True)
    df["volume"] = df["volume"].fillna(0).astype(float)
    df.sort_index(inplace=True)

    if df.empty:
        raise ValueError(f"No valid OHLC rows after cleaning for {ticker}")
    return df


def _fetch_yahoo(ticker: str, timeframe: str, period: str, host: str) -> pd.DataFrame:
    """Fetch OHLCV from Yahoo chart API host."""
    url = f"https://{host}/v8/finance/chart/{ticker}"
    params = {"interval": _yahoo_interval_for_timeframe(timeframe), "range": period, "includePrePost": "false"}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    result = data.get("chart", {}).get("result", [])
    if not result:
        raise ValueError(f"No chart data returned by Yahoo ({host})")

    chart_data = result[0]
    timestamps = chart_data.get("timestamp", [])
    if not timestamps:
        raise ValueError(f"No timestamps in Yahoo response ({host})")

    quote = chart_data.get("indicators", {}).get("quote", [{}])[0]
    df = pd.DataFrame(
        {
            "open": quote.get("open", []),
            "high": quote.get("high", []),
            "low": quote.get("low", []),
            "close": quote.get("close", []),
            "volume": quote.get("volume", []),
        },
        index=pd.to_datetime(timestamps, unit="s"),
    )
    df = _normalize_ohlcv(df, ticker)
    if timeframe == "4h":
        df = _resample_ohlcv(df, "4h", ticker)
    return df


def _resample_ohlcv(df: pd.DataFrame, rule: str, ticker: str) -> pd.DataFrame:
    resampled = df.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    return _normalize_ohlcv(resampled, ticker)


def fetch_ohlcv(
    ticker: str = "SPY",
    timeframe: str = "1h",
    period: str = "1y",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a given ticker/timeframe/period from Yahoo only.
    """
    timeframe, normalized_period = _normalize_yahoo_request(timeframe, period)
    key = _cache_key(ticker, timeframe, normalized_period)

    if use_cache and key in _cache:
        logger.info("Cache hit for %s", key)
        return _cache[key].copy()

    if normalized_period != period:
        logger.info(
            "Normalized unsupported range for %s: %s %s -> %s",
            ticker,
            timeframe,
            period,
            normalized_period,
        )
    logger.info("Fetching live %s data: timeframe=%s, period=%s", ticker, timeframe, normalized_period)
    errors: list[str] = []
    df: Optional[pd.DataFrame] = None

    for host in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        try:
            df = _fetch_yahoo(ticker, timeframe, normalized_period, host)
            logger.info("Fetched %d bars for %s from Yahoo (%s)", len(df), ticker, host)
            break
        except Exception as e:
            msg = f"Yahoo {host} failed: {e}"
            logger.warning(msg)
            errors.append(msg)

    if df is None:
        raise ValueError(
            f"Live market data unavailable for {ticker} ({timeframe}, {period}). "
            f"Provider errors: {' | '.join(errors)}"
        )

    # Cache the result
    if use_cache:
        _cache[key] = df.copy()

    logger.info("Fetched %d bars for %s", len(df), ticker)
    return df


def fetch_higher_timeframe(
    ticker: str = "SPY",
    period: str = "2y",
) -> Optional[pd.DataFrame]:
    """
    Fetch daily data for higher-timeframe alignment checks.
    Used by the confidence engine to confirm HTF trend.
    """
    try:
        return fetch_ohlcv(ticker, timeframe="1d", period=period)
    except Exception as e:
        logger.warning("Could not fetch HTF data for %s: %s", ticker, e)
        return None


def clear_cache():
    """Clear the in-memory data cache."""
    _cache.clear()
    logger.info("Data cache cleared")
