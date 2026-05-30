import { Globe, Radio, Zap } from 'lucide-react';

export default function MarketPulseBar({ ticker, analysis, refreshing, refreshLabel, lastUpdated }) {
  const regime = analysis?.regime?.current_regime?.replaceAll('_', ' ') ?? 'calibrating';
  const lastLabel = lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'pending';

  return (
    <section className="panel px-4 py-3 flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full border border-emerald-300/35 bg-emerald-400/10 grid place-items-center">
          <Radio className={`w-4 h-4 text-emerald-200 ${refreshing ? 'animate-pulse' : ''}`} />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Live Market Status</p>
          <p className="text-sm text-slate-200">{ticker} • {regime} • last sync {lastLabel}</p>
        </div>
      </div>
      <div className="flex items-center gap-5 text-sm">
        <span className="flex items-center gap-2 text-slate-300"><Zap className="w-4 h-4 text-sky-300" /> Auto cycle {refreshLabel}</span>
        <span className="flex items-center gap-2 text-slate-400"><Globe className="w-4 h-4" /> Execution window active</span>
      </div>
    </section>
  );
}
