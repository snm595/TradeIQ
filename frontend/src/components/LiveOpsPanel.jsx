import { AlertTriangle, CheckCircle2, Radio, Shield, TrendingDown, TrendingUp } from 'lucide-react';
import { clsx } from 'clsx';

const pct = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return `${Math.round(Number(value))}%`;
};

const compact = (value) => String(value || 'unknown').replaceAll('_', ' ');

const getLatestBar = (analysis) => analysis?.chart_data?.at(-1) ?? {};

const getTradeState = (analysis) => {
  const signal = analysis?.latest_signal;
  const bar = getLatestBar(analysis);
  const direction = signal?.signal ?? bar.signal;
  const decision = signal?.decision ?? bar.decision;

  if (decision === 'TRADE' && direction === 'BUY') return { label: 'ACTIVE BUY', tone: 'buy', icon: TrendingUp };
  if (decision === 'TRADE' && direction === 'SELL') return { label: 'ACTIVE SELL', tone: 'sell', icon: TrendingDown };
  if (direction === 'BUY' || direction === 'SELL') return { label: 'WAITING FOR CONFIRMATION', tone: 'wait', icon: Radio };
  return { label: 'NO TRADE', tone: 'flat', icon: Shield };
};

const deriveVetoes = (analysis) => {
  const bar = getLatestBar(analysis);
  const warnings = analysis?.latest_signal?.warnings ?? [];
  const vetoes = [...warnings];

  if (analysis?.regime?.is_choppy || bar.is_choppy) vetoes.unshift('High chop environment');
  if (Number(bar.breakout_follow_through) < 0.45) vetoes.push('Breakout follow-through weak');
  if (Number(bar.continuation_quality_score) < 55) vetoes.push('Continuation quality below threshold');
  if (Number(bar.failed_breakout_count) > 0) vetoes.push(`${bar.failed_breakout_count} recent failed breakout${Number(bar.failed_breakout_count) === 1 ? '' : 's'}`);

  return [...new Set(vetoes)].slice(0, 5);
};

const getCondition = (analysis) => {
  const bar = getLatestBar(analysis);
  if (analysis?.regime?.is_choppy || bar.is_choppy) return 'NO TRADE - High Chop Environment';
  if (Number(bar.breakout_follow_through) < 0.45) return 'Breakout Follow-Through Weak';
  if (Number(bar.continuation_quality_score) >= 70) return 'Trend Persistence Strong';
  if (analysis?.latest_signal?.signal === 'BUY') return 'BUY Setup Forming';
  if (analysis?.latest_signal?.signal === 'SELL') return 'SELL Setup Forming';
  return 'Monitoring confirmation gates';
};

const Metric = ({ label, value, tone = 'text-slate-200' }) => (
  <div className="rounded-lg border border-slate-700/70 bg-slate-950/35 px-3 py-2">
    <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
    <p className={clsx('mt-1 text-sm font-semibold capitalize', tone)}>{value}</p>
  </div>
);

export default function LiveOpsPanel({ analysis, lastUpdated, refreshing }) {
  if (!analysis) return null;

  const bar = getLatestBar(analysis);
  const state = getTradeState(analysis);
  const StateIcon = state.icon;
  const vetoes = deriveVetoes(analysis);
  const drift = analysis.latest_signal?.confidence_momentum;
  const bias = Number(bar.close) >= Number(bar.ema_200) ? 'Bullish above EMA200' : 'Bearish below EMA200';
  const signalTime = analysis.latest_signal?.timestamp || bar.time;
  const signalAge = signalTime ? new Date(signalTime).toLocaleString() : 'No timestamp';

  return (
    <section className="panel p-5 live-ops-panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Operational Decision State</p>
          <h2 className="panel-title">Live Trade Eligibility</h2>
        </div>
        <span className={clsx('ops-state-chip', `ops-state-${state.tone}`)}>
          <StateIcon className="w-4 h-4" />
          {state.label}
        </span>
      </div>

      <div className="rounded-lg border border-slate-700/70 bg-slate-950/40 p-4 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Current condition</p>
            <p className="text-xl font-semibold text-slate-100 mt-1">{getCondition(analysis)}</p>
          </div>
          <div className="flex items-center gap-2 text-sm text-emerald-200">
            <Radio className={clsx('w-4 h-4', refreshing && 'animate-pulse')} />
            {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Synchronizing'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <Metric label="Regime" value={compact(analysis.regime?.current_regime)} tone="text-sky-200" />
        <Metric label="Confidence" value={pct(analysis.latest_signal?.confidence_pct)} tone="text-cyan-200" />
        <Metric label="Continuation" value={pct(bar.continuation_quality_score)} tone="text-emerald-200" />
        <Metric label="Chop Score" value={pct(Number(bar.chop_score) * 100)} tone={analysis.regime?.is_choppy ? 'text-rose-200' : 'text-slate-200'} />
        <Metric label="Trend Bias" value={bias} />
        <Metric label="Breakout State" value={Number(bar.breakout_follow_through) >= 0.55 ? 'Follow-through valid' : 'Follow-through weak'} />
        <Metric label="Trend Persistence" value={Number(bar.trend_stability) >= 0.55 ? 'Strong' : 'Unstable'} />
        <Metric label="Confidence Drift" value={drift === null || drift === undefined ? 'Neutral' : `${drift > 0 ? '+' : ''}${drift.toFixed(1)} pts`} />
      </div>

      <div className="mt-4 grid lg:grid-cols-[1fr_1.2fr] gap-3">
        <div className="rounded-lg border border-slate-700/70 bg-slate-950/35 p-3">
          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500 mb-2">Signal age</p>
          <p className="text-sm text-slate-200">{signalAge}</p>
        </div>
        <div className="rounded-lg border border-slate-700/70 bg-slate-950/35 p-3">
          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500 mb-2">Active vetoes</p>
          {vetoes.length ? (
            <div className="flex flex-wrap gap-2">
              {vetoes.map((veto) => (
                <span key={veto} className="inline-flex items-center gap-1 rounded-md border border-amber-300/25 bg-amber-400/10 px-2 py-1 text-xs text-amber-100">
                  <AlertTriangle className="w-3 h-3" />
                  {veto}
                </span>
              ))}
            </div>
          ) : (
            <span className="inline-flex items-center gap-1 text-sm text-emerald-200">
              <CheckCircle2 className="w-4 h-4" />
              No active vetoes
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
