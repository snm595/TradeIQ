import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { 
  LineChart, 
  Activity, 
  ShieldAlert, 
  Sparkles, 
  FileText, 
  RefreshCw, 
  Check, 
  BrainCircuit, 
  Database,
  BarChart3
} from 'lucide-react';

const API_BASE = `${import.meta.env.VITE_API_URL}/api`;

export default function QuantLabsDashboard({ ticker = 'SPY', timeframe = '1d', period = '1y' }) {
  const [activeTab, setActiveTab] = useState('validation');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // States for API data
  const [validationData, setValidationData] = useState(null);
  const [forwardData, setForwardData] = useState(null);
  const [regimeData, setRegimeData] = useState(null);
  const [calibrationData, setCalibrationData] = useState(null);
  const [ablationData, setAblationData] = useState(null);
  const [runsList, setRunsList] = useState([]);
  
  // Controls
  const [reportGenerating, setReportGenerating] = useState(false);
  const [generatedReportPath, setGeneratedReportPath] = useState('');
  const [mlEnabled, setMlEnabled] = useState(false);

  const fetchTabData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'validation') {
        const res = await axios.get(`${API_BASE}/labs/long_horizon_validation`, {
          params: { ticker, timeframe, period: period === '1y' ? '10y' : period }
        });
        setValidationData(res.data);
        
        // Fetch completed experiment runs
        const runsRes = await axios.get(`${API_BASE}/labs/experiments`);
        setRunsList(runsRes.data.experiment_runs || []);
      } else if (activeTab === 'forward') {
        const res = await axios.get(`${API_BASE}/labs/forward_journal`, {
          params: { ticker, timeframe: timeframe === '1d' ? '15m' : timeframe, period: '60d' }
        });
        setForwardData(res.data);
      } else if (activeTab === 'regime') {
        const res = await axios.get(`${API_BASE}/labs/regime_diagnostics`, {
          params: { ticker, timeframe, period }
        });
        setRegimeData(res.data);
      } else if (activeTab === 'calibration') {
        const res = await axios.get(`${API_BASE}/labs/confidence_calibration`, {
          params: { ticker, timeframe, period }
        });
        setCalibrationData(res.data);
        setMlEnabled(res.data.ml_calibrator?.enabled || false);
        
        // Also fetch ablation report to show in the same screen
        const ablationRes = await axios.get(`${API_BASE}/labs/ablation_report`, {
          params: { ticker, timeframe, period }
        });
        setAblationData(ablationRes.data);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch quant labs metrics');
    } finally {
      setLoading(false);
    }
  }, [activeTab, ticker, timeframe, period]);

  // Load active tab data
  useEffect(() => {
    const timeoutId = window.setTimeout(fetchTabData, 0);
    return () => window.clearTimeout(timeoutId);
  }, [fetchTabData]);

  const handleGenerateReport = async (runId) => {
    setReportGenerating(true);
    setGeneratedReportPath('');
    try {
      const res = await axios.post(`${API_BASE}/labs/generate_report`, null, { params: { run_id: runId } });
      setGeneratedReportPath(res.data.report_path);
    } catch (err) {
      console.error(err);
      alert('Failed to generate audit report.');
    } finally {
      setReportGenerating(false);
    }
  };

  const handleToggleMl = async (checked) => {
    try {
      await axios.post(`${API_BASE}/labs/toggle_ml`, null, { params: { enabled: checked } });
      setMlEnabled(checked);
      // Reload tab to get refreshed calibrated confidence stats
      fetchTabData();
    } catch (err) {
      console.error(err);
      alert('Failed to toggle Machine Learning calibration.');
    }
  };

  return (
    <div className="panel p-5 relative overflow-hidden" id="labs-station">
      <div className="absolute top-0 right-0 w-64 h-64 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />
      
      {/* Station Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 pb-4 border-b border-slate-800/70">
        <div>
          <span className="panel-kicker text-sky-400 font-medium">TradeIQ Advanced Lab Suite</span>
          <h2 className="panel-title text-2xl font-bold tracking-tight text-white mt-1">Quantitative Research Workstation</h2>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-700/80 bg-slate-900/40 text-slate-300 text-xs">
          <Database className="w-3.5 h-3.5 text-sky-300" />
          <span>Feed: <strong className="text-white">Active Real-Time API Data</strong></span>
        </div>
      </div>

      {/* Tabs list */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-slate-800/50 pb-2">
        <button 
          onClick={() => setActiveTab('validation')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-all ${
            activeTab === 'validation' 
              ? 'bg-sky-500/15 border border-sky-400/40 text-sky-200 shadow-md shadow-sky-500/10' 
              : 'bg-slate-900/40 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          Long-Horizon Validation
        </button>
        <button 
          onClick={() => setActiveTab('forward')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-all ${
            activeTab === 'forward' 
              ? 'bg-sky-500/15 border border-sky-400/40 text-sky-200 shadow-md shadow-sky-500/10' 
              : 'bg-slate-900/40 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
          }`}
        >
          <LineChart className="w-3.5 h-3.5" />
          Forward Paper Simulation
        </button>
        <button 
          onClick={() => setActiveTab('regime')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-all ${
            activeTab === 'regime' 
              ? 'bg-sky-500/15 border border-sky-400/40 text-sky-200 shadow-md shadow-sky-500/10' 
              : 'bg-slate-900/40 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          Regime Transition Heatmap
        </button>
        <button 
          onClick={() => setActiveTab('calibration')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-all ${
            activeTab === 'calibration' 
              ? 'bg-sky-500/15 border border-sky-400/40 text-sky-200 shadow-md shadow-sky-500/10' 
              : 'bg-slate-900/40 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
          }`}
        >
          <BrainCircuit className="w-3.5 h-3.5" />
          Ablation & ML Calibration
        </button>
      </div>

      {error && (
        <div className="error-banner mb-6">
          <ShieldAlert className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center">
          <RefreshCw className="w-8 h-8 text-sky-400 animate-spin mb-3" />
          <p className="text-sm text-slate-400 tracking-wide">Syncing Advanced Labs Datasets...</p>
        </div>
      ) : (
        <div className="tab-stage mt-2">
          
          {/* TAB 1: Long-Horizon Validation */}
          {activeTab === 'validation' && validationData && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 flex flex-col gap-5">
                
                {/* CI Banner */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl border border-sky-500/20 bg-sky-500/5">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase tracking-wider text-slate-400">95% expectancy Confidence Interval</span>
                    <strong className="text-xl text-white font-bold tracking-tight mt-1">
                      {validationData.expectancy_ci_95?.[0]}R to {validationData.expectancy_ci_95?.[1]}R
                    </strong>
                    <span className="text-[11px] text-sky-300/80 mt-1 font-medium">Standard error normalized expectancy persistence</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase tracking-wider text-slate-400">95% winrate Confidence Interval</span>
                    <strong className="text-xl text-white font-bold tracking-tight mt-1">
                      {validationData.win_rate_ci_95?.[0]}% to {validationData.win_rate_ci_95?.[1]}%
                    </strong>
                    <span className="text-[11px] text-sky-300/80 mt-1 font-medium">Binomial proportion validation</span>
                  </div>
                </div>

                {/* Walk-Forward Runs */}
                <div className="panel p-4 bg-slate-900/30 border-slate-800">
                  <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">5-Period Walk-Forward Out-Of-Sample Validation</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-500 font-medium">
                          <th className="py-2.5">OOS Segment</th>
                          <th className="py-2.5 text-center">Trades</th>
                          <th className="py-2.5 text-center">Win Rate</th>
                          <th className="py-2.5 text-center">Net R</th>
                          <th className="py-2.5 text-center">Sharpe Ratio</th>
                          <th className="py-2.5 text-center">Max Drawdown</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {validationData.walk_forward_validation?.map((wf, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/10 text-slate-300">
                            <td className="py-2.5 font-medium text-slate-200">{wf.window}</td>
                            <td className="py-2.5 text-center">{wf.trades}</td>
                            <td className="py-2.5 text-center font-semibold text-emerald-400">{wf.win_rate.toFixed(1)}%</td>
                            <td className={`py-2.5 text-center font-bold ${wf.total_pnl_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {wf.total_pnl_r >= 0 ? '+' : ''}{wf.total_pnl_r.toFixed(2)}R
                            </td>
                            <td className="py-2.5 text-center text-sky-300 font-medium">{wf.sharpe_ratio.toFixed(2)}</td>
                            <td className="py-2.5 text-center text-rose-400">{wf.max_drawdown_r.toFixed(2)}R</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Regime Drift Analysis */}
                <div className="panel p-4 bg-slate-900/30 border-slate-800">
                  <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">Year-Over-Year Regime Drift Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {validationData.regime_drift?.map((drift, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-slate-800/60 bg-slate-950/40">
                        <strong className="text-sm font-bold text-white tracking-tight">{drift.year}</strong>
                        <div className="flex flex-col gap-1.5 mt-2 text-[11px]">
                          {Object.entries(drift.distribution).map(([reg, pct]) => {
                            if (pct === 0) return null;
                            return (
                              <div key={reg} className="flex justify-between items-center text-slate-400">
                                <span className="capitalize">{reg.replace('_', ' ')}</span>
                                <span className="font-semibold text-slate-200">{pct}%</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

              {/* Sidebar runs list */}
              <div className="flex flex-col gap-4">
                <div className="panel p-4 bg-slate-900/30 border-slate-800">
                  <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">Audited Experiment Snapshots</h3>
                  
                  {runsList.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No completed research runs saved yet.</p>
                  ) : (
                    <div className="flex flex-col gap-3 max-h-[420px] overflow-y-auto pr-1">
                      {runsList.map((run, idx) => (
                        <div key={idx} className="p-3 rounded-lg border border-slate-800 bg-slate-950/40 flex flex-col gap-2 hover:border-slate-700 transition-all">
                          <div className="flex justify-between items-center text-xs">
                            <span className="font-mono text-sky-400 font-bold">{run.run_id}</span>
                            <span className="text-[10px] text-slate-500">
                              {new Date(run.timestamp).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Target: {run.ticker} ({run.timeframe})</span>
                            <span className={`font-semibold ${run.validation_metrics.total_pnl_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {run.validation_metrics.total_pnl_r >= 0 ? '+' : ''}{run.validation_metrics.total_pnl_r.toFixed(1)}R
                            </span>
                          </div>
                          
                          <button
                            onClick={() => handleGenerateReport(run.run_id)}
                            className="mt-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-sky-500/10 hover:bg-sky-500/20 text-[10px] font-semibold uppercase tracking-wider text-sky-300 border border-sky-400/20 transition-all"
                            disabled={reportGenerating}
                          >
                            <FileText className="w-3 h-3" />
                            Generate Audit Report
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {generatedReportPath && (
                    <div className="mt-4 p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-xs text-emerald-300 flex items-start gap-2">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <strong className="font-semibold text-emerald-200 block">Report Audited Successfully</strong>
                        <span className="font-mono break-all text-[10px] text-slate-400 select-all block mt-1">
                          {generatedReportPath}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Forward Paper Simulation */}
          {activeTab === 'forward' && forwardData && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 flex flex-col gap-5">
                
                {/* Latency Hud */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Latency Execution</span>
                    <strong className="text-lg text-white font-bold mt-1 block">
                      {forwardData.latest_observation?.latest_signal?.latency_ms || 0} ms
                    </strong>
                    <span className="text-[10px] text-sky-400 mt-1 font-medium block">Latency slippage matched</span>
                  </div>
                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Simulated Slippage</span>
                    <strong className="text-lg text-rose-400 font-bold mt-1 block">
                      {forwardData.latest_observation?.latest_signal?.slippage_bps ? `+${forwardData.latest_observation.latest_signal.slippage_bps.toFixed(2)} bps` : '0.0 bps'}
                    </strong>
                    <span className="text-[10px] text-slate-500 mt-1 block">ATR matching slippage</span>
                  </div>
                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Forward Win Rate</span>
                    <strong className="text-lg text-emerald-400 font-bold mt-1 block">
                      {forwardData.latest_observation?.backtest_metrics?.win_rate.toFixed(1)}%
                    </strong>
                    <span className="text-[10px] text-slate-500 mt-1 block">Audit validation sample</span>
                  </div>
                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Audited Expectancy</span>
                    <strong className="text-lg text-white font-bold mt-1 block">
                      {forwardData.latest_observation?.backtest_metrics?.total_pnl_r >= 0 ? '+' : ''}{forwardData.latest_observation?.backtest_metrics?.total_pnl_r.toFixed(2)}R
                    </strong>
                    <span className="text-[10px] text-slate-500 mt-1 block">R-multiple profit total</span>
                  </div>
                </div>

                {/* MAE/MFE Excursion Replay */}
                <div className="panel p-4 bg-slate-900/30 border-slate-800">
                  <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">Maximum Adverse (MAE) & Favorable (MFE) Excursions</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-500 font-medium">
                          <th className="py-2">Entry Time</th>
                          <th className="py-2 text-center">Direction</th>
                          <th className="py-2 text-right">Entry Price</th>
                          <th className="py-2 text-right">Exit Price</th>
                          <th className="py-2 text-center">MAE (R)</th>
                          <th className="py-2 text-center">MFE (R)</th>
                          <th className="py-2 text-center">Outcome</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {forwardData.latest_observation?.backtest_metrics?.trades_list?.map((trade, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/10 text-slate-300">
                            <td className="py-2 font-mono text-slate-400">{new Date(trade.entry_time).toLocaleDateString()} {new Date(trade.entry_time).toLocaleTimeString()}</td>
                            <td className="py-2 text-center">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                trade.signal === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              }`}>
                                {trade.signal}
                              </span>
                            </td>
                            <td className="py-2 text-right font-medium">{trade.entry_price.toFixed(2)}</td>
                            <td className="py-2 text-right font-medium">{trade.exit_price.toFixed(2)}</td>
                            <td className="py-2 text-center text-rose-400 font-mono font-semibold">{trade.mae_r ? `${trade.mae_r}R` : '0R'}</td>
                            <td className="py-2 text-center text-emerald-400 font-mono font-semibold">{trade.mfe_r ? `${trade.mfe_r}R` : '0R'}</td>
                            <td className={`py-2 text-center font-bold ${trade.pnl_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {trade.pnl_r >= 0 ? '+' : ''}{trade.pnl_r.toFixed(1)}R
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>

              {/* Signal Logs timeline */}
              <div className="panel p-4 bg-slate-900/30 border-slate-800 flex flex-col gap-4">
                <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold">Live Forward Signal Observation logs</h3>
                <div className="flex flex-col gap-3 max-h-[480px] overflow-y-auto pr-1">
                  {forwardData.journal_history?.map((obs, idx) => (
                    <div key={idx} className="p-3 rounded-lg border border-slate-800 bg-slate-950/40 flex flex-col gap-2">
                      <div className="flex justify-between items-center text-[10px]">
                        <span className="text-slate-400 font-mono">{new Date(obs.logged_at).toLocaleTimeString()}</span>
                        <span className="text-[9px] uppercase font-bold text-sky-400 px-1.5 py-0.5 rounded border border-sky-400/20">
                          {obs.ticker}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-white">
                        <span>Price: <strong>${obs.close.toFixed(2)}</strong></span>
                        <span className="capitalize text-slate-300">Regime: {obs.regime?.replace('_', ' ')}</span>
                      </div>
                      
                      {obs.latest_observation?.latest_signal?.signal !== 'NO SIGNAL' ? (
                        <div className="mt-1 p-2 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
                          <span className={`font-bold ${obs.latest_observation?.latest_signal?.signal === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {obs.latest_observation?.latest_signal?.signal}
                          </span>{' '}
                          at {obs.latest_signal_time ? new Date(obs.latest_signal_time).toLocaleDateString() : ''} 
                          <span className="block mt-1 font-semibold text-slate-200">
                            Calibrated: {obs.latest_observation?.latest_signal?.confidence_pct}% ({obs.latest_observation?.latest_signal?.grade}) &rarr; {obs.latest_observation?.latest_signal?.decision}
                          </span>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-500 italic block mt-1">Observing structure — waiting for qualified continuation setup.</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* TAB 3: Regime Transition heatmap */}
          {activeTab === 'regime' && regimeData && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Markov Heatmap */}
              <div className="lg:col-span-2 panel p-4 bg-slate-900/30 border-slate-800">
                <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">Markov Regime Transition Probability Matrix</h3>
                <p className="text-[11px] text-slate-500 mb-4">Calculates year-to-year or state-to-state shift probability vector. Higher scores indicate persistent trend holding periods.</p>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-center border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-500 font-semibold">
                        <th className="py-2.5 text-left pl-3">From Regime</th>
                        {Object.keys(regimeData.transition_matrix || {}).map(state => (
                          <th key={state} className="py-2.5 text-[10px] capitalize max-w-[80px] truncate">{state.replace('_', ' ')}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30">
                      {Object.entries(regimeData.transition_matrix || {}).map(([fromState, transitions]) => (
                        <tr key={fromState} className="hover:bg-slate-800/10 text-slate-300">
                          <td className="py-3 text-left font-semibold text-slate-200 pl-3 capitalize text-[11px]">{fromState.replace('_', ' ')}</td>
                          {Object.entries(transitions).map(([toState, prob]) => {
                            // Map probability to opacity levels for a beautiful heatmap look
                            const bgOpacity = prob >= 0.6 ? 'bg-sky-500/30 text-sky-200 font-bold' :
                                              prob >= 0.3 ? 'bg-sky-500/15 text-slate-200 font-semibold' :
                                              prob >= 0.1 ? 'bg-sky-500/5 text-slate-400' : 'text-slate-600';
                            return (
                              <td key={toState} className={`py-3 ${bgOpacity} border border-slate-800/30 font-mono text-[11px]`}>
                                {(prob * 100).toFixed(0)}%
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Veto Contribution & Redundancy */}
              <div className="panel p-4 bg-slate-900/30 border-slate-800 flex flex-col gap-4">
                <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold">Veto Contribution Analytics</h3>
                <p className="text-[11px] text-slate-500">Number of potential trades rejected by each anti-chop filter on signal bars.</p>
                
                <div className="flex flex-col gap-3">
                  {Object.entries(regimeData.veto_analytics?.contributions || {}).map(([filter, count]) => {
                    const total = regimeData.veto_analytics?.total_rejected || 1;
                    const pct = Math.round((count / total) * 100);
                    return (
                      <div key={filter} className="flex flex-col gap-1 text-[11px]">
                        <div className="flex justify-between items-center text-slate-300">
                          <span className="capitalize">{filter.replace(/_/g, ' ')}</span>
                          <span className="font-semibold text-slate-200">{count} rejections ({pct}%)</span>
                        </div>
                        <div className="w-full bg-slate-800/60 rounded-full h-1.5 overflow-hidden">
                          <div className="bg-sky-400 h-full rounded-full" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          )}

          {/* TAB 4: Ablation & Calibration */}
          {activeTab === 'calibration' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Calibration reliability curve & Expectancy curves */}
              <div className="lg:col-span-2 flex flex-col gap-5">
                
                {/* ECE metrics */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Expected Calibration Error (ECE)</span>
                    <strong className="text-xl text-sky-400 font-bold mt-1 block">
                      {calibrationData?.calibration?.overall_calibration_error || 0.0}%
                    </strong>
                    <span className="text-[10px] text-slate-500 mt-1 block">Statistical deviation bounds</span>
                  </div>
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Confidence vs outcome Correlation</span>
                    <strong className="text-xl text-white font-bold mt-1 block">
                      {calibrationData?.calibration?.confidence_pnl_correlation || 0.0}
                    </strong>
                    <span className="text-[10px] text-slate-500 mt-1 block">Pearson correlation coefficient</span>
                  </div>
                </div>

                {/* Expectancy buckets */}
                <div className="panel p-4 bg-slate-900/30 border-slate-800">
                  <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">Expectancy curves by Confidence levels</h3>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {calibrationData?.calibration?.expectancy_by_confidence?.map((bucket, idx) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-950/40 text-center">
                        <span className="text-xs font-semibold text-slate-400 block">{bucket.bucket}</span>
                        <strong className={`text-lg font-bold mt-1 block ${bucket.avg_expectancy_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {bucket.avg_expectancy_r >= 0 ? '+' : ''}{bucket.avg_expectancy_r}R
                        </strong>
                        <span className="text-[10px] text-slate-500 block mt-1">{bucket.count} trades completed</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Factor Ablation variants list */}
                {ablationData && (
                  <div className="panel p-4 bg-slate-900/30 border-slate-800">
                    <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold mb-3">Systematic factor ablation contributions</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-500 font-medium">
                            <th className="py-2.5">Ablated Filter</th>
                            <th className="py-2.5 text-center">Trades Change</th>
                            <th className="py-2.5 text-center">Win Rate Shift</th>
                            <th className="py-2.5 text-center">PnL Shift (R)</th>
                            <th className="py-2.5 text-center">Sharpe Ratio Shift</th>
                            <th className="py-2.5 text-center">Drawdown Shift</th>
                            <th className="py-2.5 text-center">Regime Leakage</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                          {ablationData.marginal_contributions?.map((mc, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/10 text-slate-300">
                              <td className="py-2.5 font-medium text-slate-200 capitalize">{mc.filter_removed.replace(/_/g, ' ')}</td>
                              <td className="py-2.5 text-center text-sky-400 font-bold">{mc.trades_change > 0 ? '+' : ''}{mc.trades_change}</td>
                              <td className={`py-2.5 text-center font-semibold ${mc.win_rate_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {mc.win_rate_change >= 0 ? '+' : ''}{mc.win_rate_change}%
                              </td>
                              <td className={`py-2.5 text-center font-bold ${mc.pnl_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {mc.pnl_change >= 0 ? '+' : ''}{mc.pnl_change}R
                              </td>
                              <td className={`py-2.5 text-center ${mc.sharpe_change >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                                {mc.sharpe_change >= 0 ? '+' : ''}{mc.sharpe_change.toFixed(3)}
                              </td>
                              <td className="py-2.5 text-center text-rose-400">{mc.drawdown_change > 0 ? '+' : ''}{mc.drawdown_change.toFixed(1)}R</td>
                              <td className="py-2.5 text-center font-semibold text-rose-400">+{mc.regime_leakage_change}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

              </div>

              {/* Explainable ML Calibration */}
              <div className="panel p-4 bg-slate-900/30 border-slate-800 flex flex-col gap-5">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/50">
                  <h3 className="text-xs uppercase tracking-wider text-slate-300 font-semibold">Explainable ML Calibration</h3>
                  
                  {/* Toggle */}
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={mlEnabled} 
                      onChange={(e) => handleToggleMl(e.target.checked)}
                      className="sr-only peer" 
                    />
                    <div className="w-9 h-5 bg-slate-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-500 peer-checked:after:bg-white" />
                  </label>
                </div>

                <p className="text-[11px] text-slate-500">Calibrates the confidence scoring model dynamically using walk-forward RandomForest probabilities.</p>

                {calibrationData?.ml_calibrator?.enabled ? (
                  <div className="flex flex-col gap-5">
                    
                    {/* Ring metrics */}
                    <div className="grid grid-cols-2 gap-3 bg-slate-950/40 p-3 rounded-lg border border-slate-800/60 text-center">
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-slate-500 block">Baseline Win Rate</span>
                        <strong className="text-md text-slate-300 font-bold block mt-0.5">{calibrationData.ml_calibrator.base_rate}%</strong>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-slate-500 block">ML win Probability</span>
                        <strong className="text-md text-emerald-400 font-bold block mt-0.5">{calibrationData.ml_calibrator.win_probability}%</strong>
                      </div>
                    </div>

                    {/* Features contributions SHAP path */}
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-2.5">Calibrated Signal explainers (SHAP contributions)</span>
                      <div className="flex flex-col gap-2 max-h-[220px] overflow-y-auto pr-1">
                        {Object.entries(calibrationData.ml_calibrator.feature_contributions || {}).map(([feat, contrib]) => {
                          if (contrib === 0) return null;
                          return (
                            <div key={feat} className="flex justify-between items-center text-[10px]">
                              <span className="capitalize text-slate-400 truncate max-w-[140px]">{feat.replace(/_/g, ' ')}</span>
                              <span className={`font-mono font-bold ${contrib >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {contrib >= 0 ? '+' : ''}{contrib.toFixed(1)}%
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Importances */}
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-2">ML Feature importances</span>
                      <div className="flex flex-col gap-2 max-h-[160px] overflow-y-auto pr-1">
                        {Object.entries(calibrationData.ml_calibrator.feature_importances || {}).slice(0, 5).map(([feat, imp]) => {
                          const pct = Math.round(imp * 100);
                          return (
                            <div key={feat} className="flex flex-col gap-1 text-[10px]">
                              <div className="flex justify-between items-center text-slate-400">
                                <span className="capitalize">{feat.replace(/_/g, ' ')}</span>
                                <span className="font-semibold text-slate-300">{pct}%</span>
                              </div>
                              <div className="w-full bg-slate-800/40 rounded-full h-1 overflow-hidden">
                                <div className="bg-sky-400 h-full rounded-full" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                  </div>
                ) : (
                  <div className="py-12 flex flex-col items-center justify-center text-center p-3">
                    <Sparkles className="w-6 h-6 text-slate-500 mb-2" />
                    <p className="text-xs text-slate-400 font-medium">{calibrationData?.ml_calibrator?.message || 'Toggle ML above to trigger RandomForest out-of-sample calibration paths.'}</p>
                  </div>
                )}
              </div>

            </div>
          )}

        </div>
      )}
    </div>
  );
}
