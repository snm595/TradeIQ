import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { analyzeSymbol, backtestSymbol } from './utils/api';
import Header from './components/Header';
import PriceChart from './components/PriceChart';
import ConfidenceMeter from './components/ConfidenceMeter';
import RegimePanel from './components/RegimePanel';
import SignalExplainer from './components/SignalExplainer';
import BacktestStats from './components/BacktestStats';
import { Loader2 } from 'lucide-react';
import SidebarNav from './components/SidebarNav';
import MarketPulseBar from './components/MarketPulseBar';
import QuickStatsHud from './components/QuickStatsHud';
import ConfidenceTimeline from './components/ConfidenceTimeline';
import SignalHeatmap from './components/SignalHeatmap';
import AIAssistantPanel from './components/AIAssistantPanel';
import QuantLabsDashboard from './components/QuantLabsDashboard';
import LiveOpsPanel from './components/LiveOpsPanel';
import SignalTape from './components/SignalTape';

const REFRESH_INTERVALS = {
  '5m': 20000,
  '15m': 45000,
  '1h': 180000,
  '4h': 300000,
  '1d': 900000
};

const PERIOD_BY_TIMEFRAME = {
  '5m': '5d',
  '15m': '30d',
  '1h': '60d',
  '4h': '6mo',
  '1d': '1y'
};

const formatInterval = (ms) => {
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  return `${Math.round(ms / 60000)}m`;
};

