import { Gauge, ShieldAlert, ShieldCheck, Shield } from 'lucide-react';
import { clsx } from 'clsx';

const getRiskIcon = (riskLevel) => {
  if (riskLevel === 'low') return <ShieldCheck className="w-4 h-4 text-green-500" />;
  if (riskLevel === 'moderate') return <Shield className="w-4 h-4 text-amber-500" />;
  if (riskLevel === 'high') return <ShieldAlert className="w-4 h-4 text-red-500" />;
  return <Shield className="w-4 h-4 text-slate-500" />;
};

export default function ConfidenceMeter({ signal }) {
  if (!signal) return null;

  const { confidence_pct, grade, risk_level } = signal;
  
  // Calculate stroke dasharray for the SVG arc
  const radius = 60;
  const circumference = radius * Math.PI; // Semi-circle
  const strokeDashoffset = circumference - (confidence_pct / 100) * circumference;

  let colorClass = 'text-slate-400';
  let strokeClass = 'stroke-slate-400';
  
  if (confidence_pct >= 80) {
    colorClass = 'text-green-500';
    strokeClass = 'stroke-green-500';
  } else if (confidence_pct >= 60) {
    colorClass = 'text-amber-500';
    strokeClass = 'stroke-amber-500';
  } else if (confidence_pct > 0) {
    colorClass = 'text-red-500';
    strokeClass = 'stroke-red-500';
  }

  return (
    <section className="panel p-5 flex flex-col items-center relative overflow-hidden">
      {/* Background glow */}
      <div className={clsx("absolute top-1 left-1/2 -translate-x-1/2 w-40 h-40 rounded-full blur-3xl opacity-20 pointer-events-none animate-pulse",
        confidence_pct >= 80 ? "bg-emerald-500" : confidence_pct >= 60 ? "bg-amber-500" : "bg-rose-500"
      )} />

      <div className="flex items-center gap-2 mb-2 self-start w-full">
        <Gauge className="w-5 h-5 text-sky-300" />
        <h3 className="font-semibold text-lg">System Confidence Core</h3>
      </div>

      <div className="relative w-48 h-24 mt-6 mb-2">
        <svg className="w-full h-full" viewBox="0 0 140 70">
          {/* Background Arc */}
          <path
            d="M 10 70 A 60 60 0 0 1 130 70"
            fill="none"
            stroke="rgba(70, 99, 138, 0.52)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Progress Arc */}
          <path
            d="M 10 70 A 60 60 0 0 1 130 70"
            fill="none"
            className={clsx("transition-all duration-1000 ease-out", strokeClass)}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        
        <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center">
          <span className={clsx("text-4xl font-black tracking-tighter", colorClass)}>
            {Math.round(confidence_pct)}%
          </span>
        </div>
      </div>

      <div className="flex w-full justify-between mt-4 p-3 bg-slate-900/45 rounded-xl border border-slate-700/70">
        <div className="flex flex-col">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Grade</span>
          <span className={clsx("text-xl font-bold", colorClass)}>{grade}</span>
        </div>
        
        <div className="h-full w-px bg-slate-700 mx-2" />
        
        <div className="flex flex-col items-end">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">Risk</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            {getRiskIcon(risk_level)}
            <span className="font-medium capitalize">{risk_level}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
