import { Bot, Sparkles } from 'lucide-react';
import { referenceSummary } from '../utils/referenceLanguage';

export default function AIAssistantPanel({ signal }) {
  const reasons = signal?.reasons ?? [];
  const warnings = signal?.warnings ?? [];

  return (
    <section className="panel p-4 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-br from-cyan-300/6 to-transparent" />
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-200" />
          <h3 className="text-sm font-semibold tracking-wide">Floating AI Assistant</h3>
        </div>
        <Sparkles className="w-4 h-4 text-sky-300" />
      </div>
      <p className="text-sm text-slate-300 leading-relaxed">
        {referenceSummary(signal)}
      </p>
      {reasons[0] && <p className="text-xs text-slate-400 mt-2">Primary driver: {reasons[0]}</p>}
      {warnings[0] && (
        <p className="text-xs text-amber-300 mt-2">Risk monitor: {warnings[0]}</p>
      )}
    </section>
  );
}
