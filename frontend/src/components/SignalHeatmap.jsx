import { Grid3X3 } from 'lucide-react';

export default function SignalHeatmap({ chartData = [] }) {
  const recent = chartData.slice(-48);
  const cells = recent.map((row, idx) => {
    if (!row.signal) return { key: idx, cls: 'bg-slate-800/60 border-slate-700/70' };
    if (row.signal === 'BUY') return { key: idx, cls: 'bg-emerald-400/30 border-emerald-300/50' };
    return { key: idx, cls: 'bg-rose-400/30 border-rose-300/50' };
  });

  return (
    <section className="panel p-4">
      <div className="flex items-center gap-2 mb-3">
        <Grid3X3 className="w-4 h-4 text-cyan-300" />
        <h3 className="text-sm font-semibold tracking-wide">Signal History Heatmap</h3>
      </div>
      <div className="grid grid-cols-12 gap-1.5">
        {cells.map((cell) => (
          <div key={cell.key} className={`h-4 rounded-sm border ${cell.cls}`} />
        ))}
      </div>
    </section>
  );
}
