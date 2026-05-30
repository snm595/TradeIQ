import { BarChart3, TrendingUp, AlertTriangle, Target, Activity, ShieldCheck } from 'lucide-react';

const StatCard = ({ title, value, sub, icon: Icon, colorClass }) => (
  <div className="bg-slate-900/45 border border-slate-700/70 p-4 rounded-xl flex flex-col relative overflow-hidden group transition-transform duration-300 hover:-translate-y-1">
    <div className={`absolute -right-4 -top-4 w-16 h-16 rounded-full opacity-10 blur-xl ${colorClass} group-hover:opacity-20 transition-opacity`} />
    <div className="flex items-center gap-2 mb-3 text-muted-foreground">
      <Icon className="w-4 h-4" />
      <span className="text-sm font-medium">{title}</span>
    </div>
    <div className="flex items-end gap-2 mt-auto">
      <span className="text-2xl font-bold tracking-tight text-foreground">{value}</span>
      {sub && <span className="text-sm text-muted-foreground mb-1">{sub}</span>}
    </div>
  </div>
);

export default function BacktestStats({ metrics }) {
  if (!metrics) return null;

  const winRateColor = metrics.win_rate > 50 ? 'bg-green-500' : metrics.win_rate < 40 ? 'bg-red-500' : 'bg-amber-500';
  const pfColor = metrics.profit_factor > 1.5 ? 'bg-green-500' : metrics.profit_factor < 1.0 ? 'bg-red-500' : 'bg-amber-500';

  return (
    <section className="panel p-5 flex flex-col gap-6">
      <div className="flex items-center gap-2 border-b border-slate-700/50 pb-4">
        <BarChart3 className="w-5 h-5 text-cyan-300" />
        <h2 className="text-lg font-semibold tracking-tight">Strategy Performance (Backtest)</h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard 
          title="Win Rate" 
          value={`${metrics.win_rate}%`} 
          sub={`${metrics.wins}W / ${metrics.losses}L`}
          icon={Target}
          colorClass={winRateColor}
        />
        <StatCard 
          title="Profit Factor" 
          value={metrics.profit_factor} 
          icon={TrendingUp}
          colorClass={pfColor}
        />
        <StatCard 
          title="Sharpe Ratio" 
          value={metrics.sharpe_ratio} 
          icon={Activity}
          colorClass="bg-blue-500"
        />
        <StatCard 
          title="Max Drawdown" 
          value={`${metrics.max_drawdown_r}R`} 
          icon={AlertTriangle}
          colorClass="bg-red-500"
        />
        <StatCard 
          title="Avg R:R" 
          value={`${metrics.avg_rr}R`} 
          icon={BarChart3}
          colorClass="bg-primary"
        />
        <StatCard 
          title="Total PnL" 
          value={`${metrics.total_pnl_r}R`} 
          icon={ShieldCheck}
          colorClass={metrics.total_pnl_r > 0 ? 'bg-green-500' : 'bg-red-500'}
        />
      </div>

      <div className="bg-slate-900/30 rounded-lg p-4 flex items-center justify-between border border-slate-700/60">
        <div>
          <p className="text-sm text-muted-foreground mb-1">Signal Filtration</p>
          <div className="flex items-center gap-4 text-sm font-medium">
            <span>Total: <span className="text-foreground">{metrics.total_signals}</span></span>
            <span className="text-green-400">Taken: {metrics.trades_taken}</span>
            <span className="text-amber-500">Rejected: {metrics.trades_rejected}</span>
          </div>
        </div>
        
        <div className="text-right">
          <p className="text-sm text-muted-foreground mb-1">Filter Rate</p>
          <p className="text-lg font-bold text-primary">
            {metrics.total_signals > 0 
              ? `${Math.round((metrics.trades_rejected / metrics.total_signals) * 100)}%` 
              : '0%'}
          </p>
        </div>
      </div>
    </section>
  );
}
