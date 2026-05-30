import { CheckCircle2, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { clsx } from 'clsx';
import { buildReferenceChecklist, referenceSummary } from '../utils/referenceLanguage';

export default function SignalExplainer({ signal }) {
  if (!signal) return null;

  const { signal: dir, decision, reasons, warnings, timestamp, confidence_breakdown, market_narrative } = signal;
  const isBuy = dir === 'BUY';
  const isSell = dir === 'SELL';
  const isTrade = decision === 'TRADE';
  const checklist = buildReferenceChecklist(signal);

  return (
    <section className="panel p-5 flex flex-col h-full">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="font-semibold text-lg flex items-center gap-2">
            AI Trade Explanation Cards
          </h3>
          {timestamp && (
            <p className="text-xs text-muted-foreground mt-1">
              {new Date(timestamp).toLocaleString()}
            </p>
          )}
        </div>
        
        <div className={clsx(
          "px-4 py-1.5 rounded-full text-sm font-bold border shadow-sm",
          isTrade ? "bg-cyan-500/18 text-cyan-200 border-cyan-300/35" : "bg-slate-800 text-slate-300 border-slate-700"
        )}>
          {decision}
        </div>
      </div>

      {(isBuy || isSell) ? (
        <div className={clsx(
          "flex items-center gap-3 p-4 rounded-xl border mb-6",
          isBuy ? "bg-trade-buy" : "bg-trade-sell"
        )}>
          {isBuy ? <TrendingUp className="w-8 h-8" /> : <TrendingDown className="w-8 h-8" />}
          <div>
            <p className="text-xs uppercase font-bold tracking-wider opacity-80 mb-0.5">Detected Signal</p>
            <p className="text-xl font-black">{dir}</p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 p-4 rounded-xl border bg-slate-800/50 border-slate-700 text-slate-400 mb-6">
          <Minus className="w-8 h-8" />
          <div>
            <p className="text-xs uppercase font-bold tracking-wider opacity-80 mb-0.5">Current State</p>
            <p className="text-xl font-black">NO SIGNAL</p>
          </div>
        </div>
      )}

      <div className="mb-5 p-3 rounded-xl border border-slate-700/70 bg-slate-900/40">
        <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-2">Reference Confluence Grid</p>
        <div className="grid grid-cols-2 gap-2">
          {checklist.map((item) => (
            <div key={item.key} className="rounded-lg border border-slate-700/70 bg-slate-950/45 px-2 py-1.5">
              <p className="text-[11px] text-slate-300">{item.label}</p>
              <p className={clsx(
                'text-xs mt-0.5',
                item.status === 'pass' ? 'text-emerald-300' : item.status === 'block' ? 'text-rose-300' : 'text-amber-300'
              )}>
                {item.status === 'pass' ? item.good : item.bad}
              </p>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-3">{market_narrative || referenceSummary(signal)}</p>
        {confidence_breakdown && (
          <p className="text-[11px] text-cyan-200/90 mt-2">{confidence_breakdown}</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto pr-1 space-y-6">
        {reasons && reasons.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              Confluence Factors
            </h4>
            <ul className="space-y-2.5">
              {reasons.map((reason, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500/50 mt-1.5 shrink-0" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {warnings && warnings.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              Risk Factors
            </h4>
            <ul className="space-y-2.5">
              {warnings.map((warn, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500/50 mt-1.5 shrink-0" />
                  {warn}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function Minus({ className }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M5 12h14"/>
    </svg>
  );
}