function App() {
  const [ticker, setTicker] = useState('SPY');
  const [timeframe, setTimeframe] = useState('1d');
  const period = PERIOD_BY_TIMEFRAME[timeframe] ?? '1y';
  
  const [analysis, setAnalysis] = useState(null);
  const [backtest, setBacktest] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('pulse');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [nextRefreshAt, setNextRefreshAt] = useState(null);
  const [signalTape, setSignalTape] = useState([]);
  const [refreshInterval, setRefreshInterval] = useState(REFRESH_INTERVALS[timeframe]);
  const abortRef = useRef(null);
  const requestSeqRef = useRef(0);
  const backtestKeyRef = useRef('');
  const latestTapeKeyRef = useRef('');
  const hasAnalysisRef = useRef(false);

  const normalizedTicker = useMemo(() => ticker.trim().toUpperCase(), [ticker]);

  const handleTimeframeChange = useCallback((nextTimeframe) => {
    setTimeframe(nextTimeframe);
    setRefreshInterval(REFRESH_INTERVALS[nextTimeframe] ?? 180000);
  }, []);

  useEffect(() => {
    hasAnalysisRef.current = Boolean(analysis);
  }, [analysis]);

  const handleNavigate = (sectionId) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(sectionId);
    }
  };

  const recordSignalTape = useCallback((analysisData) => {
    const latestBar = analysisData.chart_data?.at(-1);
    const signal = analysisData.latest_signal;
    const time = latestBar?.time ?? signal?.timestamp ?? new Date().toISOString();
    const key = `${analysisData.ticker}|${analysisData.timeframe}|${time}|${signal?.signal}|${signal?.decision}|${signal?.confidence_pct}`;

    if (latestTapeKeyRef.current === key) return;
    latestTapeKeyRef.current = key;

    setSignalTape((items) => [
      {
        id: `${key}|${Date.now()}`,
        timestamp: time,
        ticker: analysisData.ticker,
        timeframe: analysisData.timeframe,
        regime: latestBar?.regime ?? analysisData.regime?.current_regime,
        signal: signal?.signal ?? latestBar?.signal ?? 'NONE',
        decision: signal?.decision ?? latestBar?.decision ?? 'WAIT',
        confidence: signal?.confidence_pct ?? latestBar?.confidence_pct ?? 0,
        warnings: signal?.warnings ?? [],
        continuation: latestBar?.continuation_quality_score ?? null
      },
      ...items
    ].slice(0, 24));
  }, []);

  const fetchData = useCallback(async ({ includeBacktest = false } = {}) => {
    if (!normalizedTicker) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = requestSeqRef.current + 1;
    requestSeqRef.current = requestId;

    const hasExistingAnalysis = hasAnalysisRef.current;
    setLoading((current) => current || !hasExistingAnalysis);
    setRefreshing(hasExistingAnalysis);
    setError(null);

    try {
      const analysisData = await analyzeSymbol(normalizedTicker, timeframe, period, { signal: controller.signal });
      if (requestSeqRef.current !== requestId) return;

      setAnalysis(analysisData);
      setLastUpdated(new Date());
      setNextRefreshAt(new Date(Date.now() + refreshInterval));
      recordSignalTape(analysisData);

      const backtestKey = `${normalizedTicker}|${timeframe}|${period}`;
      if (includeBacktest || backtestKeyRef.current !== backtestKey) {
        backtestKeyRef.current = backtestKey;
        const backtestData = await backtestSymbol(normalizedTicker, timeframe, period);
        if (requestSeqRef.current === requestId) {
          setBacktest(backtestData);
        }
      }
    } catch (err) {
      if (err.code === 'ERR_CANCELED') return;
      setError(err.response?.data?.detail || err.message || 'Failed to fetch data');
    } finally {
      if (requestSeqRef.current === requestId) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [normalizedTicker, timeframe, period, refreshInterval, recordSignalTape]);

  useEffect(() => {
    const debounce = window.setTimeout(() => {
      fetchData({ includeBacktest: true });
    }, 350);

    return () => {
      window.clearTimeout(debounce);
      abortRef.current?.abort();
    };
  }, [fetchData]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      fetchData();
    }, refreshInterval);

    return () => window.clearInterval(intervalId);
  }, [fetchData, refreshInterval]);

  const regimeClass = analysis?.regime?.current_regime ? `regime-${analysis.regime.current_regime}` : 'regime-neutral';

  return (
    <div className={`app-shell ${regimeClass}`}>
      <div className="ambient-backdrop" />
      <SidebarNav activeSection={activeSection} onNavigate={handleNavigate} />

      <main className="main-stage">
        <Header
          ticker={ticker}
          setTicker={setTicker}
          timeframe={timeframe}
          setTimeframe={handleTimeframeChange}
          onAnalyze={() => fetchData({ includeBacktest: true })}
          loading={loading}
          refreshing={refreshing}
          refreshInterval={refreshInterval}
          setRefreshInterval={setRefreshInterval}
          lastUpdated={lastUpdated}
          nextRefreshAt={nextRefreshAt}
        />

        <section id="pulse">
          <MarketPulseBar
            ticker={normalizedTicker}
            analysis={analysis}
            refreshing={refreshing}
            refreshLabel={formatInterval(refreshInterval)}
            lastUpdated={lastUpdated}
          />
        </section>

        {error && (
          <div className="error-banner">
            <div className="status-dot status-dot-danger" />
            {error}
          </div>
        )}

        <section id="market">
          <QuickStatsHud analysis={analysis} backtest={backtest} />
        </section>

        {loading && !analysis ? (
          <div className="loading-stage">
            <Loader2 className="w-12 h-12 text-sky-300 animate-spin mb-4" />
            <h2 className="text-2xl font-semibold tracking-tight text-slate-200">Calibrating Intelligence Engine</h2>
            <p className="text-slate-400 text-sm mt-2">Streaming market structure, confidence vectors, and execution profile...</p>
          </div>
        ) : analysis ? (
          <>
            <section id="ai" className="hero-grid">
              <div className="hero-chart-panel panel">
                <div className="panel-header">
                  <div>
                    <p className="panel-kicker">Market Structure Engine</p>
                    <h2 className="panel-title">{analysis.ticker} Multi-Factor Price Intelligence</h2>
                  </div>
                  <div className="price-chip">
                    <span className="status-dot status-dot-live" />
                    {analysis.current_price.toFixed(2)}
                  </div>
                </div>
                <div className="hero-chart-wrap">
                  <PriceChart data={analysis.chart_data} />
                </div>
              </div>

              <div className="hero-right-stack">
                <ConfidenceMeter signal={analysis.latest_signal} />
                <RegimePanel regime={analysis.regime} />
                <AIAssistantPanel signal={analysis.latest_signal} />
              </div>
            </section>

            <section className="ops-grid">
              <LiveOpsPanel analysis={analysis} lastUpdated={lastUpdated} refreshing={refreshing} />
              <SignalTape events={signalTape} />
            </section>

            <section className="intel-grid">
              <SignalExplainer signal={analysis.latest_signal} />
              <ConfidenceTimeline chartData={analysis.chart_data} />
              <SignalHeatmap chartData={analysis.chart_data} />
            </section>

            {backtest && (
              <section id="risk">
                <BacktestStats metrics={backtest.metrics} />
              </section>
            )}

            <section id="labs">
              <QuantLabsDashboard ticker={ticker} timeframe={timeframe} period={period} />
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}

export default App;
