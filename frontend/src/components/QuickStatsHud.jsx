import { Gauge, ShieldCheck, TrendingUp, TriangleAlert } from 'lucide-react';

const Stat = ({ label, value, icon: Icon, tone = 'text-slate-300' }) => (
  <div className="panel px-3 py-2 min-w-[130px]">
    <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500 mb-1">{label}</p>
    <div className="flex items-center gap-2">
      <Icon className={`w-4 h-4 ${tone}`} />
      <span className={`font-semibold ${tone}`}>{value}</span>
    </div>
  </div>
);

export default function QuickStatsHud({ analysis, backtest }) {
  const confidence = analysis?.latest_signal?.confidence_pct ?? 0;
  const pnl = backtest?.metrics?.total_pnl_r ?? 0;
  const trades = backtest?.metrics?.trades_taken ?? 0;
  const drawdown = backtest?.metrics?.max_drawdown_r ?? 0;

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      <Stat label="System Confidence" value={`${Math.round(confidence)}%`} icon={Gauge} tone="text-sky-200" />
      <Stat label="Taken Trades" value={trades} icon={ShieldCheck} tone="text-emerald-200" />
      <Stat label="Total PnL" value={`${pnl}R`} icon={TrendingUp} tone={pnl >= 0 ? 'text-emerald-200' : 'text-rose-200'} />
      <Stat label="Max Drawdown" value={`${drawdown}R`} icon={TriangleAlert} tone="text-amber-200" />
    </div>
  );
}
