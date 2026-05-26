import { useState, useEffect } from 'react';
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

function App() {
  const [ticker, setTicker] = useState('SPY');
  const [timeframe, setTimeframe] = useState('1d');
  const [period, setPeriod] = useState('1y');
  
  const [analysis, setAnalysis] = useState(null);
  const [backtest, setBacktest] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('pulse');

  const handleNavigate = (sectionId) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(sectionId);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [analysisData, backtestData] = await Promise.all([
        analyzeSymbol(ticker, timeframe, period),
        backtestSymbol(ticker, timeframe, period)
      ]);
      setAnalysis(analysisData);
      setBacktest(backtestData);
    } catch (err) {
      setAnalysis(null);
      setBacktest(null);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchData();
  }, []); // eslint-disable-line

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
          setTimeframe={setTimeframe}
          onAnalyze={fetchData}
          loading={loading}
        />

        <section id="pulse">
          <MarketPulseBar ticker={ticker} analysis={analysis} />
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
