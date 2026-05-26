import { LineChart } from 'lucide-react';

export default function ConfidenceTimeline({ chartData = [] }) {
  const points = chartData
    .filter((d) => d.confidence_pct != null)
    .slice(-24)
    .map((d) => Math.max(0, Math.min(100, d.confidence_pct)));

  const spark = points.length
    ? points
        .map((p, i) => `${(i / Math.max(points.length - 1, 1)) * 100},${100 - p}`)
        .join(' ')
    : '';

  return (
    <section className="panel p-4">
      <div className="flex items-center gap-2 mb-3">
        <LineChart className="w-4 h-4 text-sky-300" />
        <h3 className="text-sm font-semibold tracking-wide">Dynamic Confidence Timeline</h3>
      </div>
      <div className="h-40 rounded-xl border border-slate-700/70 bg-slate-950/40 p-3">
        {spark ? (
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <defs>
              <linearGradient id="timelineStroke" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#4fb8ff" />
                <stop offset="100%" stopColor="#20ddb6" />
              </linearGradient>
            </defs>
            <polyline fill="none" stroke="url(#timelineStroke)" strokeWidth="2.4" points={spark} />
          </svg>
        ) : (
          <div className="h-full grid place-items-center text-slate-500 text-sm">No confidence points available</div>
        )}
      </div>
    </section>
  );
}
